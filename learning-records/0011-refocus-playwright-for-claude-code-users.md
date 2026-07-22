# Playwright 改為 Claude Code 使用者路線

Status: superseded by LR-0017

使用者指出 Phase 8 應該教「給 Claude Code 使用者的 Playwright」，而不是要求學員先手動學完整 Playwright API。課程仍固定為入門 01–04、進階 05–09，但重心改為寫清楚 prompt、觀看真實 browser、審查 spec／diff／output，以及判斷證據邊界。

入門先區分 Playwright MCP live check 與 committed Playwright Test，以 local scope 連接 MCP，讓 Claude Code 走一條真實 browser path，再把同一路徑做成一個有 fail → pass evidence 的持久 test。進階才執行 <code>npx playwright init-agents --loop=claude</code>，依 planner → approved spec → generator → reviewed test → healer 的順序前進，最後把已審查 tests 接到最小 CI gate。

MCP live check 不等於持久 test；agent 顯示完成或 healer 變綠也不等於需求正確。Project-scoped MCP 設定、generated tests、healer patch、CI diff 與可能含敏感資料的 reports／traces 都必須經人工核對。
