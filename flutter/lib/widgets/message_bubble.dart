// MessageBubble — one turn in the conversation. Ported from MessageBubble.jsx.
//  - Eva: serif "voice" face, dusky mood-washed bubble, tail bottom-left,
//    *stage-direction* asides rendered quiet italic.
//  - You: humanist sans, inset surface, tail bottom-right.
//  - System: centered, faint, no bubble.

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../data/mock_chat.dart';
import '../eva_theme.dart';
import '../eva_tokens.dart';

class MessageBubble extends StatelessWidget {
  final Speaker speaker;
  final String text;
  final String? time;
  final bool remembered;
  final EvaMood mood;
  final bool caret;

  const MessageBubble({
    super.key,
    required this.speaker,
    required this.text,
    this.time,
    this.remembered = false,
    this.mood = EvaMood.neutral,
    this.caret = false,
  });

  bool get _isEva => speaker == Speaker.eva;

  @override
  Widget build(BuildContext context) {
    if (speaker == Speaker.system) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 2, horizontal: 8),
        child: Center(
          child: Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: EvaColors.textMuted,
              fontSize: EvaType.sm,
            ),
          ),
        ),
      );
    }

    final tint = _isEva && mood != EvaMood.neutral && mood != EvaMood.thinking
        ? moodGlow(mood)
        : null;

    final bubbleColor = _isEva
        ? (tint != null ? Color.lerp(EvaColors.evaBubble, tint, 0.09)! : EvaColors.evaBubble)
        : EvaColors.youBubble;
    final borderColor = _isEva
        ? (tint != null
            ? Color.lerp(EvaColors.evaBubbleLine, tint, 0.26)!
            : EvaColors.evaBubbleLine)
        : Colors.transparent;

    return Column(
      crossAxisAlignment: _isEva ? CrossAxisAlignment.start : CrossAxisAlignment.end,
      children: [
        if (remembered && _isEva) _rememberedTag(),
        AnimatedContainer(
          duration: EvaMotion.base,
          curve: EvaMotion.easeOut,
          padding: _isEva
              ? const EdgeInsets.fromLTRB(15, 11, 15, 11)
              : const EdgeInsets.fromLTRB(14, 10, 14, 10),
          decoration: BoxDecoration(
            color: bubbleColor,
            border: Border.all(color: borderColor),
            borderRadius: _isEva ? EvaRadii.evaBubble() : EvaRadii.youBubble(),
            boxShadow: EvaShadows.sm,
          ),
          child: _isEva ? _evaBody(context) : _youBody(context),
        ),
        if (time != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
            child: Text(
              time!,
              style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.textMuted),
            ),
          ),
      ],
    );
  }

  Widget _rememberedTag() {
    return const Padding(
      padding: EdgeInsets.only(bottom: 4),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.edit_outlined, size: 13, color: EvaColors.remembered),
          SizedBox(width: 5),
          Text(
            'jotted it down',
            style: TextStyle(
              fontSize: EvaType.xs,
              color: EvaColors.remembered,
              fontWeight: EvaWeights.medium,
            ),
          ),
        ],
      ),
    );
  }

  Widget _youBody(BuildContext context) {
    return Text(
      text,
      style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: EvaType.leadingNormal),
    );
  }

  Widget _evaBody(BuildContext context) {
    final base = GoogleFonts.newsreader(
      textStyle: evaVoice(16.8, color: EvaColors.textPrimary),
    );
    final aside = base.copyWith(
      fontStyle: FontStyle.italic,
      color: EvaColors.accent3.withValues(alpha: 0.92), // lavender
    );
    return Text.rich(
      TextSpan(
        style: base,
        children: [
          ..._voiceSpans(text, aside),
          if (caret)
            const WidgetSpan(
              alignment: PlaceholderAlignment.middle,
              child: _BlinkingCaret(),
            ),
        ],
      ),
    );
  }

  /// Split on *asides* and mark them as quiet italic stage directions.
  static List<InlineSpan> _voiceSpans(String text, TextStyle aside) {
    final spans = <InlineSpan>[];
    final re = RegExp(r'\*[^*]+\*');
    var last = 0;
    for (final m in re.allMatches(text)) {
      if (m.start > last) spans.add(TextSpan(text: text.substring(last, m.start)));
      final inner = text.substring(m.start + 1, m.end - 1);
      spans.add(TextSpan(text: inner, style: aside));
      last = m.end;
    }
    if (last < text.length) spans.add(TextSpan(text: text.substring(last)));
    return spans;
  }
}

class _BlinkingCaret extends StatefulWidget {
  const _BlinkingCaret();

  @override
  State<_BlinkingCaret> createState() => _BlinkingCaretState();
}

class _BlinkingCaretState extends State<_BlinkingCaret> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(seconds: 1))..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      // Hard on/off blink (steps), matching the export's eva-caret keyframes.
      opacity: _c.drive(TweenSequence<double>([
        TweenSequenceItem(tween: ConstantTween(1.0), weight: 1),
        TweenSequenceItem(tween: ConstantTween(0.0), weight: 1),
      ])),
      child: Container(
        width: 2,
        height: 18,
        margin: const EdgeInsets.only(left: 2),
        decoration: BoxDecoration(
          color: EvaColors.accent,
          borderRadius: BorderRadius.circular(1),
        ),
      ),
    );
  }
}
