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
    return Column(
      children: [
        if (widget.showHeader) _header(),
        Expanded(
          child: ListenableBuilder(
            listenable: c,
            builder: (context, _) => _messageList(),
          ),
        ),
        Composer(controller: c.draft, onSend: c.send, busy: c.busy),
      ],
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
    final extra = c.busy ? 1 : 0;
    return ListView.separated(
      controller: _scroll,
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      itemCount: messages.length + extra,
      separatorBuilder: (_, _) => const SizedBox(height: EvaSpace.s3),
      itemBuilder: (context, index) {
        if (index < messages.length) return _turn(messages[index], index);
        // The live thinking / typing turn.
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
      },
    );
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
