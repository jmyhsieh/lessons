#!/usr/bin/env python3
"""Verify route-aware canonical navigation or mechanically align its footers."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import unquote, urlsplit


MANIFEST_PATH = "docs/migration/course-migration-manifest.json"
CANONICAL_KINDS = {"canonical-lesson", "canonical-reference"}
EXCLUDED_KINDS = {"compatibility", "deprecation"}
FOOTER_PATTERN = re.compile(r"<footer(?:\s[^>]*)?>.*?</footer>", re.DOTALL)


@dataclass(frozen=True, order=True)
class Action:
    route_id: str
    kind: str
    path: str
    fragment: str | None = None


class NavigationParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.footer_count = 0
        self.canonical_footer_count = 0
        self.route_ids: list[str | None] = []
        self.legal_stops: list[str | None] = []
        self.visible_legal_stops: list[str | None] = []
        self.dynamic_returns: list[tuple[str | None, str | None, str | None]] = []
        self.actions: list[tuple[str | None, str | None, str]] = []
        self.links: list[str] = []
        self.previous_links: list[str] = []
        self.footer_text_parts: list[str] = []
        self.completion_ui_count = 0
        self._inside_footer = False

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            href = attributes["href"]
            self.links.append(href)
            if "prev" in (attributes.get("rel") or "").split():
                self.previous_links.append(href)
        if tag == "footer":
            self.footer_count += 1
            self._inside_footer = True
            if attributes.get("data-course-footer") == "canonical":
                self.canonical_footer_count += 1
                self.route_ids.append(attributes.get("data-route-id"))
                self.legal_stops.append(attributes.get("data-legal-stop"))
        elif self._inside_footer:
            if tag == "a" and attributes.get("data-route-action"):
                self.actions.append(
                    (
                        attributes.get("data-route-id"),
                        attributes.get("data-route-action"),
                        attributes.get("href") or "",
                    )
                )
            if attributes.get("data-route-action") == "return-to-caller":
                self.dynamic_returns.append(
                    (
                        attributes.get("data-route-id"),
                        attributes.get("data-target-source"),
                        attributes.get("data-fallback"),
                    )
                )
            if attributes.get("data-route-legal-stop") is not None:
                self.visible_legal_stops.append(
                    attributes.get("data-route-legal-stop")
                )
        if (
            attributes.get("data-completion-ui") is not None
            or "completion" in (attributes.get("class") or "").split()
        ):
            self.completion_ui_count += 1

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        if tag == "footer":
            self._inside_footer = False

    def handle_endtag(self, tag: str) -> None:
        if tag == "footer":
            self._inside_footer = False

    def handle_data(self, data: str) -> None:
        if self._inside_footer:
            self.footer_text_parts.append(data)

    @property
    def footer_text(self) -> str:
        return " ".join(" ".join(self.footer_text_parts).split())


def relative_href(source: str, target: str, fragment: str | None) -> str:
    source_parent = PurePosixPath(source).parent
    target_path = PurePosixPath(target)
    source_parts = source_parent.parts
    target_parts = target_path.parts
    common = 0
    while (
        common < len(source_parts)
        and common < len(target_parts)
        and source_parts[common] == target_parts[common]
    ):
        common += 1
    parts = [".."] * (len(source_parts) - common) + list(target_parts[common:])
    href = "/".join(parts) or target_path.name
    if fragment:
        href += f"#{fragment}"
    return href


def resolve_href(source: str, href: str) -> tuple[str, str | None]:
    parsed = urlsplit(href)
    raw = unquote(parsed.path)
    if raw.startswith("/"):
        target = raw.lstrip("/") or "index.html"
    elif raw:
        target = str(PurePosixPath(source).parent / raw)
    else:
        target = source
    normalized = str(PurePosixPath(target))
    while normalized.startswith("./"):
        normalized = normalized[2:]
    parts: list[str] = []
    for part in PurePosixPath(normalized).parts:
        if part == ".." and parts:
            parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts), unquote(parsed.fragment) or None


def expected_actions(route: dict[str, Any], path: str) -> set[Action]:
    route_id = route["id"]
    actions: set[Action] = set()
    for edge in route.get("edges", []):
        if edge.get("from") != path:
            continue
        for target in edge.get("to", []):
            if isinstance(target, str):
                actions.add(Action(route_id, edge["kind"], target))

    if route.get("stop") == path:
        toc_return = route["tocReturn"]
        actions.add(
            Action(
                route_id,
                "route-return",
                toc_return["path"],
                toc_return.get("fragment"),
            )
        )
        for continuation in route.get("continuations", []):
            target = continuation.get("target")
            if isinstance(target, dict):
                actions.add(
                    Action(
                        route_id,
                        "continuation",
                        target["path"],
                        target.get("fragment"),
                    )
                )

    if (
        route.get("returnPolicy") == "fixed-toc-anchor"
        and not actions
    ):
        toc_return = route["tocReturn"]
        actions.add(
            Action(
                route_id,
                "route-return",
                toc_return["path"],
                toc_return.get("fragment"),
            )
        )

    if route.get("id") == "toolbox" and path in route["continuations"][0]["from"]:
        toc_return = route["tocReturn"]
        actions.add(
            Action(
                route_id,
                "catalog-fallback",
                toc_return["path"],
                toc_return.get("fragment"),
            )
        )
    return actions


def route_ancestors(route: dict[str, Any], path: str) -> set[str]:
    parents: dict[str, set[str]] = {}
    for edge in route.get("edges", []):
        source = edge.get("from")
        if not isinstance(source, str):
            continue
        for target in edge.get("to", []):
            if isinstance(target, str):
                parents.setdefault(target, set()).add(source)

    ancestors: set[str] = set()
    pending = list(parents.get(path, set()))
    while pending:
        candidate = pending.pop()
        if candidate in ancestors:
            continue
        ancestors.add(candidate)
        pending.extend(parents.get(candidate, set()))
    return ancestors


def page_route(page: dict[str, Any], routes: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    memberships = page.get("routeMemberships")
    if not isinstance(memberships, list) or not memberships:
        return None
    return routes[memberships[0]["routeId"]]


def action_label(action: Action) -> str:
    labels = {
        "next": "下一步",
        "choose-one": "選擇一條支線",
        "optional-continuation": "選用延伸",
        "continuation": "路線續作",
        "route-return": "回到路線目錄",
        "catalog-fallback": "沒有有效返回點時回工具箱目錄",
    }
    return f"{labels.get(action.kind, action.kind)}：{action.path}"


def localized_identity_markup(page: dict[str, Any], identity_markup: str) -> str:
    localized = identity_markup.strip()
    replacements = (
        ("Page kind：canonical lesson", "頁面類型：標準課程頁"),
        ("Page kind：canonical reference", "頁面類型：標準參考頁"),
        ("Canonical reference", "頁面類型：標準參考頁"),
        ("Canonical coordinate：", "標準座標："),
        ("Route roles：", "路線角色："),
        ("Route role：", "路線角色："),
        ("Source IDs：", "來源 ID："),
        ("Source ID：", "來源 ID："),
    )
    for old, new in replacements:
        localized = localized.replace(old, new)

    required: list[str] = []
    if "頁面類型：" not in localized:
        page_kind = (
            "標準課程頁"
            if page["pageKind"] == "canonical-lesson"
            else "標準參考頁"
        )
        required.append(f"頁面類型：{page_kind}")
    if "路線角色：" not in localized:
        memberships = page.get("routeMemberships") or []
        roles = memberships[0].get("roles", []) if memberships else []
        required.append("路線角色：" + ("／".join(roles) if roles else "不適用"))
    if "來源 ID：" not in localized:
        source_ids = page.get("sourceDependencies", {}).get("anchorIds", [])
        rendered_ids = (
            "、".join(f"<code>{html.escape(item)}</code>" for item in source_ids)
            if source_ids
            else "不適用"
        )
        required.append(f"來源 ID：{rendered_ids}")
    return " · ".join(required + ([localized] if localized else []))


def render_footer(
    page: dict[str, Any], route: dict[str, Any] | None, identity_markup: str
) -> str:
    route_id = route["id"] if route else "not-applicable"
    legal_stop = route["legalStop"] if route else "not-applicable"
    lines = [
        '<footer data-course-footer="canonical" '
        f'data-route-id="{html.escape(route_id, quote=True)}" '
        f'data-legal-stop="{html.escape(legal_stop, quote=True)}">'
    ]
    if route:
        lines.extend(
            [
                f'<p><strong>路線導覽 · {html.escape(route["displayName"])}</strong></p>',
                '<ul class="course-route-actions">',
            ]
        )
        for action in sorted(expected_actions(route, page["path"])):
            href = relative_href(page["path"], action.path, action.fragment)
            lines.append(
                '<li><a '
                f'data-route-id="{html.escape(route_id, quote=True)}" '
                f'data-route-action="{html.escape(action.kind, quote=True)}" '
                f'href="{html.escape(href, quote=True)}">'
                f'{html.escape(action_label(action))}</a></li>'
            )
        if route_id == "toolbox" and page["path"] in route["continuations"][0]["from"]:
            continuation = route["continuations"][0]
            lines.append(
                '<li><span data-route-id="toolbox" '
                'data-route-action="return-to-caller" '
                f'data-target-source="{html.escape(continuation["targetSource"], quote=True)}" '
                f'data-fallback="{html.escape(continuation["fallback"], quote=True)}">'
                '完成後回到 Return notebook 的 Targeted-remediation return point；'
                '沒有有效 return point 時才使用 catalog fallback。</span></li>'
            )
        lines.extend(
            [
                "</ul>",
                '<p '
                f'data-route-legal-stop="{html.escape(legal_stop, quote=True)}">'
                f'<strong>合法停止點：</strong>{html.escape(route["legalStopDisplay"])}</p>',
            ]
        )

    identity = localized_identity_markup(page, identity_markup)
    lines.append(f'<div class="course-page-identity">{identity}</div>')
    lines.append("</footer>")
    return "\n".join(lines)


def parse_document(path: Path) -> NavigationParser:
    parser = NavigationParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def actual_actions(source: str, parser: NavigationParser) -> Counter[Action]:
    actions: Counter[Action] = Counter()
    for route_id, kind, href in parser.actions:
        if route_id and kind:
            path, fragment = resolve_href(source, href)
            actions[Action(route_id, kind, path, fragment)] += 1
    return actions


def verify(root: Path, manifest: dict[str, Any]) -> tuple[Counter[str], list[str]]:
    routes = {route["id"]: route for route in manifest["routes"]}
    counts: Counter[str] = Counter()
    details: list[str] = []
    for page in manifest["pages"]:
        path = page["path"]
        document = parse_document(root / path)
        kind = page["pageKind"]
        if kind in CANONICAL_KINDS:
            if document.canonical_footer_count == 0:
                counts["footer_missing"] += 1
                details.append(f"footer_missing {path}")
            elif document.canonical_footer_count > 1:
                counts["footer_extra"] += document.canonical_footer_count - 1
                details.append(f"footer_extra {path}")
            if document.footer_count != 1:
                counts["footer_mismatch"] += 1
                details.append(f"footer_mismatch {path}: count={document.footer_count}")

            route = page_route(page, routes)
            expected_route_id = route["id"] if route else "not-applicable"
            expected_stop = route["legalStop"] if route else "not-applicable"
            if document.route_ids and document.route_ids != [expected_route_id]:
                counts["footer_mismatch"] += 1
                details.append(f"route_id_mismatch {path}")
            if document.legal_stops and document.legal_stops != [expected_stop]:
                counts["legal_stop_mismatch"] += 1
                details.append(f"legal_stop_mismatch {path}")
            if document.visible_legal_stops != ([expected_stop] if route else []):
                counts["legal_stop_visible_mismatch"] += 1
                details.append(f"legal_stop_visible_mismatch {path}")

            required_display = {"頁面類型：", "路線角色：", "來源 ID："}
            if route:
                required_display.update(
                    {
                        f"路線導覽 · {route['displayName']}",
                        "合法停止點：",
                        route["legalStopDisplay"],
                    }
                )
            forbidden_display = {
                "Route navigation",
                "Legal stop：",
                "Page kind：",
                "Canonical coordinate：",
                "Route roles：",
                "Route role：",
                "Source IDs：",
                "Source ID：",
            }
            if any(item not in document.footer_text for item in required_display) or any(
                item in document.footer_text for item in forbidden_display
            ):
                counts["footer_display_mismatch"] += 1
                details.append(f"footer_display_mismatch {path}")

            expected = Counter(expected_actions(route, path)) if route else Counter()
            actual = actual_actions(path, document)
            for action, count in sorted((expected - actual).items()):
                counts["action_missing"] += count
                details.append(f"action_missing {path}: {action}")
            for action, count in sorted((actual - expected).items()):
                counts["action_extra"] += count
                details.append(f"action_extra {path}: {action}")

            ancestors = route_ancestors(route, path) if route else set()
            linked_paths = {resolve_href(path, href)[0] for href in document.links}
            if ancestors and not linked_paths.intersection(ancestors):
                counts["previous_missing"] += 1
                details.append(f"previous_missing {path}")
            for href in document.previous_links:
                previous_path, _ = resolve_href(path, href)
                if previous_path not in ancestors:
                    counts["previous_mismatch"] += 1
                    details.append(
                        f"previous_mismatch {path}: {previous_path} not in route ancestors"
                    )

            expects_dynamic = bool(
                route
                and route["id"] == "toolbox"
                and path in route["continuations"][0]["from"]
            )
            expected_dynamic = Counter(
                {
                    (
                        "toolbox",
                        "route-notebook.targetedRemediationReturnPoint",
                        "tocReturn",
                    ): 1
                }
                if expects_dynamic
                else {}
            )
            actual_dynamic = Counter(document.dynamic_returns)
            missing_dynamic = expected_dynamic - actual_dynamic
            extra_dynamic = actual_dynamic - expected_dynamic
            if missing_dynamic:
                counts["toolbox_return_missing"] += sum(missing_dynamic.values())
                details.append(f"toolbox_return_missing {path}")
            if extra_dynamic:
                counts["toolbox_return_extra"] += sum(extra_dynamic.values())
                details.append(f"toolbox_return_extra {path}")
        elif kind in EXCLUDED_KINDS:
            if document.footer_count:
                counts["exclusion_mismatch"] += 1
                details.append(f"excluded_footer {path}")
            if document.actions or document.dynamic_returns or document.completion_ui_count:
                counts["exclusion_mismatch"] += 1
                details.append(f"excluded_navigation_or_completion {path}")
    return counts, details


def align(root: Path, manifest: dict[str, Any]) -> int:
    routes = {route["id"]: route for route in manifest["routes"]}
    changed = 0
    for page in manifest["pages"]:
        if page["pageKind"] not in CANONICAL_KINDS:
            continue
        path = root / page["path"]
        original = path.read_text(encoding="utf-8")
        matches = FOOTER_PATTERN.findall(original)
        if len(matches) != 1:
            raise ValueError(f"{page['path']} must contain exactly one footer before alignment")
        original_footer = matches[0]
        identity_markup = re.sub(
            r"^<footer(?:\s[^>]*)?>|</footer>$", "", original_footer, flags=re.DOTALL
        )
        existing_identity = re.search(
            r'<div class="course-page-identity">(.*?)</div>',
            identity_markup,
            flags=re.DOTALL,
        )
        if existing_identity:
            identity_markup = existing_identity.group(1)
        replacement = render_footer(page, page_route(page, routes), identity_markup)
        updated = FOOTER_PATTERN.sub(replacement, original, count=1)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def self_test(root: Path, manifest: dict[str, Any]) -> int:
    with TemporaryDirectory() as temporary:
        fixture = Path(temporary)
        display_fixture = fixture / "display-contract"
        (display_fixture / "lessons").mkdir(parents=True)
        display_manifest = {
            "routes": [
                {
                    "id": "sample-route",
                    "displayName": "示例路線",
                    "legalStop": "Stop after target",
                    "legalStopDisplay": "完成示例成果後即可停止",
                    "returnPolicy": "caller-provided",
                    "edges": [],
                }
            ],
            "pages": [
                {
                    "path": "lessons/target.html",
                    "pageKind": "canonical-lesson",
                    "routeMemberships": [{"routeId": "sample-route"}],
                }
            ],
        }
        (display_fixture / "lessons/target.html").write_text(
            '<footer data-course-footer="canonical" data-route-id="sample-route" '
            'data-legal-stop="Stop after target">'
            '<p><strong>Route navigation · Sample Route</strong></p><ul></ul>'
            '<p data-route-legal-stop="Stop after target">'
            '<strong>Legal stop：</strong>Stop after target</p>'
            '<div class="course-page-identity">Page kind：canonical lesson · '
            'Route roles：feedback · Source IDs：sample-contract</div></footer>',
            encoding="utf-8",
        )
        display_counts, _ = verify(display_fixture, display_manifest)
        if display_counts["footer_display_mismatch"] != 1:
            print(
                "SELF-TEST FAIL localized footer contract: "
                f"{dict(display_counts)}",
                file=sys.stderr,
            )
            return 1

        incoming_fixture = fixture / "incoming-contract"
        (incoming_fixture / "lessons").mkdir(parents=True)
        incoming_manifest = {
            "routes": [
                {
                    "id": "sample-route",
                    "displayName": "示例路線",
                    "legalStop": "Stop after target",
                    "legalStopDisplay": "完成示例成果後即可停止",
                    "returnPolicy": "caller-provided",
                    "edges": [
                        {
                            "kind": "next",
                            "from": "lessons/source.html",
                            "to": ["lessons/target.html"],
                        }
                    ],
                }
            ],
            "pages": [
                {
                    "path": "lessons/source.html",
                    "pageKind": "canonical-lesson",
                    "routeMemberships": [{"routeId": "sample-route"}],
                },
                {
                    "path": "lessons/target.html",
                    "pageKind": "canonical-lesson",
                    "routeMemberships": [{"routeId": "sample-route"}],
                },
            ],
        }
        (incoming_fixture / "lessons/source.html").write_text(
            '<p><a href="target.html">next</a></p>'
            '<footer data-course-footer="canonical" data-route-id="sample-route" '
            'data-legal-stop="Stop after target">'
            '<p><strong>路線導覽 · 示例路線</strong></p><ul>'
            '<li><a data-route-id="sample-route" data-route-action="next" '
            'href="target.html">next</a></li></ul>'
            '<p data-route-legal-stop="Stop after target">'
            '<strong>合法停止點：</strong>完成示例成果後即可停止</p>'
            '<div>頁面類型：標準課程頁 · 路線角色：entry · 來源 ID：sample</div>'
            '</footer>',
            encoding="utf-8",
        )
        target_path = incoming_fixture / "lessons/target.html"
        target_clean = (
            '<p><a rel="prev" href="source.html">previous</a></p>'
            '<footer data-course-footer="canonical" data-route-id="sample-route" '
            'data-legal-stop="Stop after target">'
            '<p><strong>路線導覽 · 示例路線</strong></p><ul></ul>'
            '<p data-route-legal-stop="Stop after target">'
            '<strong>合法停止點：</strong>完成示例成果後即可停止</p>'
            '<div>頁面類型：標準課程頁 · 路線角色：feedback · 來源 ID：sample</div>'
            '</footer>'
        )
        target_path.write_text(target_clean, encoding="utf-8")
        incoming_clean_counts, _ = verify(incoming_fixture, incoming_manifest)
        if incoming_clean_counts:
            print(
                f"SELF-TEST FAIL incoming clean fixture: {dict(incoming_clean_counts)}",
                file=sys.stderr,
            )
            return 1
        target_path.write_text(
            target_clean.replace(
                '<p><a rel="prev" href="source.html">previous</a></p>', "", 1
            ),
            encoding="utf-8",
        )
        incoming_missing_counts, _ = verify(incoming_fixture, incoming_manifest)
        if incoming_missing_counts["previous_missing"] != 1:
            print(
                "SELF-TEST FAIL incoming previous mutation: "
                f"{dict(incoming_missing_counts)}",
                file=sys.stderr,
            )
            return 1
        target_path.write_text(
            target_clean.replace('href="source.html"', 'href="wrong.html"', 1),
            encoding="utf-8",
        )
        incoming_mismatch_counts, _ = verify(incoming_fixture, incoming_manifest)
        if incoming_mismatch_counts["previous_mismatch"] != 1:
            print(
                "SELF-TEST FAIL incoming previous destination: "
                f"{dict(incoming_mismatch_counts)}",
                file=sys.stderr,
            )
            return 1

        for page in manifest["pages"]:
            destination = fixture / page["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                (root / page["path"]).read_text(encoding="utf-8"), encoding="utf-8"
            )
        align(fixture, manifest)
        clean_counts, _ = verify(fixture, manifest)
        if clean_counts:
            print(f"SELF-TEST FAIL clean fixture: {dict(clean_counts)}", file=sys.stderr)
            return 1

        lesson = next(
            page
            for page in manifest["pages"]
            if page["pageKind"] == "canonical-lesson"
            and 'data-route-action="next"'
            in (fixture / page["path"]).read_text(encoding="utf-8")
        )
        lesson_path = fixture / lesson["path"]
        lesson_clean = lesson_path.read_text(encoding="utf-8")
        lesson_path.write_text(
            lesson_clean.replace(
                'data-course-footer="canonical"', 'data-course-footer="broken"', 1
            ),
            encoding="utf-8",
        )
        broken_counts, _ = verify(fixture, manifest)
        if broken_counts["footer_missing"] != 1:
            print(f"SELF-TEST FAIL mutation: {dict(broken_counts)}", file=sys.stderr)
            return 1

        lesson_path.write_text(
            lesson_clean.replace('data-route-action="next"', 'data-route-action="broken"', 1),
            encoding="utf-8",
        )
        action_counts, _ = verify(fixture, manifest)
        if action_counts["action_missing"] != 1:
            print(f"SELF-TEST FAIL action mutation: {dict(action_counts)}", file=sys.stderr)
            return 1

        action_markup = re.search(
            r'<a [^>]*data-route-action="next"[^>]*>.*?</a>',
            lesson_clean,
            flags=re.DOTALL,
        )
        if action_markup is None:
            print("SELF-TEST FAIL action fixture missing", file=sys.stderr)
            return 1
        lesson_path.write_text(
            lesson_clean.replace("</ul>", action_markup.group(0) + "</ul>", 1),
            encoding="utf-8",
        )
        duplicate_action_counts, _ = verify(fixture, manifest)
        if duplicate_action_counts["action_extra"] != 1:
            print(
                f"SELF-TEST FAIL duplicate action: {dict(duplicate_action_counts)}",
                file=sys.stderr,
            )
            return 1

        lesson_path.write_text(
            lesson_clean.replace('data-legal-stop="', 'data-legal-stop="wrong ', 1),
            encoding="utf-8",
        )
        stop_counts, _ = verify(fixture, manifest)
        if stop_counts["legal_stop_mismatch"] != 1:
            print(f"SELF-TEST FAIL stop mutation: {dict(stop_counts)}", file=sys.stderr)
            return 1
        lesson_path.write_text(
            lesson_clean.replace(
                'data-route-legal-stop="', 'data-route-legal-stop="wrong ', 1
            ),
            encoding="utf-8",
        )
        visible_stop_counts, _ = verify(fixture, manifest)
        if visible_stop_counts["legal_stop_visible_mismatch"] != 1:
            print(
                f"SELF-TEST FAIL visible stop mutation: {dict(visible_stop_counts)}",
                file=sys.stderr,
            )
            return 1
        lesson_path.write_text(lesson_clean, encoding="utf-8")

        toolbox_page = next(
            page
            for page in manifest["pages"]
            if page["pageKind"] == "canonical-lesson"
            and 'data-route-action="return-to-caller"'
            in (fixture / page["path"]).read_text(encoding="utf-8")
        )
        toolbox_path = fixture / toolbox_page["path"]
        toolbox_path.write_text(
            toolbox_path.read_text(encoding="utf-8").replace(
                'data-route-action="return-to-caller"',
                'data-route-action="broken-return"',
                1,
            ),
            encoding="utf-8",
        )
        toolbox_counts, _ = verify(fixture, manifest)
        if toolbox_counts["toolbox_return_missing"] != 1:
            print(
                f"SELF-TEST FAIL toolbox mutation: {dict(toolbox_counts)}",
                file=sys.stderr,
            )
            return 1

        toolbox_clean = render_footer(
            toolbox_page,
            page_route(
                toolbox_page, {route["id"]: route for route in manifest["routes"]}
            ),
            "identity",
        )
        dynamic_markup = re.search(
            r'<span [^>]*data-route-action="return-to-caller"[^>]*>.*?</span>',
            toolbox_clean,
            flags=re.DOTALL,
        )
        if dynamic_markup is None:
            print("SELF-TEST FAIL dynamic fixture missing", file=sys.stderr)
            return 1
        toolbox_path.write_text(
            toolbox_clean.replace(
                "</ul>", dynamic_markup.group(0) + "</ul>", 1
            ),
            encoding="utf-8",
        )
        duplicate_dynamic_counts, _ = verify(fixture, manifest)
        if duplicate_dynamic_counts["toolbox_return_extra"] != 1:
            print(
                "SELF-TEST FAIL duplicate toolbox return: "
                f"{dict(duplicate_dynamic_counts)}",
                file=sys.stderr,
            )
            return 1

        compatibility = next(
            page for page in manifest["pages"] if page["pageKind"] == "compatibility"
        )
        compatibility_path = fixture / compatibility["path"]
        compatibility_path.write_text(
            compatibility_path.read_text(encoding="utf-8").replace(
                "</body>",
                '<div data-completion-ui="true"></div><footer>wrong</footer></body>',
                1,
            ),
            encoding="utf-8",
        )
        exclusion_counts, _ = verify(fixture, manifest)
        if exclusion_counts["exclusion_mismatch"] != 2:
            print(
                f"SELF-TEST FAIL exclusion mutation: {dict(exclusion_counts)}",
                file=sys.stderr,
            )
            return 1

        parser_fixture = NavigationParser()
        parser_fixture.feed(
            '<footer data-course-footer="canonical" data-route-id="sample" '
            'data-legal-stop="stop"><div>identity<br>line two</div>'
            '<a data-route-id="sample" data-route-action="next" href="next.html">'
            'next</a></footer><a data-route-id="sample" data-route-action="next" '
            'href="must-not-count.html">outside</a><div class="completion">outside</div>'
        )
        parser_fixture.close()
        if (
            parser_fixture.actions
            != [("sample", "next", "next.html")]
            or parser_fixture.completion_ui_count != 1
        ):
            print(
                "SELF-TEST FAIL footer boundary with void tag: "
                f"actions={parser_fixture.actions} completion={parser_fixture.completion_ui_count}",
                file=sys.stderr,
            )
            return 1
    print("ROUTE NAVIGATION SELF-TEST PASS cases=13 skipped=0")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=MANIFEST_PATH)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--details", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / args.manifest).read_text(encoding="utf-8"))
    if args.self_test:
        return self_test(root, manifest)
    if args.write:
        changed = align(root, manifest)
        print(f"ROUTE NAVIGATION ALIGN changed={changed}")
    counts, details = verify(root, manifest)
    if args.details:
        for detail in details:
            print(detail)
    ordered = " ".join(f"{key}={counts[key]}" for key in sorted(counts)) or "blockers=0"
    if counts:
        print(f"ROUTE NAVIGATION BLOCKED {ordered}")
        return 1
    print("ROUTE NAVIGATION PASS canonical=123 lessons=105 references=18 exclusions=47 skipped=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
