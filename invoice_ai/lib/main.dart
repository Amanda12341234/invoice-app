import 'package:flutter/material.dart';
import 'package:hive_flutter/hive_flutter.dart';

import 'features/upload_queue/models/pending_invoice.dart';
import 'app.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Hive for offline queue persistence
  await Hive.initFlutter();
  Hive.registerAdapter(PendingInvoiceAdapter());
  await Hive.openBox<PendingInvoice>('invoice_queue');

  runApp(const InvoiceApp());
}
