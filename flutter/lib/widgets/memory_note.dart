// MemoryNote — one entry in Eva's notebook. Third person, the way she keeps it.
// Green left-tick + pencil mark it as a remembered fact; never a database row.
// Ported from MemoryNote.jsx.

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../eva_theme.dart';
import '../eva_tokens.dart';

class MemoryNote extends StatelessWidget {
  final String text;
  final String when;
  final String tag;
  final bool pinned;
  final VoidCallback? onOpen;
  final VoidCallback? onPin;
  final VoidCallback? onForget;

  const MemoryNote({
    super.key,
    required this.text,
    required this.when,
    required this.tag,
    this.pinned = false,
    this.onOpen,
    this.onPin,
    this.onForget,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: EvaColors.surfaceCard,
      borderRadius: BorderRadius.circular(EvaRadii.md),
      child: InkWell(
        onTap: onOpen,
        borderRadius: BorderRadius.circular(EvaRadii.md),
        child: Container(
          padding: const EdgeInsets.all(EvaSpace.s4),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(EvaRadii.md),
            border: Border.all(
              color: pinned ? EvaColors.rememberedSoft : EvaColors.surfaceLine,
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Green left-tick.
              Container(
                width: 3,
                height: 40,
                margin: const EdgeInsets.only(right: EvaSpace.s3, top: 2),
                decoration: BoxDecoration(
                  color: EvaColors.remembered.withValues(alpha: 0.8),
                  borderRadius: BorderRadius.circular(EvaRadii.pill),
                ),
              ),
              const Padding(
                padding: EdgeInsets.only(top: 2, right: EvaSpace.s3),
                child: Icon(Icons.edit_outlined, size: 16, color: EvaColors.remembered),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      text,
                      style: GoogleFonts.newsreader(
                        textStyle: evaVoice(16.3, color: EvaColors.textPrimary),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: EvaSpace.s3,
                      runSpacing: 4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        if (pinned)
                          const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.push_pin, size: 12, color: EvaColors.remembered),
                              SizedBox(width: 4),
                              Text('pinned',
                                  style: TextStyle(
                                    fontSize: EvaType.xs,
                                    color: EvaColors.remembered,
                                    fontWeight: EvaWeights.medium,
                                  )),
                            ],
                          ),
                        if (when.isNotEmpty)
                          Text(when,
                              style:
                                  const TextStyle(fontSize: EvaType.xs, color: EvaColors.textMuted)),
                        if (tag.isNotEmpty)
                          Text('#$tag',
                              style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.accent)),
                      ],
                    ),
                  ],
                ),
              ),
              Column(
                children: [
                  if (onPin != null)
                    _miniButton(
                      icon: Icons.push_pin_outlined,
                      tooltip: pinned ? 'Unpin' : 'Pin to top',
                      color: pinned ? EvaColors.remembered : EvaColors.textFaint,
                      onPressed: onPin!,
                    ),
                  if (onForget != null)
                    _miniButton(
                      icon: Icons.close,
                      tooltip: 'Ask Eva to forget this',
                      color: EvaColors.textFaint,
                      onPressed: onForget!,
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _miniButton({
    required IconData icon,
    required String tooltip,
    required Color color,
    required VoidCallback onPressed,
  }) {
    return SizedBox(
      width: 30,
      height: 30,
      child: IconButton(
        padding: EdgeInsets.zero,
        iconSize: 15,
        tooltip: tooltip,
        color: color,
        onPressed: onPressed,
        icon: Icon(icon),
      ),
    );
  }
}
