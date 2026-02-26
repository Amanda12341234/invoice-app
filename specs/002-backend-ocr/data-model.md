# 資料模型：發票辨識 Phase 2 — 後端 OCR 辨識服務

**分支**：`002-backend-ocr` | **日期**：2026-02-26

---

## 實體關係概覽

```
InvoiceUploadRequest
    │ 1
    │ 包含
    ▼ 1
RecognitionTask ──── 產生 ────► RecognitionResult
                                      │ 1
                                      │ 包含多個
                                      ▼ N
                                   LineItem

QuotaStatus（全域單例）
```

---

## 實體定義

### InvoiceUploadRequest（上傳請求）

入口邊界物件，代表一次發票圖片上傳事件。

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `request_id` | UUID | ✅ | 系統產生，唯一識別此次上傳 |
| `image_bytes` | bytes | ✅ | 原始圖片位元組（僅在記憶體中，不落地） |
| `image_mime_type` | string | ✅ | `image/jpeg`、`image/png`、`image/heic` |
| `image_size_bytes` | int | ✅ | 驗證用，上限 10 MB |
| `image_md5` | string | ✅ | 去重用，hex 字串 |
| `received_at` | datetime | ✅ | UTC 時間戳 |

**驗證規則**：
- `image_size_bytes` ≤ 10,485,760（10 MB）
- `image_mime_type` 必須在允許清單內
- 圖片解析度 ≥ 640 × 480 px（由影像庫驗證）
- `image_md5` 若已存在於近期快取（24 小時內），視為重複上傳

**狀態轉換**：無（入口物件，驗證後立即轉換為 `RecognitionTask`）

---

### RecognitionTask（辨識任務）

代表一張發票圖片的完整辨識生命週期。

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `task_id` | UUID | ✅ | 對外公開的任務識別碼 |
| `request_id` | UUID | ✅ | 關聯的 `InvoiceUploadRequest` |
| `status` | TaskStatus | ✅ | 見下方狀態機 |
| `engine_used` | EngineType | ✅（完成後） | 實際使用的辨識引擎 |
| `queued_at` | datetime | ✅ | 進入排隊時間 |
| `started_at` | datetime | ✗ | 開始處理時間 |
| `completed_at` | datetime | ✗ | 完成時間 |
| `error_message` | string | ✗ | 失敗時的說明訊息（可回傳前端） |
| `retryable` | bool | ✅ | 失敗時是否允許重試 |

**TaskStatus 狀態機**：
```
QUEUED → PROCESSING → COMPLETED
                    ↘ FAILED（retryable=true / false）
```

**EngineType 列舉**：
- `GEMINI_PRIMARY`：Google Gemini 2.0 Flash
- `PADDLEOCR_FALLBACK`：PaddleOCR + Ollama/Llama 3

**狀態轉換規則**：
- `QUEUED → PROCESSING`：worker 從佇列取出時
- `PROCESSING → COMPLETED`：辨識引擎成功回傳並驗證結果時
- `PROCESSING → FAILED(retryable=true)`：429/503 且備援亦失敗；可由 Flutter 端重試
- `PROCESSING → FAILED(retryable=false)`：圖片內容無法辨識（非技術性失敗）

---

### RecognitionResult（辨識結果）

辨識完成後的結構化發票資料。欄位名稱遵循憲章技術標準。

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `task_id` | UUID | ✅ | 關聯的 `RecognitionTask` |
| `store_name` | string | ✅ | 店家名稱（可為空字串表示辨識失敗） |
| `date` | string | ✅ | 格式 `YYYY-MM-DD`；無法辨識時為 `null` |
| `items` | LineItem[] | ✅ | 品項列表，可為空陣列 |
| `total` | number | ✅ | 發票總金額（新台幣）；無法辨識時為 `null` |
| `tax` | number | ✗ | 稅額；無法辨識時為 `null` |
| `category` | string | ✅ | `食`、`衣`、`住`、`行`（憲章指定分類） |
| `confidence` | ConfidenceLevel | ✅ | 整體辨識信心度 |
| `engine_used` | EngineType | ✅ | 產生此結果的辨識引擎 |
| `partial_failure_fields` | string[] | ✗ | 辨識失敗的欄位名稱列表 |
| `recognized_at` | datetime | ✅ | UTC 時間戳 |

**ConfidenceLevel 列舉**：`HIGH`、`MEDIUM`、`LOW`

**驗證規則**：
- `total` 若非 null，必須 > 0
- `date` 若非 null，必須通過 ISO 8601 日期格式驗證
- `category` 必須在四個指定值之內

**資料保留**：
- `RecognitionResult` 由後端回傳前端後，**後端不持久化儲存**（Phase 3 ChromaDB 負責）
- 圖片原始位元組在此實體產生後立即銷毀（憲章原則四）

---

### LineItem（發票品項）

發票上的單一消費項目，嵌入於 `RecognitionResult.items`。

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `name` | string | ✅ | 品項名稱 |
| `unit_price` | number | ✅ | 單價（新台幣） |
| `quantity` | number | ✅ | 數量（預設 1） |
| `subtotal` | number | ✗ | 小計（`unit_price × quantity`，可由 LLM 推算） |

**驗證規則**：
- `name` 不可為空字串
- `unit_price` ≥ 0
- `quantity` > 0

---

### QuotaStatus（服務額度狀態）

全域單例，追蹤免費 API 額度使用情況。

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `used_today` | int | ✅ | 今日已使用 Gemini API 次數 |
| `daily_limit` | int | ✅ | 每日上限（來自 `.env`，預設 1,500） |
| `rpm_used` | int | ✅ | 當前分鐘已使用次數 |
| `rpm_limit` | int | ✅ | 每分鐘上限（來自 `.env`，預設 15） |
| `reset_at_utc` | datetime | ✅ | 每日額度重置時間（UTC 00:00） |
| `queue_depth` | int | ✅ | 目前排隊中的任務數量 |
| `active_engine` | EngineType | ✅ | 當前主要使用的引擎 |

**狀態邏輯**：
- `used_today >= daily_limit`：強制切換至 `PADDLEOCR_FALLBACK`
- `rpm_used >= rpm_limit`：將請求排入佇列，不立即送出

---

## API 回應包裝格式

所有端點統一使用以下包裝結構：

```json
{
  "status": "success | error | queued",
  "data": { ... },
  "error": {
    "code": "ERROR_CODE",
    "message": "人類可讀的說明",
    "retryable": true
  },
  "meta": {
    "task_id": "uuid",
    "engine_used": "GEMINI_PRIMARY",
    "processing_time_ms": 1234
  }
}
```

**錯誤碼列表**：

| 錯誤碼 | HTTP 狀態 | 說明 | retryable |
|--------|----------|------|-----------|
| `INVALID_FORMAT` | 400 | 不支援的圖片格式 | false |
| `IMAGE_TOO_SMALL` | 400 | 圖片解析度不足 | false |
| `IMAGE_TOO_LARGE` | 413 | 圖片超過 10 MB | false |
| `DUPLICATE_IMAGE` | 409 | 重複上傳 | false |
| `NO_TEXT_DETECTED` | 422 | 無法偵測到文字 | false |
| `PARTIAL_RECOGNITION` | 206 | 部分欄位辨識失敗 | false |
| `QUEUE_FULL` | 503 | 佇列已滿 | true |
| `ALL_ENGINES_FAILED` | 503 | 主備援均失敗 | true |
| `TASK_NOT_FOUND` | 404 | 查詢不存在的 task_id | false |
| `RATE_LIMITED` | 429 | 請求速率超限 | true |
