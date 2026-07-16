# Mission: 與 Claude 建立可驗證、可續作的任務工作流

## Why

協助自學者從一個真實任務出發，選擇合適的 Claude surface 與 Task route，產出可檢查的 artifact、learner judgment、feedback 與 verification evidence。課程以任務成果與安全邊界為主，不把 Phase 編號、工具清單或一次生成結果當成能力證明。

## Success looks like

- 能先完成 `common-foundation`，留下 route choice 與 readiness evidence，再進入符合任務的 route。
- 能在 route 的 entry、readiness、stop、exit evidence 與 legal stop 之間工作；缺少能力時只做 targeted remediation，完成後回到原 route。
- 能區分 `Lesson practiced`、`Route artifact produced`、learner judgment、feedback 與 review evidence，不把 checklist 或模型自評當成完成權威。
- 能保留可用的 Evidence carryover，並以 Return notebook 記錄 current route anchor、next tangible win 與 legal stop。
- 能在 repo diff、browser claim、agent execution、workflow package、evaluation、rollout 或 governance 工作中，產出各 route 承諾的可重跑證據。

## Canonical route contract

`docs/migration/course-migration-manifest.json` 是 route graph 的唯一 authority。以下只列 durable route identity 與對應的 Source anchor；entry、stop、edge、continuation 與 remediation 都以 manifest 當下內容為準。

| Route ID | Durable promise anchor |
|---|---|
| `common-foundation` | `course-orient-readiness-contract` |
| `cowork-starter` | `claude-cowork-starter-surface` |
| `code-readiness` | `claude-code-cli-session-start` |
| `toolbox` | `course-equip-toolbox-contract` |
| `knowledge-delivery` | `course-knowledge-delivery-contract` |
| `design-delivery` | `course-design-delivery-contract` |
| `presentation-delivery` | `course-presentation-delivery-contract` |
| `engineering-delivery` | `course-engineering-delivery-contract` |
| `browser-evidence` | `browser-evidence-addendum-contract` |
| `agent-operations` | `agent-operations-safety-contract` |
| `workflow-standardization` | `workflow-standardization-contract` |
| `workflow-evaluation` | `workflow-evaluation-contract` |
| `scenario-rollout` | `scenario-rollout-contract` |
| `governance-lifecycle` | `governance-lifecycle-contract` |

`source-anchors.json` 是上述 claim scope、eligible sources、drift status、verified environment 與 recertification evidence 的唯一 Source registry。這份 Mission 不複製產品 availability、命令、版本、export format 或操作位置。

## Constraints

- 課程使用繁體中文與台灣用語；命令、檔名、API 名稱與 canonical identity 保留原文。
- 每課要短、可實作，並產生一個能帶回 active mission 的 tangible win。
- 本課程是純自學；learner judgment 不由模型取代，也不宣稱外部認證、組織採用、production authorization、legal approval 或 compliance approval。
- 真實來源、provenance、permission、side effect、review 與 stop condition 必須跟著 route artifact；生成內容不能取代事實查核或授權確認。
- Phase 只是穩定 catalog grouping，不是所有人都必須完成的線性等級。Task route 才定義 progression、readiness 與 exit evidence。
- repo deliverable 一旦跨過 Repo delivery boundary，就必須遵守 Code readiness 與 Review contract。

## Out of scope

- 抽象 AI 趨勢介紹或以功能數量為主的 product tour。
- 把勾選、模型自評、一次 demo、prototype、browser trace 或 benchmark 分數單獨當成 route completion。
- 把 self-study artifact 說成 production readiness、真實採用、法務、合規或組織授權。
- 在 durable guidance 內重述會漂移的產品、版本、命令或 availability claim；這些內容必須由 stable Source anchor 管理。
