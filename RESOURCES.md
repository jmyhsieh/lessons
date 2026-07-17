# AI Workflow Composition Resources

這份檔案只保留課程可依賴的高信任來源。新聞與職能案例不作為 factual source of truth；需要案例時，請回查其第一手來源。

## Knowledge

- [Guide: Claude Code overview — Anthropic](https://code.claude.com/docs/en/overview)
  Claude Code 的工作環境、支援表面與核心能力。Use for: Phase 1 的產品與 repo 工作邊界。
- [Guide: Claude Code Desktop — Anthropic](https://code.claude.com/docs/en/desktop)
  Desktop Code、Cowork／Dispatch、permission modes、worktrees、diff 與 session 管理。Use for: Phase 1 桌面 App 操作與產品表面。
- [Guide: Get started with Claude Cowork — Anthropic](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork)
  Cowork remote／local sessions、web／desktop／mobile 可用性與本機檔案邊界。Use for: Phase 1 Cowork surface 判斷與安全提醒。
- [Product: Claude Design — Anthropic](https://claude.com/product/design)
  Claude Design 的正式產品定位、視覺產物、export 與 Claude Code handoff。Use for: Phase 1 產品判斷、Phase 4 邊界與 Phase 5 格式選擇。
- [Guide: Get started with Claude Design — Anthropic](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
  Project、context、prompt、chat／comment／canvas、版本、export、<code>/design-sync</code> 與 Claude Design MCP；也列出 beta 可用性與限制。Use for: Phase 4 主線與 Phase 5 日常視覺工作流。
- [Tutorial: Using Claude Design for presentations and slide decks — Anthropic](https://claude.com/resources/tutorials/using-claude-design-for-presentations-and-slide-decks)
  受眾、訊息、deck 產生、單頁修改、圖表、分享與 HTML／PPTX／PDF export。Use for: Phase 5 簡報主線。
- [Guide: Introduction — open-slide](https://open-slide.dev/docs)
  React-first agent slide framework、固定 1920×1080 canvas、present mode 與 HTML／PDF export 的正式定位。Use for: Phase 5 第 09 課的 surface 邊界。
- [Guide: Getting started — open-slide](https://open-slide.dev/docs/getting-started)
  Workspace scaffold、dev server、agent authoring、inspector comments、static build 與 deploy 流程。Use for: Phase 5 第 09 課實作主線。
- [Guide: Agent skills overview — open-slide](https://open-slide.dev/docs/skills/overview)
  Workspace-local <code>AGENTS.md</code>、<code>create-slide</code>、<code>slide-authoring</code>、<code>apply-comments</code> 等 agent contract。Use for: Phase 5 第 09 課的 repo 安全邊界與 feedback loop。
- [Reference: Export — open-slide](https://open-slide.dev/docs/core-feature/export)
  <code>dist/</code> static HTML build、browser print PDF 與公開分享時可關閉的 UI surface。Use for: Phase 5 第 09 課 export 選擇與停止線。
- [Guide: Set up your design system in Claude Design — Anthropic](https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design)
  從 codebase、prototype、deck 與 brand assets 建立並驗證 design system。Use for: Phase 4 第 03 課與 Phase 5 品牌校正。
- [Announcement: Introducing Claude Design by Anthropic Labs — Anthropic](https://www.anthropic.com/news/claude-design-anthropic-labs)
  產品發布時的用途、互動方式、export 與 Claude Code handoff 邊界。Use for: Phase 4 產品定位；會變動的操作仍以 Help Center 為準。
- [Update: Claude Design stays on-brand for daily work — Anthropic](https://claude.com/blog/claude-design-stays-on-brand-for-daily-work)
  Design system sync、日常視覺工作與 Claude Code 整合的官方更新。Use for: Phase 4 第 03、07 課與 Phase 5 品牌精修。
- [Guide: Making Events Accessible — W3C WAI](https://www.w3.org/WAI/teach-advocate/accessible-presentations/)
  會議、訓練與簡報的可及性檢查，包括投影片文字量、口述畫面資訊與替代格式。Use for: Phase 5 第 06、07 課。
- [Tutorial: Images and complex graphics — W3C WAI](https://www.w3.org/WAI/tutorials/images/)
  圖片、圖表與複雜圖形的文字等價資訊。Use for: Phase 5 第 06 課。
- [Repository: frontend-design plugin — Anthropic](https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design)
  Claude Code 內產出 production-grade frontend code 的官方 plugin／skill；不是 Claude Design 產品。Use for: Phase 4 第 01 課的 surface 邊界。
- [Announcement: Artifacts in Claude Code — Anthropic](https://claude.com/blog/artifacts-in-claude-code)
  把 Code session context 轉成可分享 live page 的功能；不是 Claude Design 專案。Use for: Phase 4 第 01 課的 surface 邊界。
- [Guide: Best practices for Claude Code — Anthropic](https://code.claude.com/docs/en/best-practices)
  Explore-plan-code、verification-first、small scope、review 與 parallel work。Use for: Phase 1 安全流程與 Phase 4 repo 實作。
- [Reference: Permission modes — Anthropic](https://code.claude.com/docs/en/permission-modes)
  各 permission mode 的能力與 plan mode 真正保證。Use for: Phase 1 權限教學。
- [Reference: Configure permissions — Anthropic](https://code.claude.com/docs/en/permissions)
  allow/deny rules、protected paths 與設定範圍。Use for: permission rules 與安全邊界。
- [Guide: Project memory — Anthropic](https://code.claude.com/docs/en/memory)
  CLAUDE.md、CLAUDE.local.md、rules、auto memory 與載入順序。Use for: repo-level instructions 與 contract placement。
- [Guide: Extend Claude Code — Anthropic](https://code.claude.com/docs/en/features-overview)
  CLAUDE.md、Skills、Subagents、MCP、hooks、plugins 與 agent teams 的 selector。Use for: Phase 2 工具選擇。
- [Reference: Skills — Anthropic](https://code.claude.com/docs/en/skills)
  SKILL.md、invocation controls、context loading 與 supporting files。Use for: Phase 2 Skills。
- [Reference: Hooks — Anthropic](https://code.claude.com/docs/en/hooks)
  Hook events、event-specific blocking、exit codes 與 structured JSON。Use for: Phase 2 hooks 與 guardrails。
- [Guide: Subagents — Anthropic](https://code.claude.com/docs/en/sub-agents)
  Context isolation、custom agents、permissions、skills 與 hooks。Use for: Phase 2 reviewer design。
- [Guide: Worktrees — Anthropic](https://code.claude.com/docs/en/worktrees)
  CLI/Desktop worktree isolation、<code>.worktreeinclude</code> 與 cleanup。Use for: parallel sessions。
- [Guide: Programmatic usage — Anthropic](https://code.claude.com/docs/en/headless)
  <code>claude -p</code>、<code>--bare</code>、structured output 與 scripting。Use for: Phase 2 headless 與 CI。
- [Reference: Claude Code CLI — Anthropic](https://code.claude.com/docs/en/cli-usage)
  <code>--tools</code>、<code>--allowedTools</code>、<code>--permission-mode</code>、settings 與 MCP flags 的精確語義。Use for: Phase 2 one-shot／CI。
- [Reference: git status and git diff — Git](https://git-scm.com/docs/git-status)
  Tracked、untracked 與 machine-readable porcelain status 的邊界。Use for: repo 變更確認；tracked patch 比較另見 <a href="https://git-scm.com/docs/git-diff">git diff</a>。
- [Guide: Use Claude Code with Chrome — Anthropic](https://code.claude.com/docs/en/chrome)
  Browser interaction、DOM／console inspection、design verification 與 web app testing。Use for: Phase 4 第 08 課；仍需依 repo 的正式測試補足 evidence。
- [Guide: Model configuration — Anthropic](https://code.claude.com/docs/en/model-config)
  Current aliases、model-specific effort levels、<code>opusplan</code> 與 <code>ultrathink</code>。Use for: model/effort decisions。
- [Repository: mattpocock/skills](https://github.com/mattpocock/skills)
  Phase 3 使用的 upstream skills 與四大失敗模式。Use for: skill inventory；具體行為以各 SKILL.md 為準。
- [README snapshot: mattpocock/skills installation](https://github.com/mattpocock/skills/blob/66898f60e8c744e269f8ce06c2b2b99ce7660d5f/README.md)
  Claude Code native plugin 與 editable project copy 的官方安裝路徑。Use for: Phase 3 第 01 課；plugin 版本與命令變動時重查 upstream。
- [Skill: setup-matt-pocock-skills](https://github.com/mattpocock/skills/blob/66898f60e8c744e269f8ce06c2b2b99ce7660d5f/skills/engineering/setup-matt-pocock-skills/SKILL.md)
  Issue tracker、triage labels 與 domain docs 的實際設定流程。Use for: Phase 3 地基；README 摘要漂移時以本檔為準。
- [Skill: domain-modeling](https://github.com/mattpocock/skills/blob/66898f60e8c744e269f8ce06c2b2b99ce7660d5f/skills/engineering/domain-modeling/SKILL.md)
  純 glossary、lazy file creation 與三條件 ADR gate。Use for: Phase 3 的 CONTEXT.md／ADR 行為。
- [Skill: code-review](https://github.com/mattpocock/skills/blob/66898f60e8c744e269f8ce06c2b2b99ce7660d5f/skills/engineering/code-review/SKILL.md)
  固定點三點 diff、Standards／Spec 平行雙軸與分開報告。Use for: Phase 3 implement closeout 與獨立 review。
- [Skill: improve-codebase-architecture](https://github.com/mattpocock/skills/blob/66898f60e8c744e269f8ce06c2b2b99ce7660d5f/skills/engineering/improve-codebase-architecture/SKILL.md)
  先按使用者方向或近期 hot spots 限定範圍，再掃描 deepening opportunities。Use for: Phase 3 architecture 支線。
- [Skill: wayfinder](https://github.com/mattpocock/skills/blob/66898f60e8c744e269f8ce06c2b2b99ce7660d5f/skills/engineering/wayfinder/SKILL.md)
  巨大模糊 effort 的 shared map、decision tickets、fog 與 frontier；research ticket 是單 ticket session 規則的例外，會由 subagent 平行處理，並把發現留在 throwaway <code>research/&lt;name&gt;</code> branch，由 ticket 指回 context。Use for: Phase 3 選修 wayfinder 分支。
- [Paper: Physics Is All You Need?](https://arxiv.org/abs/2605.30353)
  Domain expert supervision 與 oracle tests 的案例。Use for: 說明 deterministic feedback 有效處與人類知識邊界。
- [Paper: AI Coding Agents Can Reproduce Social Science Findings](https://arxiv.org/abs/2606.11447)
  Agent reproduction tasks 與 prompt framing 的實證。Use for: 研究／資料工作流的驗證設計。

## Wisdom (Communities)

- [Anthropic Discord](https://www.anthropic.com/discord)
  官方使用者社群。Use for: 對照實際 Claude Code／Cowork 使用摩擦與版本差異。
- [mattpocock/skills Discussions](https://github.com/mattpocock/skills/discussions)
  Upstream 使用者與維護者討論。Use for: 驗證 skill routing、tracker 與 workflow 的真實用法。

## Gaps

- 仍缺台灣團隊公開、可重現且包含 repo constraints、驗證輸出與最終 PR 的第一手案例。
- Phase 4 仍缺可公開引用、同時保留 design intent、browser evidence 與 production diff 的完整 design-to-code 案例。
- Phase 5 仍缺台灣工作情境下、同時保留來源查核與實際簡報回饋的公開案例。
- open-slide 仍缺可公開引用、同時包含 source traceability、accessibility evidence 與真實彩排紀錄的完整案例。
- 若使用者不想參與社群，需記錄在 NOTES.md，避免後續重複推薦。
