import 'package:flutter_test/flutter_test.dart';
import 'package:camera/camera.dart';
import 'package:invoice_ai/features/camera_guide/models/detection_state.dart';
import 'package:invoice_ai/features/camera_guide/state/camera_provider.dart';
import 'package:invoice_ai/features/camera_guide/services/ml_kit_service.dart';

/// Fake MlKitService for testing — always returns the configured value.
class FakeMlKitService implements MlKitService {
  bool _hasText;
  FakeMlKitService({bool hasText = false}) : _hasText = hasText;

  void setHasText(bool value) => _hasText = value;

  @override
  Future<bool> hasText(CameraImage frame) async => _hasText;

  @override
  Future<void> dispose() async {}
}

void main() {
  group('CameraProvider — DetectionState', () {
    test('updateDetection(hasText: true, isSharp: true) → canCapture is true',
        () {
      final provider = CameraProvider(mlKitService: FakeMlKitService());
      provider.updateDetection(hasText: true, isSharp: true);
      expect(provider.detectionState.canCapture, isTrue);
    });

    test('updateDetection(hasText: true, isSharp: false) → canCapture is false',
        () {
      final provider = CameraProvider(mlKitService: FakeMlKitService());
      provider.updateDetection(hasText: true, isSharp: false);
      expect(provider.detectionState.canCapture, isFalse);
    });

    test('updateDetection(hasText: false, isSharp: true) → canCapture is false',
        () {
      final provider = CameraProvider(mlKitService: FakeMlKitService());
      provider.updateDetection(hasText: false, isSharp: true);
      expect(provider.detectionState.canCapture, isFalse);
    });
  });

  group('CameraProvider — warningMessage (US2)', () {
    test('no text → warningMessage is "未偵測到發票文字，請調整位置"', () {
      final provider = CameraProvider(mlKitService: FakeMlKitService());
      provider.updateDetection(hasText: false, isSharp: true);
      expect(provider.detectionState.warningMessage,
          equals('未偵測到發票文字，請調整位置'));
    });

    test('blurry image → warningMessage is "畫面模糊，請保持手機穩定"', () {
      final provider = CameraProvider(mlKitService: FakeMlKitService());
      provider.updateDetection(hasText: true, isSharp: false);
      expect(provider.detectionState.warningMessage,
          equals('畫面模糊，請保持手機穩定'));
    });

    test('good detection → warningMessage is null', () {
      final provider = CameraProvider(mlKitService: FakeMlKitService());
      provider.updateDetection(hasText: true, isSharp: true);
      expect(provider.detectionState.warningMessage, isNull);
    });
  });

  group('CameraProvider — notifyListeners', () {
    test('updateDetection notifies listeners', () {
      final provider = CameraProvider(mlKitService: FakeMlKitService());
      int notified = 0;
      provider.addListener(() => notified++);
      provider.updateDetection(hasText: true, isSharp: true);
      expect(notified, 1);
    });
  });
}
