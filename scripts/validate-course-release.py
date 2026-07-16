#!/usr/bin/env python3
"""Trace course release readiness without enforcing publication."""

from __future__ import annotations

import argparse
import copy
import json
import posixpath
import runpy
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
        self.quizzes: list[dict[str, Any]] = []
        self._quiz_stack: list[dict[str, Any]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
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
    repo_root: Path, manifest: Any
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    actual_paths = collect_site_paths(repo_root)
    documents, errors = parse_site_documents(repo_root, actual_paths)
    inventory_errors = validate_inventory(manifest, actual_paths)
    link_quiz_errors = validate_links_and_quizzes(repo_root, documents)
    compatibility_errors = validate_compatibility_graph(manifest, documents)
    errors.extend(inventory_errors)
    errors.extend(link_quiz_errors)
    errors.extend(compatibility_errors)
    details = {
        "physicalHtmlPages": len(actual_paths),
        "parsedHtmlPages": len(documents),
        "inventoryBlockers": len(inventory_errors),
        "linkOrQuizBlockers": len(link_quiz_errors),
        "compatibilityBlockers": len(compatibility_errors),
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
    pages[3]["compatibility"] = {
        "finalTargets": [
            {"path": "lessons/001-0001-target.html", "fragment": "target", "role": "successor"}
        ]
    }
    pages[4]["deprecation"] = {
        "successorTargets": [
            {"path": "lessons/001-0001-target.html", "fragment": None, "role": "successor"}
        ]
    }
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
        '<h1 id="target">Target</h1><div class="quiz" data-answer="1">'
        '<button>A</button><button>B</button></div>',
        encoding="utf-8",
    )
    (root / "lessons" / "001-0002-old.html").write_text(
        '<a href="001-0001-target.html#target">Continue</a>', encoding="utf-8"
    )
    (root / "reference" / "retired.html").write_text(
        '<a href="../lessons/001-0001-target.html">Successor</a>', encoding="utf-8"
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
        _, errors = validate_site_release(root, manifest)
        assert errors == [], errors

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
        _, errors = validate_site_release(root, manifest)
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
        _, errors = validate_site_release(root, manifest)
        assert_codes(errors, "quiz-answer-invalid")

        (root / "reference" / "unexpected.html").unlink()
        (root / "reference" / "retired.html").unlink()
        _, errors = validate_site_release(root, manifest)
        assert_codes(errors, "inventory-missing")

        chained = copy.deepcopy(manifest)
        chained["pages"][2]["pageKind"] = "compatibility"
        (root / "lessons" / "001-0002-old.html").write_text(
            '<a href="001-0001-target.html#target">Continue</a>', encoding="utf-8"
        )
        _, errors = validate_site_release(root, chained)
        assert_codes(errors, "compatibility-chain")


def run_self_test(repo_root: Path) -> None:
    run_site_self_test()
    freeze_module, manifest_module, source_module = load_modules(repo_root)
    freeze = manifest_module["load_validated_freeze"](repo_root)
    manifest = load_json(repo_root / MANIFEST_PATH, "migration manifest")
    assert freeze_module["run_self_test"](freeze, repo_root) == []
    assert manifest_module["run_self_test"](manifest, freeze) == []
    source_module["run_self_test"]()

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
    print(f"COURSE RELEASE TRACE {status} ({report['mode']})")
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
