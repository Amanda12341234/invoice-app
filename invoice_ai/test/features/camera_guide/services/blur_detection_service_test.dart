import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:camera/camera.dart';
import 'package:invoice_ai/features/camera_guide/services/blur_detection_service.dart';

// ignore: deprecated_member_use
CameraImage _fakeCameraImage(Uint8List yPlaneBytes, int width, int height) {
  // ignore: deprecated_member_use
  return CameraImage.fromPlatformData({
    'format': 35, // android YUV_420_888
    'width': width,
    'height': height,
    'lensAperture': null,
    'sensorExposureTime': null,
    'sensorSensitivity': null,
    'planes': [
      {
        'bytes': yPlaneBytes,
        'bytesPerPixel': 1,
        'bytesPerRow': width,
        'height': height,
        'width': width,
      }
    ],
  });
}

void main() {
  group('BlurDetectionService', () {
    late BlurDetectionService service;

    setUp(() {
      service = BlurDetectionService();
    });

    test('sharp image (high variance) returns false (not blurry)', () {
      // Create a checkerboard pattern → high Laplacian variance
      final bytes = Uint8List(200 * 200);
      for (int y = 0; y < 200; y++) {
        for (int x = 0; x < 200; x++) {
          bytes[y * 200 + x] = ((x + y) % 2 == 0) ? 255 : 0;
        }
      }
      final frame = _fakeCameraImage(bytes, 200, 200);
      expect(service.isBlurry(frame), isFalse);
    });

    test('uniform (blurry) image returns true (is blurry)', () {
      // All pixels the same value → zero Laplacian variance
      final bytes = Uint8List(200 * 200)..fillRange(0, 200 * 200, 128);
      final frame = _fakeCameraImage(bytes, 200, 200);
      expect(service.isBlurry(frame), isTrue);
    });

    test('very small frame falls back to not blurry', () {
      // Frame smaller than sample region → assumes not blurry (safe fallback)
      final bytes = Uint8List(50 * 50)..fillRange(0, 50 * 50, 128);
      final frame = _fakeCameraImage(bytes, 50, 50);
      expect(service.isBlurry(frame), isFalse);
    });
  });
}
