import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/camera_provider.dart';
import '../services/real_ml_kit_service.dart';
import '../widgets/capture_button.dart';
import '../widgets/viewfinder_overlay.dart';

/// Camera preview screen with viewfinder guide and capture button.
class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  late CameraProvider _cameraProvider;

  @override
  void initState() {
    super.initState();
    _cameraProvider = CameraProvider(mlKitService: RealMlKitService());
    _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    if (mounted) {
      await _cameraProvider.initialize(cameras);
    }
  }

  Future<void> _onCapture() async {
    final path = await _cameraProvider.captureImage();
    if (!mounted || path == null) return;
    Navigator.pushNamed(context, '/confirm', arguments: path);
  }

  @override
  void dispose() {
    _cameraProvider.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: _cameraProvider,
      child: Scaffold(
        backgroundColor: Colors.black,
        appBar: AppBar(
          backgroundColor: Colors.black,
          foregroundColor: Colors.white,
          title: const Text('掃描發票'),
        ),
        body: Consumer<CameraProvider>(
          builder: (context, provider, _) {
            if (!provider.isInitialized || provider.controller == null) {
              return const Center(
                child: CircularProgressIndicator(color: Colors.white),
              );
            }

            return Stack(
              fit: StackFit.expand,
              children: [
                CameraPreview(provider.controller!),
                ViewfinderOverlay(
                  overlayColor: provider.detectionState.overlayColor,
                ),
                // Warning message area
                Positioned(
                  bottom: 120,
                  left: 32,
                  right: 32,
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 300),
                    child: provider.detectionState.warningMessage != null
                        ? Container(
                            key: ValueKey(provider.detectionState.warningMessage),
                            padding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 8),
                            decoration: BoxDecoration(
                              color: Colors.orange.withOpacity(0.85),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              provider.detectionState.warningMessage!,
                              textAlign: TextAlign.center,
                              style: const TextStyle(
                                  color: Colors.white, fontSize: 14),
                            ),
                          )
                        : const SizedBox.shrink(key: ValueKey('empty')),
                  ),
                ),
                // Capture button
                Positioned(
                  bottom: 40,
                  left: 0,
                  right: 0,
                  child: Center(
                    child: CaptureButton(
                      enabled: provider.detectionState.canCapture &&
                          !provider.isCapturing,
                      onPressed: _onCapture,
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
