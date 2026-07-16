#!/usr/bin/env python3
"""Verify the bounded T02 page-level migration manifest contract."""

from __future__ import annotations

import argparse
import copy
import json
import re
import runpy
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any


EXPECTED_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "authority",
    "publicationGateMode",
    "phaseCatalog",
    "routes",
    "pages",
}
EXPECTED_AUTHORITY = {
    "manifest": "docs/migration/course-migration-manifest.json",
    "freeze": "docs/migration/course-migration-plan.md",
    "blueprintIssue": 12,
    "specIssue": 13,
    "ticketIssue": 15,
}
EXPECTED_KIND_COUNTS = {
    "navigation": 2,
    "canonical-lesson": 105,
    "canonical-reference": 18,
    "compatibility": 46,
    "deprecation": 1,
}
EXPECTED_PHASE_CATALOG = [
    {"phase": 1, "label": "Orient", "lessonCount": 7},
    {"phase": 2, "label": "Equip", "lessonCount": 11},
    {"phase": 3, "label": "Deliver", "lessonCount": 10},
    {"phase": 4, "label": "Design", "lessonCount": 7},
    {"phase": 5, "label": "Communicate", "lessonCount": 10},
    {"phase": 6, "label": "Build", "lessonCount": 14},
    {"phase": 7, "label": "Verify", "lessonCount": 7},
    {"phase": 8, "label": "Operate", "lessonCount": 8},
    {"phase": 9, "label": "Standardize", "lessonCount": 9},
    {"phase": 10, "label": "Prove", "lessonCount": 8},
    {"phase": 11, "label": "Roll out", "lessonCount": 7},
    {"phase": 12, "label": "Govern", "lessonCount": 7},
]
EXPECTED_ROUTE_IDS = {
    "agent-operations",
    "browser-evidence",
    "code-readiness",
    "common-foundation",
    "cowork-starter",
    "design-delivery",
    "engineering-delivery",
    "governance-lifecycle",
    "knowledge-delivery",
    "presentation-delivery",
    "scenario-rollout",
    "toolbox",
    "workflow-evaluation",
    "workflow-standardization",
}
ALLOWED_PAGE_KINDS = set(EXPECTED_KIND_COUNTS)
ALLOWED_ACTIONS = {
    "conditional",
    "conditionalize",
    "convert-to-reference",
    "create",
    "expand",
    "keep",
    "merge",
    "move",
    "narrow",
    "rebuild",
    "recertify",
    "rename",
    "retire",
    "rewrite",
    "split",
    "transition",
}
ALLOWED_MEMBERSHIP_ROLES = {
    "conditional",
    "entry",
    "exit-evidence",
    "feedback",
    "readiness",
    "stop",
    "tangible-win",
}
ALLOWED_EDGE_KINDS = {"choose-one", "next", "optional-continuation"}
ALLOWED_RETURN_ANCHORS = {
    "extensions",
    "phase-catalog",
    "references",
    "route-design",
    "route-engineering",
    "route-knowledge",
    "route-presentation",
    "start",
    "toolbox",
}
LESSON_PATH_PATTERN = re.compile(
    r"^lessons/(?P<phase>\d{3})-(?P<lesson>\d{4})-[a-z0-9-]+\.html$"
)
COORDINATE_PATTERN = re.compile(r"^(?P<phase>\d{3})-(?P<lesson>\d{4})$")
SAFE_FRAGMENT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PAGE_FIELDS = {
    "path",
    "origin",
    "pageKind",
    "expectedIdentity",
    "legacyCoordinate",
    "canonicalCoordinate",
    "contentDisposition",
    "routeMemberships",
    "compatibility",
    "deprecation",
    "evidenceCarryover",
    "sourceDependencies",
    "migrationStatus",
}
ROUTE_FIELDS = {
    "id",
    "kind",
    "tocReturn",
    "entry",
    "readiness",
    "stop",
    "exitEvidence",
    "legalStop",
    "returnPolicy",
    "continuations",
    "remediation",
    "edges",
}


def failure(code: str, message: str) -> str:
    return f"[{code}] {message}"


def blocker_codes(errors: list[str]) -> set[str]:
    return {error.split("]", 1)[0].lstrip("[") for error in errors}


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"{label} is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} is invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def load_validated_freeze(repo_root: Path) -> dict[str, Any]:
    verifier = runpy.run_path(
        str(repo_root / "scripts" / "verify-migration-freeze.py")
    )
    try:
        freeze = verifier["load_freeze"](
            repo_root / "docs" / "migration" / "course-migration-plan.md"
        )
    except (KeyError, ValueError) as error:
        raise ValueError(f"cannot load Freeze authority: {error}") from error
    errors = verifier["validate_freeze"](
        freeze,
        repo_root,
        verify_git_tree=True,
    )
    if errors:
        raise ValueError("Freeze authority is invalid: " + "; ".join(errors))
    return freeze


def validate_target(value: Any, label: str) -> list[str]:
    if not isinstance(value, dict):
        return [failure("target-schema", f"{label} must be an object")]
    if set(value) != {"path", "fragment", "role"}:
        return [
            failure(
                "target-schema",
                f"{label} must contain only path, fragment, and role",
            )
        ]
    path = value.get("path")
    fragment = value.get("fragment")
    role = value.get("role")
    errors = []
    if not isinstance(path, str) or not path.endswith(".html"):
        errors.append(failure("target-schema", f"{label}.path must be an HTML path"))
    if fragment is not None and (
        not isinstance(fragment, str) or SAFE_FRAGMENT_PATTERN.fullmatch(fragment) is None
    ):
        errors.append(
            failure("target-fragment", f"{label}.fragment must be a safe fragment or null")
        )
    if not isinstance(role, str) or not role:
        errors.append(failure("target-schema", f"{label}.role must be non-empty"))
    return errors


def validate_memberships(value: Any, path: str) -> list[str]:
    if not isinstance(value, list):
        return [failure("route-membership-schema", f"{path} memberships must be a list")]
    errors = []
    route_ids = []
    for index, membership in enumerate(value):
        label = f"{path} routeMemberships[{index}]"
        if not isinstance(membership, dict) or set(membership) != {"routeId", "roles"}:
            errors.append(
                failure("route-membership-schema", f"{label} has invalid fields")
            )
            continue
        route_id = membership.get("routeId")
        roles = membership.get("roles")
        if not isinstance(route_id, str) or not route_id:
            errors.append(
                failure("route-membership-schema", f"{label}.routeId is invalid")
            )
        else:
            route_ids.append(route_id)
        if (
            not isinstance(roles, list)
            or not roles
            or not all(isinstance(role, str) for role in roles)
        ):
            errors.append(failure("route-role", f"{label}.roles must be strings"))
        elif roles != sorted(set(roles)) or set(roles) - ALLOWED_MEMBERSHIP_ROLES:
            errors.append(failure("route-role", f"{label}.roles are invalid"))
        elif not {"tangible-win", "feedback"}.issubset(roles):
            errors.append(
                failure(
                    "route-feedback",
                    f"{label} must declare tangible-win and feedback",
                )
            )
    if len(route_ids) != len(set(route_ids)):
        errors.append(failure("route-membership-duplicate", f"{path} repeats a route"))
    return errors


def validate_page_schema(page: Any, index: int) -> list[str]:
    if not isinstance(page, dict):
        return [failure("page-schema", f"pages[{index}] must be an object")]
    path = page.get("path", f"pages[{index}]")
    errors = []
    if set(page) != PAGE_FIELDS:
        errors.append(failure("page-schema", f"{path} has unexpected or missing fields"))
        return errors
    if not isinstance(path, str):
        return [failure("page-schema", f"pages[{index}].path must be a string")]
    parsed = PurePosixPath(path)
    if (
        parsed.is_absolute()
        or ".." in parsed.parts
        or parsed.suffix != ".html"
        or str(parsed) != path
        or any(ord(character) < 32 or ord(character) == 127 for character in path)
    ):
        errors.append(failure("page-path", f"{path!r} is not a safe HTML path"))
    if page.get("origin") not in {"baseline", "new"}:
        errors.append(failure("page-origin", f"{path} has invalid origin"))
    if page.get("pageKind") not in ALLOWED_PAGE_KINDS:
        errors.append(failure("page-kind", f"{path} has invalid pageKind"))
    if not isinstance(page.get("expectedIdentity"), str) or not page["expectedIdentity"]:
        errors.append(failure("page-identity", f"{path} needs expectedIdentity"))
    for field in ("legacyCoordinate", "canonicalCoordinate"):
        value = page.get(field)
        if value is not None and (
            not isinstance(value, str) or COORDINATE_PATTERN.fullmatch(value) is None
        ):
            errors.append(failure("coordinate-schema", f"{path}.{field} is invalid"))
    disposition = page.get("contentDisposition")
    if not isinstance(disposition, dict) or set(disposition) != {"actions", "blueprint"}:
        errors.append(failure("disposition-schema", f"{path} disposition is invalid"))
    else:
        actions = disposition.get("actions")
        if (
            not isinstance(actions, list)
            or not actions
            or not all(isinstance(action, str) for action in actions)
            or actions != sorted(set(actions))
            or set(actions) - ALLOWED_ACTIONS
        ):
            errors.append(failure("disposition-actions", f"{path} actions are invalid"))
        if not isinstance(disposition.get("blueprint"), str) or not disposition["blueprint"]:
            errors.append(failure("disposition-schema", f"{path} blueprint is required"))
    errors.extend(validate_memberships(page.get("routeMemberships"), path))
    source = page.get("sourceDependencies")
    if not isinstance(source, dict) or set(source) != {"state", "anchorIds"}:
        errors.append(failure("source-placeholder", f"{path} source placeholder is invalid"))
    elif source.get("state") not in {"not-applicable", "pending-t03"} or source.get(
        "anchorIds"
    ) != []:
        errors.append(
            failure("source-placeholder", f"{path} must not fabricate Source anchors")
        )
    if page.get("migrationStatus") != "planned":
        errors.append(failure("migration-status", f"{path} must remain planned in T02"))
    if page.get("evidenceCarryover") not in {
        "current-route-contract",
        "lesson-practiced-unless-current-route-stop-is-revalidated",
        "not-applicable",
    }:
        errors.append(failure("evidence-carryover", f"{path} policy is invalid"))
    return errors


def validate_route_schema(route: Any, index: int) -> list[str]:
    if not isinstance(route, dict):
        return [failure("route-schema", f"routes[{index}] must be an object")]
    route_id = route.get("id", f"routes[{index}]")
    errors = []
    if set(route) != ROUTE_FIELDS:
        return [failure("route-schema", f"{route_id} has invalid fields")]
    if not isinstance(route_id, str) or not route_id:
        errors.append(failure("route-schema", f"routes[{index}].id is invalid"))
    if route.get("kind") not in {
        "extension",
        "foundation",
        "readiness",
        "starter",
        "task",
        "toolbox",
    }:
        errors.append(failure("route-schema", f"{route_id} has invalid kind"))
    target = route.get("tocReturn")
    errors.extend(validate_target(target, f"{route_id}.tocReturn"))
    if isinstance(target, dict):
        if target.get("path") != "toc.html" or target.get("fragment") not in ALLOWED_RETURN_ANCHORS:
            errors.append(failure("route-return", f"{route_id} has invalid TOC return"))
    if not isinstance(route.get("entry"), str):
        errors.append(failure("route-schema", f"{route_id}.entry must be a path"))
    readiness = route.get("readiness")
    if not isinstance(readiness, dict) or set(readiness) != {"mode", "targets"}:
        errors.append(failure("route-readiness", f"{route_id}.readiness is invalid"))
    elif readiness.get("mode") not in {"all-of", "any-of"} or not isinstance(
        readiness.get("targets"), list
    ) or not readiness["targets"] or not all(
        isinstance(path, str) for path in readiness["targets"]
    ):
        errors.append(failure("route-readiness", f"{route_id}.readiness is invalid"))
    stop = route.get("stop")
    if stop is not None and not isinstance(stop, str):
        errors.append(failure("route-schema", f"{route_id}.stop must be a path or null"))
    for field in ("exitEvidence", "legalStop", "returnPolicy"):
        if not isinstance(route.get(field), str) or not route[field]:
            errors.append(failure("route-schema", f"{route_id}.{field} is required"))
    if not isinstance(route.get("continuations"), list) or not route["continuations"]:
        errors.append(failure("route-continuation", f"{route_id} needs continuations"))
    if not isinstance(route.get("remediation"), list) or not route["remediation"]:
        errors.append(failure("route-remediation", f"{route_id} needs remediation"))
    if not isinstance(route.get("edges"), list):
        errors.append(failure("route-edge-schema", f"{route_id}.edges must be a list"))
    return errors


def validate_manifest(manifest: dict[str, Any], freeze: dict[str, Any]) -> list[str]:
    errors = []
    if set(manifest) != EXPECTED_TOP_LEVEL_KEYS:
        errors.append(
            failure(
                "manifest-schema",
                "manifest must contain only schema, authority, mode, phases, routes, and pages",
            )
        )
        return errors
    if manifest.get("schemaVersion") != 1 or isinstance(
        manifest.get("schemaVersion"), bool
    ):
        errors.append(failure("manifest-schema", "schemaVersion must be integer 1"))
    if manifest.get("authority") != EXPECTED_AUTHORITY:
        errors.append(failure("manifest-authority", "authority boundary differs from T02"))
    if manifest.get("publicationGateMode") != "report-only":
        errors.append(
            failure("publication-mode", "T02 publicationGateMode must be report-only")
        )
    if "baselinePaths" in manifest or "newCanonicalPaths" in manifest:
        errors.append(
            failure("parallel-allowlist", "manifest must not duplicate Freeze allowlists")
        )
    if manifest.get("phaseCatalog") != EXPECTED_PHASE_CATALOG:
        errors.append(failure("phase-catalog", "phase catalog differs from approved 105 lessons"))

    pages = manifest.get("pages")
    routes = manifest.get("routes")
    if not isinstance(pages, list):
        errors.append(failure("manifest-schema", "pages must be a list"))
        return errors
    if not isinstance(routes, list):
        errors.append(failure("manifest-schema", "routes must be a list"))
        return errors
    for index, page in enumerate(pages):
        errors.extend(validate_page_schema(page, index))
    for index, route in enumerate(routes):
        errors.extend(validate_route_schema(route, index))
    if errors:
        return errors

    page_paths = [page["path"] for page in pages]
    expected_paths = sorted(freeze["baselinePaths"] + freeze["newCanonicalPaths"])
    if len(page_paths) != 172 or set(page_paths) != set(expected_paths):
        missing = sorted(set(expected_paths) - set(page_paths))
        unexpected = sorted(set(page_paths) - set(expected_paths))
        errors.append(
            failure(
                "manifest-union",
                f"manifest must equal frozen 172-path union; missing={missing}; unexpected={unexpected}",
            )
        )
    if len(page_paths) != len(set(page_paths)):
        errors.append(failure("manifest-path-duplicate", "page paths must be unique"))
    if page_paths != sorted(page_paths):
        errors.append(failure("manifest-order", "pages must be sorted by path"))

    baseline_set = set(freeze["baselinePaths"])
    new_set = set(freeze["newCanonicalPaths"])
    for page in pages:
        expected_origin = "baseline" if page["path"] in baseline_set else "new"
        if page["origin"] != expected_origin:
            errors.append(
                failure("page-origin", f"{page['path']} must be {expected_origin}")
            )
        actions = page["contentDisposition"]["actions"]
        if expected_origin == "new" and actions != ["create"]:
            errors.append(
                failure(
                    "disposition-origin",
                    f"{page['path']} new canonical page must use create disposition",
                )
            )
        if expected_origin == "baseline" and "create" in actions:
            errors.append(
                failure(
                    "disposition-origin",
                    f"{page['path']} baseline page cannot use create disposition",
                )
            )
        if page["pageKind"] == "deprecation" and actions != ["retire"]:
            errors.append(
                failure(
                    "disposition-kind",
                    f"{page['path']} Deprecation must use retire disposition",
                )
            )
    origin_counts = Counter(page["origin"] for page in pages)
    if origin_counts != Counter({"baseline": 73, "new": 99}):
        errors.append(failure("origin-counts", f"unexpected origin counts: {origin_counts}"))
    kind_counts = Counter(page["pageKind"] for page in pages)
    if kind_counts != Counter(EXPECTED_KIND_COUNTS):
        errors.append(failure("kind-counts", f"unexpected page-kind counts: {kind_counts}"))
    baseline_kind_counts = Counter(
        page["pageKind"] for page in pages if page["origin"] == "baseline"
    )
    if baseline_kind_counts != Counter(
        {
            "navigation": 2,
            "canonical-lesson": 14,
            "canonical-reference": 10,
            "compatibility": 46,
            "deprecation": 1,
        }
    ):
        errors.append(
            failure(
                "baseline-classification",
                f"unexpected baseline classification: {baseline_kind_counts}",
            )
        )
    new_kind_counts = Counter(
        page["pageKind"] for page in pages if page["origin"] == "new"
    )
    if new_kind_counts != Counter(
        {"canonical-lesson": 91, "canonical-reference": 8}
    ):
        errors.append(
            failure("new-classification", f"unexpected new classification: {new_kind_counts}")
        )

    by_path = {page["path"]: page for page in pages}
    canonical_kinds = {"navigation", "canonical-lesson", "canonical-reference"}
    canonical_paths = {
        page["path"] for page in pages if page["pageKind"] in canonical_kinds
    }
    coordinates = []
    phase_counts: Counter[int] = Counter()
    for page in pages:
        path = page["path"]
        kind = page["pageKind"]
        canonical_coordinate = page["canonicalCoordinate"]
        legacy_coordinate = page["legacyCoordinate"]
        match = LESSON_PATH_PATTERN.fullmatch(path)
        if kind == "canonical-lesson":
            if match is None or canonical_coordinate is None:
                errors.append(failure("coordinate-kind", f"{path} needs a coordinate"))
            else:
                expected_coordinate = f"{match.group('phase')}-{match.group('lesson')}"
                if canonical_coordinate != expected_coordinate:
                    errors.append(
                        failure(
                            "coordinate-filename",
                            f"{path} coordinate must be {expected_coordinate}",
                        )
                    )
                coordinates.append(canonical_coordinate)
                phase_counts[int(match.group("phase"))] += 1
            if not page["routeMemberships"]:
                errors.append(
                    failure("route-membership", f"{path} needs at least one route")
                )
        elif canonical_coordinate is not None:
            errors.append(
                failure("coordinate-kind", f"{path} must not have canonical coordinate")
            )
        if page["origin"] == "baseline" and match is not None:
            expected_legacy = f"{match.group('phase')}-{match.group('lesson')}"
            if legacy_coordinate != expected_legacy:
                errors.append(
                    failure("legacy-coordinate", f"{path} legacy coordinate must be {expected_legacy}")
                )
        elif legacy_coordinate is not None:
            errors.append(failure("legacy-coordinate", f"{path} must not have legacy coordinate"))
        if kind != "canonical-lesson" and page["routeMemberships"]:
            errors.append(
                failure("route-membership", f"{path} non-lesson must not join a route")
            )
    if len(coordinates) != 105 or len(set(coordinates)) != 105:
        errors.append(failure("coordinate-duplicate", "105 coordinates must be unique"))
    expected_phase_counts = Counter(
        {item["phase"]: item["lessonCount"] for item in EXPECTED_PHASE_CATALOG}
    )
    if phase_counts != expected_phase_counts:
        errors.append(failure("coordinate-phases", f"unexpected phase counts: {phase_counts}"))

    transition_pages = []
    for page in pages:
        path = page["path"]
        kind = page["pageKind"]
        compatibility = page["compatibility"]
        deprecation = page["deprecation"]
        if kind == "compatibility":
            transition_pages.append(page)
            if not isinstance(compatibility, dict) or set(compatibility) != {
                "mode",
                "finalTargets",
                "allowChain",
                "catalogExcluded",
                "navigationExcluded",
                "completionExcluded",
            }:
                errors.append(failure("compatibility-schema", f"{path} is invalid"))
                continue
            targets = compatibility.get("finalTargets")
            if compatibility.get("mode") not in {"direct", "transition"}:
                errors.append(failure("compatibility-mode", f"{path} mode is invalid"))
            if not isinstance(targets, list) or not targets:
                errors.append(failure("compatibility-target", f"{path} needs targets"))
                continue
            for index, target in enumerate(targets):
                target_errors = validate_target(target, f"{path}.finalTargets[{index}]")
                errors.extend(target_errors)
                if target_errors:
                    continue
                target_path = target["path"]
                if target_path not in canonical_paths:
                    code = (
                        "compatibility-chain"
                        if target_path in by_path
                        and by_path[target_path]["pageKind"] in {"compatibility", "deprecation"}
                        else "compatibility-target"
                    )
                    errors.append(failure(code, f"{path} targets non-canonical {target_path}"))
                if target_path == path:
                    errors.append(failure("compatibility-target", f"{path} targets itself"))
            if compatibility.get("mode") == "direct" and len(targets) != 1:
                errors.append(failure("compatibility-mode", f"{path} direct mode needs one target"))
            if compatibility.get("mode") == "transition" and len(targets) < 2:
                errors.append(
                    failure("compatibility-mode", f"{path} transition needs multiple targets")
                )
            if compatibility.get("allowChain") is not False or any(
                compatibility.get(field) is not True
                for field in ("catalogExcluded", "navigationExcluded", "completionExcluded")
            ):
                errors.append(failure("compatibility-exclusion", f"{path} exclusions are invalid"))
            if deprecation is not None:
                errors.append(failure("transition-kind", f"{path} cannot also be deprecated"))
        elif compatibility is not None:
            errors.append(failure("transition-kind", f"{path} cannot define Compatibility"))

        if kind == "deprecation":
            transition_pages.append(page)
            if not isinstance(deprecation, dict) or set(deprecation) != {
                "reason",
                "effective",
                "successorTargets",
                "catalogExcluded",
                "navigationExcluded",
                "completionExcluded",
            }:
                errors.append(failure("deprecation-schema", f"{path} is invalid"))
                continue
            if not isinstance(deprecation.get("reason"), str) or not deprecation["reason"]:
                errors.append(failure("deprecation-schema", f"{path} needs a reason"))
            if deprecation.get("effective") != "coherent-migration-cutover":
                errors.append(failure("deprecation-schema", f"{path} effective value is invalid"))
            targets = deprecation.get("successorTargets")
            if not isinstance(targets, list) or not targets:
                errors.append(failure("deprecation-target", f"{path} needs a successor"))
            else:
                for index, target in enumerate(targets):
                    target_errors = validate_target(
                        target, f"{path}.successorTargets[{index}]"
                    )
                    errors.extend(target_errors)
                    if not target_errors and target["path"] not in canonical_paths:
                        errors.append(
                            failure(
                                "deprecation-target",
                                f"{path} targets non-canonical {target['path']}",
                            )
                        )
            if any(
                deprecation.get(field) is not True
                for field in ("catalogExcluded", "navigationExcluded", "completionExcluded")
            ):
                errors.append(failure("deprecation-exclusion", f"{path} exclusions are invalid"))
        elif deprecation is not None:
            errors.append(failure("transition-kind", f"{path} cannot define deprecation"))

    if {
        page["path"] for page in pages if page["pageKind"] == "deprecation"
    } != {"reference/ai-workflow-skill-composer.html"}:
        errors.append(failure("deprecation-identity", "the approved Deprecation path differs"))
    old_phase_three = [
        page
        for page in pages
        if page["path"].startswith("lessons/003-") and page["origin"] == "baseline"
    ]
    if any(page["pageKind"] != "compatibility" for page in old_phase_three):
        errors.append(
            failure("legacy-phase-reuse", "old Phase 3 paths must all be Compatibility")
        )
    if any(
        page["evidenceCarryover"]
        != "lesson-practiced-unless-current-route-stop-is-revalidated"
        for page in transition_pages
    ):
        errors.append(
            failure("evidence-carryover", "legacy transitions need conservative carryover")
        )

    route_ids = [route["id"] for route in routes]
    if set(route_ids) != EXPECTED_ROUTE_IDS or len(route_ids) != len(set(route_ids)):
        errors.append(failure("route-inventory", "route IDs differ from approved graph"))
    route_by_id = {route["id"]: route for route in routes}
    membership_by_path = {
        page["path"]: {item["routeId"]: set(item["roles"]) for item in page["routeMemberships"]}
        for page in pages
    }
    for page in pages:
        for membership in page["routeMemberships"]:
            if membership["routeId"] not in EXPECTED_ROUTE_IDS:
                errors.append(
                    failure(
                        "route-membership",
                        f"{page['path']} names unknown route {membership['routeId']}",
                    )
                )

    def require_canonical_lesson(path: Any, label: str) -> None:
        if not isinstance(path, str) or path not in by_path:
            errors.append(failure("route-target", f"{label} targets unknown path {path!r}"))
        elif by_path[path]["pageKind"] != "canonical-lesson":
            errors.append(failure("route-target", f"{label} must target a canonical lesson"))

    for route_id, route in route_by_id.items():
        entry = route["entry"]
        stop = route["stop"]
        require_canonical_lesson(entry, f"{route_id}.entry")
        if entry in membership_by_path and "entry" not in membership_by_path[entry].get(
            route_id, set()
        ):
            errors.append(failure("route-entry", f"{route_id} entry role is missing"))
        if route_id == "toolbox":
            if stop is not None or route["returnPolicy"] != "caller-provided-active-route":
                errors.append(
                    failure("toolbox-return", "toolbox must return to caller without Phase stop")
                )
            if any(edge.get("kind") == "next" for edge in route["edges"]):
                errors.append(failure("toolbox-next", "toolbox must not claim universal next"))
        else:
            require_canonical_lesson(stop, f"{route_id}.stop")
            if stop in membership_by_path and not {
                "stop",
                "exit-evidence",
            }.issubset(membership_by_path[stop].get(route_id, set())):
                errors.append(failure("route-stop", f"{route_id} stop roles are missing"))
            if route["returnPolicy"] != "fixed-toc-anchor":
                errors.append(failure("route-return", f"{route_id} return policy is invalid"))
        readiness = route["readiness"]
        for target in readiness["targets"]:
            require_canonical_lesson(target, f"{route_id}.readiness")
        for index, edge in enumerate(route["edges"]):
            label = f"{route_id}.edges[{index}]"
            if not isinstance(edge, dict) or set(edge) != {"kind", "from", "to", "rejoin"}:
                errors.append(failure("route-edge-schema", f"{label} is invalid"))
                continue
            if edge.get("kind") not in ALLOWED_EDGE_KINDS:
                errors.append(failure("route-edge-schema", f"{label} kind is invalid"))
            require_canonical_lesson(edge.get("from"), f"{label}.from")
            targets = edge.get("to")
            if not isinstance(targets, list) or not targets:
                errors.append(failure("route-edge-schema", f"{label}.to is invalid"))
            else:
                for target in targets:
                    require_canonical_lesson(target, f"{label}.to")
            rejoin = edge.get("rejoin")
            if rejoin is not None:
                require_canonical_lesson(rejoin, f"{label}.rejoin")
        for index, continuation in enumerate(route["continuations"]):
            label = f"{route_id}.continuations[{index}]"
            if not isinstance(continuation, dict) or set(continuation) != {
                "kind",
                "routeId",
                "target",
            }:
                errors.append(failure("route-continuation", f"{label} is invalid"))
                continue
            errors.extend(validate_target(continuation["target"], f"{label}.target"))
            target_path = continuation["target"].get("path")
            if target_path not in canonical_paths:
                errors.append(failure("route-target", f"{label} targets non-canonical page"))
            target_route = continuation.get("routeId")
            if target_route is not None and target_route not in EXPECTED_ROUTE_IDS:
                errors.append(failure("route-continuation", f"{label} routeId is unknown"))
        for index, remediation in enumerate(route["remediation"]):
            label = f"{route_id}.remediation[{index}]"
            if not isinstance(remediation, dict) or set(remediation) != {
                "when",
                "target",
                "returnTo",
            }:
                errors.append(failure("route-remediation", f"{label} is invalid"))
                continue
            if not isinstance(remediation.get("when"), str) or not remediation["when"]:
                errors.append(failure("route-remediation", f"{label}.when is required"))
            require_canonical_lesson(remediation.get("target"), f"{label}.target")
            require_canonical_lesson(remediation.get("returnTo"), f"{label}.returnTo")
    return errors


def validate_thin_slice(manifest: dict[str, Any]) -> list[str]:
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not all(isinstance(page, dict) for page in pages):
        return [failure("thin-slice", "pages are not available")]
    by_path = {page.get("path"): page for page in pages}
    expected = {
        "index.html": "navigation",
        "lessons/001-0001-four-claude-surfaces.html": "canonical-lesson",
        "lessons/001-0002-first-session-read-only.html": "compatibility",
        "lessons/001-0011-explore-plan-implement-commit.html": "compatibility",
        "lessons/001-0002-define-route-readiness.html": "canonical-lesson",
        "reference/agent-operations-safety.html": "canonical-reference",
        "reference/ai-workflow-skill-composer.html": "deprecation",
    }
    errors = []
    for path, kind in expected.items():
        if path not in by_path or by_path[path].get("pageKind") != kind:
            errors.append(failure("thin-slice", f"{path} must be {kind}"))
    direct = by_path.get("lessons/001-0002-first-session-read-only.html", {}).get(
        "compatibility"
    )
    transition = by_path.get(
        "lessons/001-0011-explore-plan-implement-commit.html", {}
    ).get("compatibility")
    if not isinstance(direct, dict) or direct.get("mode") != "direct":
        errors.append(failure("thin-slice", "direct Compatibility example is invalid"))
    if not isinstance(transition, dict) or transition.get("mode") != "transition":
        errors.append(failure("thin-slice", "transition Compatibility example is invalid"))
    return errors


def run_self_test(manifest: dict[str, Any], freeze: dict[str, Any]) -> list[str]:
    errors = []
    cases: list[tuple[str, dict[str, Any], str]] = []

    missing_baseline = copy.deepcopy(manifest)
    missing_baseline["pages"] = [
        page for page in missing_baseline["pages"] if page["path"] != "index.html"
    ]
    cases.append(("missing baseline", missing_baseline, "manifest-union"))

    duplicate_coordinate = copy.deepcopy(manifest)
    lessons = [
        page for page in duplicate_coordinate["pages"] if page["pageKind"] == "canonical-lesson"
    ]
    lessons[1]["canonicalCoordinate"] = lessons[0]["canonicalCoordinate"]
    cases.append(("duplicate coordinate", duplicate_coordinate, "coordinate-duplicate"))

    compatibility_chain = copy.deepcopy(manifest)
    compatibility_pages = [
        page for page in compatibility_chain["pages"] if page["pageKind"] == "compatibility"
    ]
    compatibility_pages[0]["compatibility"]["finalTargets"][0]["path"] = compatibility_pages[
        1
    ]["path"]
    cases.append(("Compatibility chain", compatibility_chain, "compatibility-chain"))

    unknown_route_target = copy.deepcopy(manifest)
    route_with_edge = next(route for route in unknown_route_target["routes"] if route["edges"])
    route_with_edge["edges"][0]["to"][0] = "lessons/999-9999-missing.html"
    cases.append(("unknown route target", unknown_route_target, "route-target"))

    enforced_mode = copy.deepcopy(manifest)
    enforced_mode["publicationGateMode"] = "enforced"
    cases.append(("premature enforcement", enforced_mode, "publication-mode"))

    invalid_deprecation = copy.deepcopy(manifest)
    deprecation = next(
        page for page in invalid_deprecation["pages"] if page["pageKind"] == "deprecation"
    )
    deprecation["contentDisposition"]["actions"] = ["create"]
    cases.append(("invalid Deprecation disposition", invalid_deprecation, "disposition-kind"))

    for name, mutated, expected_code in cases:
        actual = validate_manifest(mutated, freeze)
        if expected_code not in blocker_codes(actual):
            errors.append(
                failure(
                    "negative-fixture",
                    f"{name} did not fail with [{expected_code}]; got {sorted(blocker_codes(actual))}",
                )
            )

    simulated_blockers = [failure("fixture", "report-only diagnostic")]
    if exit_status(simulated_blockers, report_only=True) != 0:
        errors.append(
            failure("negative-fixture", "report-only diagnostics blocked publication")
        )
    if exit_status(simulated_blockers, report_only=False) == 0:
        errors.append(failure("negative-fixture", "strict verification failed open"))
    return errors


def report(label: str, errors: list[str]) -> bool:
    if errors:
        print(f"{label} BLOCKED ({len(errors)} errors)")
        for error in errors:
            print(f"- {error}")
        return False
    print(f"{label} PASS")
    return True


def exit_status(errors: list[str], *, report_only: bool) -> int:
    return 0 if report_only or not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="prove representative invalid manifest states fail closed",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="report manifest blockers without changing publication eligibility",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    all_errors = []
    try:
        freeze = load_validated_freeze(repo_root)
    except ValueError as error:
        freeze_errors = [failure("freeze-authority", str(error))]
        report("FREEZE AUTHORITY", freeze_errors)
        if args.report_only:
            print("PUBLICATION UNAFFECTED (report-only)")
        return exit_status(freeze_errors, report_only=args.report_only)

    try:
        manifest = load_json(
            repo_root / "docs" / "migration" / "course-migration-manifest.json",
            "migration manifest",
        )
    except ValueError as error:
        manifest_errors = [failure("manifest-load", str(error))]
        report("MIGRATION MANIFEST", manifest_errors)
        if args.report_only:
            print("PUBLICATION UNAFFECTED (report-only)")
        return exit_status(manifest_errors, report_only=args.report_only)

    manifest_errors = validate_manifest(manifest, freeze)
    thin_slice_errors = validate_thin_slice(manifest)
    report("MIGRATION MANIFEST", manifest_errors)
    report("POSITIVE THIN SLICE", thin_slice_errors)
    all_errors.extend(manifest_errors)
    all_errors.extend(thin_slice_errors)
    if args.self_test:
        self_test_errors = run_self_test(manifest, freeze) if not all_errors else [
            failure("self-test-skipped", "valid manifest is required before mutation fixtures")
        ]
        report("NEGATIVE FIXTURES", self_test_errors)
        all_errors.extend(self_test_errors)
    if args.report_only:
        print("PUBLICATION UNAFFECTED (report-only)")
    return exit_status(all_errors, report_only=args.report_only)


if __name__ == "__main__":
    sys.exit(main())
