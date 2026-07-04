// ============================================================
// Eva — Design tokens, ported 1:1 from the CSS design system.
// Source of truth: tokens/colors.css, typography.css, spacing.css.
// Keep these values in sync with the CSS — they are the same scale.
//
// Canonical palette: official Catppuccin Macchiato.
// Mood: dark, dusky, warm-under-armor. "Her room at dusk."
// ============================================================

import 'package:flutter/widgets.dart';

/// Raw + semantic colors. Alpha-prefixed ARGB hex (0xAARRGGBB).
class EvaColors {
  EvaColors._();

  // ---- Raw Catppuccin Macchiato palette ----
  // Surfaces (dusk → near-black)
  static const crust = Color(0xFF181926);
  static const mantle = Color(0xFF1E2030);
  static const base = Color(0xFF24273A);
  static const surface0 = Color(0xFF363A4F);
  static const surface1 = Color(0xFF494D64);
  static const surface2 = Color(0xFF5B6078);
  static const overlay0 = Color(0xFF6E738D);
  static const overlay1 = Color(0xFF8087A2);
  static const overlay2 = Color(0xFF939AB7);

  // Text
  static const text = Color(0xFFCAD3F5);
  static const subtext1 = Color(0xFFB8C0E0);
  static const subtext0 = Color(0xFFA5ADCB);

  // Accents
  static const rosewater = Color(0xFFF4DBD6);
  static const flamingo = Color(0xFFF0C6C6);
  static const pink = Color(0xFFF5BDE6);
  static const mauve = Color(0xFFC6A0F6);
  static const red = Color(0xFFED8796);
  static const maroon = Color(0xFFEE99A0);
  static const peach = Color(0xFFF5A97F);
  static const yellow = Color(0xFFEED49F);
  static const green = Color(0xFFA6DA95);
  static const teal = Color(0xFF8BD5CA);
  static const sky = Color(0xFF91D7E3);
  static const sapphire = Color(0xFF7DC4E4);
  static const blue = Color(0xFF8AADF4);
  static const lavender = Color(0xFFB7BDF8);

  // ---- Semantic surfaces ----
  static const bgApp = base; // the room
  static const bgSunken = crust; // deepest wells, scrim
  static const bgBar = mantle; // header / composer chrome
  static const surfaceCard = mantle; // raised panels, cards
  static const surfaceInset = surface0; // inputs, your message bubble
  static const surfaceHover = surface1; // hover fill
  static const surfaceLine = Color(0x14FFFFFF); // hairline on dark (white @ 8%)
  static const surfaceLineStrong = Color(0x24FFFFFF);

  // ---- Eva's voice surfaces ----
  static const evaBubble = Color(0xFF2A2D40); // her message ground
  static const evaBubbleLine = Color(0x12FFFFFF);
  static const youBubble = surface0; // your message ground

  // ---- Text roles ----
  static const textPrimary = text;
  static const textSecondary = subtext0;
  static const textMuted = overlay1; // timestamps, quiet meta
  static const textFaint = overlay0;
  static const textOnAccent = Color(0xFF1A1A2E); // dark ink on mauve/pink fills

  // ---- Accent roles (mauve leads — Eva's eyes) ----
  static const accent = mauve;
  static const accent2 = pink;
  static const accent3 = lavender;
  static const accentSoft = Color(0x1FC6A0F6); // mauve wash / focus ring fill
  static const accentLine = Color(0x4DC6A0F6);

  // ---- Status / meaning ----
  static const remembered = green; // "jots it down" — saved to memory
  static const rememberedSoft = Color(0x1AA6DA95);
  static const danger = red;
  static const dangerSoft = Color(0x1AED8796);
  static const warning = peach;
  static const info = sapphire;
  static const moodWarm = peach;
  static const moodCool = sapphire;

  // ---- Focus ----
  static const focusRing = mauve;
}

/// Font family names. Register the bundled faces in pubspec.yaml (see README).
class EvaFonts {
  EvaFonts._();

  /// UI / headers — warm humanist sans. Lexend is the cross-platform fallback.
  static const ui = 'LucidaSans';
  static const display = 'LucidaSans';

  /// Eva's messages & *stage-direction* asides — literary serif, often italic.
  static const voice = 'Newsreader';

  /// Mono / terminal accents.
  static const mono = 'JetBrainsMono';

  /// Fallback chain used when the bundled face is unavailable.
  static const uiFallback = <String>['Lexend'];
  static const voiceFallback = <String>['Georgia'];
  static const monoFallback = <String>['monospace'];
}

/// Type scale in logical px (CSS rem × 16). Use with EvaFonts + EvaWeights.
class EvaType {
  EvaType._();

  static const xs = 12.0; // timestamps, micro-meta
  static const sm = 13.0; // captions, system lines
  static const base = 15.0; // UI body
  static const md = 16.0; // message text
  static const lg = 18.0; // emphasis, list titles
  static const xl = 22.0; // section headers
  static const xxl = 28.0; // screen titles
  static const xxxl = 36.0; // display
  static const xxxxl = 48.0; // hero

  // Line heights (CSS unitless → Flutter `height` multiplier; same numbers)
  static const leadingTight = 1.15;
  static const leadingSnug = 1.3;
  static const leadingNormal = 1.5;
  static const leadingRelaxed = 1.65; // Eva's prose breathes a little

  // Tracking (CSS em → Flutter letterSpacing in px ≈ em × fontSize;
  // these are the em values — multiply by the glyph size at the call site).
  static const trackingTightEm = -0.02;
  static const trackingNormalEm = 0.0;
  static const trackingWideEm = 0.04;
  static const trackingCapsEm = 0.12; // eyebrow / all-caps labels
}

/// Font weights.
class EvaWeights {
  EvaWeights._();

  static const light = FontWeight.w300;
  static const regular = FontWeight.w400;
  static const medium = FontWeight.w500;
  static const semibold = FontWeight.w600;
  static const bold = FontWeight.w700;
}

/// Spacing scale (4px base) in logical px.
class EvaSpace {
  EvaSpace._();

  static const s0 = 0.0;
  static const s1 = 4.0;
  static const s2 = 8.0;
  static const s3 = 12.0;
  static const s4 = 16.0;
  static const s5 = 24.0;
  static const s6 = 32.0;
  static const s7 = 40.0;
  static const s8 = 48.0;
  static const s9 = 64.0;
}

/// Corner radii — soft edges everywhere.
class EvaRadii {
  EvaRadii._();

  static const xs = 6.0;
  static const sm = 10.0;
  static const md = 14.0; // default card / control
  static const lg = 18.0;
  static const xl = 24.0;
  static const bubble = 18.0; // chat bubble
  static const tail = 5.0; // the "tail" corner on a bubble
  static const pill = 999.0;

  // Convenience BorderRadius for chat bubbles, tail corner per side.
  static BorderRadius evaBubble() => const BorderRadius.only(
        topLeft: Radius.circular(bubble),
        topRight: Radius.circular(bubble),
        bottomRight: Radius.circular(bubble),
        bottomLeft: Radius.circular(tail), // tail bottom-left for Eva
      );
  static BorderRadius youBubble() => const BorderRadius.only(
        topLeft: Radius.circular(bubble),
        topRight: Radius.circular(bubble),
        bottomLeft: Radius.circular(bubble),
        bottomRight: Radius.circular(tail), // tail bottom-right for you
      );
}

/// Shadows — quiet, no hard black drops on dark.
class EvaShadows {
  EvaShadows._();

  static const sm = <BoxShadow>[
    BoxShadow(color: Color(0x47000000), offset: Offset(0, 1), blurRadius: 2),
  ];
  static const md = <BoxShadow>[
    BoxShadow(color: Color(0x57000000), offset: Offset(0, 6), blurRadius: 18),
  ];
  static const lg = <BoxShadow>[
    BoxShadow(color: Color(0x75000000), offset: Offset(0, 18), blurRadius: 48),
  ];
  static const pop = <BoxShadow>[
    BoxShadow(color: Color(0x80000000), offset: Offset(0, 12), blurRadius: 32),
  ];

  /// Eva's presence glow — faint mauve halo. Use sparingly (avatar / focus).
  static const glowAccent = <BoxShadow>[
    BoxShadow(color: EvaColors.accentLine, blurRadius: 0, spreadRadius: 1),
    BoxShadow(color: EvaColors.accent, blurRadius: 24, spreadRadius: -6),
  ];
  static const glowRemembered = <BoxShadow>[
    BoxShadow(color: EvaColors.remembered, blurRadius: 22, spreadRadius: -8),
  ];
}

/// Motion — unhurried, soft, never bouncy chrome.
class EvaMotion {
  EvaMotion._();

  // cubic-bezier(0.22, 1, 0.36, 1)
  static const easeOut = Cubic(0.22, 1, 0.36, 1);
  // cubic-bezier(0.4, 0, 0.2, 1)
  static const easeSoft = Cubic(0.4, 0, 0.2, 1);

  static const fast = Duration(milliseconds: 120);
  static const base = Duration(milliseconds: 220);
  static const slow = Duration(milliseconds: 420);
  static const breath = Duration(seconds: 4); // Eva's ambient presence pulse
}

/// Layout maxes / touch targets.
class EvaLayout {
  EvaLayout._();

  static const readingMaxCh = 46; // max bubble width ≈ 7–8 words/line
  static const contentMax = 760.0; // memory / settings column
  static const tapMin = 44.0; // minimum touch target
}
