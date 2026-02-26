# 研究報告：發票辨識 Phase 2 — 後端 OCR 辨識服務

**分支**：`002-backend-ocr` | **日期**：2026-02-26
**關聯計畫**：[plan.md](./plan.md)

---

## 研究議題 1：Gemini 2.0 Flash API 整合

### 決策：使用 `google-generativeai` SDK + JSON Mode + `response_schema`

**理由**：
- 官方 Python SDK，維護穩定；`response_schema` 可強制輸出符合憲章指定欄位的結構化 JSON，避免後處理解析錯誤。
- `response_mime_type="application/json"` + `response_schema` 組合在 Gemini 2.0 Flash 已正式支援，優於純 prompt 指示 JSON 格式（後者仍需 regex 抽取）。

**免費額度上限（Google AI Studio 免費層，截至 2025 初）**：
| 指標 | 數值 | 備注 |
|------|------|------|
| RPM（每分鐘請求） | 15 RPM | Gemini 2.0 Flash 免費層 |
| RPD（每日請求） | 1,500 RPD | 超出後回傳 429 |
| 輸入 token 上限 | 1,048,576 tokens | 每次請求 |

> ⚠️ 實際數值請於上線前至 [ai.google.dev/pricing](https://ai.google.dev/pricing) 確認。

**錯誤碼**：
- `429 RESOURCE_EXHAUSTED`：RPM 或 RPD 超出 → 觸發降級至 PaddleOCR
- `400 INVALID_ARGUMENT`：圖片格式/大小不符 → 回傳前端驗證錯誤
- `503 UNAVAILABLE`：服務暫停 → 觸發降級

**SDK 使用模式**：
```python
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

response = model.generate_content(
    [image_part, prompt],
    generation_config=genai.types.GenerationConfig(
        response_mime_type="application/json",
        response_schema=INVOICE_SCHEMA  # 對應憲章指定欄位
    )
)
```

**替代方案考量**：
- `google-genai`（新版 SDK）：功能等同，但文件尚不完整，暫不採用（YAGNI）。
- 直接 REST API 呼叫：維護成本高，拒絕。

---

## 研究議題 2：PaddleOCR 繁中備援整合

### 決策：`paddleocr>=2.7.0` + `lang='ch'` + Ollama/Llama 3 解析結構化欄位

**理由**：
- `ch` 語言模型（`ch_PP-OCRv4`）原生支援繁體中文，台灣統一發票測試效果良好。
- PaddleOCR 離線推論，符合「本地優先運算」憲章原則五。
- 結合 Ollama/Llama 3 可將原始 OCR 文字解析為與 Gemini 相同格式的 JSON，備援流程對前端透明。

**效能特性**：
| 環節 | CPU 耗時 | 記憶體 |
|------|---------|--------|
| PaddleOCR 偵測+辨識 | 0.8–2.3s | 300–400 MB |
| Ollama/Llama 3 解析 | 5–15s | 4–8 GB（7B 模型） |
| 備援全流程 | **6–17s** | **5–10 GB** |

**關鍵限制**：
- Ollama 預設單執行緒推論 → 備援請求需序列化排隊，不可並行。
- 首次啟動需下載 PaddleOCR 模型（~150–200 MB），後續完全離線。
- 主機記憶體建議 ≥ 8 GB（PaddleOCR + Ollama 同時載入）。

**替代方案考量**：
- EasyOCR：繁中支援較弱，拒絕。
- Tesseract：對台灣發票版面理解差，拒絕。

---

## 研究議題 3：FastAPI 圖片上傳、限流與排隊

### 決策：`UploadFile` + `slowapi` 限流 + `asyncio.Queue` 排隊 + MD5 去重

**理由**：
- `UploadFile` 為 FastAPI 原生非同步上傳介面，無需額外套件。
- `slowapi 0.1.9+`：裝飾器語法簡潔，單機無需 Redis，符合 YAGNI 原則。
- `asyncio.Queue`：stdlib 無依賴，個人使用規模（1–30 張/日）完全足夠；Celery 為過度設計。
- MD5 去重：速度快、zero-dependency；perceptual hash（imagehash）可選用於近似重複偵測，但個人場景 MD5 已足夠。

**速率限制設定（對應 Gemini 免費層）**：
- 前端限流：`15/minute`（與 Gemini RPM 對齊）
- 參數透過 `.env` 設定（`RATE_LIMIT_RPM`），禁止硬編碼（憲章原則六）

**非同步 OCR 任務模式**：
```
POST /invoices/upload
  → 驗證 → 去重 → asyncio.Queue.put_nowait()
  → 立即回傳 { task_id, status: "queued" }

背景 worker (asyncio.Semaphore(1))：
  → 取出佇列 → 呼叫 Gemini（或降級 PaddleOCR）
  → 更新 ocr_tasks[task_id].status

GET /invoices/{task_id}
  → 輪詢結果
```

**圖片驗證規則**（在辨識前執行）：
- 格式：JPEG、PNG、HEIC（HEIC 需 `pillow-heif` 轉換）
- 大小：≤ 10 MB
- 最小尺寸：640 × 480 px

**替代方案考量**：
- `fastapi-limiter`（Redis 依賴）：過度設計，拒絕。
- `Celery`：分散式任務佇列，個人專案過重，拒絕。

---

## 研究議題 4：降級策略與錯誤處理

### 決策：三層降級（Gemini → PaddleOCR+Ollama → 排隊重試）

**對應憲章錯誤降級表**：

| 失敗情境 | 降級行為 | 對前端回應 |
|---------|---------|-----------|
| Gemini 429（RPM） | 排入本地佇列，稍後重試 | `{ status: "queued", retry_after: N }` |
| Gemini 429（RPD 耗盡） | 切換 PaddleOCR+Ollama | 同成功格式，`engine: "fallback"` |
| Gemini 503 | 切換 PaddleOCR+Ollama | 同上 |
| PaddleOCR+Ollama 失敗 | 回傳可重試錯誤 | `{ status: "error", retryable: true }` |
| 圖片驗證失敗 | 立即拒絕，不消耗額度 | `{ status: "error", retryable: false }` |

---

## 研究議題 5：專案結構決策

### 決策：獨立 `backend/` 目錄（行動應用 + API 結構）

**理由**：Phase 2 引入 Python/FastAPI 後端，與現有 Flutter 前端完全不同技術棧，
應分開目錄管理依賴（`requirements.txt` vs `pubspec.yaml`），符合憲章原則七（簡單性）。

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── routers/
│   │   └── invoices.py      # /invoices/* 端點
│   ├── services/
│   │   ├── gemini_service.py
│   │   ├── paddleocr_service.py
│   │   └── ocr_orchestrator.py  # 降級邏輯
│   ├── models/
│   │   └── invoice.py       # Pydantic 模型
│   └── core/
│       ├── config.py        # 環境變數載入
│       ├── rate_limiter.py
│       └── queue_manager.py
├── tests/
│   ├── unit/
│   └── integration/
├── requirements.txt
└── .env.example
```
