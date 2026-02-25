import 'package:camera/camera.dart';

/// Abstract interface for on-device text detection.
/// Concrete implementations are injected so camera hardware can be mocked in tests.
abstract class MlKitService {
  /// Returns true if [frame] contains a sufficient area of text.
  ///
  /// Detection criteria:
  /// - Text block bounding-box area / frame area ≥ 15%
  /// - At least one text block with confidence ≥ 0.7
  Future<bool> hasText(CameraImage frame);

  /// Release any underlying resources.
  Future<void> dispose();
}
