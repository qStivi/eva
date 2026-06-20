// Eva — character-first AI companion. Web-first Flutter app (native mobile
// later). This entry wires the Catppuccin Macchiato design system (eva_theme /
// eva_tokens) onto the app and opens on the Chat screen — the heart of it.

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'eva_theme.dart';
import 'screens/chat_screen.dart';

void main() => runApp(const EvaApp());

class EvaApp extends StatelessWidget {
  const EvaApp({super.key});

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
      home: const ChatScreen(),
    );
  }
}
