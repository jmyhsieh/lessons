#!/usr/bin/env python3
"""Verify the bounded Freeze contract for the twelve-Phase migration."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


FREEZE_START = "<!-- migration-freeze-json:start -->"
FREEZE_END = "<!-- migration-freeze-json:end -->"
EXPECTED_BASELINE_COUNT = 73
EXPECTED_NEW_CANONICAL_COUNT = 99

CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]
GitHubFetcher = Callable[[Path, str], Any]


def failure(code: str, message: str) -> str:
    return f"[{code}] {message}"


def parse_rfc3339_utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        return None
    return parsed


def is_rfc3339_utc_timestamp(value: Any) -> bool:
    return parse_rfc3339_utc_timestamp(value) is not None


def run_command(
    args: list[str], repo_root: Path, *, text: bool = True
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        args,
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
    )


def parse_freeze_document(document: str) -> dict[str, Any]:
    if document.count(FREEZE_START) != 1 or document.count(FREEZE_END) != 1:
        raise ValueError("migration plan must contain exactly one freeze JSON block")
    if document.index(FREEZE_START) >= document.index(FREEZE_END):
        raise ValueError("freeze JSON markers are out of order")

    payload = document.split(FREEZE_START, 1)[1].split(FREEZE_END, 1)[0].strip()
    if not payload.startswith("```json\n") or not payload.endswith("\n```"):
        raise ValueError("freeze payload must be one fenced JSON block")

    try:
        result = json.loads(payload[len("```json\n") : -len("\n```")])
    except json.JSONDecodeError as error:
        raise ValueError(f"freeze JSON is invalid: {error}") from error

    if not isinstance(result, dict):
        raise ValueError("freeze JSON must be an object")
    return result


def load_freeze(plan_path: Path) -> dict[str, Any]:
    try:
        document = plan_path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ValueError(f"migration plan is missing: {plan_path}") from error
    return parse_freeze_document(document)


def validate_path_list(paths: Any, name: str, expected_count: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
        return [failure(f"{name}-type", f"{name} must be an array of path strings")]

    if len(paths) != expected_count:
        errors.append(
            failure(
                f"{name}-count",
                f"{name} has {len(paths)} paths; expected {expected_count}",
            )
        )
    if len(set(paths)) != len(paths):
        errors.append(failure(f"{name}-duplicate", f"{name} contains duplicate paths"))
    if paths != sorted(paths):
        errors.append(failure(f"{name}-order", f"{name} must be sorted"))

    invalid_paths = []
    for path in paths:
        parsed = PurePosixPath(path)
        if (
            parsed.is_absolute()
            or ".." in parsed.parts
            or parsed.suffix != ".html"
            or str(parsed) != path
            or any(ord(character) < 32 or ord(character) == 127 for character in path)
        ):
            invalid_paths.append(path)
    if invalid_paths:
        errors.append(
            failure(f"{name}-path", f"{name} contains invalid paths: {invalid_paths}")
        )
    return errors


def validate_object_fields(
    value: dict[str, Any], name: str, fields: dict[str, type]
) -> list[str]:
    errors = []
    for field, expected_type in fields.items():
        if field not in value:
            errors.append(failure("freeze-schema", f"{name}.{field} is required"))
            continue
        actual = value[field]
        valid = isinstance(actual, expected_type)
        if expected_type is int and isinstance(actual, bool):
            valid = False
        if (
            valid
            and expected_type is str
            and any(
                ord(character) < 32 or ord(character) == 127
                for character in actual
            )
        ):
            errors.append(
                failure(
                    "freeze-schema",
                    f"{name}.{field} must not contain control characters",
                )
            )
            continue
        if not valid:
            errors.append(
                failure(
                    "freeze-schema",
                    f"{name}.{field} must be {expected_type.__name__}",
                )
            )
    return errors


def validate_ancestry_result(returncode: int, stderr: str = "") -> list[str]:
    if returncode == 0:
        return []
    if returncode == 1:
        return [
            failure(
                "migration-ancestry",
                "preMigrationCommit is not an ancestor of the Migration branch",
            )
        ]
    return [
        failure(
            "migration-ancestry-evidence",
            stderr or "cannot verify Migration branch ancestry",
        )
    ]


def validate_isolation(
    freeze: dict[str, Any],
    *,
    current_branch: str,
    remote_branch_exists: bool | None = None,
    preview_deployment_shas: list[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    migration_branch = freeze["migration"].get("branch")
    if current_branch != migration_branch:
        errors.append(
            failure(
                "migration-checkout",
                f"current branch is {current_branch!r}; expected {migration_branch!r}",
            )
        )
    if remote_branch_exists is True:
        errors.append(
            failure(
                "remote-migration-branch",
                f"remote branch {migration_branch!r} exists and can trigger Preview",
            )
        )
    if preview_deployment_shas:
        errors.append(
            failure(
                "migration-preview-history",
                "Migration commits already have Vercel Preview deployments: "
                + ", ".join(preview_deployment_shas),
            )
        )
    return errors


def validate_freeze(
    freeze: dict[str, Any],
    repo_root: Path,
    *,
    verify_git_tree: bool,
    command_runner: CommandRunner = run_command,
) -> list[str]:
    errors: list[str] = []
    production = freeze.get("production")
    migration = freeze.get("migration")
    cutover = freeze.get("cutoverEvidence")
    authority = freeze.get("authority")
    issues = freeze.get("issues")
    baseline_paths = freeze.get("baselinePaths")
    new_paths = freeze.get("newCanonicalPaths")
    pre_migration_commit = freeze.get("preMigrationCommit")
    frozen_at = freeze.get("frozenAt")

    schema_version = freeze.get("schemaVersion")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 1
    ):
        errors.append(failure("schema-version", "schemaVersion must be integer 1"))
    if not is_rfc3339_utc_timestamp(frozen_at):
        errors.append(
            failure("freeze-time", "frozenAt must be an RFC 3339 UTC timestamp")
        )

    errors.extend(
        validate_path_list(baseline_paths, "baseline", EXPECTED_BASELINE_COUNT)
    )
    errors.extend(
        validate_path_list(new_paths, "new-canonical", EXPECTED_NEW_CANONICAL_COUNT)
    )
    string_baseline_paths = isinstance(baseline_paths, list) and all(
        isinstance(path, str) for path in baseline_paths
    )
    string_new_paths = isinstance(new_paths, list) and all(
        isinstance(path, str) for path in new_paths
    )
    if string_baseline_paths and string_new_paths:
        overlap = sorted(set(baseline_paths) & set(new_paths))
        if overlap:
            errors.append(
                failure("allowlist-overlap", f"baseline and new paths overlap: {overlap}")
            )

    object_fields = {
        "production": production,
        "migration": migration,
        "cutoverEvidence": cutover,
        "authority": authority,
        "issues": issues,
    }
    invalid_objects = [
        name for name, value in object_fields.items() if not isinstance(value, dict)
    ]
    if invalid_objects:
        errors.append(
            failure(
                "freeze-schema",
                "required fields must be objects: " + ", ".join(invalid_objects),
            )
        )
    if not isinstance(pre_migration_commit, str):
        errors.append(
            failure("freeze-schema", "preMigrationCommit must be a commit SHA string")
        )
    elif re.fullmatch(r"[0-9a-f]{40}", pre_migration_commit) is None:
        errors.append(
            failure(
                "commit-identity",
                "preMigrationCommit must be an exact 40-character lowercase SHA",
            )
        )
    if invalid_objects or not isinstance(pre_migration_commit, str):
        return errors

    errors.extend(
        validate_object_fields(
            production,
            "production",
            {
                "repository": str,
                "provider": str,
                "environment": str,
                "canonicalHost": str,
                "sourceBranch": str,
                "trigger": str,
                "deploymentId": int,
                "deploymentSha": str,
                "deploymentUrl": str,
                "deploymentCompletedAt": str,
                "indexSha256": str,
                "secondaryHost": dict,
            },
        )
    )
    errors.extend(
        validate_object_fields(
            migration,
            "migration",
            {
                "branch": str,
                "remotePolicy": str,
                "previewRisk": str,
                "cutoverTrigger": str,
            },
        )
    )
    errors.extend(
        validate_object_fields(
            cutover,
            "cutoverEvidence",
            {
                "storage": str,
                "trackerIssue": int,
                "recordFormat": str,
                "appendOnly": bool,
                "mayMutateCandidate": bool,
                "requiredIdentity": str,
            },
        )
    )
    errors.extend(
        validate_object_fields(
            issues,
            "issues",
            {"blueprint": int, "spec": int, "ticket": int},
        )
    )
    secondary_host = production.get("secondaryHost")
    if isinstance(secondary_host, dict):
        errors.extend(
            validate_object_fields(
                secondary_host,
                "production.secondaryHost",
                {
                    "url": str,
                    "expectedStatus": int,
                    "latestObservedDeploymentSha": str,
                },
            )
        )
    if errors:
        return errors

    if not is_rfc3339_utc_timestamp(production["deploymentCompletedAt"]):
        errors.append(
            failure(
                "deployment-completed-at",
                "deploymentCompletedAt must be an RFC 3339 UTC timestamp",
            )
        )
    if re.fullmatch(r"[0-9a-f]{64}", production["indexSha256"]) is None:
        errors.append(
            failure(
                "index-digest",
                "indexSha256 must be an exact lowercase SHA-256 digest",
            )
        )
    if re.fullmatch(
        r"[0-9a-f]{40}",
        production["secondaryHost"]["latestObservedDeploymentSha"],
    ) is None:
        errors.append(
            failure(
                "secondary-deployment-sha",
                "latestObservedDeploymentSha must be an exact lowercase commit SHA",
            )
        )
    if errors:
        return errors

    frozen_time = parse_rfc3339_utc_timestamp(frozen_at)
    deployment_completed_time = parse_rfc3339_utc_timestamp(
        production["deploymentCompletedAt"]
    )
    if (
        frozen_time is not None
        and deployment_completed_time is not None
        and deployment_completed_time > frozen_time
    ):
        errors.append(
            failure(
                "evidence-chronology",
                "deploymentCompletedAt must not be later than frozenAt",
            )
        )
        return errors

    if production.get("provider") != "Vercel":
        errors.append(failure("production-provider", "production provider must be Vercel"))
    if production.get("environment") != "Production":
        errors.append(
            failure("production-environment", "deployment environment must be Production")
        )
    if production.get("sourceBranch") != "main":
        errors.append(failure("production-branch", "production source branch must be main"))
    if production.get("trigger") != "vercel-git-integration-on-remote-main":
        errors.append(
            failure(
                "deployment-trigger",
                "production trigger must be the frozen Vercel remote-main integration",
            )
        )
    if production.get("deploymentSha") != pre_migration_commit:
        errors.append(
            failure("deployment-identity", "deployment SHA must equal preMigrationCommit")
        )
    if not str(production.get("canonicalHost", "")).startswith("https://"):
        errors.append(failure("production-host", "canonicalHost must be an HTTPS URL"))

    if migration.get("branch") == production.get("sourceBranch"):
        errors.append(
            failure("publishing-branch", "migration branch must differ from production branch")
        )
    if migration.get("remotePolicy") != "local-only-until-cutover":
        errors.append(
            failure(
                "preview-publication",
                "migration remotePolicy must prevent Vercel Preview publication",
            )
        )
    if migration.get("previewRisk") != "Vercel deploys remote non-main commits as Preview":
        errors.append(
            failure(
                "preview-risk",
                "previewRisk must describe Vercel publication from remote non-main commits",
            )
        )
    if migration.get("cutoverTrigger") != (
        "authorized coherent merge of the exact reviewed checkpoint to main"
    ):
        errors.append(
            failure(
                "cutover-trigger",
                "cutoverTrigger must require one authorized exact-checkpoint merge",
            )
        )

    if issues != {"blueprint": 12, "spec": 13, "ticket": 14}:
        errors.append(
            failure(
                "issue-boundary",
                "Freeze authority must remain bound to Issues #12, #13, and #14",
            )
        )

    repository_parts = production["repository"].split("/", 1)
    expected_secondary_url = (
        f"https://{repository_parts[0]}.github.io/{repository_parts[1]}/"
        if len(repository_parts) == 2
        else ""
    )
    if production["secondaryHost"]["url"] != expected_secondary_url:
        errors.append(
            failure(
                "secondary-host-url",
                "secondaryHost must be the repository's GitHub Pages URL",
            )
        )
    if production["secondaryHost"]["expectedStatus"] != 404:
        errors.append(
            failure(
                "secondary-host-status",
                "secondaryHost must preserve the frozen HTTP 404 observation",
            )
        )

    current_branch = command_runner(["git", "branch", "--show-current"], repo_root)
    if current_branch.returncode != 0 or not current_branch.stdout.strip():
        errors.append(
            failure(
                "migration-checkout-evidence",
                current_branch.stderr.strip() or "cannot determine current branch",
            )
        )
    else:
        errors.extend(
            validate_isolation(
                freeze,
                current_branch=current_branch.stdout.strip(),
            )
        )

    ancestry = command_runner(
        ["git", "merge-base", "--is-ancestor", pre_migration_commit, "HEAD"],
        repo_root,
    )
    errors.extend(validate_ancestry_result(ancestry.returncode, ancestry.stderr.strip()))

    if cutover.get("storage") != "outside-reviewed-candidate":
        errors.append(
            failure(
                "candidate-self-reference",
                "cutover evidence must remain outside the reviewed candidate",
            )
        )
    if cutover.get("appendOnly") is not True:
        errors.append(failure("cutover-mutation", "cutover evidence must be append-only"))
    if cutover.get("mayMutateCandidate") is not False:
        errors.append(
            failure("candidate-mutation", "cutover evidence must not mutate the candidate")
        )
    if cutover.get("trackerIssue") != 75:
        errors.append(
            failure("cutover-location", "cutover evidence thread must be Issue #75")
        )
    if cutover.get("recordFormat") != "append-only-comments":
        errors.append(
            failure(
                "cutover-record-format",
                "cutover evidence must use append-only comments, not a mutable body",
            )
        )
    if cutover.get("requiredIdentity") != "exact reviewed checkpoint SHA":
        errors.append(
            failure(
                "cutover-identity",
                "cutover evidence must identify the exact reviewed checkpoint SHA",
            )
        )

    expected_authority = {
        "freeze": "docs/migration/course-migration-plan.md",
        "pageDisposition": "docs/migration/course-migration-manifest.json",
        "sources": "source-anchors.json",
        "cutoverRecord": "GitHub Issue #75 comments",
    }
    if authority != expected_authority:
        errors.append(
            failure(
                "authority-boundary",
                "freeze, disposition, Source, and cutover authorities must stay distinct",
            )
        )

    if verify_git_tree and string_baseline_paths:
        resolved = command_runner(
            ["git", "rev-parse", f"{pre_migration_commit}^{{commit}}"], repo_root
        )
        if resolved.returncode != 0 or resolved.stdout.strip() != pre_migration_commit:
            errors.append(
                failure("commit-identity", "preMigrationCommit does not resolve exactly")
            )
        else:
            tree = command_runner(
                ["git", "ls-tree", "-r", "--name-only", pre_migration_commit],
                repo_root,
            )
            if tree.returncode != 0:
                errors.append(
                    failure("baseline-tree", tree.stderr.strip() or "cannot read git tree")
                )
            else:
                tree_paths = sorted(
                    path for path in tree.stdout.splitlines() if path.endswith(".html")
                )
                if tree_paths != baseline_paths:
                    missing = sorted(set(baseline_paths) - set(tree_paths))
                    unexpected = sorted(set(tree_paths) - set(baseline_paths))
                    errors.append(
                        failure(
                            "baseline-tree-mismatch",
                            f"missing from tree={missing}; unexpected in tree={unexpected}",
                        )
                    )

            index_blob = command_runner(
                ["git", "show", f"{pre_migration_commit}:index.html"],
                repo_root,
                text=False,
            )
            if index_blob.returncode != 0:
                errors.append(
                    failure(
                        "index-blob",
                        index_blob.stderr.decode(errors="replace").strip()
                        or "cannot read frozen index.html",
                    )
                )
            elif hashlib.sha256(index_blob.stdout).hexdigest() != production[
                "indexSha256"
            ]:
                errors.append(
                    failure(
                        "index-digest-mismatch",
                        "indexSha256 differs from the frozen index.html blob",
                    )
                )
    return errors


def gh_json(repo_root: Path, endpoint: str) -> Any:
    result = run_command(["gh", "api", endpoint], repo_root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"gh api failed: {endpoint}")
    return json.loads(result.stdout)


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def require_object_list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{label} must be an array of JSON objects")
    return value


def verify_github_evidence(
    freeze: dict[str, Any],
    repo_root: Path,
    *,
    github_fetcher: GitHubFetcher = gh_json,
    command_runner: CommandRunner = run_command,
) -> list[str]:
    errors: list[str] = []
    production = freeze["production"]
    commit = freeze["preMigrationCommit"]
    repository = production["repository"]

    current_branch = command_runner(["git", "branch", "--show-current"], repo_root)
    migration_history = command_runner(
        ["git", "rev-list", f"{commit}..HEAD"], repo_root
    )
    remote_branch = command_runner(
        [
            "git",
            "ls-remote",
            "--heads",
            "origin",
            f"refs/heads/{freeze['migration']['branch']}",
        ],
        repo_root,
    )
    if (
        current_branch.returncode != 0
        or migration_history.returncode != 0
        or remote_branch.returncode != 0
    ):
        errors.append(
            failure(
                "isolation-evidence",
                "cannot determine current branch, Migration history, or remote absence",
            )
        )
    else:
        try:
            previewed_shas = []
            for sha in migration_history.stdout.splitlines():
                preview_deployments = require_object_list(
                    github_fetcher(
                        repo_root,
                        f"repos/{repository}/deployments?environment=Preview&sha={sha}&per_page=1",
                    ),
                    "Preview deployments response",
                )
                if preview_deployments:
                    previewed_shas.append(sha)
            errors.extend(
                validate_isolation(
                    freeze,
                    current_branch=current_branch.stdout.strip(),
                    remote_branch_exists=bool(remote_branch.stdout.strip()),
                    preview_deployment_shas=previewed_shas,
                )
            )
        except (RuntimeError, json.JSONDecodeError, ValueError) as error:
            errors.append(failure("preview-evidence", str(error)))

    try:
        metadata = require_object(
            github_fetcher(repo_root, f"repos/{repository}"),
            "repository response",
        )
        if metadata.get("homepage") != production["canonicalHost"]:
            errors.append(
                failure("homepage-host", "repository homepage differs from canonicalHost")
            )

        remote_commit = require_object(
            github_fetcher(
                repo_root,
                f"repos/{repository}/commits/{production['sourceBranch']}",
            ),
            "remote commit response",
        )
        if remote_commit.get("sha") != commit:
            errors.append(
                failure("remote-main", "remote production branch moved from frozen commit")
            )

        deployments = require_object_list(
            github_fetcher(
                repo_root,
                f"repos/{repository}/deployments?environment=Production&per_page=1",
            ),
            "Production deployments response",
        )
        if not deployments:
            errors.append(failure("latest-deployment", "no Production deployment found"))
        else:
            deployment = deployments[0]
            if deployment.get("id") != production["deploymentId"]:
                errors.append(
                    failure(
                        "latest-deployment",
                        "frozen deployment is not latest Production",
                    )
                )
            if deployment.get("sha") != commit:
                errors.append(
                    failure("deployment-sha", "latest Production deployment SHA differs")
                )

        statuses = require_object_list(
            github_fetcher(
                repo_root,
                f"repos/{repository}/deployments/{production['deploymentId']}/statuses",
            ),
            "deployment statuses response",
        )
        if not statuses:
            errors.append(failure("deployment-status", "deployment has no status"))
        else:
            status = statuses[0]
            if status.get("state") != "success":
                errors.append(
                    failure("deployment-status", "frozen deployment is not successful")
                )
            if status.get("environment_url") != production["deploymentUrl"]:
                errors.append(
                    failure("deployment-url", "immutable deployment URL differs from freeze")
                )
            if status.get("created_at") != production["deploymentCompletedAt"]:
                errors.append(
                    failure(
                        "deployment-completed-at-mismatch",
                        "deployment completion timestamp differs from freeze",
                    )
                )

        pages_deployments = require_object_list(
            github_fetcher(
                repo_root,
                f"repos/{repository}/deployments?environment=github-pages&per_page=1",
            ),
            "GitHub Pages deployments response",
        )
        expected_pages_sha = production["secondaryHost"][
            "latestObservedDeploymentSha"
        ]
        if not pages_deployments or pages_deployments[0].get("sha") != expected_pages_sha:
            errors.append(
                failure(
                    "secondary-deployment-sha-mismatch",
                    "latest GitHub Pages deployment SHA differs from freeze",
                )
            )
    except (KeyError, RuntimeError, json.JSONDecodeError, ValueError) as error:
        errors.append(failure("github-evidence", str(error)))
    return errors


def fetch_bytes(url: str) -> tuple[int, bytes]:
    request = Request(url, headers={"User-Agent": "lessons-migration-freeze-check/1"})
    with urlopen(request, timeout=20) as response:
        return response.status, response.read()


def verify_online(freeze: dict[str, Any], repo_root: Path) -> list[str]:
    precondition_errors = validate_freeze(
        freeze, repo_root, verify_git_tree=False
    )
    if precondition_errors:
        return [
            failure("online-precondition", "Freeze contract is invalid"),
            *precondition_errors,
        ]

    errors = verify_github_evidence(freeze, repo_root)
    production = freeze["production"]
    commit = freeze["preMigrationCommit"]

    def compare_path(path: str) -> str | None:
        blob = run_command(
            ["git", "show", f"{commit}:{path}"], repo_root, text=False
        )
        if blob.returncode != 0:
            return failure("git-blob", f"cannot read {path} from {commit}")
        url = f"{production['canonicalHost'].rstrip('/')}/{quote(path, safe='/')}"
        try:
            status, body = fetch_bytes(url)
        except Exception as error:  # URL errors vary by platform and TLS stack.
            return failure("production-fetch", f"{path}: {error}")
        if status != 200:
            return failure("production-status", f"{path}: HTTP {status}")
        body_digest = hashlib.sha256(body)
        if body_digest.digest() != hashlib.sha256(blob.stdout).digest():
            return failure("production-content", f"{path}: bytes differ from {commit}")
        if path == "index.html" and body_digest.hexdigest() != production["indexSha256"]:
            return failure(
                "production-index-digest",
                "index.html digest differs from the frozen indexSha256",
            )
        return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        for result in executor.map(compare_path, freeze["baselinePaths"]):
            if result:
                errors.append(result)

    secondary = production["secondaryHost"]
    try:
        status, _ = fetch_bytes(secondary["url"])
        if status != secondary["expectedStatus"]:
            errors.append(
                failure(
                    "secondary-publisher",
                    f"secondary host returned HTTP {status}; expected {secondary['expectedStatus']}",
                )
            )
    except HTTPError as error:
        if error.code != secondary["expectedStatus"]:
            errors.append(
                failure(
                    "secondary-publisher",
                    f"secondary host returned HTTP {error.code}; expected {secondary['expectedStatus']}",
                )
            )
    except Exception as error:
        errors.append(failure("secondary-host", str(error)))
    return errors


def run_self_test(freeze: dict[str, Any], repo_root: Path) -> list[str]:
    cases = []

    missing_baseline = copy.deepcopy(freeze)
    missing_baseline["baselinePaths"].pop()
    cases.append(("missing baseline path", missing_baseline, "baseline-count"))

    duplicate_new_path = copy.deepcopy(freeze)
    duplicate_new_path["newCanonicalPaths"][-1] = duplicate_new_path[
        "newCanonicalPaths"
    ][0]
    cases.append(("duplicate new path", duplicate_new_path, "new-canonical-duplicate"))

    publishing_branch = copy.deepcopy(freeze)
    publishing_branch["migration"]["branch"] = publishing_branch["production"][
        "sourceBranch"
    ]
    cases.append(("publishing branch", publishing_branch, "publishing-branch"))

    wrong_checkout = copy.deepcopy(freeze)
    wrong_checkout["migration"]["branch"] = "codex/different-migration"
    cases.append(("wrong checkout", wrong_checkout, "migration-checkout"))

    self_referential_cutover = copy.deepcopy(freeze)
    self_referential_cutover["cutoverEvidence"]["storage"] = "inside-reviewed-candidate"
    cases.append(
        (
            "self-referential cutover",
            self_referential_cutover,
            "candidate-self-reference",
        )
    )

    malformed_object = copy.deepcopy(freeze)
    malformed_object["migration"] = None
    cases.append(("malformed object", malformed_object, "freeze-schema"))

    malformed_path = copy.deepcopy(freeze)
    malformed_path["baselinePaths"][0] = {"path": "index.html"}
    cases.append(("malformed path", malformed_path, "baseline-type"))

    control_character_path = copy.deepcopy(freeze)
    control_character_path["baselinePaths"][0] = "\x00.html"
    cases.append(
        ("control character path", control_character_path, "baseline-path")
    )

    boolean_schema_version = copy.deepcopy(freeze)
    boolean_schema_version["schemaVersion"] = True
    cases.append(("boolean schema version", boolean_schema_version, "schema-version"))

    float_schema_version = copy.deepcopy(freeze)
    float_schema_version["schemaVersion"] = 1.0
    cases.append(("float schema version", float_schema_version, "schema-version"))

    malformed_freeze_time = copy.deepcopy(freeze)
    malformed_freeze_time["frozenAt"] = "not-a-time"
    cases.append(("malformed freeze time", malformed_freeze_time, "freeze-time"))

    impossible_freeze_time = copy.deepcopy(freeze)
    impossible_freeze_time["frozenAt"] = "2026-99-99T99:99:99Z"
    cases.append(("impossible freeze time", impossible_freeze_time, "freeze-time"))

    malformed_commit = copy.deepcopy(freeze)
    malformed_commit["preMigrationCommit"] = "\x00"
    cases.append(("malformed commit", malformed_commit, "commit-identity"))

    malformed_completion_time = copy.deepcopy(freeze)
    malformed_completion_time["production"]["deploymentCompletedAt"] = "not-a-time"
    cases.append(
        (
            "malformed deployment completion time",
            malformed_completion_time,
            "deployment-completed-at",
        )
    )

    impossible_completion_time = copy.deepcopy(freeze)
    impossible_completion_time["production"][
        "deploymentCompletedAt"
    ] = "2026-99-99T99:99:99Z"
    cases.append(
        (
            "impossible deployment completion time",
            impossible_completion_time,
            "deployment-completed-at",
        )
    )

    impossible_evidence_chronology = copy.deepcopy(freeze)
    impossible_evidence_chronology["frozenAt"] = "2026-07-14T00:00:00Z"
    cases.append(
        (
            "Freeze before deployment completion",
            impossible_evidence_chronology,
            "evidence-chronology",
        )
    )

    malformed_index_digest = copy.deepcopy(freeze)
    malformed_index_digest["production"]["indexSha256"] = "not-a-digest"
    cases.append(("malformed index digest", malformed_index_digest, "index-digest"))

    malformed_pages_sha = copy.deepcopy(freeze)
    malformed_pages_sha["production"]["secondaryHost"][
        "latestObservedDeploymentSha"
    ] = "not-a-sha"
    cases.append(
        (
            "malformed secondary deployment SHA",
            malformed_pages_sha,
            "secondary-deployment-sha",
        )
    )

    missing_repository = copy.deepcopy(freeze)
    del missing_repository["production"]["repository"]
    cases.append(("missing repository", missing_repository, "freeze-schema"))

    missing_secondary_host = copy.deepcopy(freeze)
    del missing_secondary_host["production"]["secondaryHost"]
    cases.append(("missing secondary host", missing_secondary_host, "freeze-schema"))

    wrong_issue_boundary = copy.deepcopy(freeze)
    wrong_issue_boundary["issues"]["ticket"] = 999
    cases.append(("wrong issue boundary", wrong_issue_boundary, "issue-boundary"))

    wrong_preview_risk = copy.deepcopy(freeze)
    wrong_preview_risk["migration"]["previewRisk"] = "none"
    cases.append(("wrong Preview risk", wrong_preview_risk, "preview-risk"))

    wrong_secondary_status = copy.deepcopy(freeze)
    wrong_secondary_status["production"]["secondaryHost"]["expectedStatus"] = 200
    cases.append(
        ("wrong secondary host status", wrong_secondary_status, "secondary-host-status")
    )

    manual_trigger = copy.deepcopy(freeze)
    manual_trigger["production"]["trigger"] = "manual"
    cases.append(("manual trigger", manual_trigger, "deployment-trigger"))

    mutable_record = copy.deepcopy(freeze)
    mutable_record["cutoverEvidence"]["recordFormat"] = "mutable-body"
    cases.append(
        ("mutable cutover record", mutable_record, "cutover-record-format")
    )

    moving_identity = copy.deepcopy(freeze)
    moving_identity["cutoverEvidence"]["requiredIdentity"] = "latest candidate"
    cases.append(("moving cutover identity", moving_identity, "cutover-identity"))

    errors = []
    freeze_block = (
        f"{FREEZE_START}\n```json\n{json.dumps(freeze)}\n```\n{FREEZE_END}\n"
    )
    try:
        parse_freeze_document(freeze_block + freeze_block)
    except ValueError as error:
        if "exactly one" not in str(error):
            errors.append(
                failure(
                    "negative-fixture",
                    f"duplicate Freeze block returned unexpected error: {error}",
                )
            )
    else:
        errors.append(
            failure(
                "negative-fixture",
                "duplicate Freeze blocks did not fail closed",
            )
        )

    for name, mutated, expected_code in cases:
        actual = validate_freeze(mutated, repo_root, verify_git_tree=False)
        codes = {item.split("]", 1)[0].lstrip("[") for item in actual}
        if expected_code not in codes:
            errors.append(
                failure(
                    "negative-fixture",
                    f"{name} did not fail with [{expected_code}]; got {sorted(codes)}",
                )
            )

    mismatched_index_digest = copy.deepcopy(freeze)
    mismatched_index_digest["production"]["indexSha256"] = "0" * 64
    digest_errors = validate_freeze(
        mismatched_index_digest,
        repo_root,
        verify_git_tree=True,
    )
    digest_codes = {item.split("]", 1)[0].lstrip("[") for item in digest_errors}
    if "index-digest-mismatch" not in digest_codes:
        errors.append(
            failure(
                "negative-fixture",
                "mismatched indexSha256 did not fail against the frozen blob",
            )
        )

    remote_publication = validate_isolation(
        freeze,
        current_branch=freeze["migration"]["branch"],
        remote_branch_exists=True,
        preview_deployment_shas=["ancestor-migration-commit"],
    )
    remote_codes = {
        item.split("]", 1)[0].lstrip("[") for item in remote_publication
    }
    for expected_code in (
        "remote-migration-branch",
        "migration-preview-history",
    ):
        if expected_code not in remote_codes:
            errors.append(
                failure(
                    "negative-fixture",
                    f"remote publication did not fail with [{expected_code}]",
                )
            )

    def non_ancestor_runner(
        args: list[str], root: Path, *, text: bool = True
    ) -> subprocess.CompletedProcess[Any]:
        if args[:3] == ["git", "merge-base", "--is-ancestor"]:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="")
        return run_command(args, root, text=text)

    ancestry_errors = validate_freeze(
        freeze,
        repo_root,
        verify_git_tree=False,
        command_runner=non_ancestor_runner,
    )
    ancestry_codes = {
        item.split("]", 1)[0].lstrip("[") for item in ancestry_errors
    }
    if "migration-ancestry" not in ancestry_codes:
        errors.append(
            failure(
                "negative-fixture",
                "non-ancestor baseline did not fail with [migration-ancestry]",
            )
        )

    def offline_isolation_runner(
        args: list[str], root: Path, *, text: bool = True
    ) -> subprocess.CompletedProcess[Any]:
        if args[:3] == ["git", "ls-remote", "--heads"]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return run_command(args, root, text=text)

    def malformed_github_fetcher(root: Path, endpoint: str) -> Any:
        del root
        if "environment=Preview" in endpoint:
            return []
        return "not-a-json-object"

    malformed_api_errors = verify_github_evidence(
        freeze,
        repo_root,
        github_fetcher=malformed_github_fetcher,
        command_runner=offline_isolation_runner,
    )
    malformed_api_codes = {
        item.split("]", 1)[0].lstrip("[") for item in malformed_api_errors
    }
    if "github-evidence" not in malformed_api_codes:
        errors.append(
            failure(
                "negative-fixture",
                "malformed GitHub response did not return [github-evidence]",
            )
        )

    original_production = freeze["production"]
    original_repository = original_production["repository"]

    def fixture_github_fetcher(root: Path, endpoint: str) -> Any:
        del root
        if "environment=Preview" in endpoint:
            return []
        if endpoint == f"repos/{original_repository}":
            return {"homepage": original_production["canonicalHost"]}
        if "/commits/" in endpoint:
            return {"sha": freeze["preMigrationCommit"]}
        if "environment=Production" in endpoint:
            return [
                {
                    "id": original_production["deploymentId"],
                    "sha": freeze["preMigrationCommit"],
                }
            ]
        if endpoint.endswith("/statuses"):
            return [
                {
                    "state": "success",
                    "environment_url": original_production["deploymentUrl"],
                    "created_at": original_production["deploymentCompletedAt"],
                }
            ]
        if "environment=github-pages" in endpoint:
            return [
                {
                    "sha": original_production["secondaryHost"][
                        "latestObservedDeploymentSha"
                    ]
                }
            ]
        raise RuntimeError(f"unexpected fixture endpoint: {endpoint}")

    drifted_evidence = copy.deepcopy(freeze)
    drifted_evidence["production"][
        "deploymentCompletedAt"
    ] = "2099-01-01T00:00:00Z"
    drifted_evidence["production"]["secondaryHost"][
        "latestObservedDeploymentSha"
    ] = "0" * 40
    drift_errors = verify_github_evidence(
        drifted_evidence,
        repo_root,
        github_fetcher=fixture_github_fetcher,
        command_runner=offline_isolation_runner,
    )
    drift_codes = {item.split("]", 1)[0].lstrip("[") for item in drift_errors}
    expected_drift_codes = {
        "deployment-completed-at-mismatch",
        "secondary-deployment-sha-mismatch",
    }
    if not expected_drift_codes.issubset(drift_codes):
        errors.append(
            failure(
                "negative-fixture",
                "authoritative GitHub evidence drift was not fully blocked",
            )
        )

    online_precondition_errors = verify_online(control_character_path, repo_root)
    online_precondition_codes = {
        item.split("]", 1)[0].lstrip("[") for item in online_precondition_errors
    }
    if not {"online-precondition", "baseline-path"}.issubset(
        online_precondition_codes
    ):
        errors.append(
            failure(
                "negative-fixture",
                "control character path escaped the online precondition",
            )
        )
    return errors


def report(label: str, errors: list[str]) -> bool:
    if errors:
        print(f"{label} BLOCKED ({len(errors)} errors)")
        for error in errors:
            print(f"- {error}")
        return False
    print(f"{label} PASS")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--online",
        action="store_true",
        help="also compare GitHub/Vercel evidence and all 73 production URLs",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="prove representative invalid freeze states fail closed",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    plan_path = repo_root / "docs/migration/course-migration-plan.md"
    try:
        freeze = load_freeze(plan_path)
    except ValueError as error:
        print(f"FREEZE BLOCKED\n- [freeze-load] {error}")
        return 1

    passed = report(
        "FREEZE", validate_freeze(freeze, repo_root, verify_git_tree=True)
    )
    if args.self_test:
        passed = report("NEGATIVE FIXTURES", run_self_test(freeze, repo_root)) and passed
    if args.online:
        online_errors = verify_online(freeze, repo_root) if passed else [
            failure("online-skipped", "offline Freeze validation did not pass")
        ]
        passed = report("ONLINE BASELINE", online_errors) and passed
        if not online_errors:
            print(f"ONLINE URLS PASS ({len(freeze['baselinePaths'])}/73)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
