#!/usr/bin/env python3
"""Trace course release readiness without enforcing publication."""

from __future__ import annotations

import argparse
import copy
import json
import posixpath
import runpy
from collections import Counter
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import unquote, urlsplit


REPORT_MODE = "report-only"
MANIFEST_PATH = "docs/migration/course-migration-manifest.json"
REGISTRY_PATH = "source-anchors.json"
SITE_ROOT_PATHS = ("index.html", "toc.html")
SITE_DIRECTORIES = ("lessons", "reference")
EXPECTED_INVENTORY_COUNTS = {
    "navigation": 2,
    "canonical-lesson": 105,
    "canonical-reference": 18,
    "compatibility": 46,
    "deprecation": 1,
}
EXPECTED_CANONICAL_COORDINATES = 105


def blocker(code: str, message: str, subject: str | None = None) -> dict[str, str]:
    result = {"code": code, "message": message}
    if subject is not None:
        result["subject"] = subject
    return result


class CourseHTMLParser(HTMLParser):
    """Collect only the HTML facts required by the release contract."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.ids: list[str] = []
        self.text_parts: list[str] = []
        self.tag_counts: dict[str, int] = {}
        self.lang: str | None = None
        self.metadata: dict[str, list[str | None]] = {}
        self.route_links: list[dict[str, str | None]] = []
        self.catalog_links: list[dict[str, str | None]] = []
        self.quizzes: list[dict[str, Any]] = []
        self._quiz_stack: list[dict[str, Any]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
        if tag == "html":
            self.lang = attributes.get("lang")
        elif tag == "meta":
            name = attributes.get("name")
            if name and name.startswith("course:"):
                self.metadata.setdefault(name, []).append(attributes.get("content"))
        identifier = attributes.get("id")
        if identifier:
            self.ids.append(identifier)
        if tag == "a":
            name = attributes.get("name")
            if name:
                self.ids.append(name)
            href = attributes.get("href")
            if href is not None:
                self.hrefs.append(href)
                route_role = attributes.get("data-route-role")
                route_id = attributes.get("data-route-id")
                if route_role is not None or route_id is not None:
                    self.route_links.append(
                        {"href": href, "role": route_role, "routeId": route_id}
                    )
                catalog_kind = attributes.get("data-catalog-kind")
                if catalog_kind is not None:
                    self.catalog_links.append({"href": href, "kind": catalog_kind})

        if tag == "div":
            for quiz in self._quiz_stack:
                quiz["depth"] += 1
            classes = (attributes.get("class") or "").split()
            if "quiz" in classes:
                self._quiz_stack.append(
                    {
                        "answer": attributes.get("data-answer"),
                        "buttons": 0,
                        "depth": 1,
                    }
                )
        elif tag == "button" and self._quiz_stack:
            self._quiz_stack[-1]["buttons"] += 1

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "div":
            return
        completed: list[dict[str, Any]] = []
        for quiz in self._quiz_stack:
            quiz["depth"] -= 1
            if quiz["depth"] == 0:
                completed.append(quiz)
        for quiz in completed:
            self._quiz_stack.remove(quiz)
            self.quizzes.append(
                {"answer": quiz["answer"], "buttons": quiz["buttons"]}
            )

    def close(self) -> None:
        super().close()
        for quiz in self._quiz_stack:
            self.quizzes.append(
                {"answer": quiz["answer"], "buttons": quiz["buttons"]}
            )
        self._quiz_stack.clear()


def collect_site_paths(repo_root: Path) -> set[str]:
    paths = {
        path
        for path in SITE_ROOT_PATHS
        if (repo_root / path).is_file()
    }
    for directory in SITE_DIRECTORIES:
        root = repo_root / directory
        if root.is_dir():
            paths.update(
                path.relative_to(repo_root).as_posix()
                for path in root.rglob("*.html")
                if path.is_file()
            )
    return paths


def parse_site_documents(
    repo_root: Path, paths: set[str]
) -> tuple[dict[str, CourseHTMLParser], list[dict[str, str]]]:
    documents: dict[str, CourseHTMLParser] = {}
    errors: list[dict[str, str]] = []
    for path in sorted(paths):
        parser = CourseHTMLParser()
        try:
            parser.feed((repo_root / path).read_text(encoding="utf-8"))
            parser.close()
        except (OSError, UnicodeError) as error:
            errors.append(blocker("html-load", str(error), path))
            continue
        documents[path] = parser
        duplicates = sorted(
            identifier
            for identifier in set(parser.ids)
            if parser.ids.count(identifier) > 1
        )
        if duplicates:
            errors.append(
                blocker(
                    "duplicate-fragment",
                    "duplicate id/name values: " + ", ".join(duplicates),
                    path,
                )
            )
    return documents, errors


def resolve_internal_href(source: str, href: str) -> tuple[str, str] | None:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or href.startswith("//"):
        return None
    raw_path = unquote(parsed.path)
    if raw_path == "":
        target = source
    elif raw_path.startswith("/"):
        target = raw_path.lstrip("/") or "index.html"
    else:
        target = posixpath.normpath(
            str(PurePosixPath(source).parent / PurePosixPath(raw_path))
        )
    if target == ".":
        target = "index.html"
    if target.endswith("/"):
        target += "index.html"
    if target == ".." or target.startswith("../"):
        return target, unquote(parsed.fragment)
    return PurePosixPath(target).as_posix(), unquote(parsed.fragment)


def validate_inventory(
    manifest: Any, actual_paths: set[str]
) -> list[dict[str, str]]:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("pages"), list):
        return [blocker("release-manifest", "manifest pages must be a list")]
    declared = {
        page.get("path")
        for page in manifest["pages"]
        if isinstance(page, dict) and isinstance(page.get("path"), str)
    }
    errors = []
    missing = sorted(declared - actual_paths)
    unexpected = sorted(actual_paths - declared)
    if missing:
        errors.append(
            blocker(
                "inventory-missing",
                f"{len(missing)} declared HTML pages are absent; first: "
                + ", ".join(missing[:5]),
            )
        )
    if unexpected:
        errors.append(
            blocker(
                "inventory-unexpected",
                f"{len(unexpected)} HTML pages are not declared; first: "
                + ", ".join(unexpected[:5]),
            )
        )
    return errors


def validate_inventory_contract(
    manifest: Any, actual_paths: set[str]
) -> list[dict[str, str]]:
    """Verify the exact T45 physical and classified inventory contract."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("pages"), list):
        return [blocker("release-manifest", "manifest pages must be a list")]
    pages = [page for page in manifest["pages"] if isinstance(page, dict)]
    errors: list[dict[str, str]] = []
    if len(actual_paths) != 172 or len(pages) != 172:
        errors.append(
            blocker(
                "inventory-page-count",
                "physical HTML and manifest inventories must each contain exactly 172 paths",
            )
        )
    counts = Counter(page.get("pageKind") for page in pages)
    if counts != Counter(EXPECTED_INVENTORY_COUNTS):
        errors.append(
            blocker(
                "inventory-classification",
                "inventory must be exactly 172 pages classified as "
                "2 navigation, 105 canonical lessons, 18 canonical references, "
                "46 compatibility entries, and 1 deprecation notice",
            )
        )

    coordinates = [
        page.get("canonicalCoordinate")
        for page in pages
        if page.get("pageKind") == "canonical-lesson"
    ]
    valid_coordinates = [
        coordinate for coordinate in coordinates if isinstance(coordinate, str)
    ]
    if (
        len(coordinates) != EXPECTED_CANONICAL_COORDINATES
        or len(valid_coordinates) != EXPECTED_CANONICAL_COORDINATES
        or len(set(valid_coordinates)) != EXPECTED_CANONICAL_COORDINATES
    ):
        errors.append(
            blocker(
                "inventory-coordinates",
                "canonical lesson inventory must expose 105 unique coordinates",
            )
        )

    return errors


TOC_SECTION_ANCHORS = {
    "start",
    "common-foundation",
    "task-routes",
    "extensions",
    "toolbox",
    "phase-catalog",
    "references",
}


def validate_route_first_toc(
    manifest: Any, documents: dict[str, CourseHTMLParser]
) -> list[dict[str, str]]:
    """Verify the learner-visible route catalog against the manifest graph."""
    if not isinstance(manifest, dict):
        return [blocker("toc-manifest", "manifest must be an object", "toc.html")]
    routes = manifest.get("routes")
    phases = manifest.get("phaseCatalog")
    pages = manifest.get("pages")
    if not isinstance(routes, list) or not isinstance(phases, list) or not isinstance(pages, list):
        return []
    document = documents.get("toc.html")
    if document is None:
        return [blocker("toc-missing", "route-first TOC is absent", "toc.html")]

    errors: list[dict[str, str]] = []
    required_anchors = set(TOC_SECTION_ANCHORS)
    required_anchors.update(
        toc_return.get("fragment")
        for route in routes
        if isinstance(route, dict)
        and isinstance((toc_return := route.get("tocReturn")), dict)
        and isinstance(toc_return.get("fragment"), str)
    )
    missing_anchors = sorted(required_anchors - set(document.ids))
    if missing_anchors:
        errors.append(
            blocker(
                "toc-section-anchors",
                "missing route catalog anchors: " + ", ".join(missing_anchors),
                "toc.html",
            )
        )

    linked_identities = document_link_identities("toc.html", document)
    linked_paths = {path for path, _fragment in linked_identities}
    canonical_lessons = {
        page.get("path")
        for page in pages
        if isinstance(page, dict) and page.get("pageKind") == "canonical-lesson"
    }
    canonical_references = {
        page.get("path")
        for page in pages
        if isinstance(page, dict) and page.get("pageKind") == "canonical-reference"
    }
    excluded = {
        page.get("path")
        for page in pages
        if isinstance(page, dict) and page.get("pageKind") in {"compatibility", "deprecation"}
    }
    catalog_lessons = Counter()
    catalog_references = Counter()
    for link in document.catalog_links:
        resolved = resolve_internal_href("toc.html", link.get("href") or "")
        if resolved is None:
            continue
        path, _fragment = resolved
        if link.get("kind") == "lesson":
            catalog_lessons[path] += 1
        elif link.get("kind") == "reference":
            catalog_references[path] += 1
    expected_lessons = Counter({path: 1 for path in canonical_lessons})
    expected_references = Counter({path: 1 for path in canonical_references})
    visible_excluded = sorted(excluded & linked_paths)
    if catalog_lessons != expected_lessons:
        missing_lessons = sorted(expected_lessons - catalog_lessons)
        duplicate_lessons = sorted(
            path for path, count in catalog_lessons.items() if count != 1
        )
        errors.append(
            blocker(
                "toc-canonical-lessons",
                "Phase catalog must list each of 105 canonical lessons exactly once; "
                f"missing {len(missing_lessons)}, duplicate-or-extra {len(duplicate_lessons)}",
                "toc.html",
            )
        )
    if catalog_references != expected_references:
        missing_references = sorted(expected_references - catalog_references)
        duplicate_references = sorted(
            path for path, count in catalog_references.items() if count != 1
        )
        errors.append(
            blocker(
                "toc-canonical-references",
                "References must list each of 18 canonical references exactly once; "
                f"missing {len(missing_references)}, duplicate-or-extra {len(duplicate_references)}",
                "toc.html",
            )
        )
    if visible_excluded:
        errors.append(
            blocker(
                "toc-compatibility-exclusion",
                "compatibility and deprecation paths must stay out of navigation: "
                + ", ".join(visible_excluded[:5]),
                "toc.html",
            )
        )

    semantic_links = set()
    for link in document.route_links:
        resolved = resolve_internal_href("toc.html", link.get("href") or "")
        if resolved is not None:
            path, fragment = resolved
            semantic_links.add(
                (link.get("routeId"), link.get("role"), (path, fragment or None))
            )
    expected_semantic_links = set()
    for route in routes:
        if not isinstance(route, dict) or not isinstance(route.get("id"), str):
            continue
        route_id = route["id"]
        expected: list[tuple[str, str, str | None]] = []
        entry = route.get("entry")
        if isinstance(entry, str):
            expected.append(("entry", entry, None))
        readiness = route.get("readiness")
        if isinstance(readiness, dict):
            expected.extend(
                ("readiness", target, None)
                for target in readiness.get("targets", [])
                if isinstance(target, str)
            )
        stop = route.get("stop")
        if isinstance(stop, str):
            expected.append(("stop", stop, None))
        for continuation in route.get("continuations", []):
            target = continuation.get("target") if isinstance(continuation, dict) else None
            if isinstance(target, dict) and isinstance(target.get("path"), str):
                expected.append(("continuation", target["path"], target.get("fragment")))
        for role, path, fragment in expected:
            identity = (path, fragment)
            semantic_identity = (route_id, role, identity)
            expected_semantic_links.add(semantic_identity)
            if semantic_identity not in semantic_links:
                errors.append(
                    blocker(
                        "toc-route-link",
                        f"{route_id} lacks {role} link to {path}"
                        + (f"#{fragment}" if fragment else ""),
                        "toc.html",
                    )
                )
    unexpected_semantic_links = sorted(
        semantic_links - expected_semantic_links,
        key=repr,
    )
    if unexpected_semantic_links:
        errors.append(
            blocker(
                "toc-route-link",
                "route-role links not declared by the manifest: "
                + ", ".join(repr(item) for item in unexpected_semantic_links[:5]),
                "toc.html",
            )
        )
    return errors


def validate_links_and_quizzes(
    repo_root: Path, documents: dict[str, CourseHTMLParser]
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for source, document in documents.items():
        for href in document.hrefs:
            resolved = resolve_internal_href(source, href)
            if resolved is None:
                continue
            target, fragment = resolved
            if (
                target == ".."
                or target.startswith("../")
                or not (repo_root / target).is_file()
            ):
                errors.append(
                    blocker("link-target-missing", f"{href!r} resolves to {target}", source)
                )
                continue
            if fragment and target.endswith(".html"):
                target_document = documents.get(target)
                if target_document is None or fragment not in target_document.ids:
                    errors.append(
                        blocker(
                            "link-fragment-missing",
                            f"{href!r} targets missing fragment {fragment!r}",
                            source,
                        )
                    )

        for index, quiz in enumerate(document.quizzes, start=1):
            answer = quiz["answer"]
            buttons = quiz["buttons"]
            try:
                answer_index = int(answer)
            except (TypeError, ValueError):
                errors.append(
                    blocker(
                        "quiz-answer-invalid",
                        "data-answer must be a zero-based integer",
                        f"{source} quiz {index}",
                    )
                )
                continue
            if buttons == 0 or answer_index < 0 or answer_index >= buttons:
                errors.append(
                    blocker(
                        "quiz-answer-range",
                        f"answer {answer_index} is outside {buttons} button choices",
                        f"{source} quiz {index}",
                    )
                )
    return errors


def authored_metadata(page: dict[str, Any]) -> dict[str, str]:
    memberships = page.get("routeMemberships")
    route_roles: list[str] = []
    if isinstance(memberships, list):
        route_roles = sorted(
            f"{membership['routeId']}:{role}"
            for membership in memberships
            if isinstance(membership, dict)
            and isinstance(membership.get("routeId"), str)
            and isinstance(membership.get("roles"), list)
            for role in membership["roles"]
            if isinstance(role, str)
        )
    dependencies = page.get("sourceDependencies")
    anchor_ids = (
        sorted(dependencies.get("anchorIds", []))
        if isinstance(dependencies, dict)
        and isinstance(dependencies.get("anchorIds"), list)
        else []
    )
    metadata = {
        "course:canonical-coordinate": page.get("canonicalCoordinate")
        or "not-applicable",
        "course:page-kind": page.get("pageKind", ""),
        "course:route-roles": ",".join(route_roles) or "not-applicable",
        "course:source-ids": ",".join(anchor_ids) or "not-applicable",
    }
    if page.get("pageKind") == "compatibility":
        disposition = page.get("contentDisposition")
        compatibility = page.get("compatibility")
        metadata.update(
            {
                "course:legacy-identity": page.get("expectedIdentity", ""),
                "course:transition-reason": disposition.get("blueprint", "")
                if isinstance(disposition, dict)
                else "",
                "course:evidence-carryover": page.get("evidenceCarryover", ""),
                "course:transition-mode": compatibility.get("mode", "")
                if isinstance(compatibility, dict)
                else "",
            }
        )
    elif page.get("pageKind") == "deprecation":
        deprecation = page.get("deprecation")
        metadata.update(
            {
                "course:legacy-identity": page.get("expectedIdentity", ""),
                "course:retirement-reason": deprecation.get("reason", "")
                if isinstance(deprecation, dict)
                else "",
                "course:retirement-effective": deprecation.get("effective", "")
                if isinstance(deprecation, dict)
                else "",
                "course:evidence-carryover": page.get("evidenceCarryover", ""),
            }
        )
    return metadata


def validate_authored_pages(
    manifest: Any,
    documents: dict[str, CourseHTMLParser],
    *,
    required_paths: set[str],
) -> list[dict[str, str]]:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("pages"), list):
        return [blocker("release-manifest", "manifest pages must be a list")]
    pages = {
        page.get("path"): page
        for page in manifest["pages"]
        if isinstance(page, dict) and isinstance(page.get("path"), str)
    }
    errors: list[dict[str, str]] = []
    for path in sorted(required_paths):
        page = pages.get(path)
        if page is None:
            errors.append(blocker("authored-path", "path is absent from manifest", path))
            continue
        if page.get("migrationStatus") != "authored":
            errors.append(
                blocker(
                    "authored-status",
                    "required authored page must have migrationStatus=authored",
                    path,
                )
            )
        document = documents.get(path)
        if document is None:
            errors.append(blocker("authored-page-missing", "HTML page is absent", path))
            continue
        if document.lang != "zh-Hant":
            errors.append(
                blocker("page-language", "html lang must be zh-Hant", path)
            )
        for name, expected in authored_metadata(page).items():
            actual = document.metadata.get(name, [])
            if actual != [expected]:
                errors.append(
                    blocker(
                        "page-metadata",
                        f"{name} must appear exactly once with content {expected!r}",
                        path,
                    )
                )
    return errors


def document_link_identities(
    source: str, document: CourseHTMLParser
) -> set[tuple[str, str | None]]:
    identities = set()
    for href in document.hrefs:
        resolved = resolve_internal_href(source, href)
        if resolved is not None:
            path, fragment = resolved
            identities.add((path, fragment or None))
    return identities


def validate_compatibility_graph(
    manifest: Any, documents: dict[str, CourseHTMLParser]
) -> list[dict[str, str]]:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("pages"), list):
        return [blocker("release-manifest", "manifest pages must be a list")]
    pages = [page for page in manifest["pages"] if isinstance(page, dict)]
    by_path = {
        page["path"]: page
        for page in pages
        if isinstance(page.get("path"), str)
    }
    errors: list[dict[str, str]] = []
    for page in pages:
        path = page.get("path")
        if not isinstance(path, str) or path not in documents:
            continue
        kind = page.get("pageKind")
        if kind == "compatibility":
            contract = page.get("compatibility")
            targets = contract.get("finalTargets") if isinstance(contract, dict) else None
            code = "compatibility-target"
        elif kind == "deprecation":
            contract = page.get("deprecation")
            targets = contract.get("successorTargets") if isinstance(contract, dict) else None
            code = "deprecation-target"
        else:
            continue
        if not isinstance(targets, list):
            errors.append(blocker(code, "target list is missing", path))
            continue
        if kind == "compatibility" and page.get("migrationStatus") == "authored":
            visible_text = " ".join(documents[path].text_parts)
            expected_identity = page.get("expectedIdentity")
            if (
                not isinstance(expected_identity, str)
                or expected_identity not in visible_text
            ):
                errors.append(
                    blocker(
                        "compatibility-identity",
                        "authored transition must show its stable legacy identity",
                        path,
                    )
                )
            if "轉接原因" not in visible_text:
                errors.append(
                    blocker(
                        "compatibility-reason",
                        "authored transition must show a learner-visible transition reason",
                        path,
                    )
                )
            if (
                "Evidence carryover" not in visible_text
                or "Lesson practiced" not in visible_text
            ):
                errors.append(
                    blocker(
                        "evidence-carryover",
                        "authored transition must explain conservative Evidence carryover",
                        path,
                    )
                )
            if (
                isinstance(contract, dict)
                and contract.get("mode") == "transition"
                and "何時選" not in visible_text
            ):
                errors.append(
                    blocker(
                        "compatibility-guidance",
                        "split transition must explain when to choose each final target",
                        path,
                    )
                )
            if documents[path].tag_counts.get("footer", 0):
                errors.append(
                    blocker(
                        "compatibility-exclusion",
                        "Compatibility entry must not render a lesson footer",
                        path,
                    )
                )
        if kind == "deprecation" and page.get("migrationStatus") == "authored":
            visible_text = " ".join(documents[path].text_parts)
            expected_identity = page.get("expectedIdentity")
            if (
                not isinstance(expected_identity, str)
                or expected_identity not in visible_text
            ):
                errors.append(
                    blocker(
                        "deprecation-identity",
                        "authored retirement must show its stable legacy identity",
                        path,
                    )
                )
            if "退役原因" not in visible_text or "生效點" not in visible_text:
                errors.append(
                    blocker(
                        "deprecation-reason",
                        "authored retirement must show its reason and effective point",
                        path,
                    )
                )
            if (
                "Evidence carryover" not in visible_text
                or "Lesson practiced" not in visible_text
                or "不會自動" not in visible_text
            ):
                errors.append(
                    blocker(
                        "deprecation-evidence",
                        "authored retirement must explain conservative Evidence carryover",
                        path,
                    )
                )
            if "不再把這個舊身份指派給其他內容" not in visible_text:
                errors.append(
                    blocker(
                        "deprecation-reuse",
                        "authored retirement must state that its identity is not reused",
                        path,
                    )
                )
            if documents[path].tag_counts.get("footer", 0):
                errors.append(
                    blocker(
                        "deprecation-exclusion",
                        "Deprecation notice must not render a lesson footer",
                        path,
                    )
                )
        actual_links = document_link_identities(path, documents[path])
        for target in targets:
            if not isinstance(target, dict):
                errors.append(blocker(code, "target must be an object", path))
                continue
            target_path = target.get("path")
            fragment = target.get("fragment")
            if not isinstance(target_path, str):
                errors.append(blocker(code, "target path is missing", path))
                continue
            target_page = by_path.get(target_path)
            if target_page and target_page.get("pageKind") in {"compatibility", "deprecation"}:
                errors.append(
                    blocker(
                        "compatibility-chain",
                        f"final target {target_path} is another redirect page",
                        path,
                    )
                )
            identity = (target_path, fragment if isinstance(fragment, str) else None)
            if identity not in actual_links:
                errors.append(
                    blocker(
                        code,
                        f"page does not link directly to {target_path}"
                        + (f"#{fragment}" if fragment else ""),
                        path,
                    )
                )
    return errors


def validate_site_release(
    repo_root: Path, manifest: Any, *, inventory_contract: bool = True
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    actual_paths = collect_site_paths(repo_root)
    documents, errors = parse_site_documents(repo_root, actual_paths)
    inventory_errors = validate_inventory(manifest, actual_paths)
    contract_errors = (
        validate_inventory_contract(manifest, actual_paths)
        if inventory_contract
        else []
    )
    link_quiz_errors = validate_links_and_quizzes(repo_root, documents)
    compatibility_errors = validate_compatibility_graph(manifest, documents)
    toc_errors = validate_route_first_toc(manifest, documents)
    authored_paths: set[str] = set()
    if isinstance(manifest, dict):
        authored_paths = {
            page.get("path")
            for page in manifest.get("pages", [])
            if isinstance(page, dict)
            and page.get("migrationStatus") == "authored"
            and isinstance(page.get("path"), str)
        }
    authored_errors = validate_authored_pages(
        manifest, documents, required_paths=authored_paths
    )
    pages = manifest.get("pages", []) if isinstance(manifest, dict) else []
    kind_counts = Counter(
        page.get("pageKind") for page in pages if isinstance(page, dict)
    )
    coordinates = {
        page.get("canonicalCoordinate")
        for page in pages
        if isinstance(page, dict)
        and page.get("pageKind") == "canonical-lesson"
        and isinstance(page.get("canonicalCoordinate"), str)
    }
    errors.extend(inventory_errors)
    errors.extend(contract_errors)
    errors.extend(link_quiz_errors)
    errors.extend(compatibility_errors)
    errors.extend(toc_errors)
    errors.extend(authored_errors)
    details = {
        "physicalHtmlPages": len(actual_paths),
        "declaredHtmlPages": len(pages),
        "classification": {
            kind: kind_counts.get(kind, 0) for kind in EXPECTED_INVENTORY_COUNTS
        },
        "uniqueCanonicalCoordinates": len(coordinates),
        "parsedHtmlPages": len(documents),
        "inventoryBlockers": len(inventory_errors),
        "inventoryContractBlockers": len(contract_errors),
        "linkOrQuizBlockers": len(link_quiz_errors),
        "compatibilityBlockers": len(compatibility_errors),
        "tocBlockers": len(toc_errors),
        "authoredPageBlockers": len(authored_errors),
    }
    return details, errors


def load_modules(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    scripts = repo_root / "scripts"
    return (
        runpy.run_path(str(scripts / "verify-migration-freeze.py")),
        runpy.run_path(str(scripts / "verify-migration-manifest.py")),
        runpy.run_path(str(scripts / "trace-source-registry.py")),
    )


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load {label}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def validate_report_only_modes(manifest: Any, registry: Any) -> list[dict[str, str]]:
    modes = {
        "manifest": manifest.get("publicationGateMode")
        if isinstance(manifest, dict)
        else None,
        "registry": registry.get("gateMode") if isinstance(registry, dict) else None,
    }
    if all(mode == REPORT_MODE for mode in modes.values()):
        return []
    return [
        blocker(
            "enforcement-mode",
            f"release inputs must remain report-only: {modes}",
        )
    ]


def report_only_exit_code(_report: dict[str, Any]) -> int:
    return 0


def error_matches_paths(error: dict[str, str], paths: set[str]) -> bool:
    subject = error.get("subject", "")
    return any(subject == path or subject.startswith(f"{path} ") for path in paths)


def build_authored_slice_report(
    repo_root: Path,
    *,
    required_paths: set[str],
    as_of: date,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "mode": REPORT_MODE,
        "scope": "authored-slice",
        "asOf": as_of.isoformat(),
        "releaseReady": False,
        "checks": {},
        "blockers": [],
    }
    errors: list[dict[str, str]] = report["blockers"]
    try:
        _freeze_module, manifest_module, source_module = load_modules(repo_root)
        freeze = manifest_module["load_validated_freeze"](repo_root)
        manifest = load_json(repo_root / MANIFEST_PATH, "migration manifest")
        registry = load_json(repo_root / REGISTRY_PATH, "Source registry")
    except Exception as error:
        errors.append(blocker("release-runtime", f"authority loading failed: {error}"))
        report["summary"] = {"blockers": len(errors)}
        return report

    manifest_errors = manifest_module["validate_manifest"](manifest, freeze)
    if not manifest_errors:
        manifest_errors = manifest_module["validate_thin_slice"](manifest)
    errors.extend(blocker("manifest-authority", error) for error in manifest_errors)

    actual_paths = collect_site_paths(repo_root)
    documents, parse_errors = parse_site_documents(repo_root, actual_paths)
    errors.extend(
        error
        for error in parse_errors
        if error_matches_paths(error, required_paths)
    )
    metadata_errors = validate_authored_pages(
        manifest, documents, required_paths=required_paths
    )
    link_quiz_errors = [
        error
        for error in validate_links_and_quizzes(repo_root, documents)
        if error_matches_paths(error, required_paths)
    ]
    compatibility_errors = [
        error
        for error in validate_compatibility_graph(manifest, documents)
        if error_matches_paths(error, required_paths)
    ]
    toc_errors = (
        validate_route_first_toc(manifest, documents)
        if "toc.html" in required_paths
        else []
    )
    errors.extend(metadata_errors)
    errors.extend(link_quiz_errors)
    errors.extend(compatibility_errors)
    errors.extend(toc_errors)

    source_report = source_module["trace_registry"](
        registry, manifest, as_of=as_of
    )
    manifest_pages = {
        page.get("path"): page
        for page in manifest.get("pages", [])
        if isinstance(page, dict) and isinstance(page.get("path"), str)
    }
    canonical_required_paths = sorted(
        path
        for path in required_paths
        if manifest_pages.get(path, {}).get("pageKind")
        in {"canonical-lesson", "canonical-reference", "navigation"}
    )
    if canonical_required_paths:
        source_module["trace_required_path_scope"](
            source_report, manifest, paths=canonical_required_paths
        )
    errors.extend(
        blocker(
            f"source-{error['code']}",
            error["message"],
            error.get("subject"),
        )
        for error in source_report["blockers"]
    )
    errors.extend(validate_report_only_modes(manifest, registry))
    report["checks"] = {
        "requiredPaths": len(required_paths),
        "presentPaths": sum(path in documents for path in required_paths),
        "metadataBlockers": len(metadata_errors),
        "linkOrQuizBlockers": len(link_quiz_errors),
        "compatibilityBlockers": len(compatibility_errors),
        "tocBlockers": len(toc_errors),
        "sourceTrace": source_report.get("summary", {}),
    }
    report["releaseReady"] = not errors
    report["summary"] = {
        "blockers": len(errors),
        "requiredPaths": len(required_paths),
    }
    return report


def build_release_report(repo_root: Path, *, as_of: date) -> dict[str, Any]:
    report: dict[str, Any] = {
        "mode": REPORT_MODE,
        "asOf": as_of.isoformat(),
        "releaseReady": False,
        "checks": {},
        "blockers": [],
    }
    errors: list[dict[str, str]] = report["blockers"]
    try:
        _freeze_module, manifest_module, source_module = load_modules(repo_root)
        freeze = manifest_module["load_validated_freeze"](repo_root)
        manifest = load_json(repo_root / MANIFEST_PATH, "migration manifest")
        registry = load_json(repo_root / REGISTRY_PATH, "Source registry")
    except Exception as error:
        errors.append(blocker("release-runtime", f"authority loading failed: {error}"))
        report["summary"] = {"blockers": len(errors)}
        return report

    manifest_errors = manifest_module["validate_manifest"](manifest, freeze)
    if not manifest_errors:
        manifest_errors = manifest_module["validate_thin_slice"](manifest)
    for error in manifest_errors:
        errors.append(blocker("manifest-authority", error))
    authority_status = "pass" if not manifest_errors else "blocked"
    for dimension in ("frozenInventories", "coordinates", "routes"):
        report["checks"][dimension] = {
            "status": authority_status,
            "authorityBlockers": len(manifest_errors),
        }

    site_details, site_errors = validate_site_release(repo_root, manifest)
    errors.extend(site_errors)
    report["checks"]["site"] = site_details

    source_report = source_module["trace_registry"](
        registry, manifest, as_of=as_of
    )
    for error in source_report["blockers"]:
        errors.append(
            blocker(
                f"source-{error['code']}",
                error["message"],
                error.get("subject"),
            )
        )
    coverage = registry.get("coverage")
    coverage_complete = isinstance(coverage, dict) and coverage.get("complete") is True
    pending_pages = sum(
        page.get("mappingState") == "pending-t03"
        for page in source_report.get("pages", [])
        if isinstance(page, dict)
    )
    if not coverage_complete:
        errors.append(
            blocker(
                "source-coverage-incomplete",
                f"Source inventory is not complete; {pending_pages} pages remain pending",
            )
        )
    report["checks"]["sourceIds"] = {
        "coverageComplete": coverage_complete,
        "pendingPages": pending_pages,
        "traceSummary": source_report.get("summary", {}),
    }

    gate_modes = {
        "manifest": manifest.get("publicationGateMode"),
        "registry": registry.get("gateMode"),
    }
    errors.extend(validate_report_only_modes(manifest, registry))
    report["checks"]["publicationGate"] = gate_modes
    report["releaseReady"] = not errors
    report["summary"] = {
        "blockers": len(errors),
        "physicalHtmlPages": site_details["physicalHtmlPages"],
        "declaredPages": len(manifest.get("pages", [])),
    }
    return report


def fixture_manifest() -> dict[str, Any]:
    def page(path: str, kind: str) -> dict[str, Any]:
        return {"path": path, "pageKind": kind}

    pages = [
        page("index.html", "navigation"),
        page("toc.html", "navigation"),
        page("lessons/001-0001-target.html", "canonical-lesson"),
        page("lessons/001-0002-old.html", "compatibility"),
        page("reference/retired.html", "deprecation"),
    ]
    pages[2].update(
        {
            "canonicalCoordinate": "001-0001",
            "migrationStatus": "authored",
            "routeMemberships": [
                {
                    "routeId": "common-foundation",
                    "roles": ["entry", "feedback", "tangible-win"],
                }
            ],
            "sourceDependencies": {
                "state": "registered",
                "anchorIds": ["fixture-source"],
            },
        }
    )
    pages[3]["compatibility"] = {
        "mode": "direct",
        "finalTargets": [
            {"path": "lessons/001-0001-target.html", "fragment": "target", "role": "successor"}
        ],
        "allowChain": False,
        "catalogExcluded": True,
        "navigationExcluded": True,
        "completionExcluded": True,
    }
    pages[3].update(
        {
            "expectedIdentity": "lessons/001-0002-old",
            "canonicalCoordinate": None,
            "migrationStatus": "authored",
            "routeMemberships": [],
            "contentDisposition": {"blueprint": "Move"},
            "evidenceCarryover": "lesson-practiced-unless-current-route-stop-is-revalidated",
            "sourceDependencies": {"state": "not-applicable", "anchorIds": []},
        }
    )
    pages[4]["deprecation"] = {
        "reason": "Retired fixture",
        "effective": "fixture-cutover",
        "successorTargets": [
            {"path": "lessons/001-0001-target.html", "fragment": None, "role": "successor"}
        ]
    }
    pages[4].update(
        {
            "expectedIdentity": "reference/retired",
            "canonicalCoordinate": None,
            "migrationStatus": "authored",
            "routeMemberships": [],
            "evidenceCarryover": "lesson-practiced-unless-current-route-stop-is-revalidated",
            "sourceDependencies": {"state": "not-applicable", "anchorIds": []},
        }
    )
    return {"publicationGateMode": REPORT_MODE, "pages": pages}


def write_fixture_site(root: Path) -> None:
    (root / "lessons").mkdir()
    (root / "reference").mkdir()
    (root / "index.html").write_text(
        '<a href="toc.html">TOC</a>', encoding="utf-8"
    )
    (root / "toc.html").write_text(
        '<a href="lessons/001-0001-target.html#target">Start</a>', encoding="utf-8"
    )
    (root / "lessons" / "001-0001-target.html").write_text(
        '<!doctype html><html lang="zh-Hant"><head>'
        '<meta name="course:canonical-coordinate" content="001-0001">'
        '<meta name="course:page-kind" content="canonical-lesson">'
        '<meta name="course:route-roles" '
        'content="common-foundation:entry,common-foundation:feedback,'
        'common-foundation:tangible-win">'
        '<meta name="course:source-ids" content="fixture-source">'
        '</head><body><h1 id="target">Target</h1>'
        '<div class="quiz" data-answer="1">'
        '<button>A</button><button>B</button></div></body></html>',
        encoding="utf-8",
    )
    (root / "lessons" / "001-0002-old.html").write_text(
        '<!doctype html><html lang="zh-Hant"><head>'
        '<meta name="course:canonical-coordinate" content="not-applicable">'
        '<meta name="course:page-kind" content="compatibility">'
        '<meta name="course:route-roles" content="not-applicable">'
        '<meta name="course:source-ids" content="not-applicable">'
        '<meta name="course:legacy-identity" content="lessons/001-0002-old">'
        '<meta name="course:transition-reason" content="Move">'
        '<meta name="course:evidence-carryover" '
        'content="lesson-practiced-unless-current-route-stop-is-revalidated">'
        '<meta name="course:transition-mode" content="direct">'
        '</head><body><h1>lessons/001-0002-old</h1>'
        '<p>轉接原因：內容已搬移。</p>'
        '<p>Evidence carryover：保留 Lesson practiced；current route stop 仍須重新驗證。</p>'
        '<a href="001-0001-target.html#target">Continue</a></body></html>',
        encoding="utf-8",
    )
    (root / "reference" / "retired.html").write_text(
        '<!doctype html><html lang="zh-Hant"><head>'
        '<meta name="course:canonical-coordinate" content="not-applicable">'
        '<meta name="course:page-kind" content="deprecation">'
        '<meta name="course:route-roles" content="not-applicable">'
        '<meta name="course:source-ids" content="not-applicable">'
        '<meta name="course:legacy-identity" content="reference/retired">'
        '<meta name="course:retirement-reason" content="Retired fixture">'
        '<meta name="course:retirement-effective" content="fixture-cutover">'
        '<meta name="course:evidence-carryover" '
        'content="lesson-practiced-unless-current-route-stop-is-revalidated">'
        '</head><body><h1>reference/retired</h1>'
        '<p>退役原因：fixture retired。生效點：fixture-cutover。</p>'
        '<p>Evidence carryover：保留 Lesson practiced；不會自動成為 current route evidence。</p>'
        '<p>此網址不再把這個舊身份指派給其他內容。</p>'
        '<a href="../lessons/001-0001-target.html">Successor</a></body></html>',
        encoding="utf-8",
    )


def assert_codes(errors: list[dict[str, str]], *expected: str) -> None:
    actual = {error["code"] for error in errors}
    missing = set(expected) - actual
    assert not missing, (missing, errors)


def run_site_self_test() -> None:
    manifest = fixture_manifest()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        write_fixture_site(root)
        _, errors = validate_site_release(root, manifest, inventory_contract=False)
        assert errors == [], errors
        documents, parse_errors = parse_site_documents(
            root, {"lessons/001-0001-target.html"}
        )
        assert parse_errors == [], parse_errors
        authored_errors = validate_authored_pages(
            manifest,
            documents,
            required_paths={"lessons/001-0001-target.html"},
        )
        assert authored_errors == [], authored_errors

        missing_transition_contract = copy.deepcopy(manifest)
        missing_transition_contract["pages"][3]["compatibility"]["mode"] = "transition"
        invalid_transition = CourseHTMLParser()
        invalid_transition.feed(
            '<html lang="zh-Hant"><body><a href="001-0001-target.html#target">'
            "Continue</a><footer>Legacy lesson navigation</footer></body></html>"
        )
        invalid_transition.close()
        transition_errors = validate_compatibility_graph(
            missing_transition_contract,
            {"lessons/001-0002-old.html": invalid_transition},
        )
        assert_codes(
            transition_errors,
            "compatibility-identity",
            "compatibility-reason",
            "evidence-carryover",
            "compatibility-guidance",
            "compatibility-exclusion",
        )

        invalid_deprecation = CourseHTMLParser()
        invalid_deprecation.feed(
            '<html lang="zh-Hant"><body>'
            '<a href="../lessons/001-0001-target.html">Successor</a>'
            '<footer>Retired lesson navigation</footer></body></html>'
        )
        invalid_deprecation.close()
        deprecation_errors = validate_compatibility_graph(
            manifest,
            {"reference/retired.html": invalid_deprecation},
        )
        assert_codes(
            deprecation_errors,
            "deprecation-identity",
            "deprecation-reason",
            "deprecation-evidence",
            "deprecation-reuse",
            "deprecation-exclusion",
        )

        invalid_document = CourseHTMLParser()
        invalid_document.feed(
            '<html lang="en"><head>'
            '<meta name="course:canonical-coordinate" content="999-9999">'
            '</head><body></body></html>'
        )
        invalid_document.close()
        authored_errors = validate_authored_pages(
            manifest,
            {"lessons/001-0001-target.html": invalid_document},
            required_paths={"lessons/001-0001-target.html"},
        )
        assert_codes(authored_errors, "page-language", "page-metadata")

        planned_manifest = copy.deepcopy(manifest)
        planned_manifest["pages"][2]["migrationStatus"] = "planned"
        authored_errors = validate_authored_pages(
            planned_manifest,
            documents,
            required_paths={"lessons/001-0001-target.html"},
        )
        assert_codes(authored_errors, "authored-status")

        authored_errors = validate_authored_pages(
            manifest,
            {},
            required_paths={"lessons/001-0001-target.html"},
        )
        assert_codes(authored_errors, "authored-page-missing")

        (root / "toc.html").write_text(
            '<a href="missing.html">Broken</a>'
            '<a href="lessons/001-0001-target.html#absent">Fragment</a>',
            encoding="utf-8",
        )
        (root / "lessons" / "001-0001-target.html").write_text(
            '<h1 id="target">Target</h1>'
            '<div class="quiz" data-answer="3"><button>A</button></div>',
            encoding="utf-8",
        )
        (root / "lessons" / "001-0002-old.html").write_text("No successor", encoding="utf-8")
        (root / "reference" / "retired.html").write_text("No successor", encoding="utf-8")
        (root / "reference" / "unexpected.html").write_text("Unexpected", encoding="utf-8")
        _, errors = validate_site_release(root, manifest, inventory_contract=False)
        assert_codes(
            errors,
            "inventory-unexpected",
            "link-target-missing",
            "link-fragment-missing",
            "quiz-answer-range",
            "compatibility-target",
            "deprecation-target",
        )

        (root / "lessons" / "001-0001-target.html").write_text(
            '<h1 id="target">Target</h1><div class="quiz" data-answer="bad">'
            '<button>A</button></div>',
            encoding="utf-8",
        )
        _, errors = validate_site_release(root, manifest, inventory_contract=False)
        assert_codes(errors, "quiz-answer-invalid")

        (root / "reference" / "unexpected.html").unlink()
        (root / "reference" / "retired.html").unlink()
        _, errors = validate_site_release(root, manifest, inventory_contract=False)
        assert_codes(errors, "inventory-missing")

        chained = copy.deepcopy(manifest)
        chained["pages"][2]["pageKind"] = "compatibility"
        (root / "lessons" / "001-0002-old.html").write_text(
            '<a href="001-0001-target.html#target">Continue</a>', encoding="utf-8"
        )
        _, errors = validate_site_release(root, chained, inventory_contract=False)
        assert_codes(errors, "compatibility-chain")


def run_self_test(repo_root: Path) -> None:
    run_site_self_test()
    freeze_module, manifest_module, source_module = load_modules(repo_root)
    freeze = manifest_module["load_validated_freeze"](repo_root)
    manifest = load_json(repo_root / MANIFEST_PATH, "migration manifest")
    assert freeze_module["run_self_test"](freeze, repo_root) == []
    assert manifest_module["run_self_test"](manifest, freeze) == []
    source_module["run_self_test"]()

    actual_paths = collect_site_paths(repo_root)
    assert validate_inventory_contract(manifest, actual_paths) == []

    documents, parse_errors = parse_site_documents(repo_root, actual_paths)
    assert parse_errors == [], parse_errors
    assert validate_route_first_toc(manifest, documents) == []

    toc_drift = copy.deepcopy(documents["toc.html"])
    toc_drift.ids.remove("start")
    removed_route_link = toc_drift.route_links.pop(0)
    removed_route_href = removed_route_link["href"]
    canonical_lesson = next(
        page["path"]
        for page in manifest["pages"]
        if page["pageKind"] == "canonical-lesson"
        and sum(
            resolve_internal_href("toc.html", href) == (page["path"], "")
            for href in toc_drift.hrefs
        )
        == 1
    )
    canonical_reference = next(
        page["path"]
        for page in manifest["pages"]
        if page["pageKind"] == "canonical-reference"
    )
    compatibility_path = next(
        page["path"]
        for page in manifest["pages"]
        if page["pageKind"] == "compatibility"
    )
    toc_drift.hrefs = [
        href
        for href in toc_drift.hrefs
        if resolve_internal_href("toc.html", href)[0]
        not in {canonical_lesson, canonical_reference}
    ]
    toc_drift.catalog_links = [
        link
        for link in toc_drift.catalog_links
        if resolve_internal_href("toc.html", link.get("href") or "")[0]
        not in {canonical_lesson, canonical_reference}
    ]
    toc_drift.hrefs.append(compatibility_path)
    assert_codes(
        validate_route_first_toc(manifest, {"toc.html": toc_drift}),
        "toc-section-anchors",
        "toc-canonical-lessons",
        "toc-canonical-references",
        "toc-compatibility-exclusion",
        "toc-route-link",
    )
    assert removed_route_href is not None

    duplicate_toc = copy.deepcopy(documents["toc.html"])
    duplicate_lesson = next(
        link for link in duplicate_toc.catalog_links if link.get("kind") == "lesson"
    )
    duplicate_reference = next(
        link for link in duplicate_toc.catalog_links if link.get("kind") == "reference"
    )
    duplicate_toc.catalog_links.extend([duplicate_lesson, duplicate_reference])
    assert_codes(
        validate_route_first_toc(manifest, {"toc.html": duplicate_toc}),
        "toc-canonical-lessons",
        "toc-canonical-references",
    )
    extra_route_link = copy.deepcopy(documents["toc.html"])
    extra_route_link.route_links.append(
        {
            "href": "lessons/001-0007-prove-code-readiness.html",
            "role": "stop",
            "routeId": "common-foundation",
        }
    )
    assert_codes(
        validate_route_first_toc(manifest, {"toc.html": extra_route_link}),
        "toc-route-link",
    )
    assert_codes(validate_route_first_toc(manifest, {}), "toc-missing")

    physical_count_drift = set(actual_paths)
    physical_count_drift.remove(next(iter(physical_count_drift)))
    assert_codes(
        validate_inventory_contract(manifest, physical_count_drift),
        "inventory-page-count",
    )

    path_union_drift = copy.deepcopy(manifest)
    path_union_drift["pages"][0]["path"] = "reference/not-in-physical-inventory.html"
    assert_codes(
        validate_inventory(path_union_drift, actual_paths),
        "inventory-missing",
        "inventory-unexpected",
    )

    classification_drift = copy.deepcopy(manifest)
    next(
        page
        for page in classification_drift["pages"]
        if page["pageKind"] == "canonical-reference"
    )["pageKind"] = "compatibility"
    assert_codes(
        validate_inventory_contract(classification_drift, actual_paths),
        "inventory-classification",
    )

    coordinate_drift = copy.deepcopy(manifest)
    lessons = [
        page
        for page in coordinate_drift["pages"]
        if page["pageKind"] == "canonical-lesson"
    ]
    lessons[1]["canonicalCoordinate"] = lessons[0]["canonicalCoordinate"]
    assert_codes(
        validate_inventory_contract(coordinate_drift, actual_paths),
        "inventory-coordinates",
    )

    invalid_coordinate = copy.deepcopy(manifest)
    next(
        page
        for page in invalid_coordinate["pages"]
        if page["pageKind"] == "canonical-lesson"
    )["canonicalCoordinate"] = {"invalid": "container"}
    assert_codes(
        validate_inventory_contract(invalid_coordinate, actual_paths),
        "inventory-coordinates",
    )

    registry, source_manifest = source_module["positive_fixture"]()
    missing_anchor = copy.deepcopy(source_manifest)
    missing_anchor["pages"][0]["sourceDependencies"]["anchorIds"] = ["missing-anchor"]
    source_report = source_module["trace_registry"](
        registry, missing_anchor, as_of=date(2026, 7, 16)
    )
    assert any(
        error["code"] == "page-anchor-missing"
        for error in source_report["blockers"]
    )
    enforced = copy.deepcopy(registry)
    enforced["gateMode"] = "enforced"
    enforced_report = source_module["trace_registry"](
        enforced, source_manifest, as_of=date(2026, 7, 16)
    )
    assert any(error["code"] == "gate-mode" for error in enforced_report["blockers"])
    assert_codes(validate_report_only_modes(source_manifest, enforced), "enforcement-mode")
    assert report_only_exit_code({"releaseReady": False}) == 0


def parse_as_of(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as error:
        raise argparse.ArgumentTypeError("must use YYYY-MM-DD") from error


def print_text_report(report: dict[str, Any]) -> None:
    status = "READY" if report["releaseReady"] else "BLOCKED"
    label = "AUTHORED SLICE" if report.get("scope") == "authored-slice" else "RELEASE"
    print(f"COURSE {label} TRACE {status} ({report['mode']})")
    if report.get("scope") == "authored-slice":
        checks = report.get("checks", {})
        print(
            "SUMMARY "
            f"required-paths={checks.get('requiredPaths', 0)} "
            f"present-paths={checks.get('presentPaths', 0)} "
            f"metadata-blockers={checks.get('metadataBlockers', 0)} "
            f"link-or-quiz-blockers={checks.get('linkOrQuizBlockers', 0)} "
            f"compatibility-blockers={checks.get('compatibilityBlockers', 0)}"
        )
    else:
        site = report.get("checks", {}).get("site", {})
        classification = site.get("classification", {})
        print(
            "INVENTORY "
            f"physical={site.get('physicalHtmlPages', 0)} "
            f"declared={site.get('declaredHtmlPages', 0)} "
            f"kinds={classification.get('navigation', 0)}/"
            f"{classification.get('canonical-lesson', 0)}/"
            f"{classification.get('canonical-reference', 0)}/"
            f"{classification.get('compatibility', 0)}/"
            f"{classification.get('deprecation', 0)} "
            f"unique-coordinates={site.get('uniqueCanonicalCoordinates', 0)}"
        )
    for error in report["blockers"]:
        subject = f" {error['subject']}" if error.get("subject") else ""
        print(f"BLOCKER [{error['code']}]{subject}: {error['message']}")
    print("PUBLICATION UNAFFECTED (report-only)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Trace all course release contracts without blocking publication"
    )
    parser.add_argument("--as-of", type=parse_as_of, default=date.today())
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--require-path",
        action="append",
        default=[],
        metavar="PATH",
        help="validate one authored canonical page without requiring full cutover inventory",
    )
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent

    if args.self_test:
        try:
            run_self_test(repo_root)
        except Exception as error:
            print(f"RELEASE VALIDATOR SELF-TEST FAIL: {type(error).__name__}: {error}")
            print("PUBLICATION UNAFFECTED (report-only)")
            return 1
        print("RELEASE VALIDATOR SELF-TEST PASS")
        print("POSITIVE THIN SLICE PASS")
        print("NEGATIVE STATE FIXTURES PASS")
        print("PUBLICATION UNAFFECTED (report-only)")
        return 0

    try:
        if args.require_path:
            report = build_authored_slice_report(
                repo_root,
                required_paths=set(args.require_path),
                as_of=args.as_of,
            )
        else:
            report = build_release_report(repo_root, as_of=args.as_of)
    except Exception as error:  # A report-only tracer must surface, not enforce, failures.
        report = {
            "mode": REPORT_MODE,
            "asOf": args.as_of.isoformat(),
            "releaseReady": False,
            "checks": {},
            "blockers": [blocker("release-runtime", f"unexpected tracer failure: {error}")],
            "summary": {"blockers": 1},
        }
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_text_report(report)
    return report_only_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
