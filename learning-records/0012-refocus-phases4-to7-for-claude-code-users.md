# Phase 4–7 改為 Claude Code 使用者路線

Status: superseded by LR-0017

使用者要求重新檢視 Phase 4–7 是否真的是「給 Claude Code 使用者」的學習路徑。稽核結果是 Phase 6 已符合：學員把 LLM Wiki idea file、來源與問題交給 Claude Code，進階再審查 schema、ingest、query、lint 與低風險自動化。Phase 4、5 與 7 則需要修正主介面與人工關卡。

Phase 4、5 改為 Claude Code 作為主要工作介面，依 Anthropic 官方文件以 user-scoped Claude Design MCP 連線。Claude Code 整理 brief、來源、storyboard、design intent 與修改範圍，再透過 Design MCP 產生或修改成果；學員負責核准 prompt、選版、真人試用、來源查核、diff review 與實際輸出驗證。模型不能假裝完成人類回饋或 accessibility evidence。

Phase 7 改為 Claude Code × open-slide。學員不必先背 React 或 open-slide API；Claude Code 先讀 scaffold 產生的 <code>CLAUDE.md</code> 與 workspace skills，再使用 <code>/create-slide</code>、<code>/create-theme</code>、<code>/apply-comments</code>。學員核對 target 與命令、審查 diff、親自在 browser 檢查，部署則保留給有權限的 owner。

Phase 4–8 後續共同採用同一角色定義：Claude Code 是 home surface，專用產品、idea file、MCP 與 workspace skills 是被 Claude Code 使用的能力；課程主要練習 prompt、授權、審查與 evidence，而不是手動背完另一套工具。
