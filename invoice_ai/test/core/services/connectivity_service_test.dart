import 'package:flutter_test/flutter_test.dart';
import 'package:invoice_ai/core/services/connectivity_service.dart';

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
  });

  group('ConnectivityService', () {
    test('onConnectivityChanged is a Stream<bool>', () {
      final service = ConnectivityService();
      expect(service.onConnectivityChanged, isA<Stream<bool>>());
    });

    // isOnline requires the connectivity_plus platform channel which is not
    // available in unit tests. Verified on-device per quickstart.md §4.
  });
}
