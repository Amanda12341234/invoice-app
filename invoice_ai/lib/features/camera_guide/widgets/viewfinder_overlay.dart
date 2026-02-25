import 'package:flutter/material.dart';

/// Draws a rectangular viewfinder guide over the camera preview.
/// The border color reflects the current detection state:
///   - Grey  → detecting / no text
///   - Orange → text detected but blurry
///   - Green  → ready to capture
class ViewfinderOverlay extends StatelessWidget {
  final Color overlayColor;

  const ViewfinderOverlay({super.key, required this.overlayColor});

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        child: CustomPaint(
          painter: _ViewfinderPainter(color: overlayColor),
          child: const SizedBox.expand(),
        ),
      ),
    );
  }
}

class _ViewfinderPainter extends CustomPainter {
  final Color color;

  _ViewfinderPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0;

    // Darken the area outside the guide rectangle
    final dimPaint = Paint()
      ..color = Colors.black.withOpacity(0.4)
      ..style = PaintingStyle.fill;

    const margin = 32.0;
    const cornerLength = 24.0;

    final rect = Rect.fromLTWH(
      margin,
      size.height * 0.2,
      size.width - margin * 2,
      size.height * 0.55,
    );

    // Dim overlay (fullscreen minus guide rect)
    final fullPath = Path()..addRect(Rect.fromLTWH(0, 0, size.width, size.height));
    final holePath = Path()..addRect(rect);
    final dimPath = Path.combine(PathOperation.difference, fullPath, holePath);
    canvas.drawPath(dimPath, dimPaint);

    // Corner brackets
    final corners = [
      rect.topLeft,
      rect.topRight,
      rect.bottomLeft,
      rect.bottomRight,
    ];

    for (final corner in corners) {
      final isRight = corner.dx == rect.right;
      final isBottom = corner.dy == rect.bottom;

      canvas.drawLine(
        corner,
        Offset(corner.dx + (isRight ? -cornerLength : cornerLength), corner.dy),
        paint,
      );
      canvas.drawLine(
        corner,
        Offset(corner.dx, corner.dy + (isBottom ? -cornerLength : cornerLength)),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(_ViewfinderPainter oldDelegate) =>
      oldDelegate.color != color;
}
