# 實作計畫：發票辨識 Phase 2 — 後端 OCR 辨識服務

**分支**：`002-backend-ocr` | **日期**：2026-02-26 | **規格**：[spec.md](./spec.md)
**輸入**：來自 `specs/002-backend-ocr/spec.md` 的功能規格書

## 摘要

使用者（或 Flutter App 自動觸發）上傳發票圖片至 FastAPI 後端。
後端以 Google Gemini 2.0 Flash 進行多模態 OCR，解析出結構化發票資料（憲章指定 JSON 欄位）；
當 Gemini 超出免費額度或失敗時，自動降級至本地 PaddleOCR + Ollama/Llama 3 備援流程。
圖片辨識完成後立即刪除，服務提供額度狀態端點供 Flutter 端查詢。
全程零雲端費用，速率限制保護免費 API 額度不超標。

## 技術背景

**語言／版本**：Python 3.12
**主要相依套件**：
- `fastapi>=0.104.0` — 異步 Web 框架
- `uvicorn>=0.24.0` — ASGI 伺服器
- `google-generativeai>=0.7.0` — Gemini 2.0 Flash SDK
- `paddleocr>=2.7.0` + `paddlepaddle>=2.4.0` — 繁中離線 OCR 備援
- `slowapi>=0.1.9` — FastAPI 速率限制
- `pillow>=11.0.0` — 圖片格式/尺寸驗證
- `pydantic-settings>=2.0.0` — 環境變數管理
- `python-multipart>=0.0.6` — 圖片上傳支援
- `requests>=2.31.0` — Ollama HTTP 呼叫

**儲存方案**：
- 圖片：記憶體內處理（`bytes`），不落地磁碟；辨識完成即銷毀
- 任務狀態：`asyncio` 記憶體字典（`ocr_tasks: dict[str, OCRTask]`）
- 結果：不持久化（Phase 3 ChromaDB 負責）

**測試工具**：`pytest` + `httpx.AsyncClient`（FastAPI 測試用戶端）；Gemini/Ollama 以 mock service 隔離

**目標平台**：Linux 伺服器 / macOS 本機（個人使用）

**效能目標**：
- Gemini 主路徑：≤ 30 秒完成辨識
- PaddleOCR 備援路徑：≤ 20 秒（純 OCR 2s + Ollama 解析 15s）
- 上傳端點回應：≤ 200 ms（立即排隊，非同步處理）

**限制條件**：
- Gemini 免費層：15 RPM，1,500 RPD
- 圖片不持久化（憲章原則四）
- API Key 儲存於 `.env`，不可 hardcode（憲章原則四）
- 速率限制參數可透過 `.env` 設定（憲章原則六）

**規模範圍**：單機個人使用；每日 1–30 張發票；佇列上限 100 筆

## 憲章審查

*關卡：必須在第 0 階段研究前通過。第 1 階段設計後需重新審查。*

| 原則 | 狀態 | 說明 |
|------|------|------|
| **一、功能優先交付** | ✅ 通過 | 所有任務對應 FR-001～009；無推測性功能 |
| **二、零成本技術堆疊一致性** | ✅ 通過 | FastAPI + Gemini 免費層 + PaddleOCR + Ollama，均為憲章指定技術 |
| **三、測試覆蓋門檻** | ✅ 通過 | `GeminiService`、`PaddleOCRService`、`OCROrchestrator`、上傳端點均需單元測試；以 fake service mock AI 相依 |
| **四、資料完整性與隱私** | ✅ 通過 | 圖片辨識完成後立即銷毀；API Key 存於 `.env`；後端不持久化圖片 |
| **五、本地優先運算** | ✅ 通過 | Gemini 用於本地無法替代的多模態理解；向量/Embedding 留待 Phase 3 本地執行 |
| **六、API 節流保護** | ✅ 通過 | slowapi 集中限流；RPM 上限透過 `.env` 設定；超限自動排隊或降級備援 |
| **七、簡單性與 YAGNI** | ✅ 通過 | asyncio.Queue（非 Celery）；slowapi（非 Redis）；MD5（非 perceptual hash）；無推測性抽象 |

**憲章審查結論**：所有原則通過，無需複雜度追蹤記錄。

## 專案結構

### 文件（本功能）

```text
specs/002-backend-ocr/
├── plan.md              ← 本文件
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── backend-api-contracts.md
└── tasks.md             # 由 /speckit.tasks 產生
```

### 原始碼（儲存庫根目錄）

```text
backend/
├── app/
│   ├── main.py                    # FastAPI 入口，lifespan 事件（預載 PaddleOCR）
│   ├── routers/
│   │   └── invoices.py            # POST /invoices/upload, GET /invoices/{task_id}
│   ├── services/
│   │   ├── gemini_service.py      # Gemini 2.0 Flash 呼叫 + response_schema
│   │   ├── paddleocr_service.py   # PaddleOCR 初始化 + 文字提取
│   │   ├── ollama_service.py      # Ollama/Llama 3 JSON 解析
│   │   └── ocr_orchestrator.py   # 主路徑 → 備援降級邏輯
│   ├── models/
│   │   └── invoice.py             # Pydantic 模型：InvoiceResult、LineItem、TaskStatus
│   └── core/
│       ├── config.py              # pydantic-settings 環境變數
│       ├── rate_limiter.py        # slowapi Limiter 設定
│       └── queue_manager.py       # asyncio.Queue + Semaphore + ocr_tasks dict
├── tests/
│   ├── unit/
│   │   ├── test_gemini_service.py
│   │   ├── test_paddleocr_service.py
│   │   ├── test_ollama_service.py
│   │   └── test_ocr_orchestrator.py
│   └── integration/
│       └── test_upload_endpoint.py
├── requirements.txt
├── .env.example
└── .gitignore                     # 包含 .env、*.pyc、__pycache__

lib/
└── features/
    └── upload_queue/              # Phase 1（已完成）—需更新上傳端點 URL
```

**結構決策**：採用 `backend/` 獨立目錄，與 Flutter 前端（`lib/`）分離管理相依套件與執行環境，符合原則七（簡單性）。

## 複雜度追蹤

> 所有憲章原則均通過，無違規需記錄。
