import 'package:flutter/material.dart';

/// Represents the real-time camera detection result.
/// This is transient state — not persisted to disk.
class DetectionState {
  final bool hasText;
  final bool isSharp;

  const DetectionState({
    this.hasText = false,
    this.isSharp = false,
  });

  /// True when the user can safely tap the capture button.
  bool get canCapture => hasText && isSharp;

  /// Warning message to display to the user, or null when everything is OK.
  String? get warningMessage {
    if (!hasText) return '未偵測到發票文字，請調整位置';
    if (!isSharp) return '畫面模糊，請保持手機穩定';
    return null;
  }

  /// Overlay border color reflecting detection state.
  Color get overlayColor {
    if (canCapture) return Colors.green;
    if (hasText) return Colors.orange;
    return Colors.grey;
  }

  DetectionState copyWith({bool? hasText, bool? isSharp}) {
    return DetectionState(
      hasText: hasText ?? this.hasText,
      isSharp: isSharp ?? this.isSharp,
    );
  }
}
