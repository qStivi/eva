// ============================================================
// Eva — Flutter ThemeData built from the design tokens.
// A faithful starting point; tune component themes as screens land.
// ============================================================

import 'package:flutter/cupertino.dart' show CupertinoPageTransitionsBuilder;
import 'package:flutter/material.dart';
import 'eva_tokens.dart';

/// Helper: a TextStyle on the UI face.
TextStyle _ui(double size, FontWeight weight, {double? height, Color? color}) =>
    TextStyle(
      fontFamily: EvaFonts.ui,
      fontFamilyFallback: EvaFonts.uiFallback,
      fontSize: size,
      fontWeight: weight,
      height: height,
      color: color ?? EvaColors.textPrimary,
    );

/// Helper: a TextStyle on Eva's serif voice face.
TextStyle evaVoice(double size,
        {FontWeight weight = EvaWeights.regular,
        bool italic = false,
        double height = EvaType.leadingRelaxed,
        Color? color}) =>
    TextStyle(
      fontFamily: EvaFonts.voice,
      fontFamilyFallback: EvaFonts.voiceFallback,
      fontSize: size,
      fontWeight: weight,
      fontStyle: italic ? FontStyle.italic : FontStyle.normal,
      height: height,
      color: color ?? EvaColors.textPrimary,
    );

class EvaTheme {
  EvaTheme._();

  static ThemeData get dark {
    const scheme = ColorScheme.dark(
      brightness: Brightness.dark,
      primary: EvaColors.accent,
      onPrimary: EvaColors.textOnAccent,
      secondary: EvaColors.accent2,
      onSecondary: EvaColors.textOnAccent,
      tertiary: EvaColors.accent3,
      surface: EvaColors.surfaceCard,
      onSurface: EvaColors.textPrimary,
      error: EvaColors.danger,
      onError: EvaColors.textOnAccent,
      outline: EvaColors.surfaceLineStrong,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: scheme,
      scaffoldBackgroundColor: EvaColors.bgApp,
      canvasColor: EvaColors.bgApp,
      fontFamily: EvaFonts.ui,
      fontFamilyFallback: EvaFonts.uiFallback,
      splashFactory: NoSplash.splashFactory, // settles, never a hard flash

      textTheme: TextTheme(
        // Display / screen titles lean on the cozy display face, semibold, tight tracking.
        displayLarge: _ui(EvaType.xxxxl, EvaWeights.semibold,
            height: EvaType.leadingSnug),
        displayMedium: _ui(EvaType.xxxl, EvaWeights.semibold,
            height: EvaType.leadingSnug),
        headlineMedium: _ui(EvaType.xxl, EvaWeights.semibold,
            height: EvaType.leadingSnug),
        titleLarge:
            _ui(EvaType.xl, EvaWeights.semibold, height: EvaType.leadingSnug),
        titleMedium:
            _ui(EvaType.lg, EvaWeights.medium, height: EvaType.leadingNormal),
        bodyLarge:
            _ui(EvaType.md, EvaWeights.regular, height: EvaType.leadingNormal),
        bodyMedium: _ui(EvaType.base, EvaWeights.regular,
            height: EvaType.leadingNormal),
        bodySmall: _ui(EvaType.sm, EvaWeights.regular,
            height: EvaType.leadingNormal, color: EvaColors.textSecondary),
        labelSmall: _ui(EvaType.xs, EvaWeights.medium,
            color: EvaColors.textMuted),
      ),

      // Cards — raised mantle panels, soft md radius, quiet shadow.
      cardTheme: CardThemeData(
        color: EvaColors.surfaceCard,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(EvaRadii.md),
          side: const BorderSide(color: EvaColors.surfaceLine),
        ),
      ),

      // Primary action — mauve fill, dark ink, soft 14px corners.
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: EvaColors.accent,
          foregroundColor: EvaColors.textOnAccent,
          disabledBackgroundColor: EvaColors.accent.withValues(alpha: 0.5),
          elevation: 0,
          minimumSize: const Size(0, EvaLayout.tapMin),
          padding: const EdgeInsets.symmetric(
              horizontal: EvaSpace.s5, vertical: EvaSpace.s3),
          textStyle: _ui(EvaType.base, EvaWeights.semibold),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(EvaRadii.md),
          ),
        ),
      ),

      // Ghost / secondary chrome control.
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: EvaColors.textPrimary,
          minimumSize: const Size(EvaLayout.tapMin, EvaLayout.tapMin),
          padding: const EdgeInsets.symmetric(horizontal: EvaSpace.s4),
          textStyle: _ui(EvaType.base, EvaWeights.medium),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(EvaRadii.md),
          ),
        ),
      ),

      // Inputs — inset surface, hairline border, mauve focus.
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: EvaColors.surfaceInset,
        hintStyle: _ui(EvaType.base, EvaWeights.regular,
            color: EvaColors.textFaint),
        labelStyle: _ui(EvaType.sm, EvaWeights.medium,
            color: EvaColors.textSecondary),
        contentPadding: const EdgeInsets.symmetric(
            horizontal: EvaSpace.s4, vertical: EvaSpace.s3),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(EvaRadii.md),
          borderSide: const BorderSide(color: EvaColors.surfaceLine),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(EvaRadii.md),
          borderSide: const BorderSide(color: EvaColors.surfaceLine),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(EvaRadii.md),
          borderSide: const BorderSide(color: EvaColors.focusRing, width: 2),
        ),
      ),

      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((s) =>
            s.contains(WidgetState.selected)
                ? EvaColors.accent
                : EvaColors.overlay1),
        trackColor: WidgetStateProperty.resolveWith((s) =>
            s.contains(WidgetState.selected)
                ? EvaColors.accentSoft
                : EvaColors.surface0),
        trackOutlineColor:
            WidgetStateProperty.all(EvaColors.surfaceLineStrong),
      ),

      sliderTheme: const SliderThemeData(
        activeTrackColor: EvaColors.accent,
        inactiveTrackColor: EvaColors.surface0,
        thumbColor: EvaColors.accent,
        overlayColor: EvaColors.accentSoft,
      ),

      dividerTheme: const DividerThemeData(
        color: EvaColors.surfaceLine,
        thickness: 1,
        space: 1,
      ),

      dialogTheme: DialogThemeData(
        backgroundColor: EvaColors.surfaceCard,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(EvaRadii.lg),
          side: const BorderSide(color: EvaColors.surfaceLine),
        ),
        titleTextStyle: _ui(EvaType.xl, EvaWeights.semibold),
        contentTextStyle:
            _ui(EvaType.md, EvaWeights.regular, height: EvaType.leadingNormal),
      ),

      // Quiet barrier (scrim) — Crust-ish dark behind dialogs.
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: EvaColors.surfaceCard,
        modalBarrierColor: Color(0x99181926),
      ),

      appBarTheme: AppBarTheme(
        backgroundColor: EvaColors.bgBar,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: _ui(EvaType.lg, EvaWeights.semibold),
      ),

      pageTransitionsTheme: const PageTransitionsTheme(builders: {
        TargetPlatform.android: FadeUpwardsPageTransitionsBuilder(),
        TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
      }),
    );
  }
}
