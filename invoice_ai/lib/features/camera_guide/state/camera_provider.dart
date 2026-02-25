import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../models/detection_state.dart';
import '../services/blur_detection_service.dart';
import '../services/ml_kit_service.dart';
import '../../../core/utils/file_utils.dart' as file_utils;

/// Manages camera controller lifecycle and frame-by-frame detection state.
class CameraProvider extends ChangeNotifier {
  final MlKitService _mlKitService;
  final BlurDetectionService _blurService;

  CameraController? _controller;
  DetectionState _detectionState = DetectionState(hasText: false, isSharp: true);
  bool _isInitialized = false;
  bool _isCapturing = false;

  CameraProvider({
    required MlKitService mlKitService,
    BlurDetectionService? blurDetectionService,
  })  : _mlKitService = mlKitService,
        _blurService = blurDetectionService ?? BlurDetectionService();

  CameraController? get controller => _controller;
  DetectionState get detectionState => _detectionState;
  bool get isInitialized => _isInitialized;
  bool get isCapturing => _isCapturing;

  /// Initialize camera and start detection loop.
  Future<void> initialize(List<CameraDescription> cameras) async {
    if (cameras.isEmpty) return;

    _controller = CameraController(
      cameras.first,
      ResolutionPreset.high,
      enableAudio: false,
    );

    await _controller!.initialize();
    _isInitialized = true;
    notifyListeners();

    startDetectionLoop();
  }

  /// Start frame-by-frame detection loop using [imageStream].
  void startDetectionLoop() {
    _controller?.startImageStream((CameraImage frame) async {
      final isSharp = !_blurService.isBlurry(frame);
      final hasText = await _mlKitService.hasText(frame);
      updateDetection(hasText: hasText, isSharp: isSharp);
    });
  }

  /// Update detection state and notify listeners.
  void updateDetection({required bool hasText, required bool isSharp}) {
    _detectionState = DetectionState(hasText: hasText, isSharp: isSharp);
    notifyListeners();
  }

  /// Capture the current frame and return the temp file path.
  Future<String?> captureImage() async {
    if (_controller == null || !_isInitialized || _isCapturing) return null;
    _isCapturing = true;
    notifyListeners();

    try {
      await _controller!.stopImageStream();
      final path = await file_utils.getInvoiceTempPath();
      final xFile = await _controller!.takePicture();
      // Move file to our managed temp path
      await xFile.saveTo(path);
      return path;
    } catch (_) {
      return null;
    } finally {
      _isCapturing = false;
      notifyListeners();
    }
  }

  @override
  Future<void> dispose() async {
    await _controller?.stopImageStream();
    await _controller?.dispose();
    await _mlKitService.dispose();
    super.dispose();
  }
}
