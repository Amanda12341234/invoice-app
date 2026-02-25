import 'dart:typed_data';
import 'package:camera/camera.dart';

/// Detects image blur using Laplacian Variance on the Y (luma) plane.
///
/// Threshold: Variance < 15 → blurry.
/// Runs synchronously on a small sampled region for performance.
class BlurDetectionService {
  static const double _blurThreshold = 15.0;

  /// Returns true if [frame] is considered blurry.
  bool isBlurry(CameraImage frame) {
    final variance = _laplacianVariance(frame.planes[0].bytes,
        frame.width, frame.height);
    return variance < _blurThreshold;
  }

  /// Calculates the Laplacian variance of the Y-plane data.
  /// Samples a central 100x100 region to keep computation fast.
  double _laplacianVariance(Uint8List yPlane, int width, int height) {
    // Sample a central region to avoid edge effects and reduce computation
    const sampleSize = 100;
    final startX = (width - sampleSize) ~/ 2;
    final startY = (height - sampleSize) ~/ 2;

    if (startX < 1 || startY < 1 ||
        startX + sampleSize >= width - 1 ||
        startY + sampleSize >= height - 1) {
      // Frame too small to sample; assume not blurry
      return 100.0;
    }

    final List<double> laplacianValues = [];

    for (int y = startY; y < startY + sampleSize; y++) {
      for (int x = startX; x < startX + sampleSize; x++) {
        final idx = y * width + x;
        // 4-neighbour discrete Laplacian kernel
        final center = yPlane[idx].toDouble();
        final top = yPlane[(y - 1) * width + x].toDouble();
        final bottom = yPlane[(y + 1) * width + x].toDouble();
        final left = yPlane[y * width + (x - 1)].toDouble();
        final right = yPlane[y * width + (x + 1)].toDouble();

        final lap = (4 * center) - top - bottom - left - right;
        laplacianValues.add(lap);
      }
    }

    if (laplacianValues.isEmpty) return 100.0;

    // Variance of Laplacian values
    final mean = laplacianValues.reduce((a, b) => a + b) / laplacianValues.length;
    final variance = laplacianValues
            .map((v) => (v - mean) * (v - mean))
            .reduce((a, b) => a + b) /
        laplacianValues.length;

    return variance;
  }
}
