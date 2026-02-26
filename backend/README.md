# Invoice OCR Backend — Phase 2

FastAPI 後端：接收發票圖片，以 Google Gemini 2.0 Flash 辨識並回傳結構化 JSON。
當 Gemini 失敗或額度不足時自動切換至 PaddleOCR + Ollama 備援。

## 快速啟動

```bash
cp .env.example .env          # 填入 GEMINI_API_KEY
pip install -r requirements.txt
ollama pull llama3             # 備援 LLM（僅首次需要）
ollama serve &                 # 啟動 Ollama
uvicorn app.main:app --reload --port 8000
```

API 文件：http://localhost:8000/docs

## 執行測試

```bash
# 在 backend/ 目錄下
pytest tests/ -v

# 只跑單元測試
pytest tests/unit/ -v

# 只跑整合測試
pytest tests/integration/ -v
```

## 主要端點

| 端點 | 說明 |
|------|------|
| `POST /invoices/upload` | 上傳發票圖片，回傳 `task_id` |
| `GET /invoices/{task_id}` | 輪詢辨識結果 |
| `GET /invoices/health/status` | 查詢額度與佇列狀態 |

## 目錄結構

```
backend/
├── app/
│   ├── core/           # config, queue_manager, rate_limiter, image_validator
│   ├── models/         # Pydantic 資料模型
│   ├── routers/        # FastAPI 路由
│   └── services/       # Gemini, PaddleOCR, Ollama, Orchestrator
├── tests/
│   ├── unit/           # 單元測試（外部服務全部 mock）
│   └── integration/    # 整合測試（使用 httpx.AsyncClient）
├── .env.example        # 環境變數範本
└── requirements.txt
```
