import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/utils/file_utils.dart' as file_utils;
import '../../../core/services/connectivity_service.dart';
import '../../upload_queue/state/upload_queue_provider.dart';

/// Shows the captured image for confirmation before queueing for upload.
class ConfirmScreen extends StatelessWidget {
  const ConfirmScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final imagePath = ModalRoute.of(context)!.settings.arguments as String;

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: const Text('確認發票'),
      ),
      body: Column(
        children: [
          Expanded(
            child: Image.file(
              File(imagePath),
              fit: BoxFit.contain,
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(24.0),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: Colors.white),
                    ),
                    onPressed: () async {
                      await file_utils.deleteFile(imagePath);
                      if (context.mounted) Navigator.pop(context);
                    },
                    child: const Text('重新拍攝'),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () => _onConfirm(context, imagePath),
                    child: const Text('確認送出'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _onConfirm(BuildContext context, String imagePath) async {
    // Check storage before queueing
    final hasStorage = await file_utils.storageAvailable();
    if (!context.mounted) return;

    if (!hasStorage) {
      await showDialog(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text('儲存空間不足'),
          content: const Text('儲存空間不足，無法儲存離線快照'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('確定'),
            ),
          ],
        ),
      );
      return;
    }

    final queueProvider =
        Provider.of<UploadQueueProvider>(context, listen: false);
    final connectivity = ConnectivityService();
    final isOnline = await connectivity.isOnline;

    await queueProvider.addToQueue(imagePath);

    if (!context.mounted) return;

    if (isOnline) {
      queueProvider.processQueue();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('已儲存，網路恢復後自動上傳')),
      );
    }

    Navigator.popUntil(context, ModalRoute.withName('/'));
  }
}
