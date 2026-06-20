// ResponsiveHome — picks the layout by window width: the landscape DesktopShell
// on wide screens, the phone AppShell (bottom nav) on narrow ones. Both reuse
// the same screens and the shared EvaController, so it's one codebase, not two
// apps. Eva's "remembered" toast is surfaced here once, above either layout.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_shell.dart';
import 'desktop_shell.dart';
import 'eva_theme.dart';
import 'eva_tokens.dart';
import 'state/eva_controller.dart';

/// Width at/above which Eva goes landscape (sidebar + chat) instead of phone.
const double kDesktopBreakpoint = 900;

class ResponsiveHome extends StatefulWidget {
  final EvaController controller;
  const ResponsiveHome({super.key, required this.controller});

  @override
  State<ResponsiveHome> createState() => _ResponsiveHomeState();
}

class _ResponsiveHomeState extends State<ResponsiveHome> {
  StreamSubscription<String>? _toastSub;

  @override
  void initState() {
    super.initState();
    _toastSub = widget.controller.toasts.listen(_showRememberedToast);
  }

  @override
  void dispose() {
    _toastSub?.cancel();
    super.dispose();
  }

  void _showRememberedToast(String text) {
    if (!mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    messenger.clearSnackBars();
    messenger.showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        backgroundColor: EvaColors.surfaceCard,
        elevation: 0,
        width: 360,
        duration: const Duration(seconds: 4),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(EvaRadii.md),
          side: const BorderSide(color: EvaColors.remembered),
        ),
        content: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.edit_outlined, size: 16, color: EvaColors.remembered),
            const SizedBox(width: EvaSpace.s2),
            Flexible(
              child: Text(
                text,
                style: GoogleFonts.newsreader(
                  textStyle: evaVoice(EvaType.base, italic: true, color: EvaColors.textPrimary),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth >= kDesktopBreakpoint) {
          return DesktopShell(controller: widget.controller);
        }
        return AppShell(controller: widget.controller);
      },
    );
  }
}
