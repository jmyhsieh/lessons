# AI Workflow Composition Resources

這份檔案是給自學者與教材維護者使用的 research guide，不是 publication-gate database。`source-anchors.json` 才是 Source-anchor metadata、版本、verified environment、status 與 recertification evidence 的唯一 authority；需要更新產品或工具敘述時，先找到 stable anchor ID，再依 registry 的 eligible sources 與 verification recipe 重新查證。

## Route contract index

| Route ID | Source anchor ID | 研究用途 |
|---|---|---|
| `common-foundation` | `course-orient-readiness-contract` | 核對 route choice、readiness evidence 與 readiness fixture 邊界。 |
| `cowork-starter` | `claude-cowork-starter-surface` | 核對低風險 Cowork file task 的 surface 與檔案邊界。 |
| `code-readiness` | `claude-code-cli-session-start` | 核對安全 session、read-only reconnaissance 與 controlled change 的執行前提。 |
| `toolbox` | `course-equip-toolbox-contract` | 核對 just-in-time selection、smoke test、stop 與 return contract。 |
| `knowledge-delivery` | `course-knowledge-delivery-contract` | 核對 source、provenance、verification、judgment 與 feedback closeout。 |
| `design-delivery` | `course-design-delivery-contract` | 核對 bounded brief、prototype evidence 與 reviewable handoff boundary。 |
| `presentation-delivery` | `course-presentation-delivery-contract` | 核對 source pack、claim、accessibility、export 與 rehearsal evidence。 |
| `engineering-delivery` | `course-engineering-delivery-contract` | 核對 repo delivery、deterministic checks、review checkpoint 與 closeout。 |
| `browser-evidence` | `browser-evidence-addendum-contract` | 核對 observable claim、durable test、declared environment 與 addendum。 |
| `agent-operations` | `agent-operations-safety-contract` | 核對 authority、recoverability、completion proof 與 failure recovery。 |
| `workflow-standardization` | `workflow-standardization-contract` | 核對 proven workflow、package selection、version、owner 與 rerun evidence。 |
| `workflow-evaluation` | `workflow-evaluation-contract` | 核對 explicit claim、baseline、success/failure cases、limitations 與 disposition。 |
| `scenario-rollout` | `scenario-rollout-contract` | 核對 bounded self-study scenario、roles、access、feedback 與 rollback plan。 |
| `governance-lifecycle` | `governance-lifecycle-contract` | 核對 ownership、change control、data lifecycle、risk 與 tabletop evidence。 |

Route 的 entry、stop 與 edge 不在這裡複製；請查 `docs/migration/course-migration-manifest.json`。Route promise 的詳細 claim scope、source URL 與 due date 請查 registry 中同名 anchor。

## High-trust source entry points

以下連結只提供研究入口；任何教材 claim 仍須回到對應 Source anchor 留下 source check 與 profile-appropriate evidence。

- [Claude Code overview — Anthropic](https://code.claude.com/docs/en/overview)
  用於 Claude Code surface、repo workflow 與 execution boundary 的第一手查證。
- [Claude Code permissions — Anthropic](https://code.claude.com/docs/en/permissions)
  用於 permission rule、scope 與 application-enforced boundary 的第一手查證。
- [Claude Code CLI reference — Anthropic](https://code.claude.com/docs/en/cli-reference)
  用於 command、flag 與 non-interactive execution claim；不得用記憶補齊未查證選項。
- [Claude Design — Anthropic](https://claude.com/product/design)
  用於 Design surface 的正式定位；availability、操作與輸出能力須依 registry 指定來源重新查證。
- [Claude Help Center](https://support.claude.com/)
  用於 Cowork、Design 與其他 hosted surface 的當前操作與 availability 說明。
- [Playwright documentation](https://playwright.dev/docs/intro)
  用於 browser test、trace 與 declared environment 的第一手查證。
- [Git documentation](https://git-scm.com/docs)
  用於 repository status、diff、commit 與 worktree 行為的第一手查證。
- [W3C Web Accessibility Initiative](https://www.w3.org/WAI/)
  用於 accessibility principles 與 target-format verification 的規範來源。

## Source-handling rules

- 先以 stable anchor ID 確定 claim scope，再查 source；不要從一篇新聞或社群貼文反推 route promise。
- Product availability、CLI flags、model aliases、version、export format 與 UI path 都屬 drift-prone claims，必須遵守 registry 的 Drift class、due date 與 change triggers。
- Executable recipe 要重跑 declared steps 並保存 resolved version、environment 與 output；只檢查 URL 可開啟不算 recertification。
- Surface procedure 要記錄 exact surface path、availability assumptions 與 dated observable evidence；不要捏造等價 CLI。
- Principle-only anchor 只承載 durable decision rule，不替未分類的 executable 或 product claim 提供豁免。
- First-party sources 衝突時，只教可支持的交集並保留 conflict record；必要的 judgment-bearing disposition 需 Maintainer sign-off。
- 社群內容可補充使用摩擦與例外線索，但不可成為 factual source of truth 或 universal promise。

## Known evidence gaps

- 仍缺台灣工作情境下，可公開重現並同時保留 source、constraints、verification output、learner judgment 與 final artifact 的完整案例。
- 仍缺跨 route 的長期 retrieval、spacing 與 interleaving 自學紀錄，可證明 Return notebook 在中斷後仍能正確恢復 active mission。
- 若自學者不想參與社群，請記在 `NOTES.md`，後續不要把社群互動當成必要 evidence。
