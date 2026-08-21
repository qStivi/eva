// PushService — background push notifications for job completions (research
// jobs, later other async work) via UnifiedPush. Android-only: the desktop
// and web builds just skip initialization silently.
//
// Architecture: our self-hosted ntfy (ntfy.qstivi.com) doubles as the
// UnifiedPush *distributor* — install the ntfy Android app once, log it into
// ntfy.qstivi.com, and it registers a fresh per-app endpoint URL with our own
// server (no Google/Firebase, no external push service). This app is the
// UnifiedPush *application*: it asks whatever distributor is installed for an
// endpoint, then hands that endpoint to eva-task-runner (via the eva.qstivi.com
// tunnel, Access-gated the same way chat already is) so it knows where to push
// "your research job finished" notifications. See eva-task-runner/runner.py's
// /push/register.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'package:unifiedpush/unifiedpush.dart';

import '../config/eva_settings.dart';

/// Fixed base for reaching the runner — it's loopback-only on the host, only
/// reachable at all via the same public tunnel + Access gate as chat.
const String _kRunnerBase = 'https://eva.qstivi.com';
const String _kInstance = 'eva-jobs';

class PushService {
  PushService._();
  static final PushService instance = PushService._();

  final FlutterLocalNotificationsPlugin _notifications =
      FlutterLocalNotificationsPlugin();
  EvaSettings? _settings;
  bool _localNotifsReady = false;

  /// Registers UnifiedPush callbacks and asks for a distributor. Safe to call
  /// on any platform — it's a no-op off Android. Best-effort throughout: a
  /// user who hasn't installed a distributor (ntfy app) yet, or whose access
  /// token isn't set, just doesn't get push — chat still works either way.
  Future<void> init(EvaSettings settings) async {
    _settings = settings;
    if (kIsWeb || !Platform.isAndroid) return;

    await _initLocalNotifications();

    try {
      await UnifiedPush.initialize(
        onNewEndpoint: _onNewEndpoint,
        onRegistrationFailed: _onRegistrationFailed,
        onUnregistered: _onUnregistered,
        onMessage: _onMessage,
      );
      final ok = await UnifiedPush.tryUseCurrentOrDefaultDistributor();
      if (ok) {
        await UnifiedPush.register(instance: _kInstance);
      }
      // If no distributor is installed/selected, we just stay unregistered —
      // no crash, no nag. The user can install the ntfy app whenever they want
      // push and re-open Eva to pick it up (there's no "retry" trigger yet).
    } catch (e) {
      debugPrint('PushService: init failed (no push this session): $e');
    }
  }

  Future<void> _initLocalNotifications() async {
    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    await _notifications.initialize(
      const InitializationSettings(android: androidInit),
    );
    await _notifications
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();
    _localNotifsReady = true;
  }

  void _onNewEndpoint(PushEndpoint endpoint, String instance) {
    _postToRunner('/push/register', endpoint.url);
  }

  void _onRegistrationFailed(FailedReason reason, String instance) {
    debugPrint('PushService: registration failed ($reason) for $instance');
  }

  void _onUnregistered(String instance) {
    // We don't track the last endpoint URL client-side, so there's nothing to
    // tell the runner to drop here — a stale registration just fails silently
    // next time a push goes out, which eva-task-runner already logs and skips.
  }

  Future<void> _onMessage(PushMessage message, String instance) async {
    if (!_localNotifsReady) return;
    final body = message.decrypted
        ? utf8.decode(message.content, allowMalformed: true)
        : '(could not decrypt push message)';
    await _notifications.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      'Eva',
      body,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'eva_jobs',
          'Background jobs',
          channelDescription: 'Research and other background job results',
          importance: Importance.high,
          priority: Priority.high,
        ),
      ),
    );
  }

  Future<void> _postToRunner(String path, String endpointUrl) async {
    final settings = _settings;
    if (settings == null) return;
    try {
      await http.post(
        Uri.parse('$_kRunnerBase$path'),
        headers: {
          'Content-Type': 'application/json',
          ...settings.accessHeaders,
        },
        body: jsonEncode({'endpoint': endpointUrl}),
      );
    } catch (e) {
      debugPrint('PushService: could not reach runner ($path): $e');
    }
  }
}
