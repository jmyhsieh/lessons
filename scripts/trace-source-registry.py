#!/usr/bin/env python3
"""Trace Source registry state without enforcing the publication gate."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


EXPECTED_AUTHORITY = {
    "registry": "source-anchors.json",
    "pageMappings": "docs/migration/course-migration-manifest.json",
}
EXPECTED_DRIFT_WINDOWS = {"high": 30, "medium": 90, "lower": 365}
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
        if coverage.get("mode") != "representative-thin-slice":
            errors.append(
                blocker("coverage", "T03 coverage must be representative-thin-slice")
            )
        if coverage.get("complete") is not False:
            errors.append(
                blocker("coverage", "T03 must not claim complete Source inventory")
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
            "profile": None,
            "publicationState": None,
            "freshnessState": "stale",
            "dueAt": None,
            "gateState": "blocked",
            "reasonCodes": ["anchor-schema"],
        }

    anchor_id_value = anchor.get("id")
    anchor_id = anchor_id_value if nonempty_string(anchor_id_value) else fallback_id
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
        "profile": profile,
        "publicationState": publication,
        "freshnessState": freshness,
        "dueAt": due_at.isoformat() if due_at else None,
        "gateState": gate_state,
        "reasonCodes": reason_codes,
    }


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
    }
    return report


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
        "coverage": {"mode": "representative-thin-slice", "complete": False},
        "driftWindowsDays": EXPECTED_DRIFT_WINDOWS,
        "stateModel": EXPECTED_STATE_MODEL,
        "profiles": profile_definitions(),
        "anchors": [executable, surface, principle],
    }
    manifest = {
        "pages": [
            {
                "path": f"lessons/001-000{index + 1}-fixture.html",
                "pageKind": "canonical-lesson",
                "sourceDependencies": {
                    "state": "registered",
                    "anchorIds": [anchor["id"]],
                },
            }
            for index, anchor in enumerate(registry["anchors"])
        ]
    }
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
        f"blockers={summary['blockers']}"
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
