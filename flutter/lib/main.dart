// Eva — character-first AI companion. Web-first Flutter app (native mobile
// later). Loads the persisted server config, wires a live EvaController to the
// Letta backend, and opens on the responsive app shell. Tests construct EvaApp
// with no controller, which yields a mock (offline) controller.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import 'api/letta_api.dart';
import 'config/eva_settings.dart';
import 'eva_theme.dart';
import 'responsive_home.dart';
import 'services/push_service.dart';
import 'state/eva_controller.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Lock phones to portrait (landscape on a phone is cramped and off-brand);
  // leave tablets and desktop free to rotate. A no-op on web/desktop.
  final view = WidgetsBinding.instance.platformDispatcher.views.first;
  final shortestSide = (view.physicalSize / view.devicePixelRatio).shortestSide;
  if (shortestSide > 0 && shortestSide < 600) {
    SystemChrome.setPreferredOrientations(const [
      DeviceOrientation.portraitUp,
      DeviceOrientation.portraitDown,
    ]);
  }

  final settings = await EvaSettings.load();
  final controller = EvaController(
    api: LettaApi(settings.serverUrl, authHeaders: settings.accessHeaders),
    settings: settings,
  );
  // Connect in the background — the UI shows "connecting" then live/mock.
  controller.connect();
  // Same: registers for push in the background, no-op off Android and never
  // blocks first paint (a missing distributor or dead runner just means no
  // push this session, not a startup failure).
  PushService.instance.init(settings);

  runApp(EvaApp(controller: controller));
}

class EvaApp extends StatefulWidget {
  /// A live controller (from main). When null — e.g. in tests — a mock,
  /// offline controller is created instead.
  final EvaController? controller;
  const EvaApp({super.key, this.controller});

  @override
  State<EvaApp> createState() => _EvaAppState();
}

class _EvaAppState extends State<EvaApp> {
  late final EvaController _controller = widget.controller ?? EvaController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Resolve the design system's UI font (Lexend) via google_fonts so the
    // foundation can name families without bundling the proprietary Lucida Sans.
    final base = EvaTheme.dark;
    final theme = base.copyWith(
      textTheme: GoogleFonts.lexendTextTheme(base.textTheme),
    );

    return MaterialApp(
      title: 'Eva',
      debugShowCheckedModeBanner: false,
      theme: theme,
      home: ResponsiveHome(controller: _controller),
    );
  }
}
