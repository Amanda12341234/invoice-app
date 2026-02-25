import 'package:flutter_test/flutter_test.dart';
import 'package:invoice_ai/features/upload_queue/models/pending_invoice.dart';

void main() {
  group('PendingInvoice — state transitions', () {
    PendingInvoice _make() => PendingInvoice(
          id: 'test-id',
          filePath: '/tmp/test.jpg',
          status: 'pending',
          retryCount: 0,
          createdAt: DateTime(2024, 1, 1),
        );

    test('pending → uploading → uploaded is valid', () {
      final invoice = _make();
      invoice.transitionTo('uploading');
      expect(invoice.status, 'uploading');
      invoice.transitionTo('uploaded');
      expect(invoice.status, 'uploaded');
    });

    test('pending → uploading → failed is valid', () {
      final invoice = _make();
      invoice.transitionTo('uploading');
      invoice.transitionTo('failed');
      expect(invoice.status, 'failed');
    });

    test('pending → uploaded directly throws StateError', () {
      final invoice = _make();
      expect(() => invoice.transitionTo('uploaded'), throwsStateError);
    });

    test('uploaded → pending throws StateError', () {
      final invoice = _make();
      invoice.transitionTo('uploading');
      invoice.transitionTo('uploaded');
      expect(() => invoice.transitionTo('pending'), throwsStateError);
    });
  });
}
