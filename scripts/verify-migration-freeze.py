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


def failure(code: str, message: str) -> str:
    return f"[{code}] {message}"


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


def load_freeze(plan_path: Path) -> dict[str, Any]:
    try:
        document = plan_path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ValueError(f"migration plan is missing: {plan_path}") from error

    if FREEZE_START not in document or FREEZE_END not in document:
        raise ValueError("migration plan does not contain the freeze JSON markers")

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

    schema_version = freeze.get("schemaVersion")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 1
    ):
        errors.append(failure("schema-version", "schemaVersion must be integer 1"))

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
    return errors


def gh_json(repo_root: Path, endpoint: str) -> Any:
    result = run_command(["gh", "api", endpoint], repo_root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"gh api failed: {endpoint}")
    return json.loads(result.stdout)


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

    errors: list[str] = []
    production = freeze["production"]
    commit = freeze["preMigrationCommit"]
    repository = production["repository"]

    current_branch = run_command(["git", "branch", "--show-current"], repo_root)
    migration_history = run_command(
        ["git", "rev-list", f"{commit}..HEAD"], repo_root
    )
    remote_branch = run_command(
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
                preview_deployments = gh_json(
                    repo_root,
                    f"repos/{repository}/deployments?environment=Preview&sha={sha}&per_page=1",
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
        except (RuntimeError, json.JSONDecodeError) as error:
            errors.append(failure("preview-evidence", str(error)))

    try:
        metadata = gh_json(repo_root, f"repos/{repository}")
        if metadata.get("homepage") != production["canonicalHost"]:
            errors.append(
                failure("homepage-host", "repository homepage differs from canonicalHost")
            )

        remote_commit = gh_json(
            repo_root, f"repos/{repository}/commits/{production['sourceBranch']}"
        )
        if remote_commit.get("sha") != commit:
            errors.append(
                failure("remote-main", "remote production branch moved from frozen commit")
            )

        deployments = gh_json(
            repo_root,
            f"repos/{repository}/deployments?environment=Production&per_page=1",
        )
        if not deployments or deployments[0].get("id") != production["deploymentId"]:
            errors.append(
                failure("latest-deployment", "frozen deployment is not latest Production")
            )
        elif deployments[0].get("sha") != commit:
            errors.append(
                failure("deployment-sha", "latest Production deployment SHA differs")
            )

        statuses = gh_json(
            repo_root,
            f"repos/{repository}/deployments/{production['deploymentId']}/statuses",
        )
        if not statuses or statuses[0].get("state") != "success":
            errors.append(failure("deployment-status", "frozen deployment is not successful"))
        elif statuses[0].get("environment_url") != production["deploymentUrl"]:
            errors.append(
                failure("deployment-url", "immutable deployment URL differs from freeze")
            )
    except (KeyError, RuntimeError, json.JSONDecodeError) as error:
        errors.append(failure("github-evidence", str(error)))

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
        if hashlib.sha256(body).digest() != hashlib.sha256(blob.stdout).digest():
            return failure("production-content", f"{path}: bytes differ from {commit}")
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

    malformed_commit = copy.deepcopy(freeze)
    malformed_commit["preMigrationCommit"] = "\x00"
    cases.append(("malformed commit", malformed_commit, "commit-identity"))

    missing_repository = copy.deepcopy(freeze)
    del missing_repository["production"]["repository"]
    cases.append(("missing repository", missing_repository, "freeze-schema"))

    missing_secondary_host = copy.deepcopy(freeze)
    del missing_secondary_host["production"]["secondaryHost"]
    cases.append(("missing secondary host", missing_secondary_host, "freeze-schema"))

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
