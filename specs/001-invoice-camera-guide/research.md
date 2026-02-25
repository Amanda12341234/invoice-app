# 研究報告：001-invoice-camera-guide

**階段**：Phase 0 — 技術決策研究
**日期**：2026-02-25
**對應規格**：[spec.md](./spec.md)

---

## 決策 1：相機套件選型

**決定**：使用官方 `camera` 套件（Flutter 官方維護）

**理由**：
- 提供即時相機串流與逐幀（frame-by-frame）存取能力，`image_picker` 僅能呼叫系統相機 UI，無法在取景框上自訂疊加層。
- 支援 30+ FPS 即時預覽，可直接在 Flutter Widget 層繪製引導框（取景框）。
- 完整控制對焦、曝光、縮放，符合 FR-003 的即時偵測需求。

**考慮過的替代方案**：
- `image_picker`：拒絕。無法實現即時取景框，只能開啟系統相機。
- `mobile_scanner`：拒絕。為條碼/QR Code 設計，對發票過於複雜。
- `camerawesome`：拒絕。第三方維護，穩定性低於官方套件。

---

## 決策 2：文字偵測方案

**決定**：使用 `google_mlkit_text_recognition`，以 Dart Isolate 進行非阻塞幀處理

**理由**：
- 完全離線、在裝置本地執行，符合憲章原則五（本地優先運算）。
- 原生支援繁體中文，適合台灣統一發票/收據場景。
- 以獨立 Isolate 處理相機幀（每 2-3 幀採樣一次），主執行緒維持 60 FPS UI 渲染不受影響。
- 文字區域覆蓋率閾值：文字面積佔畫面 ≥ 15% 且信心值 ≥ 0.7 時，判定為「偵測成功」。

**考慮過的替代方案**：
- `google_mlkit_object_detection`：拒絕。物件偵測延遲較高，不如文字識別精確。
- 純本地 OCR（如 Tesseract）：拒絕。繁中支援不穩定，初始化時間長。

---

## 決策 3：模糊偵測方案

**決定**：使用 `image` 套件實作純 Dart Laplacian Variance 演算法（Phase 1）

**理由**：
- Laplacian Variance 為業界標準模糊偵測演算法（Instagram、Snapchat 均採用）。
- 純 Dart 實作（無 FFI/native 相依），降低初期複雜度，符合憲章原則七（簡單性）。
- 處理時間約 50-100ms（現代手機），足以在拍攝前給予即時回饋。
- 閾值設定：Laplacian Variance < 15 時顯示模糊警告並停用拍攝按鈕。

**考慮過的替代方案**：
- Dart FFI + OpenCV (`cv` 套件)：準確率更高（95%），但需 native binary（增加 2-3 MB）。保留為 Phase 1.x 升級路徑，當純 Dart 方案在低階手機效能不足時切換。
- ML Kit Object Detection 邊框偵測：拒絕。設計目的不同，延遲過高。

---

## 決策 4：離線佇列持久化方案

**決定**：使用 `hive` 套件儲存 `PendingInvoice` 物件，`connectivity_plus` 監聽網路狀態

**理由**：
- Hive 為 Flutter-native 的 NoSQL 儲存，直接儲存 Dart 物件，無需 SQL schema。
- 僅需 1 個資料模型、4 個操作（新增/讀取/更新狀態/刪除），複雜度最低。
- 跨 App 重啟持久化，符合 FR-007 的離線快照需求。
- `connectivity_plus` 提供網路狀態串流，網路恢復時自動觸發上傳。

**考慮過的替代方案**：
- `shared_preferences`：拒絕。僅支援 K-V 字串，無法有效儲存重試次數、狀態等複合欄位。
- `sqflite`：拒絕。對 10-100 筆記錄過於複雜，需 schema migration。
- `ObjectBox`：拒絕。效能優秀但依賴 native binary，對 Phase 1 規模過剩。

---

## 決策 5：狀態管理方案

**決定**：使用 `provider` 套件（`ChangeNotifier` 模式）

**理由**：
- 針對 1 人開發、10 個畫面的副業專案，Provider 提供足夠能力（70% 簡易度、95% 功能覆蓋）。
- `CameraProvider`（管理偵測狀態）+ `UploadQueueProvider`（管理佇列計數）兩個 Provider 即可覆蓋 Phase 1 所有狀態。
- `ChangeNotifier` 易於在測試中 mock，符合憲章原則三（測試覆蓋）。

**考慮過的替代方案**：
- `riverpod`：拒絕。架構更佳但學習成本高 20%，現階段無明顯收益。
- `BLoC`：拒絕。為多人團隊、50+ 畫面設計，過度工程。
- `setState`：拒絕。佇列狀態需跨多個畫面共享，散落的 setState 難以維護。

---

## 決策 6：專案目錄結構

**決定**：功能導向結構（Feature-Based）

**理由**：
- 4 個 Phase 天然對應 4 個功能目錄（`camera_guide`、`invoice_detail`、`vector_db`、`rag_chat`）。
- 1 個開發者無需 Clean Architecture 的跨層抽象；所有相關程式碼集中於同一功能目錄。
- 可在 `core/` 放置跨功能共用模組（HTTP client、Hive 初始化）。

**考慮過的替代方案**：
- 層導向（models/ services/ screens/）：拒絕。需在 3 個目錄間來回跳轉，增加認知負擔。
- Clean Architecture（entity/usecase/repository）：拒絕。對個人專案完全過度設計。

---

## 決策 7：Flutter 版本

**決定**：Flutter 3.30.x（Dart 3.7.x），2026 年初當前穩定版

**理由**：
- Dart 3.7 的 Sealed Classes 可用於相機偵測結果的型別安全表達（`DetectionResult`）。
- Records 語法減少簡單回傳值的 class 定義樣板。
- 所有選用套件（`camera`、`google_mlkit_text_recognition`、`hive`）均相容 Flutter 3.30。

**pubspec.yaml 環境設定**：
```yaml
environment:
  sdk: '>=3.6.0 <4.0.0'
  flutter: '>=3.24.0'
```

---

## 技術決策摘要表

| 決策 | 選定方案 | 主要套件 | 憲章關卡 |
|------|---------|---------|---------|
| 相機取景 | `camera` 套件 | camera ^0.10.5 | 原則二、七 |
| 文字偵測 | ML Kit + Isolate | google_mlkit_text_recognition ^0.13.0 | 原則二、五 |
| 模糊偵測 | Laplacian Variance（純 Dart） | image ^4.0.0 | 原則五、七 |
| 離線佇列 | Hive | hive ^2.2.0、connectivity_plus ^6.0.0 | 原則四 |
| 狀態管理 | Provider | provider ^7.0.0 | 原則七 |
| 目錄結構 | Feature-Based | — | 原則七 |
| Flutter 版本 | 3.30 / Dart 3.7 | — | 原則二 |
