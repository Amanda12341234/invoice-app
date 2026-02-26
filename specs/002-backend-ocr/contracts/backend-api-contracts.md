# API 契約：發票辨識 Phase 2 — 後端 OCR 辨識服務

**分支**：`002-backend-ocr` | **日期**：2026-02-26
**服務**：FastAPI 後端，監聽 `http://localhost:8000`（開發）
**消費者**：Flutter App（Phase 1 `UploadQueueService`）

---

## 全域規範

- **Content-Type**：上傳端點使用 `multipart/form-data`；其餘端點使用 `application/json`
- **字元編碼**：UTF-8
- **時間格式**：ISO 8601（`YYYY-MM-DDTHH:MM:SSZ`）
- **金額單位**：新台幣整數（`int`）或浮點數（最多兩位小數）
- **認證**：Phase 2 無認證需求（個人單機使用）

---

## 端點 1：上傳發票圖片

### `POST /invoices/upload`

接收發票圖片，驗證後排入辨識佇列。

**請求**

```
Content-Type: multipart/form-data

Fields:
  file  (required)  image/jpeg | image/png | image/heic
                    大小限制：≤ 10 MB
                    最小尺寸：640 × 480 px
```

**成功回應：`202 Accepted`**

```json
{
  "status": "queued",
  "data": null,
  "error": null,
  "meta": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "queue_depth": 1,
    "estimated_wait_seconds": 5
  }
}
```

**重複上傳回應：`409 Conflict`**

```json
{
  "status": "error",
  "data": null,
  "error": {
    "code": "DUPLICATE_IMAGE",
    "message": "此圖片已上傳，請查詢現有辨識結果",
    "retryable": false
  },
  "meta": {
    "existing_task_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**驗證錯誤回應：`400 Bad Request`**

```json
{
  "status": "error",
  "data": null,
  "error": {
    "code": "INVALID_FORMAT | IMAGE_TOO_SMALL",
    "message": "不支援的圖片格式，請使用 JPEG 或 PNG",
    "retryable": false
  },
  "meta": null
}
```

**佇列已滿：`503 Service Unavailable`**

```json
{
  "status": "error",
  "data": null,
  "error": {
    "code": "QUEUE_FULL",
    "message": "辨識佇列已滿，請稍後再試",
    "retryable": true
  },
  "meta": {
    "queue_depth": 100,
    "retry_after_seconds": 30
  }
}
```

**速率限制：`429 Too Many Requests`**

```json
{
  "status": "error",
  "data": null,
  "error": {
    "code": "RATE_LIMITED",
    "message": "請求頻率過高，請稍後再試",
    "retryable": true
  },
  "meta": {
    "retry_after_seconds": 60
  }
}
```

---

## 端點 2：查詢辨識結果

### `GET /invoices/{task_id}`

輪詢特定任務的辨識狀態與結果。

**路徑參數**

| 參數 | 型別 | 說明 |
|------|------|------|
| `task_id` | UUID | `POST /invoices/upload` 回傳的任務識別碼 |

**排隊中回應：`200 OK`**

```json
{
  "status": "queued",
  "data": null,
  "error": null,
  "meta": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "queue_position": 2,
    "estimated_wait_seconds": 10
  }
}
```

**處理中回應：`200 OK`**

```json
{
  "status": "processing",
  "data": null,
  "error": null,
  "meta": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "started_at": "2026-02-26T10:00:00Z"
  }
}
```

**成功完成回應：`200 OK`**

```json
{
  "status": "success",
  "data": {
    "store_name": "全聯福利中心信義店",
    "date": "2026-02-26",
    "items": [
      {
        "name": "統一科學麵",
        "unit_price": 15,
        "quantity": 3,
        "subtotal": 45
      },
      {
        "name": "光泉鮮奶 936ml",
        "unit_price": 89,
        "quantity": 1,
        "subtotal": 89
      }
    ],
    "total": 134,
    "tax": null,
    "category": "食",
    "confidence": "HIGH",
    "partial_failure_fields": []
  },
  "error": null,
  "meta": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "engine_used": "GEMINI_PRIMARY",
    "processing_time_ms": 3241,
    "completed_at": "2026-02-26T10:00:03Z"
  }
}
```

**部分辨識成功回應：`206 Partial Content`**

```json
{
  "status": "partial",
  "data": {
    "store_name": "全聯福利中心",
    "date": null,
    "items": [],
    "total": 134,
    "tax": null,
    "category": "食",
    "confidence": "LOW",
    "partial_failure_fields": ["date", "items"]
  },
  "error": null,
  "meta": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "engine_used": "PADDLEOCR_FALLBACK"
  }
}
```

**辨識失敗回應：`200 OK`**（任務存在，但辨識失敗）

```json
{
  "status": "error",
  "data": null,
  "error": {
    "code": "NO_TEXT_DETECTED | ALL_ENGINES_FAILED",
    "message": "無法從圖片中辨識發票資訊，請重新拍攝",
    "retryable": true
  },
  "meta": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "engine_used": "PADDLEOCR_FALLBACK"
  }
}
```

**任務不存在：`404 Not Found`**

```json
{
  "status": "error",
  "data": null,
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "找不到此辨識任務，任務可能已過期",
    "retryable": false
  },
  "meta": null
}
```

---

## 端點 3：服務健康狀態

### `GET /health`

查詢後端服務狀態、額度使用量與佇列深度。

**回應：`200 OK`**

```json
{
  "status": "healthy",
  "data": {
    "queue_depth": 0,
    "queue_max": 100,
    "used_today": 15,
    "daily_limit": 1500,
    "rpm_used": 1,
    "rpm_limit": 15,
    "active_engine": "GEMINI_PRIMARY",
    "reset_at_utc": "2026-02-27T00:00:00Z"
  },
  "error": null,
  "meta": {
    "uptime_seconds": 3600,
    "timestamp": "2026-02-26T10:00:00Z"
  }
}
```

---

## Flutter 端整合契約

Phase 1 `UploadQueueService` 呼叫後端時須遵循：

1. **輪詢間隔**：每 3 秒查詢一次 `GET /invoices/{task_id}`，最多重試 20 次（60 秒逾時）
2. **重試條件**：`error.retryable == true` → 加入 Hive 佇列，待網路恢復後重試
3. **成功條件**：`status == "success"` 或 `status == "partial"` → 傳遞 `data` 至 Phase 3 儲存
4. **圖片刪除**：收到 `status == "success"` 後，Flutter 端從 Hive 佇列移除並刪除本機暫存圖片

---

## 錯誤碼完整對照

| 錯誤碼 | HTTP | retryable | Flutter 建議行為 |
|--------|------|-----------|----------------|
| `INVALID_FORMAT` | 400 | false | 提示使用者重新拍攝 |
| `IMAGE_TOO_SMALL` | 400 | false | 提示使用者重新拍攝（更清晰） |
| `IMAGE_TOO_LARGE` | 413 | false | 壓縮後重試 |
| `DUPLICATE_IMAGE` | 409 | false | 顯示現有辨識結果 |
| `NO_TEXT_DETECTED` | 422 | false | 提示重新拍攝 |
| `PARTIAL_RECOGNITION` | 206 | false | 顯示部分結果，提示確認 |
| `QUEUE_FULL` | 503 | true | 加入本機佇列，等待 30s 重試 |
| `ALL_ENGINES_FAILED` | 503 | true | 加入本機佇列，等待 5min 重試 |
| `TASK_NOT_FOUND` | 404 | false | 重新上傳 |
| `RATE_LIMITED` | 429 | true | 等待 `retry_after_seconds` 後重試 |
