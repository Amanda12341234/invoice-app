import 'package:flutter/material.dart';
import 'package:hive/hive.dart';
import 'package:uuid/uuid.dart';

import '../models/pending_invoice.dart';
import '../../../core/services/connectivity_service.dart';

/// Manages the offline upload queue backed by Hive.
class UploadQueueProvider extends ChangeNotifier {
  final Box<PendingInvoice> _box;
  final ConnectivityService _connectivity;
  bool _isProcessing = false;

  UploadQueueProvider({
    required Box<PendingInvoice> box,
    ConnectivityService? connectivity,
  })  : _box = box,
        _connectivity = connectivity ?? ConnectivityService() {
    _connectivity.onConnectivityChanged.listen((isOnline) {
      if (isOnline) processQueue();
    });
  }

  int get pendingCount =>
      _box.values.where((i) => i.status == 'pending').length;

  List<PendingInvoice> get allInvoices => _box.values.toList();

  /// Add a new invoice image path to the queue (status: pending).
  Future<void> addToQueue(String filePath) async {
    final invoice = PendingInvoice(
      id: const Uuid().v4(),
      filePath: filePath,
      status: 'pending',
      retryCount: 0,
      createdAt: DateTime.now(),
    );
    await _box.put(invoice.id, invoice);
    notifyListeners();
  }

  /// Process all pending invoices. Phase 1: simulates upload success.
  Future<void> processQueue() async {
    if (_isProcessing) return;
    _isProcessing = true;

    final pending = _box.values
        .where((i) => i.status == 'pending' && i.retryCount < 3)
        .toList();

    for (final invoice in pending) {
      try {
        invoice.transitionTo('uploading');
        await _box.put(invoice.id, invoice);
        notifyListeners();

        // Phase 1: simulate successful upload
        await Future.delayed(const Duration(milliseconds: 500));

        invoice.transitionTo('uploaded');
        await _box.put(invoice.id, invoice);
        notifyListeners();
      } catch (_) {
        invoice.retryCount += 1;
        if (invoice.retryCount >= 3) {
          invoice.transitionTo('failed');
        } else {
          invoice.transitionTo('pending');
        }
        await _box.put(invoice.id, invoice);
        notifyListeners();
      }
    }

    _isProcessing = false;
    notifyListeners();
  }

  /// Load persisted queue on app start and auto-process if online.
  Future<void> loadQueue() async {
    notifyListeners();
    final isOnline = await _connectivity.isOnline;
    if (isOnline) processQueue();
  }
}
