import 'package:flutter/material.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:provider/provider.dart';

import 'features/camera_guide/screens/camera_screen.dart';
import 'features/camera_guide/screens/confirm_screen.dart';
import 'features/upload_queue/models/pending_invoice.dart';
import 'features/upload_queue/state/upload_queue_provider.dart';
import 'features/upload_queue/widgets/queue_badge.dart';

class InvoiceApp extends StatelessWidget {
  const InvoiceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (_) => UploadQueueProvider(
            box: Hive.box<PendingInvoice>('invoice_queue'),
          )..loadQueue(),
        ),
      ],
      child: MaterialApp(
        title: '發票辨識',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
          useMaterial3: true,
        ),
        initialRoute: '/',
        routes: {
          '/': (context) => const HomeScreen(),
          '/camera': (context) => const CameraScreen(),
          '/confirm': (context) => const ConfirmScreen(),
        },
      ),
    );
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('發票辨識'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Center(
        child: Consumer<UploadQueueProvider>(
          builder: (context, queueProvider, _) {
            return Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                QueueBadge(
                  count: queueProvider.pendingCount,
                  child: ElevatedButton.icon(
                    onPressed: () => Navigator.pushNamed(context, '/camera'),
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('掃描發票'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 32,
                        vertical: 16,
                      ),
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
