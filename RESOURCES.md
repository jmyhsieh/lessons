# AI Workflow Composition Resources

這份檔案只保留課程可依賴的高信任來源。新聞與職能案例不作為 factual source of truth；需要案例時，請回查其第一手來源。正式課程與工具實作只取每份來源中完成第一個小成果所需的最少知識。

## Knowledge

- [Guide: Claude Code overview — Anthropic](https://code.claude.com/docs/en/overview)
  Claude Code 的工作環境、支援表面與核心能力。Use for: Phase 1 的產品與 repo 工作邊界。
- [Guide: Claude Code Desktop — Anthropic](https://code.claude.com/docs/en/desktop)
  Desktop Code、Cowork／Dispatch、permission modes、worktrees、diff 與 session 管理。Use for: Phase 1 桌面 App 操作與產品表面。
- [Guide: Get started with Claude Cowork — Anthropic](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork)
  Cowork remote／local sessions、web／desktop／mobile 可用性與本機檔案邊界。Use for: Phase 1 Cowork surface 判斷與安全提醒。
- [Product: Claude Design — Anthropic](https://claude.com/product/design)
  Claude Design 的正式產品定位、視覺產物、export 與 Claude Code handoff。Use for: Phase 1 產品判斷、Phase 3 邊界與 Phase 4 格式選擇。
- [Guide: Get started with Claude Design — Anthropic](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
  Project、context、prompt、chat／comment／canvas、版本與 export；也提供 Claude Code 連線指令 <code>claude mcp add --scope user --transport http claude-design https://api.anthropic.com/v1/design/mcp</code>、<code>/design-login</code>、<code>/design-sync</code> 與 handoff 邊界。Use for: Phase 3–5 的 Claude Code × Claude Design MCP 主線。
- [Tutorial: Using Claude Design for presentations and slide decks — Anthropic](https://claude.com/resources/tutorials/using-claude-design-for-presentations-and-slide-decks)
  受眾、訊息、deck 產生、單頁修改、圖表、分享與 HTML／PPTX／PDF export。Use for: Phase 4 簡報主線。
- [Guide: Introduction — open-slide](https://open-slide.dev/docs)
  React-first agent slide framework、固定 1920×1080 canvas、present mode 與 HTML／PDF export 的正式定位。Use for: open-slide 實作第 01 課的 surface 邊界與停止線。
- [Guide: Getting started — open-slide](https://open-slide.dev/docs/getting-started)
  Workspace scaffold、dev server、Claude Code authoring、inspector comments、static build 與 deploy 流程。Use for: open-slide 實作第 02–04 課由 Claude Code 建立 workspace、使用 <code>/create-slide</code> 與 build 的入門主線。
- [Guide: Create a slide — open-slide](https://open-slide.dev/docs/flow/create-slide)
  從 agent brief 到第一張可在 dev server 檢查的投影片。Use for: open-slide 實作第 03 課三頁 vertical slice。
- [Guide: Agent skills overview — open-slide](https://open-slide.dev/docs/skills/overview)
  Workspace-local <code>AGENTS.md</code>、鏡像 <code>CLAUDE.md</code>，以及 Claude Code 可用的 <code>/create-slide</code>、<code>/slide-authoring</code>、<code>/create-theme</code>、<code>/apply-comments</code> 等 skills；<code>open-slide sync:skills</code> 可刷新本地版本。Use for: open-slide 實作第 03、05、06、08 課。
- [Guide: Themes — open-slide](https://open-slide.dev/docs/core-feature/themes)
  Theme 建立、套用與重用邊界。Use for: open-slide 實作第 06 課的最小 slide system。
- [Skill: /apply-comments — open-slide](https://open-slide.dev/docs/skills/apply-comments)
  把 inspector 的 <code>@slide-comment</code> markers 轉成 code edits，再回到瀏覽器驗證。Use for: open-slide 實作第 08 課的 comment → edit → review loop。
- [Reference: Export — open-slide](https://open-slide.dev/docs/core-feature/export)
  <code>dist/</code> static HTML build、browser print PDF 與公開分享時可關閉的 UI surface。Use for: open-slide 實作第 04、09 課的輸出與部署邊界。
- [Guide: Connect Claude Code to tools via MCP — Anthropic](https://code.claude.com/docs/en/mcp)
  Claude Code 的 stdio command ordering、<code>--</code> 分隔、local／project scope、<code>claude mcp get</code> 與 trust 邊界。Use for: Playwright 實作第 02 課與 route card 的 Claude Code 操作基準。
- [Guide: Installation — Playwright MCP](https://playwright.dev/mcp/installation)
  Node.js 需求、Claude Code 安裝、headed browser 與 Navigate → Snapshot → Interact → Re-snapshot 工作流。Use for: Playwright 實作第 01–03 課的 live browser check。
- [Guide: Test Agents — Playwright](https://playwright.dev/docs/test-agents)
  Planner、generator、healer、seed test 與 <code>npx playwright init-agents --loop=claude</code>。Use for: Playwright 實作第 05–08 課的 agent-first 進階路線。
- [Guide: Installation — Playwright Test](https://playwright.dev/docs/intro)
  Playwright Test scaffold、browser 安裝、單 project 執行、UI mode 與 HTML report。Use for: Playwright 實作第 04 課的持久 test 地基。
- [Guide: Writing tests — Playwright](https://playwright.dev/docs/writing-tests)
  <code>page</code> fixture、navigation、actions、auto-waiting 與 async assertion。Use for: Playwright 實作第 04、07 課的 test review。
- [Guide: Locators — Playwright](https://playwright.dev/docs/locators)
  User-facing locators、重新查找、retryability 與 CSS／XPath 的脆弱邊界。Use for: Playwright 實作第 04、07 課。
- [Guide: Assertions — Playwright](https://playwright.dev/docs/test-assertions)
  Web-first auto-retrying assertions 與 immediate assertions 的差異。Use for: Playwright 實作第 04、07–08 課。
- [Guide: Trace viewer — Playwright](https://playwright.dev/docs/trace-viewer)
  以 actions、DOM snapshots、network 與 assertions 診斷失敗；CI 建議 <code>on-first-retry</code>。Use for: Playwright 實作第 08 課監督 healer。
- [Guide: Projects — Playwright](https://playwright.dev/docs/test-projects)
  用 projects 表示 browsers、devices、environments 與不同 test groups。Use for: Playwright 實作第 09 課的支援矩陣。
- [Guide: Continuous Integration — Playwright](https://playwright.dev/docs/ci)
  CI 安裝依賴與 browsers、執行 tests、保存 reports／traces，以及 artifact 敏感資料邊界。Use for: Playwright 實作第 09 課。
- [Guide: Set up your design system in Claude Design — Anthropic](https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design)
  從 codebase、prototype、deck 與 brand assets 建立並驗證 design system。Use for: Phase 3 第 03、09 課與 Phase 4 第 10 課品牌校正。
- [Announcement: Introducing Claude Design by Anthropic Labs — Anthropic](https://www.anthropic.com/news/claude-design-anthropic-labs)
  產品發布時的用途、互動方式、export 與 Claude Code handoff 邊界。Use for: Phase 3 產品定位；會變動的操作仍以 Help Center 為準。
- [Update: Claude Design stays on-brand for daily work — Anthropic](https://claude.com/blog/claude-design-stays-on-brand-for-daily-work)
  Design system sync、日常視覺工作與 Claude Code 整合的官方更新。Use for: Phase 3 第 03、07 課與 Phase 4 品牌精修。
- [Guide: Easy Checks — A First Review of Web Accessibility — W3C WAI](https://www.w3.org/WAI/test-evaluate/preliminary/)
  鍵盤操作、頁面標題、替代文字、對比與其他快速 accessibility 檢查。Use for: Phase 3 第 11 課的第一輪 audit。
- [Guide: Making Events Accessible — W3C WAI](https://www.w3.org/WAI/teach-advocate/accessible-presentations/)
  會議、訓練與簡報的可及性檢查，包括投影片文字量、口述畫面資訊與替代格式。Use for: Phase 4 第 06、07、11、12 課與 open-slide 實作第 07 課。
- [Tutorial: Images and complex graphics — W3C WAI](https://www.w3.org/WAI/tutorials/images/)
  圖片、圖表與複雜圖形的文字等價資訊。Use for: Phase 4 第 06 課。
- [Repository: frontend-design plugin — Anthropic](https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design)
  Claude Code 內產出 production-grade frontend code 的官方 plugin／skill；不是 Claude Design 產品。Use for: Phase 3 第 01 課的 surface 邊界。
- [Announcement: Artifacts in Claude Code — Anthropic](https://claude.com/blog/artifacts-in-claude-code)
  把 Code session context 轉成可分享 live page 的功能；不是 Claude Design 專案。Use for: Phase 3 第 01 課的 surface 邊界。
- [Guide: Best practices for Claude Code — Anthropic](https://code.claude.com/docs/en/best-practices)
  Explore-plan-code、verification-first、small scope、review 與 parallel work。Use for: Phase 1 安全流程與 Phase 3 repo 實作。
- [Reference: Permission modes — Anthropic](https://code.claude.com/docs/en/permission-modes)
  各 permission mode 的能力與 plan mode 真正保證。Use for: Phase 1 權限教學。
- [Reference: Configure permissions — Anthropic](https://code.claude.com/docs/en/permissions)
  allow/deny rules、protected paths 與設定範圍。Use for: permission rules 與安全邊界。
- [Guide: Project memory — Anthropic](https://code.claude.com/docs/en/memory)
  CLAUDE.md、CLAUDE.local.md、rules、auto memory 與載入順序。Use for: repo-level instructions 與 contract placement。
- [Guide: Extend Claude Code — Anthropic](https://code.claude.com/docs/en/features-overview)
  CLAUDE.md、Skills、Subagents、MCP、hooks、plugins 與 agent teams 的 selector。Use for: Claude Code 擴充工具選擇。
- [Reference: Skills — Anthropic](https://code.claude.com/docs/en/skills)
  <code>SKILL.md</code>、專案／個人範圍、啟用控制、額外參考檔，以及啟用方式／執行結果分開評估的最新 Claude Code 規則。Use for: Claude Code 擴充工具的 Skills 與 Phase 6 全階段；產品行為與檔頭設定以這份最新文件為準。
- [Talk: Building Great Agent Skills: The Missing Manual — Matt Pocock, AI Engineer](https://www.youtube.com/watch?v=UNzCG3lw6O0)
  約 20 分鐘的 Skill 檢查架構：啟用方式（Trigger）、內容結構（Structure）、行為引導（Steering）、精簡整理（Pruning），以及 Skills 囤積困境、引導詞、實際查找與驗證工作、歷史堆積、無效指令等設計問題。Use for: Phase 6 的課程骨架；Claude Code 具體欄位仍回查 Anthropic 文件。
- [Skill snapshot: writing-great-skills](https://github.com/mattpocock/skills/blob/9603c1cc8118d08bc1b3bf34cf714f62178dea3b/skills/productivity/writing-great-skills/SKILL.md)
  影片架構的可執行版本，補上完成條件、按需載入、Skill 拆分與失敗模式的更精確順序。Use for: Phase 6 第 01–09 課；reviewed snapshot <code>9603c1c</code>（2026-07-18），使用前仍查 <a href="https://github.com/mattpocock/skills/blob/main/skills/productivity/writing-great-skills/SKILL.md">current version</a>。
- [Repository: MarkItDown — Microsoft](https://github.com/microsoft/markitdown)
  把 PDF、Office、圖片、音訊與其他格式轉成適合 LLM 使用的 Markdown；基礎套件不是掃描 PDF 的本機 OCR 引擎。Use for: 文件轉換實作第 01–02、04、06–07 課的輕量轉換路線。
- [Package: MarkItDown — PyPI](https://pypi.org/project/markitdown/)
  目前套件需求、extras、CLI 與 Python 用法。Use for: 文件轉換實作第 02 課的實際安裝與版本查核。
- [Package: MarkItDown OCR](https://github.com/microsoft/markitdown/blob/main/packages/markitdown-ocr/README.md)
  MarkItDown 的獨立 OCR plugin，需要 OpenAI-compatible client、model 與 API 設定；不是基礎套件或 Claude Code 訂閱內含能力。Use for: 說明文件轉換工具為何以 Docling 作為本機 OCR 主線。
- [Repository: Docling](https://github.com/docling-project/docling)
  支援本機文件解析、OCR、版面、閱讀順序、表格與 Markdown 輸出。Use for: 文件轉換實作第 01、03–08 課的掃描與複雜文件路線。
- [Guide: Docling installation](https://docling-project.github.io/docling/getting_started/installation/)
  Python、平台、accelerator 與 OCR extras 的目前需求。Use for: 文件轉換實作第 03 課的核准安裝計畫。
- [Reference: Docling CLI](https://docling-project.github.io/docling/reference/cli/)
  <code>docling convert</code>、Markdown 輸出、OCR、<code>--force-ocr</code>、表格與 device 旗標。Use for: 文件轉換實作第 03、05–07 課的命令與停止線。
- [Example: Full-page OCR — Docling](https://docling-project.github.io/docling/_generated/examples/full_page_ocr/)
  說明何時以強制 OCR 取代既有文字層。Use for: 文件轉換實作第 03、05 課，避免把 <code>--force-ocr</code> 當預設。
- [Guide: Work with images — Claude Code](https://code.claude.com/docs/en/common-workflows#work-with-images)
  Claude Code 可直接讀取圖片並協助分析；少量 PDF／圖片不一定先安裝轉換器。Use for: 文件轉換實作第 01 課的直接讀取替代路線。
- [Repository: ccusage](https://github.com/ccusage/ccusage)
  從程式開發代理（coding agent）的本機使用紀錄整理每日、工作階段與區塊報表；開源核心採 MIT License。Use for: 用量與查找實作第 01 課的 Claude Code 工作階段用量基準；不當作官方方案剩餘額度。
- [Repository: QMD](https://github.com/tobi/qmd)
  對本機 Markdown 做全文與語意搜尋；程式採 MIT License，另外下載的模型各有自己的授權。Use for: 用量與查找實作第 02 課；入門只用核准目錄與全文搜尋，不執行向量化（embedding）。
- [Reference: Tools — Claude Code](https://code.claude.com/docs/en/tools-reference)
  內建 LSP tool 可查 definition、references、types、implementations 與 call hierarchy；需要對應語言的 code intelligence plugin 與 language server。Use for: 用量與查找實作第 03 課的優先符號探索路線。
- [Guide: Discover and install plugins — Claude Code](https://code.claude.com/docs/en/discover-plugins)
  官方 marketplace 的 code intelligence plugins 會啟用 Claude Code LSP；language server binary 仍需另外安裝。Use for: 用量與查找實作第 03 課的安裝前查核與停止線。
- [Repository: Serena](https://github.com/oraios/serena)
  透過語言伺服器提供符號與專案探索工作流；開源核心採 MIT License，JetBrains 付費外掛（plugin）是另一項產品。Use for: 內建 LSP 不合適或需要更完整專案探索時的用量與查找替代工具。
- [Paper: Token Reduction Is Not Cost Reduction](https://arxiv.org/abs/2607.12161)
  實驗顯示輸出 token 變少不一定會降低計費成本，也可能傷害任務完成率。Use for: 用量與查找工具的共同邊界，不把 token 減量直接當成工具有效。
- [Repository snapshot: emilkowalski/skills](https://github.com/emilkowalski/skills/tree/6bf24434f7730ad169077756cf9c7cd7bd675fc6)
  MIT 授權的六個設計工程 Skills 與固定版本內容。Use for: Design Engineering Skills 全階段；安裝前仍要查核目前 README、commit 與寫入範圍。
- [Skill: emil-design-eng](https://github.com/emilkowalski/skills/blob/6bf24434f7730ad169077756cf9c7cd7bd675fc6/skills/emil-design-eng/SKILL.md)
  介面與動態設計原則，以及「修改前／修改後／原因」審查格式。Use for: Design Engineering Skills 實作第 02 課的單一元件審查。
- [Skill: animation-vocabulary](https://github.com/emilkowalski/skills/blob/6bf24434f7730ad169077756cf9c7cd7bd675fc6/skills/animation-vocabulary/SKILL.md)
  把模糊動態描述換成精確術語並釐清相近概念；不負責設計或實作。Use for: Design Engineering Skills 實作第 03 課。
- [Skill: apple-design](https://github.com/emilkowalski/skills/blob/6bf24434f7730ad169077756cf9c7cd7bd675fc6/skills/apple-design/SKILL.md)
  把即時回應、一對一跟隨、動量、可中斷與減少動態等 Apple 互動原則帶到網頁。Use for: Design Engineering Skills 實作第 04 課的小幅按壓回饋。
- [Skill and standards: review-animations](https://github.com/emilkowalski/skills/blob/6bf24434f7730ad169077756cf9c7cd7bd675fc6/skills/review-animations/STANDARDS.md)
  以用途、頻率、時間、緩動、效能、輸入方式與減少動態審查單一 diff。Use for: Design Engineering Skills 實作第 05 課；不延伸為盤點整個程式庫。
- [Skill: find-animation-opportunities](https://github.com/emilkowalski/skills/blob/6bf24434f7730ad169077756cf9c7cd7bd675fc6/skills/find-animation-opportunities/SKILL.md)
  唯讀提出少量候選並保留排除理由；沒有合適動畫也是有效結論。Use for: Design Engineering Skills 實作第 06 課。
- [Skill and plan template: improve-animations](https://github.com/emilkowalski/skills/blob/6bf24434f7730ad169077756cf9c7cd7bd675fc6/skills/improve-animations/SKILL.md)
  唯讀盤點整個程式庫、由使用者選擇、建立單一計畫，再受控執行。Use for: Design Engineering Skills 實作第 07–08 課；盤點不等於執行許可。
- [Video: Designing Fluid Interfaces — Apple](https://developer.apple.com/videos/play/wwdc2018/803/)
  即時回應、一對一觸控、可中斷與保留動量的第一手設計說明。Use for: Design Engineering Skills 實作第 04、08 課的互動判斷。
- [Reference: prefers-reduced-motion — MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)
  依使用者系統設定減少非必要動態的 CSS media feature。Use for: Design Engineering Skills 實作第 04、08 課。
- [Guide: Inspect and modify CSS animation effects — Chrome for Developers](https://developer.chrome.com/docs/devtools/css/animations)
  在 Chrome DevTools 檢查、重播與調整 CSS 動態。Use for: Design Engineering Skills 實作第 08 課的真實瀏覽器查核。
- [Glossary snapshot: Building Great Skills](https://github.com/mattpocock/skills/blob/9603c1cc8118d08bc1b3bf34cf714f62178dea3b/skills/productivity/writing-great-skills/GLOSSARY.md)
  流程可預期性、對話脈絡／使用者記憶負擔、資訊層級、引導詞、實際查找與驗證工作，以及精簡整理失敗模式的詞彙模型。Use for: Phase 6 進階 05–08 與速查表；不要求入門先背詞彙。
- [Reference: Hooks — Anthropic](https://code.claude.com/docs/en/hooks)
  Hook events、event-specific blocking、exit codes 與 structured JSON。Use for: Claude Code 擴充工具的 hooks 與 guardrails。
- [Guide: Subagents — Anthropic](https://code.claude.com/docs/en/sub-agents)
  Context isolation、custom agents、permissions、skills 與 hooks。Use for: Claude Code 擴充工具的 reviewer design。
- [Guide: Worktrees — Anthropic](https://code.claude.com/docs/en/worktrees)
  CLI/Desktop worktree isolation、<code>.worktreeinclude</code> 與 cleanup。Use for: parallel sessions。
- [Guide: Programmatic usage — Anthropic](https://code.claude.com/docs/en/headless)
  <code>claude -p</code>、<code>--bare</code>、structured output 與 scripting。Use for: Claude Code 擴充工具的 headless 與 CI。
- [Reference: Claude Code CLI — Anthropic](https://code.claude.com/docs/en/cli-usage)
  <code>--tools</code>、<code>--allowedTools</code>、<code>--permission-mode</code>、settings 與 MCP flags 的精確語義。Use for: Claude Code 擴充工具的 one-shot／CI。
- [Reference: git status and git diff — Git](https://git-scm.com/docs/git-status)
  Tracked、untracked 與 machine-readable porcelain status 的邊界。Use for: repo 變更確認；tracked patch 比較另見 <a href="https://git-scm.com/docs/git-diff">git diff</a>。
- [Raw idea file: LLM Wiki — Andrej Karpathy](https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md)
  設計成可直接貼給 LLM agent 閱讀並協作實作的原始說明。Use for: Phase 5 01–08；前三課取用 idea-file-first 核心，04–08 依 Architecture、Operations、Indexing and logging、Optional CLI tools 教 schema、ingest、query、lint 與安全自動化。
- [Guide: Use Claude Code with Chrome — Anthropic](https://code.claude.com/docs/en/chrome)
  Browser interaction、DOM／console inspection、design verification 與 web app testing。Use for: Phase 3 第 08、13 課，以及 Playwright 實作第 01 課的替代 live surface；仍需依 repo 的正式測試補足 evidence。
- [Guide: Model configuration — Anthropic](https://code.claude.com/docs/en/model-config)
  Current aliases（包括 <code>fable</code>）、provider-specific resolution、adaptive effort levels、<code>opusplan</code>、<code>ultracode</code> 與 <code>ultrathink</code>。Use for: model/effort 精確設定與版本校正。
- [Guide: Choosing a Claude model and effort level in Claude Code — Anthropic](https://claude.com/blog/claude-model-and-effort-level-in-claude-code)
  官方 default-first 教學：先修 context，再分辨「能力不足」與「做得不夠徹底」；model 決定 capability，effort 也影響讀檔、工具、驗證與工作步數。Use for: Phase 1 第 09 課與 Phase 2 的模型／effort 判斷。
- [Repository: mattpocock/skills](https://github.com/mattpocock/skills)
  Phase 2 使用的上游 workflow skills，以及 Phase 6 的 Skill 編寫檢查架構。Use for: Skill 清單；具體行為以各 <code>SKILL.md</code> 為準。
- [README snapshot: mattpocock/skills installation](https://github.com/mattpocock/skills/blob/66898f60e8c744e269f8ce06c2b2b99ce7660d5f/README.md)
  Claude Code native plugin 與 editable project copy 的官方安裝路徑。Use for: Phase 2 第 01 課；plugin 版本與命令變動時重查 upstream。
- [Skill: setup-matt-pocock-skills](https://github.com/mattpocock/skills/blob/66898f60e8c744e269f8ce06c2b2b99ce7660d5f/skills/engineering/setup-matt-pocock-skills/SKILL.md)
  Issue tracker、triage labels 與 domain docs 的實際設定流程。Use for: Phase 2 地基；README 摘要漂移時以本檔為準。
- [Skill: domain-modeling](https://github.com/mattpocock/skills/blob/66898f60e8c744e269f8ce06c2b2b99ce7660d5f/skills/engineering/domain-modeling/SKILL.md)
  純 glossary、lazy file creation 與三條件 ADR gate。Use for: Phase 2 的 CONTEXT.md／ADR 行為。
- [Skill: code-review](https://github.com/mattpocock/skills/blob/66898f60e8c744e269f8ce06c2b2b99ce7660d5f/skills/engineering/code-review/SKILL.md)
  固定點三點 diff、Standards／Spec 平行雙軸與分開報告。Use for: Phase 2 implement closeout 與獨立 review。
- [Skill: improve-codebase-architecture](https://github.com/mattpocock/skills/blob/66898f60e8c744e269f8ce06c2b2b99ce7660d5f/skills/engineering/improve-codebase-architecture/SKILL.md)
  先按使用者方向或近期 hot spots 限定範圍，再掃描 deepening opportunities。Use for: Phase 2 architecture 支線。
- [Skill: wayfinder](https://github.com/mattpocock/skills/blob/66898f60e8c744e269f8ce06c2b2b99ce7660d5f/skills/engineering/wayfinder/SKILL.md)
  巨大模糊 effort 的 shared map、decision tickets、fog 與 frontier；research ticket 是單 ticket session 規則的例外，會由 subagent 平行處理，並把發現留在 throwaway <code>research/&lt;name&gt;</code> branch，由 ticket 指回 context。Use for: Phase 2 選修 wayfinder 分支。
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
- Phase 3 仍缺可公開引用、同時保留 design intent、browser evidence 與 production diff 的完整 design-to-code 案例。
- Phase 4 仍缺台灣工作情境下、同時保留來源查核與實際簡報回饋的公開案例。
- open-slide 仍缺可公開引用、同時包含 source traceability、accessibility evidence 與真實彩排紀錄的完整案例。
- LLM Wiki 仍缺可公開引用、跨數月且同時展示來源漂移、矛盾裁決、lint 與長期使用價值的完整 proof pack。
- Claude Code × Playwright 仍缺台灣團隊公開、可重現且同時展示 MCP live check、planner／generator／healer 人工關卡、trace 脫敏與 CI gate 取捨的完整案例。
- Claude Code 工作技能仍缺台灣團隊公開、可重現且同時展示啟用方式基準、執行結果基準、精簡前後差異與長期維護成本的完整案例。
- 文件轉 Markdown 仍缺台灣團隊公開、可重現且同時保留原檔、OCR 抽查、表格錯誤、轉換 manifest 與知識庫交接的完整案例。
- 用量與查找工具仍缺台灣團隊公開、可重現且同時比較同類工作完成率、驗證證據、token 與總成本的長期案例。
- Design Engineering Skills 仍缺台灣團隊公開、可重現且同時保留選擇理由、正常與減少動態證據、使用者回饋及最終 diff 的長期案例。
- 若使用者不想參與社群，需記錄在 NOTES.md，避免後續重複推薦。
