# 文件轉 Markdown 改為獨立 Phase 10

Status: active

使用者確認 MarkItDown 與 Docling 可以合成一個獨立 Phase，因為兩者共同解決「讓 Claude Code 把一般文件與掃描文件轉成可查核 Markdown」這個完整成果。Phase 10 不成為 LLM Wiki 前置：一般文字型文件先用 MarkItDown，掃描或複雜文件走 Docling，本來就只有少量文件時也可直接請 Claude Code 讀取。

後續固定採入門 01–04、進階 05–08。入門只做單檔選路、一次 MarkItDown 轉換、一次 Docling 本機 OCR 與原檔對照；進階才做混合 PDF 的預設／強制 OCR 比較、可追查轉換紀錄、精確 allowlist 小批次，以及已查核 Markdown 的 LLM Wiki ingest。所有輸出都是衍生資料，必須保留原始文件與人工查核限制。
