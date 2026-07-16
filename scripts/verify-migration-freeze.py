#!/usr/bin/env python3
"""Verify the bounded Freeze contract for the twelve-Phase migration."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
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
        ):
            invalid_paths.append(path)
    if invalid_paths:
        errors.append(
            failure(f"{name}-path", f"{name} contains invalid paths: {invalid_paths}")
        )
    return errors


def validate_freeze(
    freeze: dict[str, Any], repo_root: Path, *, verify_git_tree: bool
) -> list[str]:
    errors: list[str] = []
    try:
        production = freeze["production"]
        migration = freeze["migration"]
        cutover = freeze["cutoverEvidence"]
        authority = freeze["authority"]
        baseline_paths = freeze["baselinePaths"]
        new_paths = freeze["newCanonicalPaths"]
        pre_migration_commit = freeze["preMigrationCommit"]
    except (KeyError, TypeError) as error:
        return [failure("freeze-schema", f"missing required freeze field: {error}")]

    if freeze.get("schemaVersion") != 1:
        errors.append(failure("schema-version", "schemaVersion must be 1"))

    errors.extend(
        validate_path_list(baseline_paths, "baseline", EXPECTED_BASELINE_COUNT)
    )
    errors.extend(
        validate_path_list(new_paths, "new-canonical", EXPECTED_NEW_CANONICAL_COUNT)
    )
    if isinstance(baseline_paths, list) and isinstance(new_paths, list):
        overlap = sorted(set(baseline_paths) & set(new_paths))
        if overlap:
            errors.append(
                failure("allowlist-overlap", f"baseline and new paths overlap: {overlap}")
            )

    if production.get("provider") != "Vercel":
        errors.append(failure("production-provider", "production provider must be Vercel"))
    if production.get("environment") != "Production":
        errors.append(
            failure("production-environment", "deployment environment must be Production")
        )
    if production.get("sourceBranch") != "main":
        errors.append(failure("production-branch", "production source branch must be main"))
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

    if verify_git_tree and isinstance(baseline_paths, list):
        resolved = run_command(
            ["git", "rev-parse", f"{pre_migration_commit}^{{commit}}"], repo_root
        )
        if resolved.returncode != 0 or resolved.stdout.strip() != pre_migration_commit:
            errors.append(
                failure("commit-identity", "preMigrationCommit does not resolve exactly")
            )
        else:
            tree = run_command(
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
    errors: list[str] = []
    production = freeze["production"]
    commit = freeze["preMigrationCommit"]
    repository = production["repository"]

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

    self_referential_cutover = copy.deepcopy(freeze)
    self_referential_cutover["cutoverEvidence"]["storage"] = "inside-reviewed-candidate"
    cases.append(
        (
            "self-referential cutover",
            self_referential_cutover,
            "candidate-self-reference",
        )
    )

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
