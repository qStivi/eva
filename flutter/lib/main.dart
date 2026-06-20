// Eva — character-first AI companion. Web-first Flutter app (native mobile
// later). Wires the Catppuccin Macchiato design system (eva_theme / eva_tokens)
// onto the app, hosts the shared EvaController, and opens on the app shell.

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'eva_theme.dart';
import 'responsive_home.dart';
import 'state/eva_controller.dart';

void main() => runApp(const EvaApp());

class EvaApp extends StatefulWidget {
  const EvaApp({super.key});

  @override
  State<EvaApp> createState() => _EvaAppState();
}

class _EvaAppState extends State<EvaApp> {
  final EvaController _controller = EvaController();

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
