---

description: "發票辨識 Phase 1 — Camera 取景引導 任務清單"
---

# 任務清單：發票辨識 Phase 1 — Camera 取景引導

**輸入**：設計文件來自 `specs/001-invoice-camera-guide/`
**前置條件**：plan.md ✅、spec.md ✅、research.md ✅、data-model.md ✅、contracts/ ✅

**測試**：本規格書未明確要求 TDD，測試任務已包含於各故事以確保憲章原則三（測試覆蓋門檻）合規。

**組織方式**：任務依使用者故事分組，各故事可獨立實作與驗證。

## 格式：`[ID] [P?] [Story?] 說明`

- **[P]**：可平行執行（不同檔案，無相依關係）
- **[Story]**：此任務所屬的使用者故事（US1、US2、US3）
- 所有任務均包含精確的檔案路徑

## 路徑慣例

- Flutter 功能模組：`lib/features/<feature>/`
- 核心共用：`lib/core/`
- 測試：`test/features/<feature>/` 或 `test/core/`

---

## 第一階段：初始設定（共用基礎設施）

**目的**：Flutter 專案初始化、套件設定、目錄結構建立

- [x] T001 建立 Flutter 專案（`flutter create invoice_ai --org com.invoice`）並確認執行
- [x] T002 在 `pubspec.yaml` 加入所有 Phase 1 相依套件：`camera ^0.10.5`、`google_mlkit_text_recognition ^0.13.0`、`image ^4.0.0`、`hive ^2.2.0`、`hive_flutter ^1.1.0`、`connectivity_plus ^6.0.0`、`provider ^6.1.5`、`permission_handler ^11.0.0`、`path_provider ^2.1.0`、`uuid ^4.0.0`；`dev_dependencies` 加入 `hive_generator ^2.0.0`、`build_runner ^2.4.0`
- [x] T003 [P] 依 plan.md 建立完整目錄結構：`lib/features/camera_guide/{screens,widgets,models,state,services}/`、`lib/features/upload_queue/{widgets,models,state}/`、`lib/core/{services,utils}/`、`test/features/{camera_guide,upload_queue}/`、`test/core/`
- [x] T004 [P] 設定 iOS 權限：在 `ios/Runner/Info.plist` 加入 `NSCameraUsageDescription`、`NSPhotoLibraryUsageDescription`
- [x] T005 [P] 設定 Android 權限：在 `android/app/src/main/AndroidManifest.xml` 加入 `CAMERA`、`WRITE_EXTERNAL_STORAGE`（API < 29）、`READ_MEDIA_IMAGES`（API ≥ 33）
- [x] T006 [P] 建立 `lib/app.dart`（`MaterialApp` 設定、路由定義：`/` → `HomeScreen`、`/camera` → `CameraScreen`、`/confirm` → `ConfirmScreen`）與 `lib/main.dart`（Hive 初始化、Provider 掛載、App 進入點）

---

## 第二階段：基礎建設（阻塞性前置條件）

**目的**：所有使用者故事依賴的核心基礎設施——必須在任何故事實作前完成

**⚠️ 關鍵**：此階段完成前不得開始第三、四、五階段

- [x] T007 建立 `lib/features/upload_queue/models/pending_invoice.dart`：`@HiveType(typeId: 1)` 的 `PendingInvoice` 類別，欄位：`id`（String）、`filePath`（String）、`status`（String：pending/uploading/uploaded/failed）、`retryCount`（int）、`createdAt`（DateTime）、`errorMessage`（String?）
- [x] T008 執行 Hive 程式碼產生：`flutter pub run build_runner build --delete-conflicting-outputs`（產生 `pending_invoice.g.dart`）
- [x] T009 [P] 建立 `lib/core/utils/file_utils.dart`：提供 `getInvoiceTempPath()` 回傳暫存圖片路徑（使用 `getTemporaryDirectory()`），`deleteFile(String path)` 刪除檔案，`storageAvailable()` 確認可用空間
- [x] T010 [P] 建立 `lib/features/camera_guide/models/detection_state.dart`：`DetectionState` sealed class，包含 `hasText`（bool）、`isSharp`（bool）衍生屬性 `canCapture`（bool）、`warningMessage`（String?）、`overlayColor`（Color）
- [x] T011 建立 `lib/features/camera_guide/services/ml_kit_service.dart`：定義抽象介面 `MlKitService`（`Future<bool> hasText(CameraImage frame)`），以及 `lib/features/camera_guide/services/real_ml_kit_service.dart` 實作：以 Isolate + `TextRecognizer` 分析幀，文字面積比 ≥ 15% 且信心值 ≥ 0.7 時回傳 `true`，每 3 幀分析一次（節流）
- [x] T012 [P] 建立 `lib/features/camera_guide/services/blur_detection_service.dart`：以 `image` 套件對相機幀的 Y 平面計算 Laplacian Variance；Variance < 15 時判定為模糊；提供 `bool isBlurry(CameraImage frame)` 方法
- [x] T013 [P] 建立 `lib/core/services/connectivity_service.dart`：封裝 `connectivity_plus`，提供 `bool get isOnline` 及 `Stream<bool> onConnectivityChanged` 串流

**檢查點**：基礎設施就緒——模型、服務介面、工具類別均已就位，第三階段可開始

---

## 第三階段：使用者故事 1 - 自動對焦並確認發票清晰可辨（優先順序：P1）🎯 MVP

**目標**：使用者可以打開相機、對準發票、看到取景框引導、點擊拍攝、進入確認頁

**獨立測試**：執行 `flutter test test/features/camera_guide/`；手動依 `quickstart.md` 驗證 1 節

### 使用者故事 1 的測試

- [x] T014 [P] [US1] 建立 `test/features/camera_guide/services/blur_detection_service_test.dart`：單元測試 `BlurDetectionService`——清晰幀回傳 `false`（非模糊）、模糊幀回傳 `true`；使用合成的 Y 平面 byte array 模擬幀資料
- [x] T015 [P] [US1] 建立 `test/features/camera_guide/state/camera_provider_test.dart`：測試 `CameraProvider`——`updateDetection(hasText: true, isSharp: true)` 後 `canCapture` 為 `true`、`updateDetection(hasText: true, isSharp: false)` 後 `canCapture` 為 `false`；使用 `FakeMlKitService`

### 使用者故事 1 的實作

- [x] T016 [US1] 建立 `lib/features/camera_guide/state/camera_provider.dart`：`CameraProvider extends ChangeNotifier`，管理 `DetectionState`、相機控制器初始化（`CameraController`）、`startDetectionLoop()`（每幀呼叫 `MlKitService` + `BlurDetectionService` 並更新狀態）、`captureImage()` 回傳暫存路徑，依賴 T011、T012
- [x] T017 [P] [US1] 建立 `lib/features/camera_guide/widgets/viewfinder_overlay.dart`：以 `CustomPainter` 繪製取景矩形框，接受 `Color overlayColor` 參數（灰/橘/綠），帶平滑過渡動畫（AnimatedContainer，200ms）
- [x] T018 [P] [US1] 建立 `lib/features/camera_guide/widgets/capture_button.dart`：圓形拍攝按鈕，接受 `bool enabled` 與 `VoidCallback? onPressed`；`enabled = false` 時呈現半透明灰色，`enabled = true` 時呈現主色
- [x] T019 [US1] 建立 `lib/features/camera_guide/screens/camera_screen.dart`：整合 `CameraController`（`CameraPreview`）+ `ViewfinderOverlay`（疊加層）+ `CaptureButton`（底部中央）；Consumer 監聽 `CameraProvider`；相機頁面顯示後 ≤ 1 秒啟動預覽（SC-002）；依賴 T016、T017、T018
- [x] T020 [US1] 建立 `lib/features/camera_guide/screens/confirm_screen.dart`：顯示拍攝圖片預覽（`Image.file`）、「確認送出」按鈕（呼叫 `UploadQueueProvider.addToQueue`）、「重新拍攝」按鈕（刪除暫存圖片並 `Navigator.pop`）；依賴 T019
- [x] T021 [US1] 更新 `lib/app.dart`：將 `CameraProvider` 加入 `MultiProvider`；首頁加入「掃描發票」按鈕（點擊 → `/camera`），確保進入相機 ≤ 2 步（SC-001）

**檢查點**：使用者故事 1 完整可用——可開啟相機、看到引導框、拍攝、進入確認頁

---

## 第四階段：使用者故事 2 - 偵測模糊或無文字圖片並阻擋無效上傳（優先順序：P2）

**目標**：無文字或模糊場景時，拍攝按鈕停用並顯示具體警告文字

**獨立測試**：將鏡頭對準空白牆面確認按鈕停用；手動依 `quickstart.md` 驗證 2A、2B 節

### 使用者故事 2 的測試

- [x] T022 [P] [US2] 在 `test/features/camera_guide/state/camera_provider_test.dart` 補充：測試警告訊息邏輯——`hasText: false` → `warningMessage` 等於「未偵測到發票文字，請調整位置」；`hasText: true, isSharp: false` → `warningMessage` 等於「畫面模糊，請保持手機穩定」；`hasText: true, isSharp: true` → `warningMessage` 為 `null`

### 使用者故事 2 的實作

- [x] T023 [US2] 更新 `lib/features/camera_guide/models/detection_state.dart`：在 `DetectionState` 中補充 `warningMessage` 計算邏輯（`hasText == false` → 文字未偵測訊息；`isSharp == false` → 模糊訊息；兩者均成立 → `null`）
- [x] T024 [US2] 更新 `lib/features/camera_guide/screens/camera_screen.dart`：在 `CaptureButton` 上方加入警告文字區域（`AnimatedSwitcher` 控制淡入淡出）；當 `warningMessage != null` 時顯示黃色警告條；當偵測成功（`canCapture = true`）時警告條消失；2 秒內完成狀態切換（SC-003）；依賴 T023

**檢查點**：使用者故事 1 與 2 均可獨立運作——取景引導正常，品質過濾正常

---

## 第五階段：使用者故事 3 - 離線快照與自動排隊上傳（優先順序：P3）

**目標**：無網路時拍攝進入佇列；網路恢復後 30 秒內自動上傳；主頁顯示待上傳數

**獨立測試**：關閉網路 → 拍攝 → 確認 badge 顯示 1 → 恢復網路 → 確認 30 秒內 badge 歸零；手動依 `quickstart.md` 驗證 4、5 節

### 使用者故事 3 的測試

- [x] T025 [P] [US3] 建立 `test/features/upload_queue/state/upload_queue_provider_test.dart`：測試 `addToQueue` 後 `pendingCount` 增加 1；測試 `processQueue`（mock 上傳成功）後 `pendingCount` 減少；測試重試邏輯：`retryCount >= 3` 後狀態變為 `failed`
- [x] T026 [P] [US3] 建立 `test/features/upload_queue/models/pending_invoice_test.dart`：測試 `PendingInvoice` 狀態轉換合法性（pending → uploading → uploaded；pending → uploading → failed）；測試非法轉換（pending → uploaded 直接跳過）應丟出錯誤

### 使用者故事 3 的實作

- [x] T027 [US3] 建立 `lib/features/upload_queue/state/upload_queue_provider.dart`：`UploadQueueProvider extends ChangeNotifier`，管理 Hive Box（`invoice_queue`）；提供 `addToQueue(filePath)`、`processQueue()`（實際上傳留 Phase 2 介接，此階段模擬成功）、`pendingCount`（getter）、`loadQueue()`（App 啟動時呼叫）；網路恢復時監聽 `ConnectivityService` 自動觸發 `processQueue()`（SC-005：≤ 30 秒）；依賴 T007、T008、T013
- [x] T028 [P] [US3] 建立 `lib/features/upload_queue/widgets/queue_badge.dart`：`QueueBadge` Widget，接受 `int count`；`count == 0` 時不顯示；`count > 0` 時在按鈕右上角顯示紅色計數（最多顯示「99+」）
- [x] T029 [US3] 更新 `lib/features/camera_guide/screens/confirm_screen.dart` 的「確認送出」邏輯：有網路 → 呼叫 `addToQueue` 並立即觸發 `processQueue`；無網路 → 呼叫 `addToQueue`（pending 狀態）並顯示 Toast「已儲存，網路恢復後自動上傳」；依賴 T027
- [x] T030 [US3] 更新 `lib/app.dart` 的首頁：將 `UploadQueueProvider` 加入 `MultiProvider`，「掃描發票」按鈕加上 `QueueBadge`（Consumer 監聽 `pendingCount`）；依賴 T027、T028

**儲存空間錯誤處理**（FR-009，邊界情況）：
- [x] T031 [US3] 更新 `lib/features/camera_guide/screens/confirm_screen.dart`：在 `addToQueue` 前呼叫 `FileUtils.storageAvailable()`；不足時顯示 AlertDialog「儲存空間不足，無法儲存離線快照」（SC-006）；依賴 T009

**檢查點**：所有使用者故事均可獨立運作

---

## 第 N 階段：細化與跨切面關注點

**目的**：覆蓋所有故事的收尾改善

- [x] T032 [P] 建立 `test/core/services/connectivity_service_test.dart`：測試 `ConnectivityService.isOnline` 在 mock offline/online 下的正確回傳
- [x] T033 更新 `lib/main.dart` 加入 App 啟動時的佇列恢復：`UploadQueueProvider.loadQueue()` + 若網路可用則觸發 `processQueue()`（確保跨重啟持久化，SC-006）
- [x] T034 [P] 依 `quickstart.md` 所有驗證節點進行手動端對端測試（P1 正常拍攝 → P2 模糊偵測 → P3 離線佇列）
- [x] T035 [P] 建立 `README.md`：記錄 Phase 1 本機執行方式（`flutter run`、設備需求）與已知限制

---

## 相依關係與執行順序

### 階段相依

- **第一階段（初始設定）**：無相依，立即開始
- **第二階段（基礎建設）**：依賴第一階段完成——阻塞所有使用者故事
- **第三階段（US1）**：依賴第二階段完成
- **第四階段（US2）**：依賴第三階段（`camera_screen.dart` 需先存在）
- **第五階段（US3）**：依賴第二階段完成（可與第三階段平行，不同檔案）
- **第 N 階段（細化）**：依賴所有使用者故事完成

### 使用者故事相依

- **US1（P1）**：基礎建設後可開始；MVP 核心
- **US2（P2）**：US1 完成後開始（擴充 `camera_screen.dart`）
- **US3（P3）**：基礎建設後即可開始（與 US1 平行開發，不同模組）；`confirm_screen.dart` 整合依賴 US1

### 各使用者故事內部順序

- 測試先寫（T014、T015 先於 T016）
- 模型先於服務（T010 先於 T011）
- 服務先於畫面（T016 先於 T019）
- 核心畫面先於整合（T019 先於 T020）

### 平行機會

- 第一階段：T003、T004、T005、T006 可同時進行
- 第二階段：T009、T010、T012、T013 可與 T007→T008→T011 流程平行
- US1：T014、T015（測試）可與 T017、T018（Widget）平行
- US3：T025、T026（測試）可與 T028（`queue_badge.dart`）平行

---

## 平行範例：第二階段

```bash
# 同時啟動（不同檔案，無相依）：
任務：「建立 lib/core/utils/file_utils.dart」（T009）
任務：「建立 lib/features/camera_guide/models/detection_state.dart」（T010）
任務：「建立 lib/features/camera_guide/services/blur_detection_service.dart」（T012）
任務：「建立 lib/core/services/connectivity_service.dart」（T013）

# 依序執行（有相依）：
T007（PendingInvoice 類別）→ T008（build_runner 產生程式碼）→ T011（MlKitService 介面）
```

---

## 實作策略

### MVP 優先（僅使用者故事 1）

1. 完成第一階段：初始設定（T001-T006）
2. 完成第二階段：基礎建設（T007-T013）——**關鍵，阻塞所有故事**
3. 完成第三階段：使用者故事 1（T014-T021）
4. **停止並驗證**：依 `quickstart.md` 驗證 1 節
5. 可展示 MVP：相機取景 + 拍攝確認流程完整運作

### 增量交付

1. 完成初始設定 + 基礎建設 → 基礎就緒
2. 新增 US1 → 手動驗證 → **MVP 展示**
3. 新增 US2 → 手動驗證 → 品質過濾完整
4. 新增 US3 → 手動驗證 → 離線功能完整
5. 細化 → Phase 1 完成，可進入 Phase 2

### 平行開發機會（若有第二開發者）

基礎建設完成後：
- 開發者 A：US1（相機取景、拍攝流程）
- 開發者 B：US3（Hive 佇列、網路監聽）——不同模組，無衝突

---

## 備注

- [P] = 不同檔案，無相依，可平行執行
- [US?] 標籤追溯任務至使用者故事
- T008（build_runner）必須在 T007 完成後執行，且每次修改 `@HiveType` 後需重新執行
- 實際上傳邏輯（HTTP 送至 FastAPI）為 Phase 2 範疇；Phase 1 的 `processQueue` 以模擬成功（`await Future.delayed`）替代
- 每個任務或邏輯群組完成後提交（git commit）
- 在任何**檢查點**停下來手動驗證，再繼續下一階段
