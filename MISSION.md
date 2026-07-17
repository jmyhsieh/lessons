# Mission: 與 Claude 建立從想法到可驗證交付的工作流

## Why
學會判斷 Claude、Cowork、Claude Design、Claude Code 與 skills 各自適合的工作流，並能把模糊想法、視覺探索與 repo 實作串成可驗證、可交付的成果。

## Success looks like
- 能依任務性質選擇 Claude、Cowork、Claude Design、Claude Code 或本地 skill。
- 能在陌生 repo 中用唯讀探索、plan mode、測試與 review 控制風險。
- 完成 Phase 3 後，能用 skills 把需求、bug 與維護工作變成有 spec、驗證證據與 handoff 的可交付成果。
- 選修 Phase 4 後，能從 Claude Code 連接 Claude Design MCP，讓 Claude Code 整理四句 brief、傳入一份視覺參考、比較兩個方向，再由真人完成一次試用；選定方向回到 repo 後，能審查實作並親自打開驗證。
- 選讀 Phase 4 進階 09–13 後，能在 Claude Code 觸發 design system sync、補齊狀態與 responsive 規則，分清 Claude Code 的檢查清單與真人 accessibility evidence，最後以 bounded handoff、tests 與 browser evidence 完成 production closeout。
- 能分清楚模型 review、真實使用者回饋與 browser／test evidence，不把好看的 prototype 當成 production-ready 成果。
- 完成 Phase 5 後，能讓 Claude Code 整理三份可信資料與三頁故事，透過 Claude Design MCP 產生初稿、為一種受眾修改，再由真人查核重要主張、打開輸出並彩排，最後把同一份已核准內容改作成一頁摘要。
- 選讀 Phase 5 進階 09–12 後，能讓 Claude Code 維護 claim ledger 與可重用 deck system，由真人稽核 accessibility、實際輸出格式與彩排結果，再透過 Claude Code 封存一個受控版本。
- 完成 Phase 6 後，能把 LLM Wiki raw idea file 交給 Claude Code 建立最小版本、加入第一份真實來源，並提出一個能回查來源的問題。
- 選讀 Phase 6 進階 04–08 後，能讓 schema 隨實際規則演進，完成一次有 review 的 ingest、一次可寫回的 query、一次 lint 修正，並把一個低風險檢查做成可重跑命令。
- 完成 Phase 7 入門 01–04 後，能請 Claude Code 判斷 open-slide 是否適合交付需求；核准 scaffold 命令後，在隔離 workspace 以 <code>/create-slide</code> 完成三頁切片，審查 diff，並在 build 後親自打開正式輸出。
- 選讀 Phase 7 進階 05–09 後，能讓 Claude Code 先讀 <code>CLAUDE.md</code> 與 workspace skills，再使用 <code>/create-theme</code>、<code>/apply-comments</code> 等能力建立可重用 slide system、關閉回饋迴圈，並在人工查核來源、accessibility、權限與 rollback 後準備交付包。
- 完成 Phase 8 入門 01–04 後，能判斷 Claude Code 應做 Playwright MCP live check 或持久 Playwright Test，在 local scope 連接並核對 MCP、觀看一條真實 browser path，並審查第一個 test 的 diff 與可解釋 fail → pass evidence。
- 選讀 Phase 8 進階 05–09 後，能為 Claude Code 初始化 Playwright Test Agents，以 planner → approved spec → generator → reviewed test 建立受控流程，用 trace 監督 healer，並把已審查 tests 接到最小 CI gate。

## Constraints
- 課程使用繁體中文與台灣用語；命令、檔名、API 名稱保留英文。
- 每課要短、可實作、可回到真實 repo 使用。
- Phase 4–8 都以「Claude Code 使用者」為學習角色：Claude Code 是主要工作介面，Claude Design MCP、open-slide workspace skills、LLM Wiki idea file 與 Playwright 是被 Claude Code 使用的專用能力；學員練習的是 prompt、授權、diff review 與 evidence review，不是先手動背完整 API。
- Phase 4–8 採 beginner-first：每課只做一個小動作，先得到可見成果；進階術語、完整治理與 production-grade 驗證只能作為後續擴充，不得成為入門門檻。
- Claude Design 仍是 beta；課程不依賴單一按鈕位置或未保證的功能。
- Claude Design MCP 先依官方文件採 user scope 連線並以 <code>/design-login</code> 登入；連線只提供工具能力，不代表授權 Claude Code 修改未指定的 repo、公開內容或代替真人回饋。
- Phase 4 是選修設計路線；沒有視覺介面的工作不需要為了結業而使用 Claude Design。
- Phase 4 入門 01–08 是獨立完成線；進階 09–13 只在小畫面真的要進產品時使用，不得回頭變成入門前置。
- Phase 5 使用真實來源與受眾；主線只做三頁簡報與一頁摘要，不以模型生成內容取代來源確認或人工彩排。
- Phase 5 入門 01–08 是獨立完成線；進階 09–12 只處理 Claude Design 簡報的可信對外交付，code-first 路線移到 Phase 7。
- Phase 6 不綁定特定 plugin 或 app；原始資料不被改寫，Wiki 頁不是 factual source of truth。
- Phase 6 入門 01–03 只要求一個 raw 連結、一份真實來源與一個問題；進階 04–08 不得回頭變成入門門檻。
- Phase 6 自動化只從可重跑、可檢查、低破壞性的步驟開始；不把無人審查的批次 ingest 或大規模改寫列為完成條件。
- Phase 7 入門 01–04 不要求先懂 React 或手動背 open-slide API，只要求能核對 Claude Code 提議的命令、審查三頁 diff、親自打開正式輸出；進階 05–09 不得回頭變成入門前置。
- Phase 7 不把 open-slide 說成 PPTX 工具；部署是需 owner 與授權的外部狀態變更，不以公開網址作為必修完成條件。
- Phase 8 入門 01–04 不要求手動背 Playwright API；學員要會寫清楚 prompt、觀看 headed browser、審查 agent 產生的 diff／output，並理解 MCP live check 不等於持久 test。
- Playwright MCP 先使用 local scope；只有團隊核對 server command、來源與權限後，才把 project-scoped 設定納入 repo。
- Phase 8 進階 05–09 只在需要擴大已驗證 paths、診斷 failure 或形成 delivery gate 時使用；planner spec、generated test、healer patch 與 CI diff 都需要人工核准。
- Report、trace 與 screenshot 視為可能含敏感資料的受控 artifact；Playwright evidence 不能取代人工 usability、完整 accessibility 或視覺品質判斷。
- 勾完實作清單只代表完成操作，不等於掌握；能交出課堂要求的 artifact、說明判斷並通過回饋，才算具備該課的 exit evidence。
- 封閉系統與遺產系統只作為高風險範例，不是課程唯一場景。

## Out of scope
- 抽象 AI 趨勢介紹。
- 把生成畫面、Claude 自評或一次 demo 當成 usability、accessibility 或 production readiness 的證明。
- 把一次漂亮的生成結果當成可直接對外發布的成品。
- 未經驗證的職能案例堆疊。
- 把模型產生的 wiki 頁面當成不需回查來源的權威事實。
- 把 design system sync、完整 accessibility audit、claim ledger 或 proof pack 當成 Phase 4–6 初學者的結業條件；Phase 7 入門只要求最小三頁 build 與實際開啟，Phase 8 入門只要求一次受控 live check 與一個有紅綠證據的持久 test，不要求 Test Agents 或 CI。
