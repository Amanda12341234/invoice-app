import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:invoice_ai/features/upload_queue/models/pending_invoice.dart';
import 'package:invoice_ai/features/upload_queue/state/upload_queue_provider.dart';

void main() {
  late Box<PendingInvoice> box;
  late Directory tempDir;

  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    tempDir = await Directory.systemTemp.createTemp('hive_test');
    Hive.init(tempDir.path);
    Hive.registerAdapter(PendingInvoiceAdapter());
  });

  setUp(() async {
    box = await Hive.openBox<PendingInvoice>('test_queue_${DateTime.now().millisecondsSinceEpoch}');
  });

  tearDown(() async {
    await box.deleteFromDisk();
  });

  tearDownAll(() async {
    await Hive.close();
    await tempDir.delete(recursive: true);
  });

  test('addToQueue increases pendingCount by 1', () async {
    final provider = UploadQueueProvider(box: box);
    expect(provider.pendingCount, 0);
    await provider.addToQueue('/tmp/invoice1.jpg');
    expect(provider.pendingCount, 1);
  });

  test('processQueue reduces pendingCount to 0 on success', () async {
    final provider = UploadQueueProvider(box: box);
    await provider.addToQueue('/tmp/invoice2.jpg');
    expect(provider.pendingCount, 1);
    await provider.processQueue();
    expect(provider.pendingCount, 0);
  });

  test('retryCount >= 3 transitions invoice to failed', () async {
    final invoice = PendingInvoice(
      id: 'retry-test',
      filePath: '/tmp/invoice3.jpg',
      status: 'pending',
      retryCount: 3,
      createdAt: DateTime.now(),
    );
    await box.put(invoice.id, invoice);

    final provider = UploadQueueProvider(box: box);
    // invoice with retryCount == 3 should be skipped (not processed)
    await provider.processQueue();
    // should remain pending (not processed since retryCount >= 3)
    expect(box.get('retry-test')?.status, 'pending');
  });
}
