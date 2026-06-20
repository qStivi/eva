// MemoryScreen — "What I remember." Eva's notebook, never a database. Tag
// filter, pinned entries float to the top, tap an entry to inspect the moment
// she wrote it down. Ported from MemoryScreen.jsx + MemoryDetail.jsx.

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../data/mock_chat.dart';
import '../eva_theme.dart';
import '../eva_tokens.dart';
import '../state/eva_controller.dart';
import '../widgets/bits.dart';
import '../widgets/memory_note.dart';

class MemoryScreen extends StatefulWidget {
  final EvaController controller;
  const MemoryScreen({super.key, required this.controller});

  @override
  State<MemoryScreen> createState() => _MemoryScreenState();
}

class _MemoryScreenState extends State<MemoryScreen> {
  String _filter = 'all';

  EvaController get c => widget.controller;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: c,
      builder: (context, _) {
        final tags = <String>[];
        for (final m in c.memories) {
          if (!tags.contains(m.tag)) tags.add(m.tag);
        }
        final shown = (_filter == 'all'
            ? List<Memory>.of(c.memories)
            : c.memories.where((m) => m.tag == _filter).toList())
          ..sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));
        final pinnedCount = c.memories.where((m) => m.pinned).length;

        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 28),
          children: [
            Text('What I remember', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 6),
            _voiceIntro(
              "Don't read too much into it. I just keep track of the things that matter to you. ",
              '*closes the notebook halfway*',
            ),
            const SizedBox(height: EvaSpace.s4),
            Row(
              children: [
                _keptBadge(c.memories.length),
                if (pinnedCount > 0) ...[
                  const SizedBox(width: EvaSpace.s2),
                  Icon(Icons.push_pin, size: 12, color: EvaColors.remembered),
                  const SizedBox(width: 4),
                  Text('$pinnedCount pinned',
                      style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.remembered)),
                ],
              ],
            ),
            const SizedBox(height: EvaSpace.s3),
            Wrap(
              spacing: 7,
              runSpacing: 7,
              children: [
                _tagChip('All', 'all'),
                for (final t in tags) _tagChip('#$t', t),
              ],
            ),
            const SizedBox(height: EvaSpace.s4),
            if (shown.isEmpty)
              _emptyState()
            else
              for (final m in shown)
                Padding(
                  padding: const EdgeInsets.only(bottom: EvaSpace.s3),
                  child: MemoryNote(
                    text: m.text,
                    when: m.when,
                    tag: m.tag,
                    pinned: m.pinned,
                    onOpen: () => _openDetail(m),
                    onPin: () => c.togglePin(m.id),
                    onForget: () => _confirmForget(m),
                  ),
                ),
          ],
        );
      },
    );
  }

  Widget _voiceIntro(String body, String aside) {
    final base = GoogleFonts.newsreader(
      textStyle: evaVoice(16.3, color: EvaColors.textSecondary),
    );
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 460),
      child: Text.rich(TextSpan(style: base, children: [
        TextSpan(text: body),
        TextSpan(
          text: aside,
          style: base.copyWith(
            fontStyle: FontStyle.italic,
            color: EvaColors.accent3.withValues(alpha: 0.92),
          ),
        ),
      ])),
    );
  }

  Widget _keptBadge(int n) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: EvaSpace.s3, vertical: 5),
      decoration: BoxDecoration(
        color: EvaColors.rememberedSoft,
        borderRadius: BorderRadius.circular(EvaRadii.pill),
        border: Border.all(color: EvaColors.remembered.withValues(alpha: 0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.edit_outlined, size: 13, color: EvaColors.remembered),
          const SizedBox(width: 5),
          Text('$n kept',
              style: const TextStyle(
                fontSize: EvaType.xs,
                color: EvaColors.remembered,
                fontWeight: EvaWeights.medium,
              )),
        ],
      ),
    );
  }

  Widget _tagChip(String label, String value) {
    final active = _filter == value;
    return Material(
      color: active ? EvaColors.accent : Colors.transparent,
      borderRadius: BorderRadius.circular(EvaRadii.pill),
      child: InkWell(
        onTap: () => setState(() => _filter = value),
        borderRadius: BorderRadius.circular(EvaRadii.pill),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(EvaRadii.pill),
            border: Border.all(color: active ? Colors.transparent : EvaColors.surfaceLine),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: EvaType.xs,
              fontWeight: EvaWeights.medium,
              color: active ? EvaColors.textOnAccent : EvaColors.textSecondary,
            ),
          ),
        ),
      ),
    );
  }

  Widget _emptyState() {
    final all = _filter == 'all';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: EvaSpace.s7),
      child: Column(
        children: [
          const Icon(Icons.menu_book_outlined, size: 28, color: EvaColors.textFaint),
          const SizedBox(height: EvaSpace.s3),
          Text(all ? "The notebook's empty." : 'Nothing under that one yet.',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          Text(
            all
                ? "Talk to me for a while. I'll keep the parts that matter — don't make it weird."
                : 'Try another tag, or just tell me something new.',
            textAlign: TextAlign.center,
            style: const TextStyle(color: EvaColors.textSecondary, height: EvaType.leadingNormal),
          ),
        ],
      ),
    );
  }

  void _openDetail(Memory m) {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: EvaColors.surfaceCard,
      barrierColor: const Color(0x99181926),
      isScrollControlled: true,
      showDragHandle: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(EvaRadii.xl)),
      ),
      builder: (sheetContext) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 4, 20, 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              m.text,
              style: GoogleFonts.newsreader(
                textStyle: evaVoice(EvaType.lg, color: EvaColors.textPrimary),
              ),
            ),
            const SizedBox(height: EvaSpace.s4),
            const Eyebrow('When she wrote it down'),
            Text(m.context,
                style: const TextStyle(color: EvaColors.textSecondary, height: EvaType.leadingNormal)),
            const SizedBox(height: EvaSpace.s5),
            Row(
              children: [
                OutlinedButton.icon(
                  onPressed: () {
                    c.togglePin(m.id);
                    Navigator.of(sheetContext).pop();
                  },
                  icon: Icon(m.pinned ? Icons.push_pin : Icons.push_pin_outlined, size: 16),
                  label: Text(m.pinned ? 'Unpin' : 'Pin'),
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: () {
                    Navigator.of(sheetContext).pop();
                    _confirmForget(m);
                  },
                  style: TextButton.styleFrom(foregroundColor: EvaColors.danger),
                  icon: const Icon(Icons.close, size: 16),
                  label: const Text('Forget it'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _confirmForget(Memory m) {
    showDialog<void>(
      context: context,
      barrierColor: const Color(0x99181926),
      builder: (dialogContext) => AlertDialog(
        title: const Text('Forget this?'),
        content: Text.rich(TextSpan(children: [
          TextSpan(text: 'I\'ll let go of "${m.text}" — for good. '),
          TextSpan(
            text: "Your call. I won't bring it up again.",
            style: GoogleFonts.newsreader(
              textStyle: evaVoice(EvaType.md, italic: true, color: EvaColors.textSecondary),
            ),
          ),
        ])),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Keep it'),
          ),
          ElevatedButton(
            onPressed: () {
              c.forget(m.id);
              Navigator.of(dialogContext).pop();
            },
            style: ElevatedButton.styleFrom(backgroundColor: EvaColors.danger),
            child: const Text('Forget it'),
          ),
        ],
      ),
    );
  }
}
