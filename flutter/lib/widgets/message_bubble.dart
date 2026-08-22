// MessageBubble — one turn in the conversation. Ported from MessageBubble.jsx.
//  - Eva: serif "voice" face, dusky mood-washed bubble, tail bottom-left,
//    *stage-direction* asides rendered quiet italic.
//  - You: humanist sans, inset surface, tail bottom-right.
//  - System: centered, faint, no bubble.

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:google_fonts/google_fonts.dart';

import '../api/letta_api.dart' show TraceEntry, TraceKind;
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
  final List<String> tools;

  /// The full step-by-step trace (reasoning + tool calls) behind this turn —
  /// drives the expandable "N tools used · thought for Ns" disclosure. See
  /// docs/2026-08-22-tool-trace-transparency-spec.md.
  final List<TraceEntry> trace;
  final double? elapsedSeconds;

  const MessageBubble({
    super.key,
    required this.speaker,
    required this.text,
    this.time,
    this.remembered = false,
    this.mood = EvaMood.neutral,
    this.caret = false,
    this.tools = const [],
    this.trace = const [],
    this.elapsedSeconds,
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
        if (_isEva && trace.isNotEmpty) _TraceDisclosure(trace: trace, elapsedSeconds: elapsedSeconds),
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

    // While the reply is still typing out, keep the fast plain-text path with the
    // blinking caret (re-parsing markdown every frame would be janky). Markdown is
    // rendered once the message is committed.
    if (caret) {
      return Text.rich(
        TextSpan(style: base, children: [
          ..._voiceSpans(text, aside),
          const WidgetSpan(
            alignment: PlaceholderAlignment.middle,
            child: _BlinkingCaret(),
          ),
        ]),
      );
    }

    return MarkdownBody(
      data: text,
      selectable: false,
      styleSheet: _evaMarkdown(base, aside),
    );
  }

  /// Markdown styled for Eva: serif body, her `*stage directions*` (markdown em)
  /// as quiet lavender italics, mono code, restrained headings.
  static MarkdownStyleSheet _evaMarkdown(TextStyle base, TextStyle aside) {
    final mono = TextStyle(
      fontFamily: EvaFonts.mono,
      fontFamilyFallback: EvaFonts.monoFallback,
      fontSize: EvaType.sm,
      color: EvaColors.textPrimary,
    );
    return MarkdownStyleSheet(
      p: base,
      pPadding: EdgeInsets.zero,
      strong: base.copyWith(fontWeight: EvaWeights.semibold),
      em: aside,
      h1: base.copyWith(fontSize: EvaType.xl, fontWeight: EvaWeights.semibold, height: EvaType.leadingSnug),
      h2: base.copyWith(fontSize: EvaType.lg, fontWeight: EvaWeights.semibold, height: EvaType.leadingSnug),
      h3: base.copyWith(fontSize: EvaType.md, fontWeight: EvaWeights.semibold),
      listBullet: base,
      a: base.copyWith(color: EvaColors.accent, decoration: TextDecoration.underline),
      code: mono.copyWith(backgroundColor: EvaColors.surfaceInset),
      codeblockPadding: const EdgeInsets.all(EvaSpace.s3),
      codeblockDecoration: BoxDecoration(
        color: EvaColors.surfaceInset,
        borderRadius: BorderRadius.circular(EvaRadii.sm),
      ),
      blockquotePadding: const EdgeInsets.only(left: EvaSpace.s3),
      blockquote: base.copyWith(color: EvaColors.textSecondary),
      blockquoteDecoration: const BoxDecoration(
        border: Border(left: BorderSide(color: EvaColors.surfaceLineStrong, width: 3)),
      ),
      horizontalRuleDecoration: const BoxDecoration(
        border: Border(top: BorderSide(color: EvaColors.surfaceLine)),
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

/// The "N tools used · thought for Ns" line under Eva's bubble — the
/// generalized, always-honest replacement for the old hardcoded tool tag.
/// Tapping it expands her reasoning and every tool call inline: name,
/// arguments, and what came back. Covers every tool she has, not an
/// allowlist — see docs/2026-08-22-tool-trace-transparency-spec.md.
class _TraceDisclosure extends StatefulWidget {
  final List<TraceEntry> trace;
  final double? elapsedSeconds;
  const _TraceDisclosure({required this.trace, this.elapsedSeconds});

  @override
  State<_TraceDisclosure> createState() => _TraceDisclosureState();
}

class _TraceDisclosureState extends State<_TraceDisclosure> {
  bool _open = false;

  String get _summary {
    final toolCount = widget.trace.where((e) => e.kind == TraceKind.toolCall).length;
    final parts = <String>[];
    if (toolCount > 0) parts.add('$toolCount tool${toolCount == 1 ? '' : 's'} used');
    final secs = widget.elapsedSeconds;
    if (secs != null && secs >= 1) parts.add('thought for ${secs.round()}s');
    if (parts.isNotEmpty) return parts.join(' · ');
    // Reasoning-only turn (rare — the local model often leaves reasoning
    // empty) or a sub-second round trip: still surface *something* tappable
    // rather than silently dropping a real trace.
    final n = widget.trace.length;
    return '$n step${n == 1 ? '' : 's'}';
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(EvaRadii.sm),
            onTap: () => setState(() => _open = !_open),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 1),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.bolt_outlined, size: 13, color: EvaColors.textMuted),
                  const SizedBox(width: 5),
                  Text(
                    _summary,
                    style: const TextStyle(
                      fontSize: EvaType.xs,
                      color: EvaColors.textMuted,
                      fontWeight: EvaWeights.medium,
                    ),
                  ),
                  Icon(
                    _open ? Icons.expand_less : Icons.expand_more,
                    size: 15,
                    color: EvaColors.textMuted,
                  ),
                ],
              ),
            ),
          ),
          if (_open)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 440),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [for (final e in widget.trace) _entry(e)],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _entry(TraceEntry e) {
    if (e.kind == TraceKind.reasoning) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Text(
          e.text ?? '',
          style: TextStyle(
            fontSize: EvaType.xs,
            fontStyle: FontStyle.italic,
            color: EvaColors.accent3.withValues(alpha: 0.85),
          ),
        ),
      );
    }
    final failed = (e.status ?? 'success') != 'success';
    final mono = const TextStyle(fontFamily: EvaFonts.mono, fontFamilyFallback: EvaFonts.monoFallback);
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 3),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: EvaColors.surfaceInset,
        borderRadius: BorderRadius.circular(EvaRadii.sm),
        border: failed ? Border.all(color: EvaColors.maroon.withValues(alpha: 0.4)) : null,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(Icons.build_circle_outlined,
                  size: 13, color: failed ? EvaColors.maroon : EvaColors.textMuted),
              const SizedBox(width: 5),
              Expanded(
                child: Text(
                  e.name,
                  style: mono.copyWith(
                    fontSize: EvaType.xs,
                    fontWeight: EvaWeights.semibold,
                    color: EvaColors.textPrimary,
                  ),
                ),
              ),
              if (failed)
                Text(e.status ?? 'error',
                    style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.maroon)),
            ],
          ),
          if (e.args != null) ...[
            const SizedBox(height: 4),
            Text(_formatArgs(e.args),
                style: mono.copyWith(fontSize: EvaType.xs, color: EvaColors.textSecondary)),
          ],
          if (e.result != null && e.result!.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              e.truncated ? '${_formatResult(e.result!)}\n…(truncated)' : _formatResult(e.result!),
              style: mono.copyWith(fontSize: EvaType.xs, color: EvaColors.textMuted),
              maxLines: 14,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }
}

/// Compact, readable rendering of a tool call's arguments — `key: value`
/// lines for the common object case, otherwise the raw value.
String _formatArgs(dynamic args) {
  if (args == null) return '(no args)';
  if (args is Map) {
    if (args.isEmpty) return '(no args)';
    return args.entries
        .map((e) => '${e.key}: ${e.value is String ? e.value : jsonEncode(e.value)}')
        .join('\n');
  }
  if (args is String && args.isEmpty) return '(no args)';
  return args.toString();
}

/// Pretty-prints a tool's raw return if it's JSON; otherwise shows it as-is.
String _formatResult(String result) {
  try {
    return const JsonEncoder.withIndent('  ').convert(jsonDecode(result));
  } catch (_) {
    return result;
  }
}
