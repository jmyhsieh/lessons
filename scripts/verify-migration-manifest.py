#!/usr/bin/env python3
"""Verify the bounded T02 page-level migration manifest contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
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
ALLOWED_MIGRATION_STATUSES = {"planned", "authored"}
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
    "review-reentry",
    "stop",
    "tangible-win",
}
ALLOWED_EDGE_KINDS = {"choose-one", "next", "optional-continuation"}
ALLOWED_STATIC_CONTINUATION_KINDS = {
    "conditional-review-reentry",
    "llm-wiki-overlay",
    "optional-route",
    "requires-readiness",
    "return-to-catalog",
    "review-reentry",
    "route",
}
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
EXPECTED_NAVIGATION_PATHS = {"index.html", "toc.html"}
# Independent digests of the reviewed page and route projections pin exact
# contracts, including the evolving Source mappings, without a second manifest.
EXPECTED_PAGE_MATRIX_SHA256 = (
    "d914adeed9c5fcbea342061eff2a0f7079b7021a7ff6ab7d694100fd2cc96b9c"
)
EXPECTED_ROUTE_CONTRACT_SHA256 = (
    "f412397e52c5cc19a858519238f049ac7b3e1ed7c4048f3120073832d5a56a4e"
)
EXPECTED_TOOLBOX_SELECTIONS = [
    "lessons/002-0002-set-permission-boundaries.html",
    "lessons/002-0003-select-model-and-effort.html",
    "lessons/002-0004-smoke-test-hook.html",
    "lessons/002-0005-add-guardrail-hook.html",
    "lessons/002-0006-use-existing-skill.html",
    "lessons/002-0007-connect-trusted-mcp.html",
    "lessons/002-0008-delegate-read-only-investigation.html",
    "lessons/002-0009-isolate-parallel-work.html",
    "lessons/002-0010-run-headless-one-shot.html",
    "lessons/002-0011-bound-ci-automation.html",
]
EXPECTED_PAGE_POLICIES = {
    "navigation": ("not-applicable", "pending-t03"),
    "canonical-lesson": ("current-route-contract", "pending-t03"),
    "canonical-reference": ("not-applicable", "pending-t03"),
    "compatibility": (
        "lesson-practiced-unless-current-route-stop-is-revalidated",
        "not-applicable",
    ),
    "deprecation": (
        "lesson-practiced-unless-current-route-stop-is-revalidated",
        "not-applicable",
    ),
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
    if not isinstance(page.get("origin"), str) or page.get("origin") not in {
        "baseline",
        "new",
    }:
        errors.append(failure("page-origin", f"{path} has invalid origin"))
    if not isinstance(page.get("pageKind"), str) or page.get(
        "pageKind"
    ) not in ALLOWED_PAGE_KINDS:
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
    else:
        source_state = source.get("state")
        anchor_ids = source.get("anchorIds")
        if (
            not isinstance(source_state, str)
            or source_state not in {"not-applicable", "pending-t03", "registered"}
            or not isinstance(anchor_ids, list)
            or not all(isinstance(anchor_id, str) and anchor_id for anchor_id in anchor_ids)
            or anchor_ids != sorted(set(anchor_ids))
        ):
            errors.append(
                failure("source-placeholder", f"{path} Source dependencies are invalid")
            )
        elif source_state == "registered" and not anchor_ids:
            errors.append(
                failure("source-placeholder", f"{path} registered Source dependencies need IDs")
            )
        elif source_state != "registered" and anchor_ids:
            errors.append(
                failure("source-placeholder", f"{path} unregistered Source dependencies need no IDs")
            )
    if page.get("migrationStatus") not in ALLOWED_MIGRATION_STATUSES:
        errors.append(failure("migration-status", f"{path} has invalid migrationStatus"))
    if not isinstance(page.get("evidenceCarryover"), str) or page.get(
        "evidenceCarryover"
    ) not in {
        "current-route-contract",
        "lesson-practiced-unless-current-route-stop-is-revalidated",
        "not-applicable",
    }:
        errors.append(failure("evidence-carryover", f"{path} policy is invalid"))
    return errors


def validate_dynamic_return(value: Any, label: str) -> list[str]:
    fields = {"kind", "routeId", "from", "targetSource", "fallback"}
    if not isinstance(value, dict) or set(value) != fields:
        return [failure("route-continuation", f"{label} has invalid dynamic-return fields")]
    errors = []
    if value.get("kind") != "return-to-caller" or value.get("routeId") is not None:
        errors.append(failure("route-continuation", f"{label} is not return-to-caller"))
    if value.get("from") != EXPECTED_TOOLBOX_SELECTIONS:
        errors.append(
            failure("route-continuation", f"{label}.from must be the ten toolbox selections")
        )
    if value.get("targetSource") != "route-notebook.targetedRemediationReturnPoint":
        errors.append(failure("route-continuation", f"{label}.targetSource is invalid"))
    if value.get("fallback") != "tocReturn":
        errors.append(failure("route-continuation", f"{label}.fallback is invalid"))
    return errors


def validate_remediation_return(value: Any, label: str) -> list[str]:
    if isinstance(value, str):
        return []
    if not isinstance(value, dict) or set(value) != {"source", "fallback"}:
        return [failure("route-remediation", f"{label} has invalid fields")]
    if value != {
        "source": "route-notebook.targetedRemediationReturnPoint",
        "fallback": "tocReturn",
    }:
        return [failure("route-remediation", f"{label} is not the toolbox dynamic return")]
    return []


def validate_route_schema(route: Any, index: int) -> list[str]:
    if not isinstance(route, dict):
        return [failure("route-schema", f"routes[{index}] must be an object")]
    route_id = route.get("id", f"routes[{index}]")
    errors = []
    if set(route) != ROUTE_FIELDS:
        return [failure("route-schema", f"{route_id} has invalid fields")]
    if not isinstance(route_id, str) or not route_id:
        errors.append(failure("route-schema", f"routes[{index}].id is invalid"))
    if not isinstance(route.get("kind"), str) or route.get("kind") not in {
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
        if (
            target.get("path") != "toc.html"
            or not isinstance(target.get("fragment"), str)
            or target.get("fragment") not in ALLOWED_RETURN_ANCHORS
        ):
            errors.append(failure("route-return", f"{route_id} has invalid TOC return"))
    if not isinstance(route.get("entry"), str):
        errors.append(failure("route-schema", f"{route_id}.entry must be a path"))
    readiness = route.get("readiness")
    if not isinstance(readiness, dict) or set(readiness) != {"mode", "targets"}:
        errors.append(failure("route-readiness", f"{route_id}.readiness is invalid"))
    else:
        readiness_targets = readiness.get("targets")
        if (
            not isinstance(readiness.get("mode"), str)
            or readiness.get("mode") not in {"all-of", "any-of"}
            or not isinstance(readiness_targets, list)
            or not readiness_targets
            or not all(isinstance(path, str) for path in readiness_targets)
            or len(readiness_targets) != len(set(readiness_targets))
        ):
            errors.append(failure("route-readiness", f"{route_id}.readiness is invalid"))
    stop = route.get("stop")
    if stop is not None and not isinstance(stop, str):
        errors.append(failure("route-schema", f"{route_id}.stop must be a path or null"))
    for field in ("exitEvidence", "legalStop", "returnPolicy"):
        if not isinstance(route.get(field), str) or not route[field]:
            errors.append(failure("route-schema", f"{route_id}.{field} is required"))

    continuations = route.get("continuations")
    if not isinstance(continuations, list) or not continuations:
        errors.append(failure("route-continuation", f"{route_id} needs continuations"))
    else:
        for continuation_index, continuation in enumerate(continuations):
            label = f"{route_id}.continuations[{continuation_index}]"
            if not isinstance(continuation, dict):
                errors.append(failure("route-continuation", f"{label} must be an object"))
                continue
            if continuation.get("kind") == "return-to-caller":
                errors.extend(validate_dynamic_return(continuation, label))
                continue
            if set(continuation) != {"kind", "routeId", "target"}:
                errors.append(failure("route-continuation", f"{label} has invalid fields"))
                continue
            if not isinstance(continuation.get("kind"), str) or continuation.get(
                "kind"
            ) not in ALLOWED_STATIC_CONTINUATION_KINDS:
                errors.append(failure("route-continuation-kind", f"{label} kind is invalid"))
            target_route = continuation.get("routeId")
            if target_route is not None and not isinstance(target_route, str):
                errors.append(failure("route-continuation", f"{label}.routeId is invalid"))
            errors.extend(validate_target(continuation.get("target"), f"{label}.target"))

    remediation = route.get("remediation")
    if not isinstance(remediation, list) or not remediation:
        errors.append(failure("route-remediation", f"{route_id} needs remediation"))
    else:
        for remediation_index, item in enumerate(remediation):
            label = f"{route_id}.remediation[{remediation_index}]"
            if not isinstance(item, dict) or set(item) != {"when", "target", "returnTo"}:
                errors.append(failure("route-remediation", f"{label} is invalid"))
                continue
            if not isinstance(item.get("when"), str) or not item["when"]:
                errors.append(failure("route-remediation", f"{label}.when is required"))
            if not isinstance(item.get("target"), str):
                errors.append(failure("route-remediation", f"{label}.target must be a path"))
            errors.extend(validate_remediation_return(item.get("returnTo"), f"{label}.returnTo"))

    edges = route.get("edges")
    if not isinstance(edges, list):
        errors.append(failure("route-edge-schema", f"{route_id}.edges must be a list"))
    else:
        for edge_index, edge in enumerate(edges):
            label = f"{route_id}.edges[{edge_index}]"
            if not isinstance(edge, dict) or set(edge) != {"kind", "from", "to", "rejoin"}:
                errors.append(failure("route-edge-schema", f"{label} is invalid"))
                continue
            if not isinstance(edge.get("kind"), str) or edge.get(
                "kind"
            ) not in ALLOWED_EDGE_KINDS:
                errors.append(failure("route-edge-schema", f"{label} kind is invalid"))
            if not isinstance(edge.get("from"), str):
                errors.append(failure("route-edge-schema", f"{label}.from must be a path"))
            edge_targets = edge.get("to")
            if (
                not isinstance(edge_targets, list)
                or not edge_targets
                or not all(isinstance(path, str) for path in edge_targets)
            ):
                errors.append(failure("route-edge-schema", f"{label}.to is invalid"))
            elif len(edge_targets) != len(set(edge_targets)):
                errors.append(failure("route-edge-duplicate", f"{label}.to repeats a target"))
            if edge.get("rejoin") is not None and not isinstance(edge.get("rejoin"), str):
                errors.append(failure("route-edge-schema", f"{label}.rejoin is invalid"))
    return errors


def validate_manifest(manifest: Any, freeze: dict[str, Any]) -> list[str]:
    if not isinstance(manifest, dict):
        return [failure("manifest-schema", "manifest must be a JSON object")]
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
    page_identities = [page["expectedIdentity"] for page in pages]
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
    if len(page_identities) != len(set(page_identities)):
        errors.append(failure("page-identity-duplicate", "expectedIdentity values must be unique"))

    baseline_set = set(freeze["baselinePaths"])
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
        expected_identity = page["path"][: -len(".html")]
        if page["expectedIdentity"] != expected_identity:
            errors.append(
                failure(
                    "page-identity",
                    f"{page['path']} expectedIdentity must be {expected_identity}",
                )
            )
        expected_carryover, expected_source_state = EXPECTED_PAGE_POLICIES[
            page["pageKind"]
        ]
        if page["evidenceCarryover"] != expected_carryover:
            errors.append(
                failure(
                    "evidence-carryover",
                    f"{page['path']} carryover must match {page['pageKind']}",
                )
            )
        actual_source_state = page["sourceDependencies"]["state"]
        source_state_matches = (
            actual_source_state in {"pending-t03", "registered"}
            if expected_source_state == "pending-t03"
            else actual_source_state == expected_source_state
        )
        if not source_state_matches:
            errors.append(
                failure(
                    "source-placeholder",
                    f"{page['path']} source state must match {page['pageKind']}",
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
    navigation_paths = {
        page["path"] for page in pages if page["pageKind"] == "navigation"
    }
    if navigation_paths != EXPECTED_NAVIGATION_PATHS:
        errors.append(
            failure("navigation-paths", f"navigation paths differ: {sorted(navigation_paths)}")
        )
    page_digest = hashlib.sha256(
        json.dumps(
            pages,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if page_digest != EXPECTED_PAGE_MATRIX_SHA256:
        errors.append(
            failure(
                "page-matrix",
                "reviewed page contract or Source mappings differ",
            )
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
            if not isinstance(compatibility.get("mode"), str) or compatibility.get(
                "mode"
            ) not in {"direct", "transition"}:
                errors.append(failure("compatibility-mode", f"{path} mode is invalid"))
            if not isinstance(targets, list) or not targets:
                errors.append(failure("compatibility-target", f"{path} needs targets"))
                continue
            target_paths = [
                target.get("path")
                for target in targets
                if isinstance(target, dict) and isinstance(target.get("path"), str)
            ]
            if len(target_paths) != len(set(target_paths)):
                errors.append(
                    failure("transition-target-duplicate", f"{path} repeats a final target")
                )
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
                target_paths = [
                    target.get("path")
                    for target in targets
                    if isinstance(target, dict) and isinstance(target.get("path"), str)
                ]
                if len(target_paths) != len(set(target_paths)):
                    errors.append(
                        failure(
                            "transition-target-duplicate",
                            f"{path} repeats a successor target",
                        )
                    )
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

    def require_route_member(path: str, route_id: str, label: str) -> None:
        require_canonical_lesson(path, label)
        if route_id not in membership_by_path.get(path, {}):
            errors.append(
                failure("route-membership", f"{label} is not a member of {route_id}")
            )

    def reachable_from(start: str, adjacency: dict[str, set[str]]) -> set[str]:
        reached = set()
        pending = [start]
        while pending:
            current = pending.pop()
            if current in reached:
                continue
            reached.add(current)
            pending.extend(adjacency.get(current, set()) - reached)
        return reached

    for route_id, route in route_by_id.items():
        entry = route["entry"]
        stop = route["stop"]
        require_route_member(entry, route_id, f"{route_id}.entry")
        if "entry" not in membership_by_path.get(entry, {}).get(route_id, set()):
            errors.append(failure("route-entry", f"{route_id} entry role is missing"))
        if route_id == "toolbox":
            if stop is not None or route["returnPolicy"] != "caller-provided-active-route":
                errors.append(
                    failure("toolbox-return", "toolbox must return to caller without Phase stop")
                )
            if any(edge["kind"] == "next" for edge in route["edges"]):
                errors.append(failure("toolbox-next", "toolbox must not claim universal next"))
            if len(route["continuations"]) != 1 or route["continuations"][0][
                "kind"
            ] != "return-to-caller":
                errors.append(
                    failure("route-continuation", "toolbox needs one dynamic return-to-caller")
                )
            if route["tocReturn"] != {
                "path": "toc.html",
                "fragment": "toolbox",
                "role": "catalog-fallback",
            }:
                errors.append(
                    failure("toolbox-return", "toolbox TOC target must be fallback-only")
                )
        else:
            require_route_member(stop, route_id, f"{route_id}.stop")
            if not {"stop", "exit-evidence"}.issubset(
                membership_by_path.get(stop, {}).get(route_id, set())
            ):
                errors.append(failure("route-stop", f"{route_id} stop roles are missing"))
            if route["returnPolicy"] != "fixed-toc-anchor":
                errors.append(failure("route-return", f"{route_id} return policy is invalid"))
            if route["tocReturn"]["role"] != "route-return":
                errors.append(
                    failure("route-return", f"{route_id} TOC target needs route-return role")
                )
        for target in route["readiness"]["targets"]:
            require_canonical_lesson(target, f"{route_id}.readiness")

        edge_signatures = [json.dumps(edge, sort_keys=True) for edge in route["edges"]]
        if len(edge_signatures) != len(set(edge_signatures)):
            errors.append(failure("route-edge-duplicate", f"{route_id} repeats an edge"))
        graph_nodes = {entry}
        if stop is not None:
            graph_nodes.add(stop)
        adjacency: dict[str, set[str]] = {}
        for index, edge in enumerate(route["edges"]):
            label = f"{route_id}.edges[{index}]"
            edge_from = edge["from"]
            require_route_member(edge_from, route_id, f"{label}.from")
            graph_nodes.add(edge_from)
            adjacency.setdefault(edge_from, set()).update(edge["to"])
            for target in edge["to"]:
                require_route_member(target, route_id, f"{label}.to")
                graph_nodes.add(target)
            rejoin = edge["rejoin"]
            if rejoin is not None:
                require_route_member(rejoin, route_id, f"{label}.rejoin")
                graph_nodes.add(rejoin)

        member_paths = {
            path for path, memberships in membership_by_path.items() if route_id in memberships
        }
        ungraphed = sorted(member_paths - graph_nodes)
        if ungraphed:
            errors.append(
                failure("route-member-graph", f"{route_id} members are outside its graph: {ungraphed}")
            )
        reached = reachable_from(entry, adjacency)
        unreachable = sorted(graph_nodes - reached)
        if unreachable:
            errors.append(
                failure("route-reachability", f"{route_id} has unreachable nodes: {unreachable}")
            )
        if stop is not None and stop not in reached:
            errors.append(failure("route-stop-reachability", f"{route_id} stop is unreachable"))
        for index, edge in enumerate(route["edges"]):
            rejoin = edge["rejoin"]
            if rejoin is None:
                continue
            for target in edge["to"]:
                if rejoin not in reachable_from(target, adjacency):
                    errors.append(
                        failure(
                            "route-rejoin",
                            f"{route_id}.edges[{index}] target {target} cannot reach {rejoin}",
                        )
                    )

        continuation_signatures = []
        for index, continuation in enumerate(route["continuations"]):
            label = f"{route_id}.continuations[{index}]"
            continuation_signatures.append(json.dumps(continuation, sort_keys=True))
            kind = continuation["kind"]
            if kind == "return-to-caller":
                if route_id != "toolbox":
                    errors.append(
                        failure("route-continuation", f"{label} is only valid for toolbox")
                    )
                continue
            target = continuation["target"]
            target_path = target["path"]
            target_route = continuation["routeId"]
            if kind in {"route", "requires-readiness", "optional-route", "llm-wiki-overlay"}:
                if target_route not in route_by_id:
                    errors.append(
                        failure("route-continuation", f"{label} routeId is unknown")
                    )
                elif target_path != route_by_id[target_route]["entry"]:
                    errors.append(
                        failure(
                            "route-continuation-target",
                            f"{label} must target {target_route}'s entry",
                        )
                    )
                if target["fragment"] is not None or target["role"] != "route-entry":
                    errors.append(
                        failure(
                            "route-continuation-target",
                            f"{label} must use the target route-entry identity",
                        )
                    )
            elif kind in {"review-reentry", "conditional-review-reentry"}:
                if target_route not in route_by_id:
                    errors.append(
                        failure("route-continuation", f"{label} routeId is unknown")
                    )
                else:
                    require_route_member(target_path, target_route, f"{label}.target")
                    if "review-reentry" not in membership_by_path.get(target_path, {}).get(
                        target_route, set()
                    ):
                        errors.append(
                            failure(
                                "route-continuation-target",
                                f"{label} target lacks review-reentry role",
                            )
                        )
                if target["fragment"] is not None or target["role"] != "review-reentry":
                    errors.append(
                        failure(
                            "route-continuation-target",
                            f"{label} must use the review-reentry identity",
                        )
                    )
            elif kind == "return-to-catalog":
                if target_route is not None or target != route["tocReturn"]:
                    errors.append(
                        failure(
                            "route-continuation-target",
                            f"{label} must equal the route TOC return target",
                        )
                    )
        if len(continuation_signatures) != len(set(continuation_signatures)):
            errors.append(
                failure("route-continuation-duplicate", f"{route_id} repeats a continuation")
            )

        for index, remediation in enumerate(route["remediation"]):
            label = f"{route_id}.remediation[{index}]"
            require_canonical_lesson(remediation["target"], f"{label}.target")
            return_to = remediation["returnTo"]
            if isinstance(return_to, str):
                require_route_member(return_to, route_id, f"{label}.returnTo")
            elif route_id != "toolbox":
                errors.append(
                    failure("route-remediation", f"{label} dynamic return is toolbox-only")
                )
    route_digest = hashlib.sha256(
        json.dumps(
            routes,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if route_digest != EXPECTED_ROUTE_CONTRACT_SHA256:
        errors.append(
            failure(
                "route-contract",
                "Issue #13 route graph or remediation contract differs",
            )
        )
    return errors


def validate_thin_slice(manifest: dict[str, Any]) -> list[str]:
    pages = manifest.get("pages")
    routes = manifest.get("routes")
    if (
        not isinstance(pages, list)
        or not all(
            isinstance(page, dict) and isinstance(page.get("path"), str) for page in pages
        )
        or not isinstance(routes, list)
        or not all(
            isinstance(route, dict) and isinstance(route.get("id"), str) for route in routes
        )
    ):
        return [failure("thin-slice-skipped", "validated pages and routes are required")]
    by_path = {page["path"]: page for page in pages}
    route_by_id = {route["id"]: route for route in routes}
    expected_kinds = {
        "index.html": "navigation",
        "lessons/001-0001-four-claude-surfaces.html": "canonical-lesson",
        "lessons/001-0002-first-session-read-only.html": "compatibility",
        "lessons/001-0011-explore-plan-implement-commit.html": "compatibility",
        "lessons/001-0002-define-route-readiness.html": "canonical-lesson",
        "lessons/004-0007-handoff-to-claude-code.html": "compatibility",
        "reference/agent-operations-safety.html": "canonical-reference",
        "reference/ai-workflow-case-library.html": "compatibility",
        "reference/ai-workflow-skill-composer.html": "deprecation",
    }
    errors = []
    for path, kind in expected_kinds.items():
        if path not in by_path or by_path[path].get("pageKind") != kind:
            errors.append(failure("thin-slice", f"{path} must be {kind}"))

    def expect_compatibility(path: str, mode: str, targets: list[dict[str, Any]]) -> None:
        value = by_path.get(path, {}).get("compatibility")
        if (
            not isinstance(value, dict)
            or value.get("mode") != mode
            or value.get("finalTargets") != targets
        ):
            errors.append(failure("thin-slice", f"{path} exact Compatibility targets differ"))

    expect_compatibility(
        "lessons/001-0002-first-session-read-only.html",
        "direct",
        [
            {
                "path": "lessons/001-0004-prepare-claude-code-session.html",
                "fragment": None,
                "role": "primary-successor",
            }
        ],
    )
    expect_compatibility(
        "lessons/001-0011-explore-plan-implement-commit.html",
        "transition",
        [
            {
                "path": "lessons/006-0001-choose-engineering-route.html",
                "fragment": None,
                "role": "route-entry",
            },
            {
                "path": "lessons/006-0007-implement-and-create-review-checkpoint.html",
                "fragment": None,
                "role": "implementation",
            },
            {
                "path": "lessons/006-0008-review-final-candidate.html",
                "fragment": None,
                "role": "review",
            },
            {
                "path": "lessons/006-0009-complete-engineering-closeout.html",
                "fragment": None,
                "role": "closeout",
            },
        ],
    )
    expect_compatibility(
        "lessons/004-0007-handoff-to-claude-code.html",
        "transition",
        [
            {
                "path": "lessons/004-0007-assemble-design-handoff-bundle.html",
                "fragment": None,
                "role": "primary-successor",
            },
            {
                "path": "lessons/002-0001-choose-toolbox-lesson.html",
                "fragment": None,
                "role": "toolbox-continuation",
            },
            {
                "path": "lessons/006-0001-choose-engineering-route.html",
                "fragment": None,
                "role": "engineering-continuation",
            },
        ],
    )
    expect_compatibility(
        "reference/ai-workflow-case-library.html",
        "direct",
        [
            {
                "path": "reference/ai-functional-workflow-case-library.html",
                "fragment": "product",
                "role": "canonical-case-hub",
            }
        ],
    )

    deprecation = by_path.get("reference/ai-workflow-skill-composer.html", {}).get(
        "deprecation"
    )
    expected_successor = [
        {
            "path": "lessons/009-0003-choose-workflow-package.html",
            "fragment": None,
            "role": "workflow-package-selector",
        }
    ]
    if not isinstance(deprecation, dict) or deprecation.get(
        "successorTargets"
    ) != expected_successor:
        errors.append(failure("thin-slice", "Deprecation successor differs"))

    def membership_roles(path: str, route_id: str) -> list[str] | None:
        memberships = by_path.get(path, {}).get("routeMemberships")
        if not isinstance(memberships, list):
            return None
        for membership in memberships:
            if isinstance(membership, dict) and membership.get("routeId") == route_id:
                roles = membership.get("roles")
                return roles if isinstance(roles, list) else None
        return None

    expected_conditional_roles = ["conditional", "feedback", "tangible-win"]
    for path, route_id in (
        ("lessons/004-0003-sync-design-system.html", "design-delivery"),
        ("lessons/007-0006-diagnose-with-trace.html", "browser-evidence"),
    ):
        if membership_roles(path, route_id) != expected_conditional_roles:
            errors.append(failure("thin-slice", f"{path} conditional role differs"))
    if by_path.get("lessons/004-0003-sync-design-system.html", {}).get(
        "contentDisposition", {}
    ).get("actions") != ["conditionalize", "keep"]:
        errors.append(failure("thin-slice", "Design-system conditional disposition differs"))
    if membership_roles(
        "lessons/006-0008-review-final-candidate.html", "engineering-delivery"
    ) != ["feedback", "review-reentry", "tangible-win"]:
        errors.append(failure("thin-slice", "engineering review-reentry role differs"))

    def edge_signatures(route_id: str) -> list[tuple[Any, ...]] | None:
        route = route_by_id.get(route_id)
        if not isinstance(route, dict) or not isinstance(route.get("edges"), list):
            return None
        signatures = []
        for edge in route["edges"]:
            try:
                signatures.append(
                    (
                        edge["kind"],
                        by_path[edge["from"]]["canonicalCoordinate"],
                        tuple(by_path[target]["canonicalCoordinate"] for target in edge["to"]),
                        by_path[edge["rejoin"]]["canonicalCoordinate"]
                        if edge["rejoin"] is not None
                        else None,
                    )
                )
            except (KeyError, TypeError):
                return None
        return signatures

    expected_graphs = {
        "knowledge-delivery": [
            ("next", "003-0001", ("003-0002",), None),
            (
                "choose-one",
                "003-0002",
                ("003-0003", "003-0008", "003-0009", "003-0010"),
                "003-0003",
            ),
            ("next", "003-0008", ("003-0003",), None),
            ("next", "003-0009", ("003-0003",), None),
            ("next", "003-0010", ("003-0003",), None),
            ("choose-one", "003-0003", ("003-0004", "003-0007"), "003-0005"),
            ("next", "003-0004", ("003-0005",), None),
            ("next", "003-0007", ("003-0005",), None),
            ("next", "003-0005", ("003-0006",), None),
        ],
        "design-delivery": [
            ("next", "004-0001", ("004-0002",), None),
            ("choose-one", "004-0002", ("004-0003", "004-0004"), "004-0004"),
            ("next", "004-0003", ("004-0004",), None),
            ("next", "004-0004", ("004-0005",), None),
            ("next", "004-0005", ("004-0006",), None),
            ("next", "004-0006", ("004-0007",), None),
        ],
        "engineering-delivery": [
            (
                "choose-one",
                "006-0001",
                ("006-0002", "006-0010", "006-0011", "006-0012", "006-0013"),
                "006-0003",
            ),
            ("next", "006-0002", ("006-0003",), None),
            ("choose-one", "006-0003", ("006-0004", "006-0005"), "006-0005"),
            ("next", "006-0004", ("006-0005",), None),
            ("next", "006-0005", ("006-0006",), None),
            ("next", "006-0006", ("006-0007",), None),
            ("next", "006-0007", ("006-0008",), None),
            ("next", "006-0008", ("006-0009",), None),
            ("next", "006-0010", ("006-0003",), None),
            ("next", "006-0011", ("006-0003",), None),
            ("next", "006-0012", ("006-0003",), None),
            ("next", "006-0013", ("006-0014",), None),
            ("next", "006-0014", ("006-0003",), None),
        ],
        "browser-evidence": [
            ("next", "007-0001", ("007-0002",), None),
            ("next", "007-0002", ("007-0003",), None),
            ("next", "007-0003", ("007-0004",), None),
            ("next", "007-0004", ("007-0005",), None),
            ("choose-one", "007-0005", ("007-0006", "007-0007"), "007-0007"),
            ("next", "007-0006", ("007-0007",), None),
        ],
        "agent-operations": [
            ("next", "008-0001", ("008-0002",), None),
            ("next", "008-0002", ("008-0003",), None),
            ("choose-one", "008-0003", ("008-0004", "008-0008"), "008-0005"),
            ("next", "008-0004", ("008-0005",), None),
            ("next", "008-0005", ("008-0006",), None),
            ("next", "008-0008", ("008-0005",), None),
            ("next", "008-0006", ("008-0007",), None),
        ],
        "workflow-standardization": [
            ("choose-one", "009-0001", ("009-0002", "009-0009"), "009-0003"),
            ("next", "009-0002", ("009-0003",), None),
            ("next", "009-0009", ("009-0003",), None),
            (
                "choose-one",
                "009-0003",
                ("009-0004", "009-0005", "009-0006", "009-0007"),
                "009-0008",
            ),
            ("next", "009-0004", ("009-0008",), None),
            ("next", "009-0005", ("009-0008",), None),
            ("next", "009-0006", ("009-0008",), None),
            ("next", "009-0007", ("009-0008",), None),
        ],
    }
    for route_id, expected_signatures in expected_graphs.items():
        if edge_signatures(route_id) != expected_signatures:
            errors.append(failure("thin-slice", f"{route_id} graph signature differs"))

    expected_knowledge_overlay = {
        "kind": "llm-wiki-overlay",
        "routeId": "agent-operations",
        "target": {
            "path": "lessons/008-0001-define-deterministic-check.html",
            "fragment": None,
            "role": "route-entry",
        },
    }
    knowledge_continuations = route_by_id.get("knowledge-delivery", {}).get(
        "continuations", []
    )
    if expected_knowledge_overlay not in knowledge_continuations:
        errors.append(failure("thin-slice", "Knowledge overlay must target the Phase 8 entry"))
    if any(
        continuation.get("kind") == "llm-wiki-overlay"
        for continuation in route_by_id.get("agent-operations", {}).get("continuations", [])
        if isinstance(continuation, dict)
    ):
        errors.append(failure("thin-slice", "Phase 8 must not duplicate the overlay continuation"))
    expected_review_reentry = {
        "kind": "review-reentry",
        "routeId": "engineering-delivery",
        "target": {
            "path": "lessons/006-0008-review-final-candidate.html",
            "fragment": None,
            "role": "review-reentry",
        },
    }
    if route_by_id.get("browser-evidence", {}).get("continuations") != [
        expected_review_reentry
    ]:
        errors.append(failure("thin-slice", "Phase 7 review re-entry differs"))
    return errors


def run_self_test(manifest: dict[str, Any], freeze: dict[str, Any]) -> list[str]:
    errors = []
    cases: list[tuple[str, Any, str]] = [
        ("null manifest root", None, "manifest-schema"),
        ("boolean manifest root", False, "manifest-schema"),
        ("numeric manifest root", 0.25, "manifest-schema"),
        ("list manifest root", [{"unexpected": None}], "manifest-schema"),
    ]

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

    malformed_edge = copy.deepcopy(manifest)
    next(route for route in malformed_edge["routes"] if route["id"] == "toolbox")[
        "edges"
    ][0] = "not-an-object"
    cases.append(("malformed edge", malformed_edge, "route-edge-schema"))

    malformed_continuation_target = copy.deepcopy(manifest)
    malformed_continuation_target["routes"][0]["continuations"][0][
        "target"
    ] = "not-an-object"
    cases.append(
        (
            "malformed continuation target",
            malformed_continuation_target,
            "target-schema",
        )
    )

    malformed_dynamic_return = copy.deepcopy(manifest)
    next(
        route for route in malformed_dynamic_return["routes"] if route["id"] == "toolbox"
    )["continuations"][0]["from"] = "not-a-list"
    cases.append(
        ("malformed dynamic return", malformed_dynamic_return, "route-continuation")
    )

    container_origin = copy.deepcopy(manifest)
    container_origin["pages"][0]["origin"] = []
    cases.append(("container origin enum", container_origin, "page-origin"))

    container_page_kind = copy.deepcopy(manifest)
    container_page_kind["pages"][0]["pageKind"] = {}
    cases.append(("container pageKind enum", container_page_kind, "page-kind"))

    container_source_state = copy.deepcopy(manifest)
    container_source_state["pages"][0]["sourceDependencies"]["state"] = []
    cases.append(
        ("container Source state enum", container_source_state, "source-placeholder")
    )

    registered_without_ids = copy.deepcopy(manifest)
    registered_without_ids["pages"][0]["sourceDependencies"] = {
        "state": "registered",
        "anchorIds": [],
    }
    cases.append(
        ("registered Source without IDs", registered_without_ids, "source-placeholder")
    )

    pending_with_ids = copy.deepcopy(manifest)
    pending_with_ids["pages"][0]["sourceDependencies"] = {
        "state": "pending-t03",
        "anchorIds": ["fabricated-anchor"],
    }
    cases.append(("pending Source with IDs", pending_with_ids, "source-placeholder"))

    invalid_migration_status = copy.deepcopy(manifest)
    invalid_migration_status["pages"][0]["migrationStatus"] = "complete"
    cases.append(
        ("invalid migration status", invalid_migration_status, "migration-status")
    )

    container_carryover = copy.deepcopy(manifest)
    container_carryover["pages"][0]["evidenceCarryover"] = {}
    cases.append(
        ("container carryover enum", container_carryover, "evidence-carryover")
    )

    container_route_kind = copy.deepcopy(manifest)
    container_route_kind["routes"][0]["kind"] = []
    cases.append(("container route kind enum", container_route_kind, "route-schema"))

    container_readiness_mode = copy.deepcopy(manifest)
    container_readiness_mode["routes"][0]["readiness"]["mode"] = {}
    cases.append(
        ("container readiness mode enum", container_readiness_mode, "route-readiness")
    )

    container_continuation_kind = copy.deepcopy(manifest)
    container_continuation_kind["routes"][0]["continuations"][0]["kind"] = []
    cases.append(
        (
            "container continuation kind enum",
            container_continuation_kind,
            "route-continuation-kind",
        )
    )

    container_edge_kind = copy.deepcopy(manifest)
    container_edge_kind["routes"][0]["edges"][0]["kind"] = {}
    cases.append(
        ("container edge kind enum", container_edge_kind, "route-edge-schema")
    )

    container_compatibility_mode = copy.deepcopy(manifest)
    next(
        page
        for page in container_compatibility_mode["pages"]
        if page["pageKind"] == "compatibility"
    )["compatibility"]["mode"] = []
    cases.append(
        (
            "container Compatibility mode enum",
            container_compatibility_mode,
            "compatibility-mode",
        )
    )

    container_toc_fragment = copy.deepcopy(manifest)
    container_toc_fragment["routes"][0]["tocReturn"]["fragment"] = []
    cases.append(
        ("container TOC fragment enum", container_toc_fragment, "target-fragment")
    )

    legal_route_kind_swap = copy.deepcopy(manifest)
    next(
        route
        for route in legal_route_kind_swap["routes"]
        if route["id"] == "common-foundation"
    )["kind"] = "task"
    cases.append(("legal route kind swap", legal_route_kind_swap, "route-contract"))

    legal_readiness_mode_swap = copy.deepcopy(manifest)
    next(
        route
        for route in legal_readiness_mode_swap["routes"]
        if route["id"] == "workflow-standardization"
    )["readiness"]["mode"] = "all-of"
    cases.append(
        ("legal readiness mode swap", legal_readiness_mode_swap, "route-contract")
    )

    legal_readiness_target_swap = copy.deepcopy(manifest)
    next(
        route
        for route in legal_readiness_target_swap["routes"]
        if route["id"] == "common-foundation"
    )["readiness"]["targets"] = [
        "lessons/012-0007-complete-governance-lifecycle-policy.html"
    ]
    cases.append(
        ("legal readiness target swap", legal_readiness_target_swap, "route-contract")
    )

    legal_continuation_kind_swap = copy.deepcopy(manifest)
    next(
        route
        for route in legal_continuation_kind_swap["routes"]
        if route["id"] == "common-foundation"
    )["continuations"][0]["kind"] = "requires-readiness"
    cases.append(
        (
            "legal continuation kind swap",
            legal_continuation_kind_swap,
            "route-contract",
        )
    )

    legal_edge_kind_swap = copy.deepcopy(manifest)
    next(
        route
        for route in legal_edge_kind_swap["routes"]
        if route["id"] == "common-foundation"
    )["edges"][0]["kind"] = "optional-continuation"
    cases.append(("legal edge kind swap", legal_edge_kind_swap, "route-contract"))

    malformed_remediation_return = copy.deepcopy(manifest)
    next(
        route
        for route in malformed_remediation_return["routes"]
        if route["id"] == "toolbox"
    )["remediation"][0]["returnTo"] = {"source": "missing-fallback"}
    cases.append(
        (
            "malformed remediation return",
            malformed_remediation_return,
            "route-remediation",
        )
    )

    duplicate_identity = copy.deepcopy(manifest)
    duplicate_identity["pages"][1]["expectedIdentity"] = duplicate_identity["pages"][0][
        "expectedIdentity"
    ]
    cases.append(("duplicate identity", duplicate_identity, "page-identity-duplicate"))

    wrong_identity = copy.deepcopy(manifest)
    wrong_identity["pages"][1]["expectedIdentity"] = "wrong-identity"
    cases.append(("wrong path identity", wrong_identity, "page-identity"))

    wrong_source_state = copy.deepcopy(manifest)
    next(
        page
        for page in wrong_source_state["pages"]
        if page["pageKind"] == "canonical-lesson"
    )["sourceDependencies"]["state"] = "not-applicable"
    cases.append(("wrong source state", wrong_source_state, "source-placeholder"))

    wrong_carryover = copy.deepcopy(manifest)
    next(
        page for page in wrong_carryover["pages"] if page["pageKind"] == "canonical-lesson"
    )["evidenceCarryover"] = "not-applicable"
    cases.append(("wrong carryover", wrong_carryover, "evidence-carryover"))

    wrong_navigation = copy.deepcopy(manifest)
    next(page for page in wrong_navigation["pages"] if page["path"] == "index.html")[
        "pageKind"
    ] = "canonical-reference"
    cases.append(("wrong navigation inventory", wrong_navigation, "navigation-paths"))

    cross_route_edge = copy.deepcopy(manifest)
    next(
        route for route in cross_route_edge["routes"] if route["id"] == "common-foundation"
    )["edges"][0]["to"][0] = "lessons/012-0007-complete-governance-lifecycle-policy.html"
    cases.append(("cross-route edge", cross_route_edge, "route-membership"))

    wrong_membership = copy.deepcopy(manifest)
    next(
        page
        for page in wrong_membership["pages"]
        if page["path"] == "lessons/003-0004-produce-reviewable-knowledge-slice.html"
    )["routeMemberships"][0]["routeId"] = "governance-lifecycle"
    cases.append(("wrong route membership", wrong_membership, "route-membership"))

    unknown_continuation_kind = copy.deepcopy(manifest)
    unknown_continuation_kind["routes"][0]["continuations"][0]["kind"] = "invented"
    cases.append(
        (
            "unknown continuation kind",
            unknown_continuation_kind,
            "route-continuation-kind",
        )
    )

    wrong_continuation_target = copy.deepcopy(manifest)
    continuation = wrong_continuation_target["routes"][0]["continuations"][0]
    continuation["target"]["path"] = "lessons/003-0001-select-knowledge-deliverable.html"
    cases.append(
        (
            "wrong continuation target",
            wrong_continuation_target,
            "route-continuation-target",
        )
    )

    wrong_review_role = copy.deepcopy(manifest)
    next(
        route for route in wrong_review_role["routes"] if route["id"] == "browser-evidence"
    )["continuations"][0]["target"]["role"] = "route-entry"
    cases.append(("wrong review target role", wrong_review_role, "route-continuation-target"))

    duplicate_transition_target = copy.deepcopy(manifest)
    transition = next(
        page
        for page in duplicate_transition_target["pages"]
        if page["path"] == "lessons/001-0011-explore-plan-implement-commit.html"
    )["compatibility"]["finalTargets"]
    transition[1] = copy.deepcopy(transition[0])
    cases.append(
        (
            "duplicate transition target",
            duplicate_transition_target,
            "transition-target-duplicate",
        )
    )

    duplicate_edge = copy.deepcopy(manifest)
    edge_route = next(
        route for route in duplicate_edge["routes"] if route["id"] == "common-foundation"
    )
    edge_route["edges"].append(copy.deepcopy(edge_route["edges"][0]))
    cases.append(("duplicate edge", duplicate_edge, "route-edge-duplicate"))

    unreachable_stop = copy.deepcopy(manifest)
    next(
        route for route in unreachable_stop["routes"] if route["id"] == "common-foundation"
    )["edges"] = []
    cases.append(("unreachable route stop", unreachable_stop, "route-stop-reachability"))

    wrong_toolbox_remediation = copy.deepcopy(manifest)
    next(
        route
        for route in wrong_toolbox_remediation["routes"]
        if route["id"] == "toolbox"
    )["remediation"][0]["target"] = "lessons/001-0002-define-route-readiness.html"
    cases.append(
        (
            "wrong toolbox remediation",
            wrong_toolbox_remediation,
            "route-contract",
        )
    )

    missing_origin_remediation = copy.deepcopy(manifest)
    next(
        route
        for route in missing_origin_remediation["routes"]
        if route["id"] == "workflow-standardization"
    )["remediation"].pop()
    cases.append(
        (
            "missing originating-route remediation",
            missing_origin_remediation,
            "route-contract",
        )
    )

    wrong_general_remediation_target = copy.deepcopy(manifest)
    next(
        route
        for route in wrong_general_remediation_target["routes"]
        if route["id"] == "common-foundation"
    )["remediation"][0][
        "target"
    ] = "lessons/012-0007-complete-governance-lifecycle-policy.html"
    cases.append(
        (
            "wrong general remediation target",
            wrong_general_remediation_target,
            "route-contract",
        )
    )

    wrong_general_remediation_condition = copy.deepcopy(manifest)
    next(
        route
        for route in wrong_general_remediation_condition["routes"]
        if route["id"] == "common-foundation"
    )["remediation"][0]["when"] = "invented-gap"
    cases.append(
        (
            "wrong general remediation condition",
            wrong_general_remediation_condition,
            "route-contract",
        )
    )

    wrong_general_remediation_return = copy.deepcopy(manifest)
    next(
        route
        for route in wrong_general_remediation_return["routes"]
        if route["id"] == "common-foundation"
    )["remediation"][0][
        "returnTo"
    ] = "lessons/001-0001-four-claude-surfaces.html"
    cases.append(
        (
            "wrong general remediation return",
            wrong_general_remediation_return,
            "route-contract",
        )
    )

    exact_target_swap = copy.deepcopy(manifest)
    next(
        page
        for page in exact_target_swap["pages"]
        if page["path"] == "lessons/001-0002-first-session-read-only.html"
    )["compatibility"]["finalTargets"][0][
        "path"
    ] = "lessons/001-0003-complete-cowork-starter.html"
    cases.append(("exact target swap", exact_target_swap, "page-matrix"))

    unsampled_disposition = copy.deepcopy(manifest)
    next(
        page
        for page in unsampled_disposition["pages"]
        if page["path"] == "lessons/001-0003-read-only-repo-tour.html"
    )["contentDisposition"]["actions"] = ["keep"]
    cases.append(
        ("unsampled disposition change", unsampled_disposition, "page-matrix")
    )

    unsampled_target = copy.deepcopy(manifest)
    next(
        page
        for page in unsampled_target["pages"]
        if page["path"] == "lessons/001-0003-read-only-repo-tour.html"
    )["compatibility"]["finalTargets"][0][
        "path"
    ] = "lessons/001-0004-prepare-claude-code-session.html"
    cases.append(("unsampled target change", unsampled_target, "page-matrix"))

    unsampled_fragment = copy.deepcopy(manifest)
    next(
        page
        for page in unsampled_fragment["pages"]
        if page["path"] == "reference/ai-developer-workflow-case-library.html"
    )["compatibility"]["finalTargets"][0]["fragment"] = "founder"
    cases.append(("unsampled fragment change", unsampled_fragment, "page-matrix"))

    removed_conditional_role = copy.deepcopy(manifest)
    roles = next(
        page
        for page in removed_conditional_role["pages"]
        if page["path"] == "lessons/004-0003-sync-design-system.html"
    )["routeMemberships"][0]["roles"]
    roles.remove("conditional")
    cases.append(("removed conditional role", removed_conditional_role, "page-matrix"))

    removed_conditional_disposition = copy.deepcopy(manifest)
    next(
        page
        for page in removed_conditional_disposition["pages"]
        if page["path"] == "lessons/004-0003-sync-design-system.html"
    )["contentDisposition"]["actions"] = ["keep"]
    cases.append(
        (
            "removed conditional disposition",
            removed_conditional_disposition,
            "page-matrix",
        )
    )

    for name, mutated, expected_code in cases:
        try:
            actual = validate_manifest(mutated, freeze)
            if not actual:
                actual = validate_thin_slice(mutated)
        except Exception as error:
            errors.append(
                failure(
                    "negative-fixture",
                    f"{name} crashed instead of returning blockers: {type(error).__name__}: {error}",
                )
            )
            continue
        if expected_code not in blocker_codes(actual):
            errors.append(
                failure(
                    "negative-fixture",
                    f"{name} did not fail with [{expected_code}]; got {sorted(blocker_codes(actual))}",
                )
            )
        if exit_status(actual, report_only=True) != 0:
            errors.append(
                failure("negative-fixture", f"{name} blocked report-only verification")
            )
        if exit_status(actual, report_only=False) == 0:
            errors.append(failure("negative-fixture", f"{name} failed open in strict mode"))

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

    try:
        manifest_errors = validate_manifest(manifest, freeze)
        thin_slice_errors = (
            validate_thin_slice(manifest)
            if not manifest_errors
            else [failure("thin-slice-skipped", "valid manifest is required")]
        )
    except Exception as error:
        manifest_errors = [
            failure(
                "validator-runtime",
                f"validation raised {type(error).__name__}: {error}",
            )
        ]
        thin_slice_errors = [
            failure("thin-slice-skipped", "validator runtime blocker must be resolved")
        ]
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
