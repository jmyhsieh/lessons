# Mission: 與 Claude 建立從想法到可驗證交付的工作流

## Why
站在台灣工程師的工作現場，學會判斷 Claude、Cowork、Claude Design、Claude Code 與 Skills 各自適合的工作方式，並能把模糊想法、視覺探索與程式庫（repo）實作串成可驗證、可交付的成果；需要重用團隊流程時，也能讓 Claude Code 協助寫出可預期、可維護的工作技能（Skill）。

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
- 完成 Phase 9 入門 01–04 後，能從真實 repo 的重複流程做出專案 Skill，決定由工程師手動啟用或讓 Claude 自動啟用，並用執行步驟、參考資料與可檢查的完成條件審查第一次執行結果。
- 選讀 Phase 9 進階 05–09 後，能用按需載入、引導詞、實際查找與驗證工作，以及精簡整理改善 Skill，並在新的 Claude Code 對話分開測試啟用方式與執行結果，而不是把一次成功當成可靠。
- 完成 Phase 10 入門 01–04 後，能讓 Claude Code 依文字層、版面與敏感性選擇 MarkItDown、Docling 或直接讀取；轉換一份文字型文件與一份掃描 PDF，並把 Markdown 與原始文件逐項對照。
- 選讀 Phase 10 進階 05–08 後，能比較預設擷取與強制 OCR、留下可追查轉換紀錄、批次處理精確核准清單，並把已查核 Markdown 連同原始來源與已知限制交給 LLM Wiki。
- 選修 Phase 11 後，能依問題讓 Claude Code 選用 ccusage、QMD 或 Serena：記錄一個工作階段的用量基準、搜尋一組核准的 Markdown 並回查原文，或唯讀找出一個程式符號的定義與兩個引用。
- 完成 Phase 12 入門 01–04 後，能查核並安裝 emilkowalski/skills，請 Claude Code 審查一個介面元件、把一個模糊動態說清楚，並完成一個有真實瀏覽器證據的按壓回饋。
- 選讀 Phase 12 進階 05–08 後，能審查一份固定動態差異、保留一項，也排除一項並寫下理由、建立一份內容完整且可直接交接的改善計畫，再依核准範圍執行並查核。

## Constraints
- 全課程都以「台灣工程師使用 Claude Code」為學習角色。實際情境放在程式庫、程式差異（diff）、測試、權限與交接，不用抽象的 AI 工作術語代替工作現場。
- 課程使用繁體中文與台灣用語。中文先講概念；英文只保留產品名、命令、欄位，以及術語第一次出現時的原文。
- 每課只完成一個可檢查的成果，內容要短、可實作，也要能回到真實程式庫使用；不得在同一課塞入多組尚未解釋的新名詞。
- Claude Code 是主要工作介面；Claude Design MCP、open-slide 工作區技能、LLM Wiki 原始想法檔、Playwright 與工作技能（Skills）是由 Claude Code 使用或維護的專用能力。學員練習需求說明、授權、程式差異審查與證據審查，不先手動背完整 API。
- Phase 4–12 採 beginner-first：每課只做一個小動作，先得到可見成果；進階術語、完整治理與 production-grade 驗證只能作為後續擴充，不得成為入門門檻。
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
- Phase 9 入門 01–04 只要求一個專案 Skill、一個由工程師決定的啟用方式、一份最小結構與一次可觀察執行；不要求先安裝 plugin、建立完整 Skill 收藏庫或跑正式效能評測。
- Phase 9 先收緊完成條件，只有在新對話的證據顯示 Claude 仍會搶快時，才拆分 Skill 來隱藏完成後才需要的步驟；不得為了看起來模組化而增加對話脈絡負擔或使用者記憶負擔。
- Skill 的可靠性是流程可預期，不是逐字相同輸出；Claude 自動啟用 Skill 的啟用方式與 Skill 執行後結果必須分開評估。
- Phase 10 是獨立選修，不是 Phase 6 前置。一般文字型 PDF／Office 文件先試 MarkItDown；掃描 PDF、圖片或複雜版面才走 Docling；少量文件也可直接請 Claude Code 讀取。
- Phase 11 是三課獨立選修，不是其他 Phase 的前置。ccusage 只量本機使用紀錄，不代表成果品質或官方剩餘額度；QMD 入門只搜尋精確核准的 Markdown 目錄，不下載模型；Serena 入門只在真實程式庫做唯讀符號探索。三個工具都不得宣稱保證省 token 或降低總成本。
- Phase 12 是獨立選修，不是 Phase 4 的前置。入門 01–04 只要求安全安裝、單一元件審查、單一動態需求卡與一個按壓回饋；進階 05–08 才盤點整個程式庫、建立計畫並受控執行。任何 Skill 的建議都不取代 diff、測試、真實瀏覽器與人工判斷。
- Phase 12 不以模仿 Apple 外觀或增加動畫數量為目標。高頻操作、鍵盤路徑與沒有明確用途的狀態變化可以不加動態；實作要檢查 <code>prefers-reduced-motion</code>，計畫與目前 commit 不符時必須停止。
- MarkItDown 基礎套件不得被描述為會自動替掃描 PDF 做本機 OCR；Claude Code 訂閱也不得被當成 MarkItDown OCR plugin 的 API 憑證。課程入門不依賴雲端 Vision API。
- Docling 的 <code>--force-ocr</code> 只用於確認的掃描頁或損壞文字層，不是預設選項。敏感文件留在核准的本機環境，批次只處理精確 allowlist，所有 Markdown 都保留原檔並人工查核。
- 勾完實作清單只代表完成操作，不等於掌握；能交出課堂要求的 artifact、說明判斷並通過回饋，才算具備該課的 exit evidence。
- 封閉系統與遺產系統只作為高風險範例，不是課程唯一場景。

## Out of scope
- 抽象 AI 趨勢介紹。
- 把生成畫面、Claude 自評或一次 demo 當成 usability、accessibility 或 production readiness 的證明。
- 把一次漂亮的生成結果當成可直接對外發布的成品。
- 未經驗證的職能案例堆疊。
- 把模型產生的 wiki 頁面當成不需回查來源的權威事實。
- 把 design system sync、完整 accessibility audit、claim ledger 或 proof pack 當成 Phase 4–6 初學者的結業條件；Phase 7 入門只要求最小三頁 build 與實際開啟，Phase 8 入門只要求一次受控 live check 與一個有紅綠證據的持久 test，不要求 Test Agents 或 CI。
- 把下載大量社群 Skills、追求逐字固定輸出，或一次成功執行當成工作技能品質證明。
- 把轉換命令成功、OCR 輸出順暢或 Markdown 格式漂亮，當成內容已與原始文件一致的證明。
- 把 Skill 的審查結論或計畫當成不需程式與瀏覽器查核的合併許可，或為了展示技巧替高頻操作加入多餘動態。
- 雲端 OCR／VLM、無人審查的遞迴批次掃描、production-scale 文件管線與高擬真文件重製。
