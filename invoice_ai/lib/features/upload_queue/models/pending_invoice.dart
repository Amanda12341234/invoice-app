import 'package:hive/hive.dart';

part 'pending_invoice.g.dart';

/// Valid upload status values for PendingInvoice.
class UploadStatus {
  static const String pending = 'pending';
  static const String uploading = 'uploading';
  static const String uploaded = 'uploaded';
  static const String failed = 'failed';
}

@HiveType(typeId: 1)
class PendingInvoice extends HiveObject {
  @HiveField(0)
  late String id;

  @HiveField(1)
  late String filePath;

  @HiveField(2)
  late String status; // pending | uploading | uploaded | failed

  @HiveField(3)
  late int retryCount;

  @HiveField(4)
  late DateTime createdAt;

  @HiveField(5)
  String? errorMessage;

  PendingInvoice({
    required this.id,
    required this.filePath,
    this.status = UploadStatus.pending,
    this.retryCount = 0,
    required this.createdAt,
    this.errorMessage,
  });

  bool get canRetry => retryCount < 3;

  bool get isPending =>
      status == UploadStatus.pending || status == UploadStatus.failed;

  /// Transition to a new status. Enforces valid state machine transitions.
  void transitionTo(String newStatus) {
    final valid = _validTransitions[status] ?? {};
    if (!valid.contains(newStatus)) {
      throw StateError(
        'Invalid status transition: $status → $newStatus',
      );
    }
    status = newStatus;
  }

  static const Map<String, Set<String>> _validTransitions = {
    UploadStatus.pending: {UploadStatus.uploading},
    UploadStatus.uploading: {UploadStatus.uploaded, UploadStatus.failed},
    UploadStatus.failed: {UploadStatus.uploading},
    UploadStatus.uploaded: {},
  };
}
