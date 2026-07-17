#!/usr/bin/env python3
"""Verify that durable course docs follow the canonical route/source contracts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
DOC_PATHS = ("MISSION.md", "RESOURCES.md", "NOTES.md")
MANIFEST_PATH = "docs/migration/course-migration-manifest.json"
REGISTRY_PATH = "source-anchors.json"
REQUIRED_DURABLE_PATHS = (
    "assets/templates/route-notebook.md",
    "docs/migration/cutover-report.md",
    "docs/maintenance/source-recertification.md",
    "learning-records/0004-adopt-route-based-twelve-phase-catalog.md",
    "learning-records/README.md",
)
FORBIDDEN_DURABLE_PATHS = (
    "reference/return-notebook-template.md",
    "learning-records/0004-adopt-route-based-course-migration.md",
)
FULL_GIT_SHA_PATTERN = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])")

REQUIRED_ANCHORS = {
    "common-foundation": "course-orient-readiness-contract",
    "cowork-starter": "claude-cowork-starter-surface",
    "code-readiness": "claude-code-cli-session-start",
    "toolbox": "course-equip-toolbox-contract",
    "knowledge-delivery": "course-knowledge-delivery-contract",
    "design-delivery": "course-design-delivery-contract",
    "presentation-delivery": "course-presentation-delivery-contract",
    "engineering-delivery": "course-engineering-delivery-contract",
    "browser-evidence": "browser-evidence-addendum-contract",
    "agent-operations": "agent-operations-safety-contract",
    "workflow-standardization": "workflow-standardization-contract",
    "workflow-evaluation": "workflow-evaluation-contract",
    "scenario-rollout": "scenario-rollout-contract",
    "governance-lifecycle": "governance-lifecycle-contract",
}

BANNED_CLAIMS = (
    "完成 Phase",
    "Phase 3 後",
    "Phase 4 是選修設計路線",
    "Phase 5 的 Claude Design 01–08 是主線",
    "Claude Design 仍是 beta",
    "Harness",
)

def load_json(root: Path, path: str) -> dict:
    with (root / path).open(encoding="utf-8") as handle:
        return json.load(handle)


def verify(root: Path) -> list[str]:
    errors: list[str] = []
    for path in REQUIRED_DURABLE_PATHS:
        if not (root / path).is_file():
            errors.append(f"durable-path: missing required public contract {path}")
    for path in FORBIDDEN_DURABLE_PATHS:
        if (root / path).exists():
            errors.append(f"durable-duplicate: legacy contract path still exists {path}")
    cutover_path = root / "docs/migration/cutover-report.md"
    if cutover_path.is_file() and FULL_GIT_SHA_PATTERN.search(
        cutover_path.read_text(encoding="utf-8")
    ):
        errors.append(
            "cutover-self-identity: cutover template must not embed a commit SHA"
        )
    manifest = load_json(root, MANIFEST_PATH)
    registry = load_json(root, REGISTRY_PATH)
    docs = {path: (root / path).read_text(encoding="utf-8") for path in DOC_PATHS}
    combined = "\n".join(docs.values())

    route_ids = [route["id"] for route in manifest.get("routes", [])]
    if set(route_ids) != set(REQUIRED_ANCHORS):
        errors.append("route-map: validator route map differs from manifest")

    registry_ids = {anchor["id"] for anchor in registry.get("anchors", [])}
    missing_registry = sorted(set(REQUIRED_ANCHORS.values()) - registry_ids)
    if missing_registry:
        errors.append(f"source-registry: missing stable anchors {missing_registry}")

    mission = docs["MISSION.md"]
    if f"`{MANIFEST_PATH}`" not in mission:
        errors.append("mission-authority: canonical route manifest is not named")
    if f"`{REGISTRY_PATH}`" not in mission:
        errors.append("mission-authority: Source registry is not named")
    for route_id in route_ids:
        if f"`{route_id}`" not in mission:
            errors.append(f"mission-route: missing canonical route ID {route_id}")
        anchor_id = REQUIRED_ANCHORS.get(route_id)
        if anchor_id and f"`{anchor_id}`" not in mission:
            errors.append(f"mission-anchor: {route_id} does not name {anchor_id}")

    resources = docs["RESOURCES.md"]
    if f"`{REGISTRY_PATH}`" not in resources:
        errors.append("resources-authority: Source registry is not named")
    for anchor_id in REQUIRED_ANCHORS.values():
        if f"`{anchor_id}`" not in resources:
            errors.append(f"resources-anchor: missing stable anchor ID {anchor_id}")

    for claim in BANNED_CLAIMS:
        if claim in combined:
            errors.append(f"legacy-claim: durable docs still contain {claim!r}")

    return errors


def run_self_test() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "docs/migration").mkdir(parents=True)
        routes = [{"id": route_id} for route_id in REQUIRED_ANCHORS]
        anchors = [{"id": anchor_id} for anchor_id in REQUIRED_ANCHORS.values()]
        (root / MANIFEST_PATH).write_text(json.dumps({"routes": routes}), encoding="utf-8")
        (root / REGISTRY_PATH).write_text(json.dumps({"anchors": anchors}), encoding="utf-8")
        route_lines = "\n".join(
            f"- `{route_id}` — `{anchor_id}`"
            for route_id, anchor_id in REQUIRED_ANCHORS.items()
        )
        (root / "MISSION.md").write_text(
            f"`{MANIFEST_PATH}`\n`{REGISTRY_PATH}`\n{route_lines}\n", encoding="utf-8"
        )
        (root / "RESOURCES.md").write_text(
            f"`{REGISTRY_PATH}`\n" + "\n".join(f"`{item}`" for item in REQUIRED_ANCHORS.values()),
            encoding="utf-8",
        )
        (root / "NOTES.md").write_text(
            "Active mission 與 route contract 是 teaching authority。\n",
            encoding="utf-8",
        )
        fixture_content = {
            "assets/templates/route-notebook.md": "# Return notebook\n## Mission\n",
            "docs/migration/cutover-report.md": "# Cutover report template\nCandidate commit SHA：\n",
            "docs/maintenance/source-recertification.md": "# Source recertification contract\nSource anchor ID：\n",
            "learning-records/0004-adopt-route-based-twelve-phase-catalog.md": "# Route-based catalog\nStatus: adopted\n",
            "learning-records/README.md": "# Learning records\n0004-adopt-route-based-twelve-phase-catalog.md\n",
        }
        for path in REQUIRED_DURABLE_PATHS:
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(fixture_content[path], encoding="utf-8")
        if verify(root):
            print("SELF TEST FAILED: valid fixture was rejected")
            return 1
        missing_path = root / REQUIRED_DURABLE_PATHS[0]
        missing_path.unlink()
        missing_failures = verify(root)
        if not any("durable-path" in item for item in missing_failures):
            print("SELF TEST FAILED: missing durable public contract was accepted")
            return 1
        missing_path.write_text("restored fixture\n", encoding="utf-8")
        legacy_path = root / "reference/return-notebook-template.md"
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text("duplicate\n", encoding="utf-8")
        cutover_path = root / "docs/migration/cutover-report.md"
        clean_cutover = cutover_path.read_text(encoding="utf-8")
        cutover_path.write_text(
            clean_cutover + "0123456789abcdef0123456789abcdef01234567\n",
            encoding="utf-8",
        )
        unsafe_failures = verify(root)
        missing_codes = [
            code
            for code in ("durable-duplicate", "cutover-self-identity")
            if not any(code in item for item in unsafe_failures)
        ]
        if missing_codes:
            print(
                "SELF TEST FAILED: unsafe durable contracts were accepted: "
                + ", ".join(missing_codes)
            )
            return 1
        legacy_path.unlink()
        cutover_path.write_text(clean_cutover, encoding="utf-8")
        (root / "MISSION.md").write_text("完成 Phase 5 後即可使用 Harness。", encoding="utf-8")
        failures = verify(root)
        if not failures or not any("legacy-claim" in item for item in failures):
            print("SELF TEST FAILED: invalid fixture was accepted")
            return 1
    print("DURABLE COURSE DOCS SELF TEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    errors = verify(ROOT)
    if errors:
        print("DURABLE COURSE DOCS BLOCKED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("DURABLE COURSE DOCS READY")
    print(f"routes={len(REQUIRED_ANCHORS)} source-anchors={len(set(REQUIRED_ANCHORS.values()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
