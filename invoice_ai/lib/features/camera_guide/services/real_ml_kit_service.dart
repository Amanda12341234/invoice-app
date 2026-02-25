import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';

import 'ml_kit_service.dart';

/// On-device implementation using Google ML Kit Text Recognition.
/// Frame analysis is throttled to every 3rd frame to keep the UI at 60 FPS.
class RealMlKitService implements MlKitService {
  final TextRecognizer _recognizer =
      TextRecognizer(script: TextRecognitionScript.chinese);

  static const double _textAreaThreshold = 0.15;
  int _frameCounter = 0;
  bool _processing = false;
  bool? _lastResult;

  @override
  Future<bool> hasText(CameraImage frame) async {
    // Throttle: analyse every 3rd frame
    _frameCounter++;
    if (_frameCounter % 3 != 0) {
      return _lastResult ?? false;
    }

    // Skip if previous analysis is still in-flight
    if (_processing) return _lastResult ?? false;
    _processing = true;

    try {
      final inputImage = _convertToInputImage(frame);
      if (inputImage == null) {
        _lastResult = false;
        return false;
      }

      final recognised = await _recognizer.processImage(inputImage);

      final frameArea = frame.width.toDouble() * frame.height.toDouble();
      double textArea = 0;

      for (final block in recognised.blocks) {
        final box = block.boundingBox;
        textArea += box.width * box.height;
      }

      final ratio = frameArea > 0 ? textArea / frameArea : 0.0;
      _lastResult = ratio >= _textAreaThreshold;
      return _lastResult!;
    } catch (_) {
      _lastResult = false;
      return false;
    } finally {
      _processing = false;
    }
  }

  InputImage? _convertToInputImage(CameraImage frame) {
    try {
      final allBytes = BytesBuilder();
      for (final plane in frame.planes) {
        allBytes.add(plane.bytes);
      }
      final bytes = allBytes.toBytes();

      final metadata = InputImageMetadata(
        size: Size(frame.width.toDouble(), frame.height.toDouble()),
        rotation: InputImageRotation.rotation0deg,
        format: InputImageFormat.nv21,
        bytesPerRow: frame.planes.first.bytesPerRow,
      );

      return InputImage.fromBytes(bytes: bytes, metadata: metadata);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<void> dispose() async {
    await _recognizer.close();
  }
}
