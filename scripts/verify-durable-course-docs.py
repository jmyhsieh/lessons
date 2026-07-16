#!/usr/bin/env python3
"""Verify that durable course docs follow the canonical route/source contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
DOC_PATHS = ("MISSION.md", "RESOURCES.md", "NOTES.md")
MANIFEST_PATH = "docs/migration/course-migration-manifest.json"
REGISTRY_PATH = "source-anchors.json"

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
        if verify(root):
            print("SELF TEST FAILED: valid fixture was rejected")
            return 1
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
