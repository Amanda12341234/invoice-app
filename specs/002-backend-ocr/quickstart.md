# 快速入門：發票辨識 Phase 2 — 後端 OCR 辨識服務

**分支**：`002-backend-ocr` | **日期**：2026-02-26

---

## 前置條件

| 項目 | 版本 | 說明 |
|------|------|------|
| Python | 3.12 | 建議使用 `pyenv` 管理版本 |
| pip | latest | `pip install --upgrade pip` |
| Ollama | latest | 下載：https://ollama.ai |
| Gemini API Key | — | Google AI Studio 免費申請 |

---

## 1. 取得環境設定

```bash
# 複製環境變數範本
cp backend/.env.example backend/.env

# 編輯並填入 Gemini API Key
# GEMINI_API_KEY=your_key_here
```

> 🔒 `.env` 已列於 `.gitignore`，**絕對不可提交至 Git**（憲章原則四）

---

## 2. 安裝相依套件

```bash
cd backend
pip install -r requirements.txt
```

**首次安裝注意**：`paddleocr` 在第一次執行時會自動下載繁中模型（~150–200 MB），需要網路連線。

---

## 3. 啟動本地 Ollama 服務

```bash
# 下載 Llama 3 模型（約 4 GB，僅需一次）
ollama pull llama3

# 啟動 Ollama 服務（預設監聽 localhost:11434）
ollama serve
```

---

## 4. 啟動 FastAPI 後端

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API 文件：http://localhost:8000/docs

---

## 5. 測試發票上傳

```bash
# 使用 curl 測試上傳端點
curl -X POST http://localhost:8000/invoices/upload \
  -F "file=@/path/to/invoice.jpg"

# 回應範例：
# { "status": "queued", "task_id": "abc-123", "queue_depth": 1 }
```

```bash
# 輪詢辨識結果
curl http://localhost:8000/invoices/abc-123

# 完成回應範例：
# {
#   "status": "success",
#   "data": {
#     "store_name": "全聯福利中心",
#     "date": "2026-02-26",
#     "items": [{"name": "統一泡麵", "unit_price": 15, "quantity": 2}],
#     "total": 30,
#     "category": "食"
#   },
#   "meta": { "engine_used": "GEMINI_PRIMARY", "processing_time_ms": 3200 }
# }
```

---

## 6. 確認服務狀態

```bash
# 查詢額度與佇列狀態
curl http://localhost:8000/health

# 回應範例：
# {
#   "status": "healthy",
#   "queue_depth": 0,
#   "used_today": 3,
#   "daily_limit": 1500,
#   "active_engine": "GEMINI_PRIMARY"
# }
```

---

## 目錄結構

```
backend/
├── app/
│   ├── main.py                  # FastAPI 入口、lifespan 設定
│   ├── routers/
│   │   └── invoices.py          # POST /invoices/upload, GET /invoices/{task_id}
│   ├── services/
│   │   ├── gemini_service.py    # Gemini 2.0 Flash 呼叫邏輯
│   │   ├── paddleocr_service.py # PaddleOCR + Ollama 備援邏輯
│   │   └── ocr_orchestrator.py  # 降級策略協調
│   ├── models/
│   │   └── invoice.py           # Pydantic 資料模型
│   └── core/
│       ├── config.py            # 環境變數（pydantic-settings）
│       ├── rate_limiter.py      # slowapi 設定
│       └── queue_manager.py     # asyncio.Queue + Semaphore
├── tests/
│   ├── unit/
│   │   ├── test_gemini_service.py
│   │   ├── test_paddleocr_service.py
│   │   └── test_ocr_orchestrator.py
│   └── integration/
│       └── test_upload_endpoint.py
├── requirements.txt
└── .env.example
```

---

## 常見問題

**Q：PaddleOCR 初始化很慢？**
A：第一次啟動需下載模型，後續啟動約 3–5 秒。建議在 FastAPI `lifespan` 事件中預載。

**Q：Gemini 回傳 429？**
A：已自動排隊重試。若每日額度耗盡，系統切換 PaddleOCR 備援，服務不中斷。

**Q：如何調整速率限制？**
A：修改 `.env` 中的 `RATE_LIMIT_RPM`（預設 15）。不可硬編碼（憲章原則六）。

**Q：Flutter 端如何連接？**
A：Phase 1 的 `UploadQueueService` 需更新上傳端點 URL 為 `http://<server>:8000/invoices/upload`。
