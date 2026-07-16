# Course Migration Freeze Plan

本文件是十二 Phase Migration 的唯一 **Freeze authority**。它固定 publication boundary、pre-migration identity、73 個 Migration baseline paths 與 99 個 new canonical paths；後續 page-level disposition 由 `course-migration-manifest.json` 單獨管理，不得複製或改寫這兩份 allowlists。

若本文件的 offline 或 online verification 失敗，T02 及其所有 downstream tickets 都維持 blocked，並重新開啟 T01 處理 drift；不得自行改 counts 或把目前 checkout 當成新 baseline。

## Frozen publication boundary

- Production canonical host：<https://lessons-three-xi.vercel.app>
- Provider／environment：Vercel `Production`
- Observed production trigger：Vercel Git integration 將 remote `main` commits 自動部署到 `Production`；remote non-`main` commits 會建立 `Preview` deployments。
- Pre-migration commit：`3d2f3dd437be6ceb06092bd276533b0b0c84cbac`
- Production deployment：GitHub deployment `5455233611`，Vercel 回報 `success`，deployment SHA 與 remote `main` 均為上述 commit。
- Dedicated Migration branch：`codex/course-migration`，在 coherent cutover 前維持 **local-only**。不得 push，因為 remote branch 會產生可連線的 Vercel Preview，形成 incomplete catalog publication。
- Coherent cutover：只有 Issue #75 記錄 exact reviewed checkpoint 與 Maintainer authorization 後，才可將該 checkpoint 一次合併到 `main`。不得 rebuild、挑入額外變更或分批發布。

GitHub Pages 不是 production：`https://jmyhsieh.github.io/lessons/` 在 Freeze 時回傳 `404`，最近一次 `github-pages` deployment 仍停在舊 SHA `6ec0276d6484ffc9425f94a145c3f62ecb70f4e4`。不得因 repository 仍有 `pages-build-deployment` workflow 而把它當成 active production boundary。

## Evidence observed for T01

Observation time：`2026-07-16T08:26:14Z`

| Claim | Evidence |
|---|---|
| Canonical production host | Repository homepage metadata 指向 Vercel alias；alias 回傳 `HTTP 200`、`server: Vercel`。 |
| Exact production identity | [Deployment 5455233611](https://github.com/jmyhsieh/lessons/deployments/Production) 與 commit status 均記錄 SHA `3d2f3dd437be6ceb06092bd276533b0b0c84cbac`、state `success`。 |
| Public bytes match candidate | Production `index.html` SHA-256 為 `cae763f33a866da38b0ff4d8b7a06907a4715a38c6f6cd76432470d40f0a9de5`，與 frozen Git blob byte-for-byte 相同；online verifier擴大到全部 73 paths。 |
| Preview risk exists | GitHub deployments 同時存在 Vercel `Preview` records for non-production refs，因此 dedicated branch 必須 local-only。 |
| Dedicated branch is isolated | Current checkout 為 `codex/course-migration`；remote 無同名 branch，`preMigrationCommit..HEAD` 的全部 Migration commits 均無 Vercel `Preview` deployment。 |
| GitHub Pages is not production | Public Pages URL 回傳 `404`，且最後 Pages deployment SHA 不等於 frozen commit。 |

## Authority boundaries

| Concern | Single authority |
|---|---|
| Frozen publication boundary and 73／99 allowlists | 本文件 |
| Page-level dispositions, coordinates, route edges and Compatibility targets | `docs/migration/course-migration-manifest.json`（T02） |
| Source anchors, freshness, versions and gate state | `source-anchors.json`（T03 起） |
| Coherent cutover authorization and post-publication evidence | GitHub Issue #75 的 append-only comments（T62／T63） |

Cutover comments 必須位於 reviewed candidate 外，引用 exact checkpoint SHA，並依序追加 counts、deterministic validation、browser evidence、Source gate、Review evidence、Maintainer authorization 與 production verification。建立或追加這些 comments 不得改變 candidate。Repo 內不建立第二份 cutover record 或 release contract。

## Machine-readable Freeze contract

<!-- migration-freeze-json:start -->
```json
{
  "schemaVersion": 1,
  "frozenAt": "2026-07-16T08:26:14Z",
  "issues": {
    "blueprint": 12,
    "spec": 13,
    "ticket": 14
  },
  "preMigrationCommit": "3d2f3dd437be6ceb06092bd276533b0b0c84cbac",
  "production": {
    "repository": "jmyhsieh/lessons",
    "provider": "Vercel",
    "environment": "Production",
    "canonicalHost": "https://lessons-three-xi.vercel.app",
    "sourceBranch": "main",
    "trigger": "vercel-git-integration-on-remote-main",
    "deploymentId": 5455233611,
    "deploymentSha": "3d2f3dd437be6ceb06092bd276533b0b0c84cbac",
    "deploymentUrl": "https://lessons-du8hy98te-jmyhsiehs-projects.vercel.app",
    "deploymentCompletedAt": "2026-07-15T10:05:59Z",
    "indexSha256": "cae763f33a866da38b0ff4d8b7a06907a4715a38c6f6cd76432470d40f0a9de5",
    "secondaryHost": {
      "url": "https://jmyhsieh.github.io/lessons/",
      "expectedStatus": 404,
      "latestObservedDeploymentSha": "6ec0276d6484ffc9425f94a145c3f62ecb70f4e4"
    }
  },
  "migration": {
    "branch": "codex/course-migration",
    "remotePolicy": "local-only-until-cutover",
    "previewRisk": "Vercel deploys remote non-main commits as Preview",
    "cutoverTrigger": "authorized coherent merge of the exact reviewed checkpoint to main"
  },
  "cutoverEvidence": {
    "storage": "outside-reviewed-candidate",
    "trackerIssue": 75,
    "recordFormat": "append-only-comments",
    "appendOnly": true,
    "mayMutateCandidate": false,
    "requiredIdentity": "exact reviewed checkpoint SHA"
  },
  "authority": {
    "freeze": "docs/migration/course-migration-plan.md",
    "pageDisposition": "docs/migration/course-migration-manifest.json",
    "sources": "source-anchors.json",
    "cutoverRecord": "GitHub Issue #75 comments"
  },
  "baselinePaths": [
    "index.html",
    "lessons/001-0001-four-claude-surfaces.html",
    "lessons/001-0002-first-session-read-only.html",
    "lessons/001-0003-read-only-repo-tour.html",
    "lessons/001-0004-permission-plan-mode.html",
    "lessons/001-0005-first-safe-code-change.html",
    "lessons/001-0006-claude-md.html",
    "lessons/001-0007-permission-rules.html",
    "lessons/001-0008-session-commands.html",
    "lessons/001-0009-model-effort.html",
    "lessons/001-0010-cowork-hands-on.html",
    "lessons/001-0011-explore-plan-implement-commit.html",
    "lessons/001-0012-verification-context.html",
    "lessons/002-0001-hooks-basics.html",
    "lessons/002-0002-guardrail-hooks.html",
    "lessons/002-0003-skills.html",
    "lessons/002-0004-mcp.html",
    "lessons/002-0005-subagents-context.html",
    "lessons/002-0006-custom-subagent-review.html",
    "lessons/002-0007-worktrees.html",
    "lessons/002-0008-writer-reviewer-session.html",
    "lessons/002-0009-headless-one-shot.html",
    "lessons/002-0010-ci-automation-boundary.html",
    "lessons/003-0001-matt-pocock-skills-foundation.html",
    "lessons/003-0002-ask-matt.html",
    "lessons/003-0003-repo-map.html",
    "lessons/003-0004-grill-with-docs.html",
    "lessons/003-0005-prototype.html",
    "lessons/003-0006-to-spec.html",
    "lessons/003-0007-to-tickets.html",
    "lessons/003-0008-implement.html",
    "lessons/003-0009-triage.html",
    "lessons/003-0010-diagnosing-bugs.html",
    "lessons/003-0011-architecture.html",
    "lessons/003-0012-handoff.html",
    "lessons/003-0013-wayfinder-chart-map.html",
    "lessons/003-0014-wayfinder-frontier.html",
    "lessons/004-0001-choose-claude-design-surface.html",
    "lessons/004-0002-write-design-brief.html",
    "lessons/004-0003-sync-design-system.html",
    "lessons/004-0004-explore-design-directions.html",
    "lessons/004-0005-refine-and-version.html",
    "lessons/004-0006-prototype-and-validate.html",
    "lessons/004-0007-handoff-to-claude-code.html",
    "lessons/004-0008-implement-and-verify.html",
    "lessons/005-0001-choose-daily-visual-output.html",
    "lessons/005-0002-build-source-pack.html",
    "lessons/005-0003-storyboard-presentation.html",
    "lessons/005-0004-create-deck-in-claude-design.html",
    "lessons/005-0005-refine-deck-for-audience.html",
    "lessons/005-0006-verify-claims-and-accessibility.html",
    "lessons/005-0007-export-and-rehearse.html",
    "lessons/005-0008-repurpose-one-pager-social.html",
    "lessons/005-0009-build-versioned-deck-with-open-slide.html",
    "reference/ai-developer-workflow-case-library.html",
    "reference/ai-founder-workflow-case-library.html",
    "reference/ai-functional-workflow-case-library.html",
    "reference/ai-ops-revops-workflow-case-library.html",
    "reference/ai-platform-governance-workflow-case-library.html",
    "reference/ai-research-data-workflow-case-library.html",
    "reference/ai-workflow-case-library.html",
    "reference/ai-workflow-skill-composer.html",
    "reference/claude-code-command-surface.html",
    "reference/claude-code-model-effort.html",
    "reference/claude-design-daily-output-picker.html",
    "reference/claude-design-presentation-workflow.html",
    "reference/claude-design-to-code-workflow.html",
    "reference/claude-product-picker.html",
    "reference/course-glossary.html",
    "reference/mattpocock-skills-phase3-reference.html",
    "reference/open-slide-agent-deck-workflow.html",
    "reference/wayfinder-map-workflow.html",
    "toc.html"
  ],
  "newCanonicalPaths": [
    "lessons/001-0002-define-route-readiness.html",
    "lessons/001-0003-complete-cowork-starter.html",
    "lessons/001-0004-prepare-claude-code-session.html",
    "lessons/001-0005-map-repo-read-only.html",
    "lessons/001-0006-plan-readiness-fixture.html",
    "lessons/001-0007-prove-code-readiness.html",
    "lessons/002-0001-choose-toolbox-lesson.html",
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
    "lessons/003-0001-select-knowledge-deliverable.html",
    "lessons/003-0002-preserve-sources-and-provenance.html",
    "lessons/003-0003-build-source-to-claim-outline.html",
    "lessons/003-0004-produce-reviewable-knowledge-slice.html",
    "lessons/003-0005-verify-knowledge-deliverable.html",
    "lessons/003-0006-complete-knowledge-delivery-closeout.html",
    "lessons/003-0007-produce-first-llm-wiki-slice.html",
    "lessons/003-0008-normalize-local-source.html",
    "lessons/003-0009-query-local-source-corpus.html",
    "lessons/003-0010-query-local-tabular-data.html",
    "lessons/004-0006-check-prototype-assumptions.html",
    "lessons/004-0007-assemble-design-handoff-bundle.html",
    "lessons/005-0001-choose-presentation-route.html",
    "lessons/005-0010-build-diagram-as-code-with-mermaid-cli.html",
    "lessons/006-0001-choose-engineering-route.html",
    "lessons/006-0002-map-repository.html",
    "lessons/006-0003-align-engineering-request.html",
    "lessons/006-0004-prototype-technical-question.html",
    "lessons/006-0005-write-delivery-spec.html",
    "lessons/006-0006-slice-spec-into-tickets.html",
    "lessons/006-0007-implement-and-create-review-checkpoint.html",
    "lessons/006-0008-review-final-candidate.html",
    "lessons/006-0009-complete-engineering-closeout.html",
    "lessons/006-0010-triage-external-report.html",
    "lessons/006-0011-diagnose-hard-bug.html",
    "lessons/006-0012-find-architecture-seam.html",
    "lessons/006-0013-chart-wayfinder-map.html",
    "lessons/006-0014-resolve-wayfinder-frontier.html",
    "lessons/007-0001-scope-browser-claim.html",
    "lessons/007-0002-choose-browser-surface.html",
    "lessons/007-0003-record-observable-baseline.html",
    "lessons/007-0004-promote-claim-to-playwright-test.html",
    "lessons/007-0005-rerun-in-declared-environment.html",
    "lessons/007-0006-diagnose-with-trace.html",
    "lessons/007-0007-complete-browser-evidence-addendum.html",
    "lessons/008-0001-define-deterministic-check.html",
    "lessons/008-0002-choose-agent-execution-surface.html",
    "lessons/008-0003-bound-write-authority.html",
    "lessons/008-0004-run-recoverable-workflow.html",
    "lessons/008-0005-prove-workflow-completion.html",
    "lessons/008-0006-exercise-failure-and-recovery.html",
    "lessons/008-0007-complete-operating-workflow-closeout.html",
    "lessons/008-0008-run-recoverable-llm-wiki-maintenance.html",
    "lessons/009-0001-select-proven-workflow.html",
    "lessons/009-0002-extract-workflow-contract.html",
    "lessons/009-0003-choose-workflow-package.html",
    "lessons/009-0004-package-as-playbook-or-template.html",
    "lessons/009-0005-package-as-claude-md.html",
    "lessons/009-0006-package-as-skill.html",
    "lessons/009-0007-package-as-command-or-process.html",
    "lessons/009-0008-complete-standardization-closeout.html",
    "lessons/009-0009-extract-llm-wiki-maintenance-contract.html",
    "lessons/010-0001-set-workflow-evaluation-claim.html",
    "lessons/010-0002-define-comparison-frame.html",
    "lessons/010-0003-build-success-case-set.html",
    "lessons/010-0004-build-failure-case-set.html",
    "lessons/010-0005-record-comparative-evidence.html",
    "lessons/010-0006-dispose-evidence-conflicts.html",
    "lessons/010-0007-complete-workflow-evidence-dossier.html",
    "lessons/010-0008-add-local-usage-cost-evidence.html",
    "lessons/011-0001-bound-team-scenario.html",
    "lessons/011-0002-assign-rollout-roles.html",
    "lessons/011-0003-bound-pilot-access-and-data.html",
    "lessons/011-0004-prepare-rollout-readiness.html",
    "lessons/011-0005-design-review-and-escalation.html",
    "lessons/011-0006-design-feedback-and-rollback.html",
    "lessons/011-0007-complete-scenario-rollout-plan.html",
    "lessons/012-0001-charter-governance-scope.html",
    "lessons/012-0002-design-change-control.html",
    "lessons/012-0003-define-data-lifecycle-controls.html",
    "lessons/012-0004-build-risk-and-cost-register.html",
    "lessons/012-0005-run-incident-tabletop.html",
    "lessons/012-0006-run-change-retirement-tabletop.html",
    "lessons/012-0007-complete-governance-lifecycle-policy.html",
    "reference/agent-operations-safety.html",
    "reference/browser-evidence-selector.html",
    "reference/engineering-delivery-skills-reference.html",
    "reference/knowledge-delivery-evidence-checklist.html",
    "reference/llm-wiki-capstone-thread.html",
    "reference/repo-review-contract.html",
    "reference/workflow-maturity-workbook.html",
    "reference/workflow-package-selector.html"
  ]
}
```
<!-- migration-freeze-json:end -->

## Verification

Offline positive slice：

```sh
python3 scripts/verify-migration-freeze.py
```

Representative fail-closed fixtures：

```sh
python3 scripts/verify-migration-freeze.py --self-test
```

Online publication evidence（需要 GitHub authentication 與 network）：

```sh
python3 scripts/verify-migration-freeze.py --online
```

Online mode 會重新確認 current checkout、remote Migration branch absence、完整 Migration commit history 無 Vercel Preview、repository homepage、remote `main`、latest Vercel Production deployment、deployment status、secondary GitHub Pages boundary，並把全部 73 production URLs 與 frozen Git blobs 做 byte-level comparison。

## T01 stop line

本票不建立 page-level manifest、Source registry、full release validator、lessons、references、navigation 或 cutover evidence。本票完成只代表 Freeze contract 已可重跑驗證；不代表任何 Phase、route 或 Migration release 完成。
