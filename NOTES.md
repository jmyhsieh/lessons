# Teaching Notes

- 使用者偏好 Phase 5 聚焦 Claude Design 的簡報等日常應用；入門主線固定為三份資料、三頁簡報、一次彩排與一頁摘要。
- open-slide 已從 Phase 5 選修抽成獨立 Phase 7；Phase 5 只保留 Claude Design 簡報與可信交付，從結尾連到 Phase 7 選路。
- 課堂 checklist 只表示步驟已操作；完成判定還要看 artifact、判斷說明與回饋證據，不能把勾選狀態當成 mastery。
- 本 repo 依 `AGENTS.md` 維持 standalone HTML 與 embedded CSS；新增頁面要比照相鄰教材，視覺一致性用全站 audit 驗證，不另引入 shared stylesheet。
- 使用者明確回饋原 Phase 6 太難，並要求連同 Phase 4、5 一起檢查。Phase 4–8 一律採 beginner-first：每課一個小動作、先做出可見成果，再在最後列出進階術語；不要把完整 workflow governance 當作入門。
- 使用者進一步確認 Karpathy 的 raw idea file 本來就是要直接交給 Claude Code，因此 Phase 6 入門固定為前三課：agent 建立最小版本、加入第一份來源、問第一個能回查來源的問題。
- Phase 6 的 schema、ingest、query、lint 與自動化放在 04–08 進階路線；不得改寫成前三課的必要前置。自動化先選 deterministic、低破壞、可觀察成功與失敗的檢查，內容裁決與大批寫入保留 review。
- Phase 4 在既有入門 01–08 後加入進階 09–13：只在小畫面要進產品時處理 design system 校正、state／responsive matrix、accessibility、implementation-ready handoff 與 production closeout。
- Phase 5 在既有入門 01–08 後加入進階 09–12：claim ledger、deck system、交付檔稽核與受控彩排是對外交付主線。
- Phase 7 固定為入門 01–04、進階 05–09。入門只做選路、隔離 workspace、三頁切片與 build 後實際開啟；進階才教 Claude Code workspace contract、可重用元件、來源與 accessibility、comment feedback loop，以及有授權與 rollback 的部署準備。
- Phase 8 固定為給 Claude Code 使用者的 Playwright 教學，入門 01–04、進階 05–09。入門先區分 MCP live check 與 durable test，以 local scope 連接 Playwright MCP、觀看一條真實 browser path，再審查 Claude Code 產生的第一個 test 與 fail → pass evidence；進階才初始化 Test Agents，依序核准 planner spec、generator test、healer patch 與最小 CI diff。不得把 agent 綠燈、自動化所有 UI、完整跨瀏覽器矩陣或 CI 當成入門門檻。
- 使用者要求重新檢視 Phase 4–7 是否真的是「Claude Code 使用者」路線。Phase 6 已符合；Phase 4、5 原本前半段仍像直接操作 Claude Design，改成 Claude Code 作為主要介面，透過官方 Claude Design MCP 產生與修改設計，真人負責授權、選版、試用、來源查核與實際輸出驗證。
- Phase 7 不再用泛稱 agent 當學習者。open-slide scaffold 產生的 <code>CLAUDE.md</code> 與 workspace skills 是 Claude Code 的工作契約；課程改為讓 Claude Code 讀 contract、使用 <code>/create-slide</code>、<code>/create-theme</code>、<code>/apply-comments</code>，學員審查命令、diff、browser output 與部署邊界。
