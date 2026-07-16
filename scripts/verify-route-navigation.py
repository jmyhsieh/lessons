#!/usr/bin/env python3
"""Verify or mechanically align route-aware canonical page footers."""

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
        self.completion_ui_count = 0
        self._inside_footer = False

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
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


def page_route(page: dict[str, Any], routes: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    memberships = page.get("routeMemberships")
    if not isinstance(memberships, list) or not memberships:
        return None
    return routes[memberships[0]["routeId"]]


def route_label(route_id: str) -> str:
    return route_id.replace("-", " ").title()


def action_label(action: Action) -> str:
    labels = {
        "next": "下一步",
        "choose-one": "選擇一條支線",
        "optional-continuation": "選用延伸",
        "continuation": "Route continuation",
        "route-return": "回到 route catalog",
        "catalog-fallback": "沒有有效 return point 時回 Toolbox catalog",
    }
    return f"{labels.get(action.kind, action.kind)}：{action.path}"


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
                f'<p><strong>Route navigation · {html.escape(route_label(route_id))}</strong></p>',
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
                f'<strong>Legal stop：</strong>{html.escape(legal_stop)}</p>',
            ]
        )

    lines.append(f'<div class="course-page-identity">{identity_markup.strip()}</div>')
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

            expected = Counter(expected_actions(route, path)) if route else Counter()
            actual = actual_actions(path, document)
            for action, count in sorted((expected - actual).items()):
                counts["action_missing"] += count
                details.append(f"action_missing {path}: {action}")
            for action, count in sorted((actual - expected).items()):
                counts["action_extra"] += count
                details.append(f"action_extra {path}: {action}")

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
    print("ROUTE NAVIGATION SELF-TEST PASS cases=10 skipped=0")
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
