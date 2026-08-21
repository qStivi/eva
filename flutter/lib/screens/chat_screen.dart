// ChatScreen — the conversation. The heart of the product. Reads everything
// from the shared EvaController; the AppShell owns the title bar, so by default
// this screen shows no header of its own (showHeader: true is for standalone use).

import 'dart:math';

import 'package:flutter/material.dart';

import '../data/mock_chat.dart';
import '../eva_tokens.dart';
import '../state/eva_controller.dart';
import '../widgets/composer.dart';
import '../widgets/message_bubble.dart';
import '../widgets/presence.dart';
import '../widgets/typing_indicator.dart';

class ChatScreen extends StatefulWidget {
  final EvaController controller;
  final bool showHeader;

  const ChatScreen({super.key, required this.controller, this.showHeader = false});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final ScrollController _scroll = ScrollController();

  EvaController get c => widget.controller;

  @override
  void initState() {
    super.initState();
    c.addListener(_onChange);
  }

  @override
  void dispose() {
    c.removeListener(_onChange);
    _scroll.dispose();
    super.dispose();
  }

  void _onChange() {
    // Keep the latest turn in view as messages arrive / reveal.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: EvaMotion.base,
          curve: EvaMotion.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    // Wrap the WHOLE screen (not just the message list) so the Composer rebuilds
    // on every controller change too — otherwise its `busy` stays stale and the
    // send button gets stuck on the spinner until an unrelated relayout (e.g.
    // dismissing the keyboard) forces a full rebuild.
    return ListenableBuilder(
      listenable: c,
      builder: (context, _) => Column(
        children: [
          if (widget.showHeader) _header(),
          Expanded(child: _messageList()),
          Composer(controller: c.draft, onSend: c.send, busy: c.busy, onCancel: c.cancelThinking),
        ],
      ),
    );
  }

  Widget _header() {
    final moodKey = c.thinking ? EvaMood.thinking : c.evaMood;
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [EvaColors.bgBar, Color(0x0024273A)],
        ),
      ),
      child: Row(
        children: [
          PresenceOrb(mood: moodKey, size: 44),
          const SizedBox(width: EvaSpace.s3),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Eva', style: Theme.of(context).textTheme.titleMedium),
              Text(moodLine(moodKey),
                  style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.textMuted)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _messageList() {
    final messages = c.messages;
    // Build the turns, then the live thinking/typing turn, interleaved with
    // separators — the same content the old ListView produced.
    final turns = <Widget>[
      for (var i = 0; i < messages.length; i++) _turn(messages[i], i),
      if (c.busy) _liveTurn(messages),
    ];
    final children = <Widget>[];
    for (var i = 0; i < turns.length; i++) {
      if (i > 0) children.add(const SizedBox(height: EvaSpace.s3));
      children.add(turns[i]);
    }

    // Bottom-anchored: content sits above the composer and grows upward, so a
    // short conversation has no top dead-space. minHeight pins it to the bottom;
    // a long conversation overflows and scrolls as before.
    const padding = EdgeInsets.fromLTRB(16, 8, 16, 16);
    return LayoutBuilder(
      builder: (context, constraints) => SingleChildScrollView(
        controller: _scroll,
        padding: padding,
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minHeight: constraints.maxHeight - padding.vertical,
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.end,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: children,
          ),
        ),
      ),
    );
  }

  /// The live thinking / typing turn shown while Eva is composing.
  Widget _liveTurn(List<ChatMessage> messages) {
    if (c.typingText != null) {
      return _evaRow(
        MessageBubble(
          speaker: Speaker.eva,
          text: c.typingText!,
          mood: c.typingMood,
          caret: true,
        ),
        showAvatar: messages.isEmpty || messages.last.from != Speaker.eva,
        mood: c.typingMood,
      );
    }
    return _evaRow(const TypingIndicator(), showAvatar: true, mood: EvaMood.thinking);
  }

  Widget _turn(ChatMessage m, int index) {
    if (m.from == Speaker.system) {
      return MessageBubble(speaker: Speaker.system, text: m.text);
    }
    if (m.from == Speaker.eva) {
      final prev = index > 0 ? c.messages[index - 1] : null;
      return _evaRow(
        MessageBubble(
          speaker: Speaker.eva,
          text: m.text,
          time: m.time,
          remembered: m.remembered,
          mood: m.mood,
          tools: m.tools,
        ),
        showAvatar: prev == null || prev.from != Speaker.eva,
        mood: m.mood,
      );
    }
    return Align(
      alignment: Alignment.centerRight,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: _readingMax(context)),
        child: MessageBubble(speaker: Speaker.you, text: m.text, time: m.time),
      ),
    );
  }

  /// Eva's turn: her avatar (only at the start of a run) beside the bubble.
  Widget _evaRow(Widget bubble, {required bool showAvatar, required EvaMood mood}) {
    return Align(
      alignment: Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: _readingMax(context) + 38),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 30,
              child: showAvatar ? EvaAvatar(mood: mood, size: 30) : null,
            ),
            const SizedBox(width: EvaSpace.s2),
            Flexible(child: bubble),
          ],
        ),
      ),
    );
  }

  double _readingMax(BuildContext context) {
    final w = MediaQuery.of(context).size.width;
    return min(w * 0.86, 600);
  }
}
