#!/usr/bin/env python3
"""Trace Source registry state without enforcing the publication gate."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


EXPECTED_AUTHORITY = {
    "registry": "source-anchors.json",
    "pageMappings": "docs/migration/course-migration-manifest.json",
}
EXPECTED_DRIFT_WINDOWS = {"high": 30, "medium": 90, "lower": 365}
EXPECTED_COVERAGE_MODE = "migration-release-candidate"
EXPECTED_NEXT_WAVE = "maintainer-sign-off"
PROFILE_CONTRACTS = {
    "executable-recipe": {
        "evidenceMethod": "command-reproduction",
        "requiredMetadata": [
            "versionAnchor",
            "declaredEnvironment",
            "steps",
            "expectedEvidence",
        ],
    },
    "surface-procedure": {
        "evidenceMethod": "surface-observation",
        "requiredMetadata": [
            "surfacePath",
            "availabilityAssumptions",
            "expectedEvidence",
        ],
    },
    "principle-only": {
        "evidenceMethod": "contract-inspection",
        "requiredMetadata": ["principleStatement", "sources"],
    },
}
EXPECTED_STATE_MODEL = {
    "publication": ["draft", "active", "inactive"],
    "freshness": ["current", "due", "stale"],
    "gate": ["pass", "blocked"],
    "publicationTransitions": {
        "draft": ["active", "inactive"],
        "active": ["inactive"],
        "inactive": ["draft"],
    },
    "freshnessTransitions": {
        "current": ["due", "stale"],
        "due": ["current", "stale"],
        "stale": ["current"],
    },
    "gateDerivation": "deterministic-not-authored",
}
ALLOWED_PAGE_STATES = {"pending-t03", "registered", "not-applicable"}
MOVING_VERSION_IDENTITIES = {"latest", "stable", "main", "head", "trunk"}

StatusFetcher = Callable[[str], int]


def blocker(code: str, message: str, subject: str | None = None) -> dict[str, str]:
    result = {"code": code, "message": message}
    if subject:
        result["subject"] = subject
    return result


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def nonempty_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(nonempty_string(item) for item in value)
    )


def nonempty_string_mapping(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and bool(value)
        and all(nonempty_string(key) and nonempty_string(item) for key, item in value.items())
    )


def parse_date(value: Any) -> date | None:
    if not nonempty_string(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def valid_https_url(value: Any) -> bool:
    if not nonempty_string(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def add_required_string_blocker(
    errors: list[dict[str, str]],
    container: dict[str, Any],
    key: str,
    code: str,
    subject: str,
) -> None:
    if not nonempty_string(container.get(key)):
        errors.append(blocker(code, f"{key} must be a non-empty string", subject))


def validate_top_level(registry: dict[str, Any], errors: list[dict[str, str]]) -> None:
    if registry.get("schemaVersion") != 1:
        errors.append(blocker("registry-schema", "schemaVersion must be 1"))

    authority = registry.get("authority")
    if not isinstance(authority, dict):
        errors.append(blocker("registry-authority", "authority must be an object"))
    else:
        for key, expected in EXPECTED_AUTHORITY.items():
            if authority.get(key) != expected:
                errors.append(
                    blocker(
                        "registry-authority",
                        f"authority.{key} must be {expected}",
                    )
                )

    if registry.get("gateMode") != "report-only":
        errors.append(
            blocker("gate-mode", "T03 gateMode must remain report-only")
        )

    coverage = registry.get("coverage")
    if not isinstance(coverage, dict):
        errors.append(blocker("coverage", "coverage must be an object"))
    else:
        if coverage.get("mode") != EXPECTED_COVERAGE_MODE:
            errors.append(
                blocker(
                    "coverage",
                    f"coverage mode must be {EXPECTED_COVERAGE_MODE}",
                )
            )
        if coverage.get("complete") is not True:
            errors.append(
                blocker(
                    "coverage",
                    "full candidate coverage must be complete before Maintainer sign-off",
                )
            )
        if coverage.get("nextWave") != EXPECTED_NEXT_WAVE:
            errors.append(
                blocker(
                    "coverage",
                    f"coverage nextWave must be {EXPECTED_NEXT_WAVE}",
                )
            )

    if registry.get("driftWindowsDays") != EXPECTED_DRIFT_WINDOWS:
        errors.append(
            blocker("drift-windows", "drift windows must be high=30, medium=90, lower=365")
        )

    if registry.get("stateModel") != EXPECTED_STATE_MODEL:
        errors.append(
            blocker(
                "state-model",
                "Publication, Freshness, Gate states and transitions differ from the approved model",
            )
        )

    profiles = registry.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != set(PROFILE_CONTRACTS):
        errors.append(
            blocker("source-profiles", "all three approved Source profiles are required")
        )
        return
    for profile, contract in PROFILE_CONTRACTS.items():
        definition = profiles.get(profile)
        if not isinstance(definition, dict):
            errors.append(
                blocker("source-profiles", f"{profile} definition must be an object")
            )
            continue
        if definition.get("evidenceMethod") != contract["evidenceMethod"]:
            errors.append(
                blocker(
                    "source-profiles",
                    f"{profile} evidenceMethod must be {contract['evidenceMethod']}",
                )
            )
        if definition.get("requiredMetadata") != contract["requiredMetadata"]:
            errors.append(
                blocker(
                    "source-profiles",
                    f"{profile} requiredMetadata differs from the approved contract",
                )
            )


def validate_sources(
    anchor: dict[str, Any],
    anchor_id: str,
    as_of: date,
    errors: list[dict[str, str]],
) -> set[str]:
    sources = anchor.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(blocker("source-metadata", "sources must be non-empty", anchor_id))
        return set()

    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        subject = f"{anchor_id}.sources[{index}]"
        if not isinstance(source, dict):
            errors.append(blocker("source-metadata", "source must be an object", subject))
            continue
        source_id = source.get("id")
        if not nonempty_string(source_id):
            errors.append(blocker("source-metadata", "source id is required", subject))
        elif source_id in source_ids:
            errors.append(blocker("source-metadata", "source id must be unique", subject))
        else:
            source_ids.add(source_id)
        if not valid_https_url(source.get("url")):
            errors.append(blocker("source-metadata", "source URL must use HTTPS", subject))
        add_required_string_blocker(errors, source, "kind", "source-metadata", subject)
        source_checked_at = parse_date(source.get("checkedAt"))
        if source_checked_at is None:
            errors.append(
                blocker("source-metadata", "checkedAt must use YYYY-MM-DD", subject)
            )
        elif source_checked_at > as_of:
            errors.append(
                blocker("source-metadata", "checkedAt cannot be in the future", subject)
            )
    return source_ids


def validate_conflicts(
    anchor: dict[str, Any],
    anchor_id: str,
    errors: list[dict[str, str]],
) -> bool:
    conflicts = anchor.get("conflicts")
    if not isinstance(conflicts, list):
        errors.append(blocker("conflict-metadata", "conflicts must be a list", anchor_id))
        return True

    required_unresolved = False
    for index, conflict in enumerate(conflicts):
        subject = f"{anchor_id}.conflicts[{index}]"
        if not isinstance(conflict, dict):
            errors.append(blocker("conflict-metadata", "conflict must be an object", subject))
            required_unresolved = True
            continue
        for key in ("id", "summary", "disposition"):
            add_required_string_blocker(errors, conflict, key, "conflict-metadata", subject)
        status = conflict.get("status")
        scope = conflict.get("scope")
        if not isinstance(status, str) or status not in ("resolved", "unresolved"):
            errors.append(blocker("conflict-metadata", "invalid conflict status", subject))
        if not isinstance(scope, str) or scope not in ("required-path", "optional-path"):
            errors.append(blocker("conflict-metadata", "invalid conflict scope", subject))
        if status == "unresolved" and scope == "required-path":
            required_unresolved = True
    return required_unresolved


def validate_profile(
    anchor: dict[str, Any],
    anchor_id: str,
    profile: str | None,
    evidence: dict[str, Any] | None,
    as_of: date,
    errors: list[dict[str, str]],
) -> bool:
    unresolved_version = False
    if profile == "executable-recipe":
        version = anchor.get("versionAnchor")
        if not isinstance(version, dict):
            errors.append(
                blocker("version-anchor", "Executable recipe requires versionAnchor", anchor_id)
            )
            unresolved_version = True
        else:
            for key in ("kind", "resolvedIdentity", "resolvedFrom", "resolvedAt"):
                add_required_string_blocker(errors, version, key, "version-anchor", anchor_id)
            identity = version.get("resolvedIdentity")
            if nonempty_string(identity):
                normalized = identity.strip().lower()
                if normalized in MOVING_VERSION_IDENTITIES or "@latest" in normalized:
                    errors.append(
                        blocker(
                            "version-anchor",
                            "resolvedIdentity must be immutable, not a moving alias",
                            anchor_id,
                        )
                    )
                    unresolved_version = True
            else:
                unresolved_version = True
            resolved_at = parse_date(version.get("resolvedAt"))
            if resolved_at is None:
                errors.append(
                    blocker("version-anchor", "resolvedAt must use YYYY-MM-DD", anchor_id)
                )
                unresolved_version = True
            elif resolved_at > as_of:
                errors.append(
                    blocker("version-anchor", "resolvedAt cannot be in the future", anchor_id)
                )
                unresolved_version = True
        if not nonempty_string_mapping(anchor.get("declaredEnvironment")):
            errors.append(
                blocker("profile-metadata", "Executable recipe requires declaredEnvironment", anchor_id)
            )
        for key in ("availabilityAssumptions", "steps", "expectedEvidence"):
            if not nonempty_string_list(anchor.get(key)):
                errors.append(
                    blocker("profile-metadata", f"Executable recipe requires {key}", anchor_id)
                )
        if evidence is not None:
            if not nonempty_string_mapping(evidence.get("environment")):
                errors.append(
                    blocker("recertification-evidence", "command evidence requires environment", anchor_id)
                )
            if not nonempty_string_list(evidence.get("steps")):
                errors.append(
                    blocker("recertification-evidence", "command evidence requires steps", anchor_id)
                )
            if not nonempty_string_list(evidence.get("resolvedVersions")):
                errors.append(
                    blocker(
                        "recertification-evidence",
                        "command evidence requires resolvedVersions",
                        anchor_id,
                    )
                )
            elif isinstance(version, dict) and version.get("resolvedIdentity") not in evidence.get(
                "resolvedVersions", []
            ):
                errors.append(
                    blocker(
                        "version-anchor",
                        "evidence must include the resolved immutable identity",
                        anchor_id,
                    )
                )
                unresolved_version = True
    elif profile == "surface-procedure":
        for key in ("surfacePath",):
            add_required_string_blocker(errors, anchor, key, "profile-metadata", anchor_id)
        for key in ("availabilityAssumptions", "expectedEvidence"):
            if not nonempty_string_list(anchor.get(key)):
                errors.append(
                    blocker("profile-metadata", f"Surface procedure requires {key}", anchor_id)
                )
        if anchor.get("commandMetadata") != "not-applicable":
            errors.append(
                blocker(
                    "profile-metadata",
                    "Surface procedure commandMetadata must be not-applicable",
                    anchor_id,
                )
            )
        if any(key in anchor for key in ("versionAnchor", "declaredEnvironment", "steps")):
            errors.append(
                blocker(
                    "profile-metadata",
                    "Surface procedure must not invent executable metadata",
                    anchor_id,
                )
            )
        if evidence is not None and evidence.get("surfacePath") != anchor.get("surfacePath"):
            errors.append(
                blocker(
                    "recertification-evidence",
                    "surface evidence must repeat the exact observed surfacePath",
                    anchor_id,
                )
            )
    elif profile == "principle-only":
        add_required_string_blocker(
            errors, anchor, "principleStatement", "profile-metadata", anchor_id
        )
        if anchor.get("commandMetadata") != "not-applicable":
            errors.append(
                blocker(
                    "profile-metadata",
                    "Principle-only commandMetadata must be not-applicable",
                    anchor_id,
                )
            )
        if any(
            key in anchor
            for key in ("versionAnchor", "declaredEnvironment", "steps", "surfacePath")
        ):
            errors.append(
                blocker(
                    "profile-metadata",
                    "Principle-only anchor must not invent executable or surface metadata",
                    anchor_id,
                )
            )
    return unresolved_version


def trace_anchor(
    anchor: Any,
    *,
    index: int,
    as_of: date,
    drift_windows: dict[str, int],
    seen_ids: set[str],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    fallback_id = f"anchors[{index}]"
    start = len(errors)
    if not isinstance(anchor, dict):
        errors.append(blocker("anchor-schema", "anchor must be an object", fallback_id))
        return {
            "id": fallback_id,
            "ownerPath": None,
            "profile": None,
            "publicationState": None,
            "freshnessState": "stale",
            "dueAt": None,
            "gateState": "blocked",
            "reasonCodes": ["anchor-schema"],
        }

    anchor_id_value = anchor.get("id")
    anchor_id = anchor_id_value if nonempty_string(anchor_id_value) else fallback_id
    owner_path_value = anchor.get("ownerPath")
    owner_path = owner_path_value if nonempty_string(owner_path_value) else None
    if not nonempty_string(anchor_id_value):
        errors.append(blocker("anchor-id", "anchor id is required", anchor_id))
    elif anchor_id in seen_ids:
        errors.append(blocker("anchor-id", "anchor id must be unique", anchor_id))
    else:
        seen_ids.add(anchor_id)

    add_required_string_blocker(errors, anchor, "claimScope", "anchor-schema", anchor_id)
    if "freshnessState" in anchor or "gateState" in anchor:
        errors.append(
            blocker(
                "derived-state-authored",
                "freshnessState and gateState must be derived by the tracer",
                anchor_id,
            )
        )

    profile_value = anchor.get("profile")
    profile = profile_value if isinstance(profile_value, str) else None
    if profile not in PROFILE_CONTRACTS:
        errors.append(blocker("source-profile", "invalid Source profile", anchor_id))

    drift_value = anchor.get("driftClass")
    drift_class = drift_value if isinstance(drift_value, str) else None
    if drift_class not in drift_windows:
        errors.append(blocker("drift-class", "invalid Drift class", anchor_id))

    publication_value = anchor.get("publicationState")
    publication = publication_value if isinstance(publication_value, str) else None
    if publication not in {"draft", "active", "inactive"}:
        errors.append(blocker("publication-state", "invalid Publication state", anchor_id))

    source_ids = validate_sources(anchor, anchor_id, as_of, errors)
    if not nonempty_string_list(anchor.get("changeTriggers")):
        errors.append(
            blocker("change-triggers", "changeTriggers must be a non-empty string list", anchor_id)
        )

    trigger_events = anchor.get("triggerEvents", [])
    open_trigger = False
    if not isinstance(trigger_events, list):
        errors.append(blocker("change-triggers", "triggerEvents must be a list", anchor_id))
    else:
        for event_index, event in enumerate(trigger_events):
            subject = f"{anchor_id}.triggerEvents[{event_index}]"
            if not isinstance(event, dict):
                errors.append(blocker("change-triggers", "trigger event must be an object", subject))
                open_trigger = True
                continue
            add_required_string_blocker(errors, event, "trigger", "change-triggers", subject)
            event_status = event.get("status")
            if not isinstance(event_status, str) or event_status not in ("open", "resolved"):
                errors.append(blocker("change-triggers", "invalid trigger event status", subject))
            if event_status == "open":
                open_trigger = True

    required_unresolved_conflict = validate_conflicts(anchor, anchor_id, errors)

    evidence_value = anchor.get("recertificationEvidence")
    evidence = evidence_value if isinstance(evidence_value, dict) else None
    checked_at: date | None = None
    evidence_result: str | None = None
    if evidence is None:
        errors.append(
            blocker("recertification-evidence", "recertificationEvidence must be an object", anchor_id)
        )
    else:
        checked_at = parse_date(evidence.get("checkedAt"))
        if checked_at is None:
            errors.append(
                blocker(
                    "recertification-evidence",
                    "evidence checkedAt must use YYYY-MM-DD",
                    anchor_id,
                )
            )
        elif checked_at > as_of:
            errors.append(
                blocker(
                    "recertification-evidence",
                    "evidence checkedAt cannot be in the future",
                    anchor_id,
                )
            )
        add_required_string_blocker(
            errors, evidence, "actor", "recertification-evidence", anchor_id
        )
        contract = PROFILE_CONTRACTS.get(profile or "")
        expected_method = contract["evidenceMethod"] if contract else None
        if evidence.get("verificationMethod") != expected_method:
            errors.append(
                blocker(
                    "recertification-evidence",
                    "verificationMethod does not match the Source profile",
                    anchor_id,
                )
            )
        evidence_source_ids = evidence.get("sourceIds")
        if not nonempty_string_list(evidence_source_ids):
            errors.append(
                blocker(
                    "recertification-evidence",
                    "evidence sourceIds must be a non-empty string list",
                    anchor_id,
                )
            )
        elif (
            len(evidence_source_ids) != len(set(evidence_source_ids))
            or set(evidence_source_ids) != source_ids
        ):
            errors.append(
                blocker(
                    "recertification-evidence",
                    "evidence must cover every declared source exactly once",
                    anchor_id,
                )
            )
        evidence_result_value = evidence.get("result")
        evidence_result = evidence_result_value if isinstance(evidence_result_value, str) else None
        if evidence_result not in {"pass", "fail"}:
            errors.append(
                blocker("recertification-evidence", "evidence result must be pass or fail", anchor_id)
            )
        if not nonempty_string_list(evidence.get("observations")):
            errors.append(
                blocker(
                    "recertification-evidence",
                    "evidence observations must be a non-empty string list",
                    anchor_id,
                )
            )

    unresolved_version = validate_profile(
        anchor, anchor_id, profile, evidence, as_of, errors
    )

    due_at: date | None = None
    if checked_at is not None and drift_class in drift_windows:
        due_at = checked_at + timedelta(days=drift_windows[drift_class])

    if evidence_result == "fail":
        freshness = "stale"
    elif (
        checked_at is None
        or checked_at > as_of
        or due_at is None
        or as_of >= due_at
        or open_trigger
    ):
        freshness = "due"
    else:
        freshness = "current"

    if publication == "draft":
        errors.append(
            blocker("publication-not-active", "draft anchor cannot pass the Publication gate", anchor_id)
        )
    if publication == "active" and freshness == "due":
        errors.append(blocker("freshness-due", "active anchor is due", anchor_id))
    if publication == "active" and freshness == "stale":
        errors.append(blocker("freshness-stale", "active anchor is stale", anchor_id))
    if publication == "active" and required_unresolved_conflict:
        errors.append(
            blocker(
                "first-party-conflict",
                "active required-path First-party conflict is unresolved",
                anchor_id,
            )
        )
    if publication == "active" and unresolved_version:
        errors.append(
            blocker("unresolved-version", "active Version anchor is unresolved", anchor_id)
        )

    local_errors = errors[start:]
    reason_codes = list(dict.fromkeys(item["code"] for item in local_errors))
    if publication == "inactive" and not any(
        code in {"anchor-schema", "anchor-id", "source-metadata"} for code in reason_codes
    ):
        gate_state = "pass"
    else:
        gate_state = "blocked" if reason_codes else "pass"

    return {
        "id": anchor_id,
        "ownerPath": owner_path,
        "profile": profile,
        "publicationState": publication,
        "freshnessState": freshness,
        "dueAt": due_at.isoformat() if due_at else None,
        "gateState": gate_state,
        "reasonCodes": reason_codes,
    }


def validate_anchor_ownership(
    anchors: list[Any],
    anchor_results: list[dict[str, Any]],
    manifest: Any,
    errors: list[dict[str, str]],
) -> None:
    """Require one registered manifest page to own and map every active anchor."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("pages"), list):
        return

    page_by_path = {
        page.get("path"): page
        for page in manifest["pages"]
        if isinstance(page, dict) and nonempty_string(page.get("path"))
    }
    mapped_anchor_ids: set[str] = set()
    for page in page_by_path.values():
        dependencies = page.get("sourceDependencies")
        if not isinstance(dependencies, dict) or dependencies.get("state") != "registered":
            continue
        anchor_ids = dependencies.get("anchorIds")
        if isinstance(anchor_ids, list):
            mapped_anchor_ids.update(
                item for item in anchor_ids if nonempty_string(item)
            )

    for index, result in enumerate(anchor_results):
        anchor = anchors[index] if index < len(anchors) else None
        if not isinstance(anchor, dict) or result.get("publicationState") != "active":
            continue
        start = len(errors)
        anchor_id = result["id"]
        owner_path = result.get("ownerPath")
        if owner_path is None:
            errors.append(
                blocker(
                    "anchor-owner",
                    "active anchor requires exactly one ownerPath",
                    anchor_id,
                )
            )
        else:
            owner_page = page_by_path.get(owner_path)
            if owner_page is None:
                errors.append(
                    blocker(
                        "anchor-owner-missing",
                        f"owner page is absent from the manifest: {owner_path}",
                        anchor_id,
                    )
                )
            else:
                dependencies = owner_page.get("sourceDependencies")
                if (
                    not isinstance(dependencies, dict)
                    or dependencies.get("state") != "registered"
                ):
                    errors.append(
                        blocker(
                            "anchor-owner-unregistered",
                            f"owner page is not Source-registered: {owner_path}",
                            anchor_id,
                        )
                    )
                else:
                    anchor_ids = dependencies.get("anchorIds")
                    if not isinstance(anchor_ids, list) or anchor_id not in anchor_ids:
                        errors.append(
                            blocker(
                                "anchor-owner-mismatch",
                                f"owner page does not map the anchor: {owner_path}",
                                anchor_id,
                            )
                        )
        if anchor_id not in mapped_anchor_ids:
            errors.append(
                blocker(
                    "anchor-unmapped",
                    "active anchor is not mapped by any registered page",
                    anchor_id,
                )
            )

        local_errors = errors[start:]
        if local_errors:
            result["reasonCodes"] = list(
                dict.fromkeys(
                    [*result["reasonCodes"], *(item["code"] for item in local_errors)]
                )
            )
            result["gateState"] = "blocked"


def trace_pages(
    manifest: Any,
    anchor_states: dict[str, dict[str, Any]],
    *,
    coverage_complete: bool,
    errors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    if not isinstance(manifest, dict):
        errors.append(blocker("page-manifest", "page manifest root must be an object"))
        return []
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        errors.append(blocker("page-manifest", "page manifest pages must be a list"))
        return []

    results: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for index, page in enumerate(pages):
        fallback = f"pages[{index}]"
        if not isinstance(page, dict):
            errors.append(blocker("page-manifest", "page must be an object", fallback))
            continue
        path_value = page.get("path")
        path = path_value if nonempty_string(path_value) else fallback
        if not nonempty_string(path_value):
            errors.append(blocker("page-manifest", "page path is required", path))
        elif path in seen_paths:
            errors.append(blocker("page-manifest", "page path must be unique", path))
        else:
            seen_paths.add(path)

        dependencies = page.get("sourceDependencies")
        if not isinstance(dependencies, dict):
            errors.append(
                blocker("page-mapping", "sourceDependencies must be an object", path)
            )
            continue
        state_value = dependencies.get("state")
        state = state_value if isinstance(state_value, str) else None
        anchor_ids = dependencies.get("anchorIds")
        if state not in ALLOWED_PAGE_STATES:
            errors.append(blocker("page-mapping", "invalid source dependency state", path))
        if not isinstance(anchor_ids, list) or not all(nonempty_string(item) for item in anchor_ids):
            errors.append(blocker("page-mapping", "anchorIds must be a string list", path))
            anchor_ids = []
        if len(anchor_ids) != len(set(anchor_ids)):
            errors.append(blocker("page-mapping", "anchorIds must be unique", path))

        page_reasons: list[str] = []
        if state == "registered":
            if not anchor_ids:
                errors.append(
                    blocker("page-mapping", "registered page requires anchorIds", path)
                )
                page_reasons.append("missing-anchor-id")
            page_kind = page.get("pageKind")
            if not isinstance(page_kind, str) or page_kind not in (
                "canonical-lesson",
                "canonical-reference",
                "navigation",
            ):
                errors.append(
                    blocker(
                        "page-mapping",
                        "only active canonical or navigation pages may be registered",
                        path,
                    )
                )
                page_reasons.append("invalid-page-kind")
            for anchor_id in anchor_ids:
                anchor_state = anchor_states.get(anchor_id)
                if anchor_state is None:
                    errors.append(
                        blocker(
                            "page-anchor-missing",
                            f"mapped anchor does not exist: {anchor_id}",
                            path,
                        )
                    )
                    page_reasons.append("page-anchor-missing")
                elif anchor_state["publicationState"] != "active":
                    errors.append(
                        blocker(
                            "page-anchor-inactive",
                            f"mapped anchor is not active: {anchor_id}",
                            path,
                        )
                    )
                    page_reasons.append("page-anchor-inactive")
                elif anchor_state["gateState"] != "pass":
                    errors.append(
                        blocker(
                            "page-anchor-blocked",
                            f"mapped anchor is blocked: {anchor_id}",
                            path,
                        )
                    )
                    page_reasons.append("page-anchor-blocked")
        elif state in {"pending-t03", "not-applicable"} and anchor_ids:
            errors.append(
                blocker("page-mapping", f"{state} page must not list anchorIds", path)
            )
            page_reasons.append("unexpected-anchor-id")

        if coverage_complete and state == "pending-t03":
            errors.append(
                blocker("page-coverage", "complete coverage cannot contain pending-t03", path)
            )
            page_reasons.append("page-coverage")

        if state == "registered":
            gate_state = "blocked" if page_reasons else "pass"
        elif state == "not-applicable":
            gate_state = "not-applicable"
        else:
            gate_state = "unassessed"
        results.append(
            {
                "path": path,
                "mappingState": state,
                "anchorIds": anchor_ids,
                "gateState": gate_state,
                "reasonCodes": list(dict.fromkeys(page_reasons)),
            }
        )
    return results


def trace_registry(
    registry: Any,
    manifest: Any,
    *,
    as_of: date,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    report: dict[str, Any] = {
        "mode": "report-only",
        "asOf": as_of.isoformat(),
        "coverage": "unknown",
        "anchors": [],
        "pages": [],
        "blockers": errors,
    }
    if not isinstance(registry, dict):
        errors.append(blocker("registry-schema", "registry root must be an object"))
        report["summary"] = {
            "anchors": 0,
            "registeredPages": 0,
            "blockedAnchors": 0,
            "blockedPages": 0,
            "blockers": len(errors),
            "ownedAnchors": 0,
            "baselineReady": False,
        }
        return report

    validate_top_level(registry, errors)
    coverage = registry.get("coverage")
    coverage_complete = isinstance(coverage, dict) and coverage.get("complete") is True
    report["coverage"] = coverage.get("mode") if isinstance(coverage, dict) else "unknown"
    drift_windows = registry.get("driftWindowsDays")
    if drift_windows != EXPECTED_DRIFT_WINDOWS:
        drift_windows = EXPECTED_DRIFT_WINDOWS

    anchors_value = registry.get("anchors")
    anchors = anchors_value if isinstance(anchors_value, list) else []
    if not isinstance(anchors_value, list) or not anchors_value:
        errors.append(blocker("anchor-schema", "anchors must be a non-empty list"))

    seen_ids: set[str] = set()
    anchor_results = [
        trace_anchor(
            anchor,
            index=index,
            as_of=as_of,
            drift_windows=drift_windows,
            seen_ids=seen_ids,
            errors=errors,
        )
        for index, anchor in enumerate(anchors)
    ]
    anchor_states = {item["id"]: item for item in anchor_results}
    validate_anchor_ownership(anchors, anchor_results, manifest, errors)
    page_results = trace_pages(
        manifest,
        anchor_states,
        coverage_complete=coverage_complete,
        errors=errors,
    )
    report["anchors"] = anchor_results
    report["pages"] = page_results
    report["summary"] = {
        "anchors": len(anchor_results),
        "registeredPages": sum(
            item["mappingState"] == "registered" for item in page_results
        ),
        "blockedAnchors": sum(
            item["gateState"] == "blocked" for item in anchor_results
        ),
        "blockedPages": sum(item["gateState"] == "blocked" for item in page_results),
        "blockers": len(errors),
        "ownedAnchors": sum(
            item["publicationState"] == "active" and item["ownerPath"] is not None
            for item in anchor_results
        ),
        "baselineReady": bool(anchor_results)
        and not errors
        and all(
            item["publicationState"] != "active"
            or (
                item["ownerPath"] is not None
                and item["freshnessState"] == "current"
                and item["gateState"] == "pass"
            )
            for item in anchor_results
        ),
    }
    return report


def refresh_blocker_summary(report: dict[str, Any]) -> None:
    errors = report.get("blockers")
    summary = report.get("summary")
    if isinstance(errors, list) and isinstance(summary, dict):
        summary["blockers"] = len(errors)
        if errors:
            summary["baselineReady"] = False


def trace_required_pages(
    report: dict[str, Any],
    required_paths: list[str],
) -> tuple[set[str], int]:
    """Validate preselected required pages and return their anchors and pass count."""
    errors = report.get("blockers")
    if not isinstance(errors, list):
        raise ValueError("Source report blockers must be a list")
    traced_pages = {
        page.get("path"): page
        for page in report.get("pages", [])
        if isinstance(page, dict) and isinstance(page.get("path"), str)
    }
    passing = 0
    required_anchor_ids: set[str] = set()
    for path in required_paths:
        traced = traced_pages.get(path)
        if traced is None:
            errors.append(
                blocker("required-page-missing", "page is absent from Source trace", path)
            )
        elif traced.get("mappingState") != "registered":
            errors.append(
                blocker(
                    "required-page-unregistered",
                    "required page must have registered Source dependencies",
                    path,
                )
            )
        elif traced.get("gateState") != "pass":
            errors.append(
                blocker(
                    "required-page-blocked",
                    "required page Source gate must pass",
                    path,
                )
            )
        else:
            passing += 1
            required_anchor_ids.update(traced.get("anchorIds", []))
    refresh_blocker_summary(report)
    return required_anchor_ids, passing


def trace_required_coordinate_scope(
    report: dict[str, Any],
    manifest: Any,
    *,
    coordinate_prefixes: list[str],
) -> set[str]:
    """Require selected canonical lesson phases without authoring a page allowlist."""
    if not coordinate_prefixes:
        return set()
    errors = report.get("blockers")
    if not isinstance(errors, list):
        raise ValueError("Source report blockers must be a list")
    pages = manifest.get("pages") if isinstance(manifest, dict) else None
    if not isinstance(pages, list):
        errors.append(
            blocker(
                "required-scope-manifest",
                "required coordinate scope needs manifest pages",
            )
        )
        refresh_blocker_summary(report)
        return set()

    prefixes = set(coordinate_prefixes)
    required_paths = []
    for page in pages:
        if not isinstance(page, dict) or page.get("pageKind") != "canonical-lesson":
            continue
        coordinate = page.get("canonicalCoordinate")
        path = page.get("path")
        if (
            isinstance(coordinate, str)
            and coordinate.split("-", 1)[0] in prefixes
            and isinstance(path, str)
        ):
            required_paths.append(path)

    if not required_paths:
        errors.append(
            blocker(
                "required-scope-empty",
                "coordinate prefixes select no canonical lessons",
            )
        )
    required_anchor_ids, passing = trace_required_pages(report, required_paths)
    report["requiredCoordinateScope"] = {
        "prefixes": sorted(prefixes),
        "pages": len(required_paths),
        "passing": passing,
    }
    return required_anchor_ids


def trace_required_route_scope(
    report: dict[str, Any],
    manifest: Any,
    *,
    route_ids: list[str],
) -> set[str]:
    """Require canonical lessons selected by manifest route membership."""
    if not route_ids:
        return set()
    errors = report.get("blockers")
    if not isinstance(errors, list):
        raise ValueError("Source report blockers must be a list")
    pages = manifest.get("pages") if isinstance(manifest, dict) else None
    if not isinstance(pages, list):
        errors.append(
            blocker("required-route-manifest", "required route scope needs manifest pages")
        )
        refresh_blocker_summary(report)
        return set()

    selected_route_ids = set(route_ids)
    required_paths = []
    for page in pages:
        if not isinstance(page, dict) or page.get("pageKind") != "canonical-lesson":
            continue
        memberships = page.get("routeMemberships")
        path = page.get("path")
        if not isinstance(memberships, list) or not isinstance(path, str):
            continue
        if any(
            isinstance(membership, dict)
            and membership.get("routeId") in selected_route_ids
            for membership in memberships
        ):
            required_paths.append(path)

    if not required_paths:
        errors.append(
            blocker(
                "required-route-empty",
                "route ids select no canonical lessons",
            )
        )
    required_anchor_ids, passing = trace_required_pages(report, required_paths)
    report["requiredRouteScope"] = {
        "routeIds": sorted(selected_route_ids),
        "pages": len(required_paths),
        "passing": passing,
    }
    return required_anchor_ids


def trace_required_path_scope(
    report: dict[str, Any],
    manifest: Any,
    *,
    paths: list[str],
) -> set[str]:
    """Require explicitly requested canonical paths in addition to route scope."""
    if not paths:
        return set()
    errors = report.get("blockers")
    if not isinstance(errors, list):
        raise ValueError("Source report blockers must be a list")
    pages = manifest.get("pages") if isinstance(manifest, dict) else None
    if not isinstance(pages, list):
        errors.append(
            blocker("required-path-manifest", "required path scope needs manifest pages")
        )
        refresh_blocker_summary(report)
        return set()

    canonical_by_path = {
        page.get("path"): page
        for page in pages
        if isinstance(page, dict)
        and page.get("pageKind") in {"canonical-lesson", "canonical-reference", "navigation"}
        and isinstance(page.get("path"), str)
    }
    requested_paths = sorted(set(paths))
    required_paths = []
    for path in requested_paths:
        if path not in canonical_by_path:
            errors.append(
                blocker(
                    "required-path-missing",
                    "required path is absent or not canonical in the manifest",
                    path,
                )
            )
        else:
            required_paths.append(path)

    required_anchor_ids, passing = trace_required_pages(report, required_paths)
    report["requiredPathScope"] = {
        "paths": requested_paths,
        "pages": len(required_paths),
        "passing": passing,
    }
    return required_anchor_ids


def fetch_source_status(url: str) -> int:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if (
        parsed.netloc == "github.com"
        and len(parts) == 4
        and parts[2] == "issues"
        and parts[3].isdigit()
    ):
        result = subprocess.run(
            [
                "gh",
                "issue",
                "view",
                parts[3],
                "--repo",
                f"{parts[0]}/{parts[1]}",
                "--json",
                "number",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            return 200
        raise OSError(result.stderr.strip() or "authenticated GitHub issue fetch failed")
    request = Request(
        url,
        headers={"User-Agent": "lessons-source-registry-validator/1.0"},
    )
    with urlopen(request, timeout=20) as response:
        return response.status


def verify_source_urls(
    registry: Any,
    *,
    status_fetcher: StatusFetcher = fetch_source_status,
    anchor_ids: set[str] | None = None,
) -> tuple[dict[str, int], list[dict[str, str]]]:
    """Check declared primary-source URLs without changing publication state."""
    anchors = registry.get("anchors") if isinstance(registry, dict) else None
    if not isinstance(anchors, list):
        return (
            {"urls": 0, "passing": 0},
            [blocker("source-url-schema", "online check requires registry anchors")],
        )
    selected_anchors = [
        anchor
        for anchor in anchors
        if isinstance(anchor, dict)
        and (anchor_ids is None or anchor.get("id") in anchor_ids)
    ]
    urls = sorted(
        {
            source["url"]
            for anchor in selected_anchors
            if isinstance(anchor.get("sources"), list)
            for source in anchor["sources"]
            if isinstance(source, dict) and valid_https_url(source.get("url"))
        }
    )

    def check(url: str) -> tuple[str, int | None, str | None]:
        try:
            return url, status_fetcher(url), None
        except Exception as error:  # Network and TLS failures vary by platform.
            return url, None, str(error)

    errors: list[dict[str, str]] = []
    passing = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        for url, status, fetch_error in executor.map(check, urls):
            if fetch_error is not None:
                errors.append(blocker("source-url-fetch", fetch_error, url))
            elif status is None or status < 200 or status >= 400:
                errors.append(
                    blocker("source-url-status", f"returned HTTP {status}", url)
                )
            else:
                passing += 1
    return {"urls": len(urls), "passing": passing}, errors


def profile_definitions() -> dict[str, dict[str, Any]]:
    return copy.deepcopy(PROFILE_CONTRACTS)


def common_fixture_anchor(anchor_id: str, profile: str) -> dict[str, Any]:
    source_id = f"{anchor_id}-source"
    return {
        "id": anchor_id,
        "claimScope": f"Fixture claim for {profile}.",
        "profile": profile,
        "driftClass": "high",
        "publicationState": "active",
        "sources": [
            {
                "id": source_id,
                "url": "https://example.com/official",
                "kind": "first-party-product-doc",
                "checkedAt": "2026-07-16",
            }
        ],
        "changeTriggers": ["new release"],
        "triggerEvents": [],
        "conflicts": [],
        "recertificationEvidence": {
            "checkedAt": "2026-07-16",
            "actor": "fixture",
            "sourceIds": [source_id],
            "verificationMethod": PROFILE_CONTRACTS[profile]["evidenceMethod"],
            "result": "pass",
            "observations": ["expected fixture evidence observed"],
        },
    }


def positive_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    executable = common_fixture_anchor("fixture-executable", "executable-recipe")
    executable.update(
        {
            "versionAnchor": {
                "kind": "binary-version",
                "resolvedIdentity": "fixture@1.0.0",
                "resolvedFrom": "fixture --version",
                "resolvedAt": "2026-07-16",
            },
            "declaredEnvironment": {"platform": "fixture", "shell": "fixture"},
            "availabilityAssumptions": ["fixture is installed"],
            "steps": ["fixture --version"],
            "expectedEvidence": ["fixture@1.0.0"],
        }
    )
    executable["recertificationEvidence"].update(
        {
            "environment": {"platform": "fixture", "shell": "fixture"},
            "steps": ["fixture --version"],
            "resolvedVersions": ["fixture@1.0.0"],
        }
    )

    surface = common_fixture_anchor("fixture-surface", "surface-procedure")
    surface.update(
        {
            "surfacePath": "Fixture > Surface",
            "availabilityAssumptions": ["fixture surface is available"],
            "expectedEvidence": ["fixture surface result"],
            "commandMetadata": "not-applicable",
        }
    )
    surface["recertificationEvidence"]["surfacePath"] = "Fixture > Surface"

    principle = common_fixture_anchor("fixture-principle", "principle-only")
    principle.update(
        {
            "principleStatement": "Fixture evidence must remain reviewable.",
            "commandMetadata": "not-applicable",
        }
    )

    registry = {
        "schemaVersion": 1,
        "authority": EXPECTED_AUTHORITY,
        "gateMode": "report-only",
        "coverage": {
            "mode": EXPECTED_COVERAGE_MODE,
            "complete": True,
            "nextWave": EXPECTED_NEXT_WAVE,
        },
        "driftWindowsDays": EXPECTED_DRIFT_WINDOWS,
        "stateModel": EXPECTED_STATE_MODEL,
        "profiles": profile_definitions(),
        "anchors": [executable, surface, principle],
    }
    manifest = {
        "pages": [
            {
                "path": f"lessons/001-000{index + 1}-fixture.html",
                "canonicalCoordinate": f"001-000{index + 1}",
                "pageKind": "canonical-lesson",
                "routeMemberships": [
                    {"routeId": "fixture-route", "roles": ["fixture"]}
                ],
                "sourceDependencies": {
                    "state": "registered",
                    "anchorIds": [anchor["id"]],
                },
            }
            for index, anchor in enumerate(registry["anchors"])
        ]
    }
    for index, anchor in enumerate(registry["anchors"]):
        anchor["ownerPath"] = f"lessons/001-000{index + 1}-fixture.html"
    return registry, manifest


def assert_has_code(report: dict[str, Any], code: str) -> None:
    assert any(item["code"] == code for item in report["blockers"]), (
        code,
        report["blockers"],
    )


def run_self_test() -> None:
    as_of = date(2026, 7, 16)
    registry, manifest = positive_fixture()
    report = trace_registry(registry, manifest, as_of=as_of)
    assert report["blockers"] == [], report["blockers"]
    assert {item["profile"] for item in report["anchors"]} == set(PROFILE_CONTRACTS)
    assert all(item["freshnessState"] == "current" for item in report["anchors"])
    assert all(item["gateState"] == "pass" for item in report["anchors"])
    assert all(item["gateState"] == "pass" for item in report["pages"])
    assert report["summary"]["ownedAnchors"] == 3
    assert report["summary"]["baselineReady"] is True

    online_summary, online_errors = verify_source_urls(
        registry,
        status_fetcher=lambda _url: 200,
    )
    assert online_errors == [], online_errors
    assert online_summary == {"urls": 1, "passing": 1}

    failed_summary, failed_errors = verify_source_urls(
        registry,
        status_fetcher=lambda _url: 503,
    )
    assert failed_summary == {"urls": 1, "passing": 0}
    assert any(error["code"] == "source-url-status" for error in failed_errors)

    def failing_fetcher(_url: str) -> int:
        raise OSError("fixture network failure")

    _, fetch_errors = verify_source_urls(
        registry,
        status_fetcher=failing_fetcher,
    )
    assert any(error["code"] == "source-url-fetch" for error in fetch_errors)

    scoped_report = copy.deepcopy(report)
    trace_required_coordinate_scope(
        scoped_report,
        manifest,
        coordinate_prefixes=["001"],
    )
    assert scoped_report["blockers"] == [], scoped_report["blockers"]

    pending_manifest = copy.deepcopy(manifest)
    pending_manifest["pages"][0]["sourceDependencies"] = {
        "state": "pending-t03",
        "anchorIds": [],
    }
    pending_report = trace_registry(registry, pending_manifest, as_of=as_of)
    trace_required_coordinate_scope(
        pending_report,
        pending_manifest,
        coordinate_prefixes=["001"],
    )
    assert_has_code(pending_report, "required-page-unregistered")

    empty_scope_report = copy.deepcopy(report)
    trace_required_coordinate_scope(
        empty_scope_report,
        manifest,
        coordinate_prefixes=["999"],
    )
    assert_has_code(empty_scope_report, "required-scope-empty")

    route_scoped_report = copy.deepcopy(report)
    trace_required_route_scope(
        route_scoped_report,
        manifest,
        route_ids=["fixture-route"],
    )
    assert route_scoped_report["blockers"] == [], route_scoped_report["blockers"]

    pending_route_report = trace_registry(registry, pending_manifest, as_of=as_of)
    trace_required_route_scope(
        pending_route_report,
        pending_manifest,
        route_ids=["fixture-route"],
    )
    assert_has_code(pending_route_report, "required-page-unregistered")

    empty_route_report = copy.deepcopy(report)
    trace_required_route_scope(
        empty_route_report,
        manifest,
        route_ids=["missing-route"],
    )
    assert_has_code(empty_route_report, "required-route-empty")

    path_scoped_report = copy.deepcopy(report)
    trace_required_path_scope(
        path_scoped_report,
        manifest,
        paths=["lessons/001-0001-fixture.html"],
    )
    assert path_scoped_report["blockers"] == [], path_scoped_report["blockers"]

    pending_path_report = trace_registry(registry, pending_manifest, as_of=as_of)
    trace_required_path_scope(
        pending_path_report,
        pending_manifest,
        paths=["lessons/001-0001-fixture.html"],
    )
    assert_has_code(pending_path_report, "required-page-unregistered")

    missing_path_report = copy.deepcopy(report)
    trace_required_path_scope(
        missing_path_report,
        manifest,
        paths=["reference/missing.html"],
    )
    assert_has_code(missing_path_report, "required-path-missing")

    invalid_scope_manifest = {"pages": None}
    invalid_route_manifest_report = copy.deepcopy(report)
    trace_required_route_scope(
        invalid_route_manifest_report,
        invalid_scope_manifest,
        route_ids=["fixture-route"],
    )
    assert invalid_route_manifest_report["summary"]["blockers"] == len(
        invalid_route_manifest_report["blockers"]
    )

    invalid_path_manifest_report = copy.deepcopy(report)
    trace_required_path_scope(
        invalid_path_manifest_report,
        invalid_scope_manifest,
        paths=["lessons/001-0001-fixture.html"],
    )
    assert invalid_path_manifest_report["summary"]["blockers"] == len(
        invalid_path_manifest_report["blockers"]
    )

    due_registry = copy.deepcopy(registry)
    due_report = trace_registry(due_registry, manifest, as_of=date(2026, 8, 15))
    assert_has_code(due_report, "freshness-due")

    empty_environment = copy.deepcopy(registry)
    empty_environment["anchors"][0]["declaredEnvironment"] = {}
    empty_environment["anchors"][0]["recertificationEvidence"]["environment"] = {}
    environment_report = trace_registry(empty_environment, manifest, as_of=as_of)
    assert_has_code(environment_report, "profile-metadata")
    assert_has_code(environment_report, "recertification-evidence")

    duplicate_evidence_source = copy.deepcopy(registry)
    duplicate_evidence_source["anchors"][0]["recertificationEvidence"][
        "sourceIds"
    ].append("fixture-executable-source")
    duplicate_source_report = trace_registry(
        duplicate_evidence_source, manifest, as_of=as_of
    )
    assert_has_code(duplicate_source_report, "recertification-evidence")

    contradictory_profile = copy.deepcopy(registry)
    contradictory_profile["profiles"]["executable-recipe"]["requiredMetadata"] = [
        "fabricated"
    ]
    profile_report = trace_registry(contradictory_profile, manifest, as_of=as_of)
    assert_has_code(profile_report, "source-profiles")

    future_evidence = copy.deepcopy(registry)
    future_evidence["anchors"][0]["sources"][0]["checkedAt"] = "2027-07-16"
    future_evidence["anchors"][0]["versionAnchor"]["resolvedAt"] = "2027-07-16"
    future_evidence["anchors"][0]["recertificationEvidence"][
        "checkedAt"
    ] = "2027-07-16"
    future_report = trace_registry(future_evidence, manifest, as_of=as_of)
    assert_has_code(future_report, "source-metadata")
    assert_has_code(future_report, "version-anchor")
    assert_has_code(future_report, "recertification-evidence")
    future_anchor = next(
        item for item in future_report["anchors"] if item["id"] == "fixture-executable"
    )
    assert future_anchor["freshnessState"] == "due"
    assert future_anchor["gateState"] == "blocked"

    stale_registry = copy.deepcopy(registry)
    stale_registry["anchors"][0]["recertificationEvidence"]["result"] = "fail"
    stale_report = trace_registry(stale_registry, manifest, as_of=as_of)
    assert_has_code(stale_report, "freshness-stale")

    draft_registry = copy.deepcopy(registry)
    draft_registry["anchors"][0]["publicationState"] = "draft"
    draft_report = trace_registry(draft_registry, manifest, as_of=as_of)
    assert_has_code(draft_report, "publication-not-active")
    assert_has_code(draft_report, "page-anchor-inactive")

    inactive_registry = copy.deepcopy(registry)
    inactive_registry["anchors"][0]["publicationState"] = "inactive"
    inactive_registry["anchors"][0]["recertificationEvidence"]["result"] = "fail"
    inactive_manifest = copy.deepcopy(manifest)
    inactive_manifest["pages"][0]["sourceDependencies"] = {
        "state": "pending-t03",
        "anchorIds": [],
    }
    inactive_report = trace_registry(inactive_registry, inactive_manifest, as_of=as_of)
    inactive_anchor = next(
        item for item in inactive_report["anchors"] if item["id"] == "fixture-executable"
    )
    assert inactive_anchor["freshnessState"] == "stale"
    assert inactive_anchor["gateState"] == "pass"

    moving_registry = copy.deepcopy(registry)
    moving_registry["anchors"][0]["versionAnchor"]["resolvedIdentity"] = "latest"
    moving_report = trace_registry(moving_registry, manifest, as_of=as_of)
    assert_has_code(moving_report, "version-anchor")
    assert_has_code(moving_report, "unresolved-version")

    conflict_registry = copy.deepcopy(registry)
    conflict_registry["anchors"][0]["conflicts"].append(
        {
            "id": "fixture-conflict",
            "summary": "First-party sources disagree.",
            "status": "unresolved",
            "scope": "required-path",
            "disposition": "pending maintainer decision",
        }
    )
    conflict_report = trace_registry(conflict_registry, manifest, as_of=as_of)
    assert_has_code(conflict_report, "first-party-conflict")

    missing_mapping = copy.deepcopy(manifest)
    missing_mapping["pages"][0]["sourceDependencies"]["anchorIds"] = ["missing"]
    mapping_report = trace_registry(registry, missing_mapping, as_of=as_of)
    assert_has_code(mapping_report, "page-anchor-missing")

    missing_owner = copy.deepcopy(registry)
    del missing_owner["anchors"][0]["ownerPath"]
    missing_owner_report = trace_registry(missing_owner, manifest, as_of=as_of)
    assert_has_code(missing_owner_report, "anchor-owner")

    unregistered_owner_manifest = copy.deepcopy(manifest)
    unregistered_owner_manifest["pages"][0]["sourceDependencies"] = {
        "state": "pending-t03",
        "anchorIds": [],
    }
    unregistered_owner_report = trace_registry(
        registry, unregistered_owner_manifest, as_of=as_of
    )
    assert_has_code(unregistered_owner_report, "anchor-owner-unregistered")
    assert_has_code(unregistered_owner_report, "anchor-unmapped")

    owner_mapping_mismatch = copy.deepcopy(manifest)
    owner_mapping_mismatch["pages"][0]["sourceDependencies"]["anchorIds"] = [
        "fixture-surface"
    ]
    owner_mapping_mismatch_report = trace_registry(
        registry, owner_mapping_mismatch, as_of=as_of
    )
    assert_has_code(owner_mapping_mismatch_report, "anchor-owner-mismatch")

    authored_state = copy.deepcopy(registry)
    authored_state["anchors"][0]["gateState"] = "pass"
    state_report = trace_registry(authored_state, manifest, as_of=as_of)
    assert_has_code(state_report, "derived-state-authored")

    invented_surface_command = copy.deepcopy(registry)
    invented_surface_command["anchors"][1]["steps"] = ["invented --command"]
    surface_report = trace_registry(invented_surface_command, manifest, as_of=as_of)
    assert_has_code(surface_report, "profile-metadata")

    bad_mode = copy.deepcopy(registry)
    bad_mode["gateMode"] = "enforced"
    mode_report = trace_registry(bad_mode, manifest, as_of=as_of)
    assert_has_code(mode_report, "gate-mode")

    bad_next_wave = copy.deepcopy(registry)
    bad_next_wave["coverage"]["nextWave"] = "skip-authoring"
    next_wave_report = trace_registry(bad_next_wave, manifest, as_of=as_of)
    assert_has_code(next_wave_report, "coverage")

    complete_candidate = copy.deepcopy(registry)
    complete_candidate["coverage"] = {
        "mode": "migration-release-candidate",
        "complete": True,
        "nextWave": "maintainer-sign-off",
    }
    complete_candidate_report = trace_registry(
        complete_candidate, manifest, as_of=as_of
    )
    assert not any(
        item["code"] in {"coverage", "page-coverage"}
        for item in complete_candidate_report["blockers"]
    ), complete_candidate_report["blockers"]

    incomplete_coverage = copy.deepcopy(registry)
    incomplete_coverage["coverage"]["complete"] = False
    incomplete_coverage_report = trace_registry(
        incomplete_coverage, manifest, as_of=as_of
    )
    assert_has_code(incomplete_coverage_report, "coverage")

    pre_authoring_coverage = copy.deepcopy(registry)
    pre_authoring_coverage["coverage"]["mode"] = "pre-authoring-baseline"
    pre_authoring_coverage_report = trace_registry(
        pre_authoring_coverage, manifest, as_of=as_of
    )
    assert_has_code(pre_authoring_coverage_report, "coverage")

    pending_page_manifest = copy.deepcopy(manifest)
    pending_page_manifest["pages"][0]["sourceDependencies"] = {
        "state": "pending-t03",
        "anchorIds": [],
    }
    pending_page_report = trace_registry(
        registry, pending_page_manifest, as_of=as_of
    )
    assert_has_code(pending_page_report, "page-coverage")

    malformed_drift = copy.deepcopy(registry)
    malformed_drift["driftWindowsDays"]["high"] = []
    drift_report = trace_registry(malformed_drift, manifest, as_of=as_of)
    assert_has_code(drift_report, "drift-windows")

    malformed_conflict = copy.deepcopy(registry)
    malformed_conflict["anchors"][0]["conflicts"].append(
        {
            "id": "malformed",
            "summary": "Malformed enum fixture.",
            "status": [],
            "scope": {},
            "disposition": "fixture",
        }
    )
    conflict_schema_report = trace_registry(malformed_conflict, manifest, as_of=as_of)
    assert_has_code(conflict_schema_report, "conflict-metadata")

    malformed_trigger = copy.deepcopy(registry)
    malformed_trigger["anchors"][0]["triggerEvents"] = [
        {"trigger": "fixture", "status": []}
    ]
    trigger_report = trace_registry(malformed_trigger, manifest, as_of=as_of)
    assert_has_code(trigger_report, "change-triggers")

    malformed_page_kind = copy.deepcopy(manifest)
    malformed_page_kind["pages"][0]["pageKind"] = []
    page_kind_report = trace_registry(registry, malformed_page_kind, as_of=as_of)
    assert_has_code(page_kind_report, "page-mapping")

    assert report_only_exit_code(stale_report) == 0


def report_only_exit_code(_report: dict[str, Any]) -> int:
    return 0


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def runtime_report(message: str, *, as_of: date) -> dict[str, Any]:
    error = blocker("tracer-runtime", message)
    return {
        "mode": "report-only",
        "asOf": as_of.isoformat(),
        "coverage": "unknown",
        "anchors": [],
        "pages": [],
        "blockers": [error],
        "summary": {
            "anchors": 0,
            "registeredPages": 0,
            "blockedAnchors": 0,
            "blockedPages": 0,
            "blockers": 1,
            "ownedAnchors": 0,
            "baselineReady": False,
        },
    }


def print_text_report(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print("SOURCE REGISTRY TRACE (report-only)")
    print(f"AS OF {report['asOf']}")
    print(f"COVERAGE {report['coverage']}")
    print(
        "SUMMARY "
        f"anchors={summary['anchors']} "
        f"registered-pages={summary['registeredPages']} "
        f"blocked-anchors={summary['blockedAnchors']} "
        f"blocked-pages={summary['blockedPages']} "
        f"blockers={summary['blockers']} "
        f"owned-anchors={summary['ownedAnchors']} "
        f"baseline-ready={str(summary['baselineReady']).lower()}"
    )
    for item in report["anchors"]:
        print(
            "ANCHOR "
            f"{item['id']} "
            f"publication={item['publicationState']} "
            f"freshness={item['freshnessState']} "
            f"gate={item['gateState']} "
            f"due={item['dueAt']}"
        )
    for item in report["blockers"]:
        subject = f" {item['subject']}" if "subject" in item else ""
        print(f"BLOCKER [{item['code']}]{subject}: {item['message']}")
    online_sources = report.get("onlineSources")
    if isinstance(online_sources, dict):
        print(
            "ONLINE SOURCES "
            f"urls={online_sources.get('urls', 0)} "
            f"passing={online_sources.get('passing', 0)}"
        )
    print("PUBLICATION UNAFFECTED (report-only)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Trace Source registry state without enforcing publication"
    )
    parser.add_argument("--registry", default="source-anchors.json")
    parser.add_argument(
        "--manifest", default="docs/migration/course-migration-manifest.json"
    )
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--online",
        action="store_true",
        help="check every declared Source URL while keeping the gate report-only",
    )
    parser.add_argument(
        "--require-coordinate-prefix",
        action="append",
        default=[],
        metavar="PPP",
        help="require every canonical lesson in a three-digit phase to pass",
    )
    parser.add_argument(
        "--require-route",
        action="append",
        default=[],
        metavar="ROUTE_ID",
        help="require every canonical lesson in a manifest route to pass",
    )
    parser.add_argument(
        "--require-path",
        action="append",
        default=[],
        metavar="PATH",
        help="also require an explicit canonical manifest path to pass",
    )
    args = parser.parse_args()

    as_of = parse_date(args.as_of)
    if as_of is None:
        parser.error("--as-of must use YYYY-MM-DD")

    if args.self_test:
        run_self_test()
        print("SOURCE REGISTRY SELF-TEST PASS")
        print("NEGATIVE STATE FIXTURES PASS")
        print("PUBLICATION UNAFFECTED (report-only)")
        return 0

    try:
        registry = load_json(Path(args.registry))
        manifest = load_json(Path(args.manifest))
        report = trace_registry(registry, manifest, as_of=as_of)
        required_anchor_ids: set[str] | None = None
        invalid_prefixes = [
            prefix
            for prefix in args.require_coordinate_prefix
            if len(prefix) != 3 or not prefix.isdigit() or prefix == "000"
        ]
        if invalid_prefixes:
            report["blockers"].append(
                blocker(
                    "required-scope-prefix",
                    "coordinate prefixes must be three digits other than 000: "
                    + ", ".join(invalid_prefixes),
                )
            )
            report["summary"]["blockers"] = len(report["blockers"])
        elif args.require_coordinate_prefix:
            required_anchor_ids = trace_required_coordinate_scope(
                report,
                manifest,
                coordinate_prefixes=args.require_coordinate_prefix,
            )
        if args.require_route:
            route_anchor_ids = trace_required_route_scope(
                report,
                manifest,
                route_ids=args.require_route,
            )
            if required_anchor_ids is None:
                required_anchor_ids = route_anchor_ids
            else:
                required_anchor_ids.update(route_anchor_ids)
        if args.require_path:
            path_anchor_ids = trace_required_path_scope(
                report,
                manifest,
                paths=args.require_path,
            )
            if required_anchor_ids is None:
                required_anchor_ids = path_anchor_ids
            else:
                required_anchor_ids.update(path_anchor_ids)
        if args.online:
            online_summary, online_errors = verify_source_urls(
                registry,
                anchor_ids=required_anchor_ids,
            )
            report["onlineSources"] = online_summary
            report["blockers"].extend(online_errors)
            refresh_blocker_summary(report)
    except (OSError, json.JSONDecodeError) as error:
        report = runtime_report(str(error), as_of=as_of)
    except Exception as error:  # Keep unexpected tracer failures observable but non-blocking.
        report = runtime_report(f"unexpected tracer failure: {error}", as_of=as_of)

    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_text_report(report)
    return report_only_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
