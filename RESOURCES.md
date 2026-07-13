# AI Workflow Composition Resources

這份檔案只保留課程可依賴的高信任來源。新聞與職能案例不作為 factual source of truth；需要案例時，從 [職能工作流案例總覽](reference/ai-functional-workflow-case-library.html) 進入，並回查其第一手來源。

## Knowledge

- [Guide: Claude Code overview — Anthropic](https://code.claude.com/docs/en/overview)
  Claude Code 的工作環境、支援表面與核心能力。Use for: Phase 1 的產品與 repo 工作邊界。
- [Guide: Claude Code Desktop — Anthropic](https://code.claude.com/docs/en/desktop)
  Desktop Code、Cowork／Dispatch、permission modes、worktrees、diff 與 session 管理。Use for: Phase 1 桌面 App 操作與產品表面。
- [Guide: Best practices for Claude Code — Anthropic](https://code.claude.com/docs/en/best-practices)
  Explore-plan-code、verification-first、small scope、review 與 parallel work。Use for: Phase 1 安全流程與 Phase 4 rehearsal。
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
  Hook events、event-specific blocking、exit codes 與 structured JSON。Use for: hooks、guardrails 與 Phase 4 promotion。
- [Guide: Subagents — Anthropic](https://code.claude.com/docs/en/sub-agents)
  Context isolation、custom agents、permissions、skills 與 hooks。Use for: Phase 2 reviewer design。
- [Guide: Worktrees — Anthropic](https://code.claude.com/docs/en/worktrees)
  CLI/Desktop worktree isolation、<code>.worktreeinclude</code> 與 cleanup。Use for: parallel sessions。
- [Guide: Programmatic usage — Anthropic](https://code.claude.com/docs/en/headless)
  <code>claude -p</code>、<code>--bare</code>、structured output 與 scripting。Use for: headless、CI 與 minimal runner。
- [Guide: Model configuration — Anthropic](https://code.claude.com/docs/en/model-config)
  Current aliases、model-specific effort levels、<code>opusplan</code> 與 <code>ultrathink</code>。Use for: model/effort decisions。
- [Guide: Claude Agent SDK — Anthropic](https://code.claude.com/docs/en/agent-sdk/overview)
  Programmatic agents、tools、permissions、hooks、sessions 與 deployment boundary。Use for: Phase 4 Labs。
- [Guide: Agent observability — Anthropic](https://code.claude.com/docs/en/agent-sdk/observability)
  Traces、metrics、events、token/cost 與 failure locations。Use for: harness evidence 與 telemetry boundaries。
- [Guide: Session storage — Anthropic](https://code.claude.com/docs/en/agent-sdk/session-storage)
  Resumable session storage 與 transcript persistence。Use for: 區分 session store、run history 與 evidence。
- [Guide: Cost tracking — Anthropic](https://code.claude.com/docs/en/agent-sdk/cost-tracking)
  SDK cost estimates 的範圍與限制。Use for: runner metadata；不得作正式財務決策。
- [Repository: mattpocock/skills](https://github.com/mattpocock/skills)
  Phase 3 使用的 upstream skills 與四大失敗模式。Use for: skill inventory；具體行為以各 SKILL.md 為準。
- [Skill: setup-matt-pocock-skills](https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills/SKILL.md)
  Issue tracker、triage labels 與 domain docs 的實際設定流程。Use for: Phase 3 地基；README 摘要漂移時以本檔為準。
- [Skill: wayfinder](https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md)
  巨大模糊 effort 的 shared map、decision tickets、fog、frontier 與單 ticket session 流程。Use for: Phase 3 選修 wayfinder 分支。
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
- Phase 4 仍缺可公開引用、與課程 contract 完全對齊的 starter runner repository。
- 若使用者不想參與社群，需記錄在 NOTES.md，避免後續重複推薦。
