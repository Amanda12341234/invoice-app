# 免費 AI 發票辨識 RAG 系統 — 開發指引

自動從所有功能計畫產生。最後更新：2026-02-25

## 使用中的技術

| 層級 | 工具／套件 | 版本 |
|------|-----------|------|
| 前端語言 | Dart / Flutter | 3.7 / 3.30.x |
| 相機取景 | camera | ^0.10.5 |
| 文字偵測 | google_mlkit_text_recognition | ^0.13.0 |
| 模糊偵測 | image (Laplacian Variance) | ^4.0.0 |
| 離線佇列 | hive + hive_flutter | ^2.2.0 / ^1.1.0 |
| 網路監聽 | connectivity_plus | ^6.0.0 |
| 狀態管理 | provider | ^7.0.0 |
| 權限管理 | permission_handler | ^11.0.0 |
| 後端（Phase 2） | FastAPI (Python 3.12) | 待定 |
| OCR / LLM（Phase 2） | Google Gemini 2.0 Flash | 免費額度 |
| 備援 OCR（Phase 2） | PaddleOCR | 開源 |
| 向量資料庫（Phase 3） | ChromaDB (Local Mode) | 開源 |
| AI 框架（Phase 4） | LangChain | 開源 |

## 專案結構

```text
lib/
├── features/
│   ├── camera_guide/              # Phase 1（當前）
│   │   ├── screens/
│   │   ├── widgets/
│   │   ├── models/
│   │   ├── state/
│   │   └── services/
│   └── upload_queue/              # Phase 1（佇列，跨 Phase 共用）
│       ├── widgets/
│       ├── models/
│       └── state/
├── core/
│   ├── services/
│   └── utils/
├── main.dart
└── app.dart

test/
├── features/
│   ├── camera_guide/
│   └── upload_queue/
└── core/

specs/                             # Speckit 文件
└── 001-invoice-camera-guide/
    ├── plan.md
    ├── spec.md
    ├── research.md
    ├── data-model.md
    ├── quickstart.md
    ├── contracts/
    └── tasks.md  (由 /speckit.tasks 產生)
```

## 指令

```bash
# Flutter 開發
flutter run                        # 在連接的裝置執行
flutter test                       # 執行所有測試
flutter build apk --release        # 建置 Android APK
flutter build ios --release        # 建置 iOS（需 macOS）

# 相依套件
flutter pub get                    # 安裝套件
flutter pub upgrade                # 升級套件（謹慎，檢查 changelog）

# Hive 程式碼產生（修改 @HiveType 後需執行）
flutter pub run build_runner build --delete-conflicting-outputs
```

## 程式碼風格

- 語言：Dart 3.7，啟用 null safety
- 使用 `sealed class` 表達結果型別（`DetectionResult`、`UploadResult`）
- 使用 `records` 取代單純傳遞資料的輕量 class
- 相機硬體相依一律透過抽象介面（`MlKitService`）隔離，以利測試
- 狀態管理：`ChangeNotifier` + `provider`，禁止直接在 Widget 中存取 Hive
- 圖片暫存路徑使用 `path_provider` 的 `getTemporaryDirectory()`

## 近期變更

- **001-invoice-camera-guide**（2026-02-25）：
  Phase 1 Camera 取景引導——相機取景框、ML Kit 文字偵測、
  Laplacian 模糊偵測、Hive 離線佇列、自動上傳觸發。

<!-- 手動新增區塊開始 -->
<!-- 手動新增區塊結束 -->
