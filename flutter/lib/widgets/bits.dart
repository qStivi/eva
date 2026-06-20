// Small shared bits: the section "eyebrow" label, the model switcher pill, and
// a status dot. Ported from the design export's tokens + ModelPill.jsx.

import 'package:flutter/material.dart';

import '../eva_tokens.dart';

/// A quiet all-caps section label (the `.eva-eyebrow` class in the export).
class Eyebrow extends StatelessWidget {
  final String text;
  const Eyebrow(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: EvaSpace.s2),
      child: Text(
        text.toUpperCase(),
        style: const TextStyle(
          fontSize: EvaType.xs,
          fontWeight: EvaWeights.semibold,
          letterSpacing: 1.4, // ~0.12em at 12px
          color: EvaColors.textFaint,
        ),
      ),
    );
  }
}

/// The curated "which brain Eva runs on" switcher trigger.
class ModelPill extends StatelessWidget {
  final String name;
  final bool open;
  final VoidCallback onPressed;

  const ModelPill({super.key, required this.name, required this.onPressed, this.open = false});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: EvaColors.surfaceInset,
      borderRadius: BorderRadius.circular(EvaRadii.pill),
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(EvaRadii.pill),
        child: Container(
          height: 36,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(EvaRadii.pill),
            border: Border.all(color: open ? EvaColors.accentLine : EvaColors.surfaceLine),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.auto_awesome, size: 15, color: EvaColors.accent),
              const SizedBox(width: EvaSpace.s2),
              Text(name,
                  style: const TextStyle(
                    fontSize: EvaType.sm,
                    fontWeight: EvaWeights.medium,
                    color: EvaColors.textPrimary,
                  )),
              const SizedBox(width: 6),
              AnimatedRotation(
                turns: open ? 0.5 : 0,
                duration: EvaMotion.fast,
                child: const Icon(Icons.keyboard_arrow_down, size: 16, color: EvaColors.textMuted),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// A small status dot — online (green), thinking (mauve), offline (red).
class StatusDot extends StatelessWidget {
  final bool thinking;
  const StatusDot({super.key, this.thinking = false});

  @override
  Widget build(BuildContext context) {
    final color = thinking ? EvaColors.accent : EvaColors.remembered;
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color,
        boxShadow: [BoxShadow(color: color.withValues(alpha: 0.5), blurRadius: 6)],
      ),
    );
  }
}
