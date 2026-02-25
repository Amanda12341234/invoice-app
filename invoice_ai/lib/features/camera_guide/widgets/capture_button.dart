import 'package:flutter/material.dart';

/// Circular capture button.
/// Appears semi-transparent grey when [enabled] is false,
/// and the primary theme color when [enabled] is true.
class CaptureButton extends StatelessWidget {
  final bool enabled;
  final VoidCallback? onPressed;

  const CaptureButton({
    super.key,
    required this.enabled,
    this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    final color = enabled
        ? Theme.of(context).colorScheme.primary
        : Colors.white.withOpacity(0.4);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      width: 72,
      height: 72,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color,
        border: Border.all(color: Colors.white, width: 3),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: enabled ? onPressed : null,
          child: const Icon(Icons.camera_alt, color: Colors.white, size: 32),
        ),
      ),
    );
  }
}
