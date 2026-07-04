// TypingIndicator — Eva is composing. Three dots that bob slowly inside her
// bubble shape, so "she's thinking" reads as a turn, not a spinner. Ported from
// TypingIndicator.jsx (1.2s cycle, staggered 0.16s per dot).

import 'package:flutter/material.dart';

import '../eva_tokens.dart';

class TypingIndicator extends StatefulWidget {
  const TypingIndicator({super.key, this.dotSize = 6});

  final double dotSize;

  @override
  State<TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<TypingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1200),
  )..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
      decoration: BoxDecoration(
        color: EvaColors.evaBubble,
        border: Border.all(color: EvaColors.evaBubbleLine),
        borderRadius: EvaRadii.evaBubble(),
        boxShadow: EvaShadows.sm,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(3, (i) => _dot(i)),
      ),
    );
  }

  Widget _dot(int i) {
    return Padding(
      padding: EdgeInsets.only(right: i < 2 ? widget.dotSize - 1 : 0),
      child: AnimatedBuilder(
        animation: _c,
        builder: (context, child) {
          // Stagger each dot's phase by 0.16s within the 1.2s cycle.
          final phase = (_c.value - i * (0.16 / 1.2)) % 1.0;
          // 0,80,100% -> low/flat; 40% -> peak (lifted + bright).
          final lift = phase < 0.8 ? Curves.easeInOut.transform(_peak(phase)) : 0.0;
          final opacity = 0.3 + 0.7 * lift;
          return Opacity(
            opacity: opacity,
            child: Transform.translate(offset: Offset(0, -3 * lift), child: child),
          );
        },
        child: Container(
          width: widget.dotSize,
          height: widget.dotSize,
          decoration: const BoxDecoration(
            color: EvaColors.textMuted,
            shape: BoxShape.circle,
          ),
        ),
      ),
    );
  }

  // Triangle peaking at 40% of the cycle, zero by 80%.
  double _peak(double t) {
    if (t <= 0.4) return t / 0.4;
    if (t < 0.8) return 1 - (t - 0.4) / 0.4;
    return 0;
  }
}
