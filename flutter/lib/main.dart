// Eva — toolchain + design-foundation smoke screen.
//
// This is NOT the real UI. It exists only to prove the Flutter toolchain works
// and that the design-system foundation (lib/eva_tokens.dart, lib/eva_theme.dart)
// compiles and renders: the Catppuccin Macchiato palette, the mauve accent, Eva's
// serif `evaVoice` face, the avatar asset, and the google_fonts font path.
// The actual screens (Chat / Presence / Notebook / Settings) come next.

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'eva_tokens.dart';
import 'eva_theme.dart';

void main() => runApp(const EvaSmokeApp());

class EvaSmokeApp extends StatelessWidget {
  const EvaSmokeApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Resolve the design system's font family names (Lexend / Newsreader /
    // JetBrains Mono) through google_fonts so the verbatim foundation files can
    // reference them by name without bundling the proprietary Lucida Sans.
    final base = EvaTheme.dark;
    final theme = base.copyWith(
      textTheme: GoogleFonts.lexendTextTheme(base.textTheme),
    );

    return MaterialApp(
      title: 'Eva',
      debugShowCheckedModeBanner: false,
      theme: theme,
      home: const _SmokeScreen(),
    );
  }
}

class _SmokeScreen extends StatelessWidget {
  const _SmokeScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: EvaLayout.contentMax),
          child: Padding(
            padding: const EdgeInsets.all(EvaSpace.s6),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Avatar asset + presence glow proves asset bundling works.
                Container(
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    boxShadow: EvaShadows.glowAccent,
                  ),
                  child: const CircleAvatar(
                    radius: 40,
                    backgroundColor: EvaColors.surfaceCard,
                    backgroundImage: AssetImage('assets/eva.webp'),
                  ),
                ),
                const SizedBox(height: EvaSpace.s5),
                // Eva's serif voice, with a stage direction the way the persona speaks.
                Text(
                  '*glances up* …Oh. You actually got the toolchain working.',
                  style: GoogleFonts.newsreader(
                    textStyle: evaVoice(EvaType.lg, italic: true),
                  ),
                ),
                const SizedBox(height: EvaSpace.s3),
                Text(
                  'Catppuccin Macchiato · mauve accent · serif voice — foundation renders.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: EvaSpace.s6),
                Wrap(
                  spacing: EvaSpace.s3,
                  runSpacing: EvaSpace.s3,
                  children: [
                    ElevatedButton(
                      onPressed: () {},
                      child: const Text('Primary (mauve)'),
                    ),
                    OutlinedButton(onPressed: () {}, child: const Text('Ghost')),
                    // "Remembered" affordance uses the reserved green.
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: EvaSpace.s3,
                        vertical: EvaSpace.s2,
                      ),
                      decoration: BoxDecoration(
                        color: EvaColors.rememberedSoft,
                        borderRadius: BorderRadius.circular(EvaRadii.pill),
                        border: Border.all(color: EvaColors.remembered),
                      ),
                      child: Text(
                        'remembered',
                        style: TextStyle(
                          color: EvaColors.remembered,
                          fontFamily: EvaFonts.mono,
                          fontSize: EvaType.xs,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
