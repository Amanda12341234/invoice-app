# UI 契約：001-invoice-camera-guide

**類型**：行動應用內部畫面契約（Mobile UI Contracts）
**日期**：2026-02-25

Phase 1 為純前端功能（無後端 API），契約定義各畫面間的導航與資料交換介面。

---

## 契約 1：HomeScreen → CameraScreen 導航

**觸發條件**：使用者點擊主頁的「掃描發票」按鈕

**輸入（HomeScreen 傳遞）**：無

**輸出（CameraScreen 初始狀態）**：
- 相機初始化並開啟預覽
- DetectionState = `{ hasText: false, isSharp: false, warningMessage: null }`
- 取景框顯示（預設顏色：待機灰）

---

## 契約 2：CameraScreen 內部狀態機

**相機偵測結果（每幀更新）**：

```
輸入：CameraImage (幀資料)
輸出：DetectionState

DetectionState {
  hasText: bool          // 文字面積 ≥ 15% 且信心值 ≥ 0.7
  isSharp: bool          // Laplacian Variance ≥ 15
  warningMessage: String?  // null = 無警告
}
```

**UI 回應規則**：

| `hasText` | `isSharp` | 拍攝按鈕 | 取景框顏色 | 警告訊息 |
|-----------|-----------|---------|-----------|---------|
| false | any | 停用 | 灰色 | 「未偵測到發票文字，請調整位置」 |
| true | false | 停用 | 橘色 | 「畫面模糊，請保持手機穩定」 |
| true | true | **啟用** | **綠色** | 無 |

---

## 契約 3：CameraScreen → ConfirmScreen 導航

**觸發條件**：使用者點擊已啟用的拍攝按鈕

**輸入（CameraScreen 傳遞）**：
```
CaptureResult {
  filePath: String   // 圖片本機暫存路徑
  capturedAt: DateTime
}
```

**ConfirmScreen 顯示**：
- 拍攝圖片預覽（全螢幕）
- 兩個操作按鈕：「確認送出」、「重新拍攝」

---

## 契約 4：ConfirmScreen 操作結果

### 4a. 使用者選擇「確認送出」

**有網路時**：
```
輸出 → UploadQueue.addToQueue(filePath)
     → 狀態立即設為 uploading
     → 觸發上傳流程（Phase 2 範疇）
     → 導航回 HomeScreen
     → HomeScreen badge 更新（若上傳中）
```

**無網路時**：
```
輸出 → UploadQueue.addToQueue(filePath)
     → 狀態設為 pending
     → 顯示 Toast：「已儲存，網路恢復後自動上傳」
     → 導航回 HomeScreen
     → HomeScreen badge 顯示待上傳數量
```

### 4b. 使用者選擇「重新拍攝」

```
輸出 → 刪除 filePath 指向的暫存圖片
     → 導航回 CameraScreen（清除 DetectionState）
```

---

## 契約 5：UploadQueue → HomeScreen Badge 更新

**觸發條件**：UploadQueueProvider 的 `pendingCount` 變更

**輸出介面**：
```
UploadQueueProvider {
  pendingCount: int    // 0 時不顯示 badge；> 0 時顯示數字 badge
}
```

**Badge 顯示規則**：
- `pendingCount == 0`：不顯示 badge
- `1 ≤ pendingCount ≤ 99`：顯示數字
- `pendingCount > 99`：顯示「99+」

---

## 契約 6：網路恢復自動上傳觸發

**觸發條件**：`connectivity_plus` 偵測到網路恢復（`ConnectivityResult.mobile` 或 `wifi`）

**行為**：
```
UploadQueueService.processQueue()
  → 取得所有 pending 且 retryCount < 3 的項目
  → 依建立時間（FIFO）依序上傳
  → 上傳成功：刪除 Hive 記錄 + 刪除本機圖片
  → 上傳失敗：retryCount++；≥ 3 時設為 failed
  → 完成後更新 UploadQueueProvider.pendingCount
```

**通知（上傳完成後）**：
```
若成功上傳 N 筆：
  顯示通知：「{N} 張發票已完成上傳，請至記帳頁查看結果」
```

---

## 契約 7：儲存空間不足錯誤

**觸發條件**：`addToQueue` 或拍攝儲存時本機空間不足

**輸出**：
```
ErrorResult {
  code: "STORAGE_FULL"
  message: "儲存空間不足，無法儲存離線快照"
  action: SHOW_DIALOG  // 顯示對話框，引導使用者清理空間
}
```
