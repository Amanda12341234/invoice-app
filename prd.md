# 專案憲章：免費 AI 發票辨識 RAG 系統 (Constitution)

## 1. 專案核心願景 (Vision)
打造一個零成本運行的個人財務 AI 助手。透過 Flutter 手機端擷取發票，並在後端利用開源 OCR 與 Google Gemini 免費 API 實現自動化記帳與智慧對話 (RAG)。

---

## 2. 零成本技術棧 (Zero-Cost Tech Stack)

| 層級 | 推薦工具 (免費版) | 選用理由 |
| :--- | :--- | :--- |
| **前端開發** | **Flutter** | 開源跨平台，社群資源豐富。 |
| **影像處理** | **Google ML Kit (On-Device)** | **完全免費**且離線可用，用於前端即時偵測與預過濾。 |
| **後端 API** | **FastAPI (Python)** | 高性能、異步處理，適合 AI 任務調度。 |
| **OCR & LLM** | **Google Gemini 2.0 Flash** | **Google AI Studio 免費額度**：支援 Vision 圖片辨識，開發期每日請求額度充足。 |
| **備用 OCR** | **PaddleOCR (Open Source)** | 若不連雲端，本地端最強的繁中 OCR 模型。 |
| **向量資料庫** | **ChromaDB (Local Mode)** | 開源向量庫，直接運行在伺服器硬碟，無須訂閱費用。 |
| **AI 框架** | **LangChain** | 開源，支援彈性切換不同的免費模型。 |

---

## 3. 核心功能規格 (Core Specs)

### A. 智慧影像擷取 (Flutter Side)
* **自動對焦與邊框偵測：** 使用 `google_ml_kit_object_detection` 偵測發票，確保上傳圖片不模糊。
* **本地端初步過濾：** 在上傳前先用 `google_ml_kit_text_recognition` 確認圖片中含有文字，減少無效 API 調用。

### B. 結構化資料提取 (Backend Side)
* **Prompt 策略：** 利用 Gemini 2.0 Flash 的 Vision 能力，將圖片直接轉為 JSON。
* **資料欄位定義：** - `store_name`: 店名
  - `date`: 消費日期 (YYYY-MM-DD)
  - `items`: 清單 (含名稱、單價、數量)
  - `total`: 總金額
  - `category`: 消費分類 (食/衣/住/行)

### C. RAG 知識庫管理
* **Embedding:** 使用 `sentence-transformers` (HuggingFace 免費模型) 進行本地向量轉換。
* **Storage:** 所有的發票 JSON 轉換為向量後存入 `ChromaDB` 持久化目錄。

---

## 4. 開發準則 (Development Principles)

1. **API 節流保護 (Rate Limiting):** - 由於使用 Gemini 免費層，後端需實作 `Rate Limiter`，避免每分鐘請求數 (RPM) 超標。
2. **隱私與安全:** - 使用者發票圖檔處理完後立即刪除，僅保留結構化數據。
   - API Key 必須儲存在 `.env` 環境變數中，嚴禁提交至 Git。
3. **本地優先 (Local-First):** - 向量運算與 OCR 解析盡量在後端本地主機完成，減少對雲端收費服務的依賴。

---

## 5. 實作路徑 (Roadmap)

- [ ] **Phase 1:** Flutter 整合 Camera 與 ML Kit 實現發票取景引導。
- [ ] **Phase 2:** Python FastAPI 串接 Google AI Studio (Gemini API) 進行圖片解析。
- [ ] **Phase 3:** 整合 ChromaDB，將辨識結果存入向量資料庫。
- [ ] **Phase 4:** 開發 LangChain 檢索鏈，實現「我上個月在全聯買了什麼？」的對話功能。

---

## 6. 錯誤處理 (Error Handling)
* **辨識異常：** 若 Gemini 回傳失敗，後端自動切換至 `PaddleOCR` 提取原始文字，再交由本地 `Ollama (Llama 3)` 嘗試修復數據。
* **網路斷線：** Flutter 端支援「離線快照」，待有網路時再自動上傳排隊處理。