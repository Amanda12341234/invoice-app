# 實作計畫：發票辨識 Phase 1 — Camera 取景引導

**分支**：`001-invoice-camera-guide` | **日期**：2026-02-25 | **規格**：[spec.md](./spec.md)
**輸入**：來自 `specs/001-invoice-camera-guide/spec.md` 的功能規格書

## 摘要

使用者透過手機相機對準實體發票，App 即時偵測文字區域與畫面清晰度，
在確認品質後拍攝並暫存圖片；無網路時圖片進入本機佇列，網路恢復後自動上傳至後端（Phase 2）。
技術方法：Flutter `camera` 套件取景 + `google_mlkit_text_recognition` 離線文字偵測 +
純 Dart Laplacian Variance 模糊偵測 + `hive` 持久化佇列 + `connectivity_plus` 自動上傳觸發。

## 技術背景

**語言／版本**：Dart 3.7 / Flutter 3.30.x（2026 年初當前穩定版）
**主要相依套件**：
- `camera ^0.10.5` — 即時取景框與幀存取
- `google_mlkit_text_recognition ^0.13.0` — 離線文字偵測（繁中原生支援）
- `image ^4.0.0` — Laplacian Variance 模糊偵測
- `hive ^2.2.0` + `hive_flutter ^1.1.0` — 佇列持久化
- `connectivity_plus ^6.0.0` — 網路狀態監聽
- `provider ^7.0.0` — 狀態管理
- `permission_handler ^11.0.0` — 相機與儲存權限

**儲存方案**：Hive（本機 NoSQL）+ 裝置檔案系統（圖片暫存）
**測試工具**：`flutter_test`（Unit + Widget tests）；相機相依以 fake service mock
**目標平台**：iOS 15+ / Android 7.0+（行動應用）
**效能目標**：取景框顯示 ≤ 1 秒；模糊/文字偵測警告 ≤ 2 秒；UI 維持 60 FPS
**限制條件**：完全離線可用（Phase 1 無後端呼叫）；零額外雲端費用
**規模範圍**：單人個人使用；佇列預期 1-50 筆

## 憲章審查

*關卡：第 0 階段研究前通過。第 1 階段設計後重新審查。*

| 原則 | 狀態 | 說明 |
|------|------|------|
| **一、功能優先交付** | ✅ 通過 | 所有任務均對應 FR-001～009；無額外工程 |
| **二、零成本技術堆疊** | ✅ 通過 | Flutter + ML Kit On-Device + Hive 均為免費開源 |
| **三、測試覆蓋門檻** | ✅ 通過 | `CameraProvider`、`BlurDetectionService`、`UploadQueueService` 均需單元測試；以 fake service 解決硬體相依 |
| **四、資料完整性與隱私** | ✅ 通過 | 圖片上傳成功後立即刪除（FR-006 確認流程設計）；Phase 1 無財務記錄 |
| **五、本地優先運算** | ✅ 通過 | 文字偵測、模糊偵測、佇列管理全部在裝置本地執行 |
| **六、API 節流保護** | N/A | Phase 1 無後端 API 呼叫 |
| **七、簡單性與 YAGNI** | ✅ 通過 | Provider（非 BLoC）、Hive（非 ObjectBox）、純 Dart 模糊偵測（非 FFI）；無推測性抽象 |

**憲章審查結論**：所有適用原則通過，無違規需記錄於複雜度追蹤表。

## 專案結構

### 文件（本功能）

```text
specs/001-invoice-camera-guide/
├── plan.md              ← 本文件
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── mobile-ui-contracts.md
├── checklists/
│   └── requirements.md
└── tasks.md             ← 由 /speckit.tasks 產生
```

### 原始碼（儲存庫根目錄）

```text
lib/
├── features/
│   ├── camera_guide/              # Phase 1 主要功能
│   │   ├── screens/
│   │   │   ├── camera_screen.dart
│   │   │   └── confirm_screen.dart
│   │   ├── widgets/
│   │   │   ├── viewfinder_overlay.dart   # 取景框 + 顏色回饋
│   │   │   └── capture_button.dart
│   │   ├── models/
│   │   │   └── detection_state.dart      # 瞬態，不持久化
│   │   ├── state/
│   │   │   └── camera_provider.dart      # ChangeNotifier
│   │   └── services/
│   │       ├── ml_kit_service.dart       # 抽象介面（可 mock）
│   │       ├── real_ml_kit_service.dart
│   │       └── blur_detection_service.dart
│   └── upload_queue/              # 跨 Phase 共用
│       ├── widgets/
│       │   └── queue_badge.dart          # 主頁 badge
│       ├── models/
│       │   └── pending_invoice.dart      # Hive 物件
│       └── state/
│           └── upload_queue_provider.dart
├── core/
│   ├── services/
│   │   └── connectivity_service.dart    # 網路監聽
│   └── utils/
│       └── file_utils.dart              # 暫存路徑管理
├── main.dart
└── app.dart

test/
├── features/
│   ├── camera_guide/
│   │   ├── state/camera_provider_test.dart
│   │   └── services/blur_detection_service_test.dart
│   └── upload_queue/
│       ├── state/upload_queue_provider_test.dart
│       └── models/pending_invoice_test.dart
└── core/
    └── services/connectivity_service_test.dart
```

**結構決策**：採用功能導向結構（Feature-Based）。
`camera_guide/` 封裝 Phase 1 所有相關程式碼；
`upload_queue/` 獨立為跨功能模組（Phase 2 上傳邏輯將在此擴充）；
`core/` 放置跨 Phase 共用工具。

## 複雜度追蹤

> 憲章審查無違規，本表無需填寫。
