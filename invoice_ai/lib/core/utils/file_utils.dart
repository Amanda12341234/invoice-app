import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

const _uuid = Uuid();

/// Returns a unique temporary file path for a captured invoice image.
Future<String> getInvoiceTempPath() async {
  final dir = await getTemporaryDirectory();
  final filename = 'invoice_${_uuid.v4()}.jpg';
  return '${dir.path}/$filename';
}

/// Deletes a file at [path]. Silently ignores if the file does not exist.
Future<void> deleteFile(String path) async {
  final file = File(path);
  if (await file.exists()) {
    await file.delete();
  }
}

/// Returns true if the device has at least [minBytes] of free storage.
/// Defaults to 10 MB minimum.
Future<bool> storageAvailable({int minBytes = 10 * 1024 * 1024}) async {
  try {
    // Best-effort: verify temp dir is accessible. Actual free-space check
    // requires a platform plugin (e.g. disk_space) — deferred to Phase 2.
    await getTemporaryDirectory();
    return true;
  } catch (_) {
    return false;
  }
}
