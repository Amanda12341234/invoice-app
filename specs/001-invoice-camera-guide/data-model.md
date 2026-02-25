# 資料模型：001-invoice-camera-guide

**階段**：Phase 1 — 設計
**日期**：2026-02-25
**對應規格**：[spec.md](./spec.md)

---

## 實體：PendingInvoice（待上傳發票快照）

代表一次拍攝動作的本機記錄，從拍攝完成至後端確認上傳成功為止存在於本機佇列。

### 欄位定義

| 欄位名稱 | 型別 | 必填 | 說明 |
|---------|------|------|------|
| `id` | String (UUID) | ✓ | 唯一識別碼，建立時產生 |
| `filePath` | String | ✓ | 圖片在裝置上的本機絕對路徑 |
| `status` | UploadStatus (enum) | ✓ | 當前上傳狀態（見下方） |
| `retryCount` | int | ✓ | 已重試次數，預設 0，上限 3 |
| `createdAt` | DateTime | ✓ | 拍攝時間戳記（UTC） |
| `errorMessage` | String? | — | 最後一次失敗的錯誤訊息，選填 |

### 狀態機：UploadStatus

```
pending → uploading → uploaded (終態，記錄刪除)
         ↘ failed   (重試次數 ≥ 3)
pending ← failed    (使用者手動重試)
```

| 狀態值 | 說明 |
|--------|------|
| `pending` | 等待上傳，網路可用時自動處理 |
| `uploading` | 上傳中，避免重複送出 |
| `uploaded` | 上傳成功，記錄由佇列移除 |
| `failed` | 重試超過 3 次，需使用者手動確認重試 |

### 驗證規則

- `filePath` 必須指向一個存在於裝置上的可讀檔案。
- `retryCount` 不得超過 3；達到上限時狀態自動設為 `failed`。
- `createdAt` 一旦設定後不可修改。
- 狀態轉換必須遵循上方狀態機，禁止跨狀態跳轉（例：`pending` → `uploaded`）。

---

## 實體：UploadQueue（上傳佇列）

代表所有 `PendingInvoice` 的集合，提供佇列操作的統一入口。

### 行為定義

| 操作 | 輸入 | 輸出 | 說明 |
|------|------|------|------|
| `addToQueue` | `filePath: String` | `PendingInvoice` | 建立 `pending` 狀態記錄並持久化 |
| `getPendingItems` | — | `List<PendingInvoice>` | 取得所有 `pending` 或 `failed` 且重試次數 < 3 的項目 |
| `updateStatus` | `id, UploadStatus, errorMessage?` | `void` | 更新狀態，同時持久化 |
| `removeItem` | `id: String` | `void` | 刪除已成功上傳的記錄 |
| `pendingCount` | — | `int` | 取得待上傳數量（供 UI badge 顯示） |

### 持久化

- 所有 `PendingInvoice` 物件持久化至 Hive Box（`invoice_queue`）。
- App 啟動時自動從 Hive 重新載入佇列狀態，確保跨重啟不遺失。

---

## 實體：DetectionState（相機偵測狀態）

代表相機即時分析的當前結果，為瞬態（transient）資料，不持久化。

### 欄位定義

| 欄位名稱 | 型別 | 說明 |
|---------|------|------|
| `hasText` | bool | 目前畫面是否偵測到文字區域（覆蓋率 ≥ 15%） |
| `isSharp` | bool | 畫面是否清晰（Laplacian Variance ≥ 15） |
| `warningMessage` | String? | 需顯示的警告文字，`null` 表示無警告 |

### 衍生屬性（不儲存）

```
canCapture = hasText && isSharp
overlayColor = canCapture ? green : (hasText ? orange : grey)
```

---

## 實體關係圖

```
UploadQueue
    │ contains (1..*)
    ▼
PendingInvoice
    │ filePath points to
    ▼
[裝置本機圖片檔案]
    │ (上傳成功後由後端處理，Phase 2 範疇)
    ▼
[後端 Phase 2 接收]

DetectionState  ── (transient, drives UI only) ──→ CameraScreen
```

---

## 儲存邊界說明

| 資料 | 儲存位置 | 生命週期 |
|------|---------|---------|
| `PendingInvoice` | Hive（本機） | 建立至上傳成功或使用者手動清除 |
| 圖片檔案（.jpg） | 裝置本機暫存目錄 | 上傳成功後由 App **立即刪除**（憲章原則四） |
| `DetectionState` | 記憶體（Provider） | 相機頁面存在期間 |
