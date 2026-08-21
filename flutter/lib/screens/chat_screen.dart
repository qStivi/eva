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
    // Keep the latest turn in view as messages arrive / reveal. The list is
    // reverse:true now, so "newest" is scroll offset 0, not maxScrollExtent.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          0,
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
    final hasLive = c.busy;
    final itemCount = messages.length + (hasLive ? 1 : 0);

    // reverse:true does two things for free, replacing what the old
    // SingleChildScrollView(Column) + LayoutBuilder/ConstrainedBox hack was
    // trying to hand-roll: (1) lazy building — with real history now up to
    // ~60 messages (see _loadHistory), eagerly building every bubble into a
    // Column was the actual cause of the scroll jank; ListView only builds
    // what's near the viewport. (2) bottom-anchoring for a short conversation
    // (empty space stays at the top, content sits at the bottom) comes from
    // the reversed axis itself, no minHeight math needed — which also
    // removes the negative-minHeight assertion that math could throw when
    // the keyboard opens and shrinks the available height.
    return ListView.separated(
      controller: _scroll,
      reverse: true,
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      itemCount: itemCount,
      separatorBuilder: (context, _) => const SizedBox(height: EvaSpace.s3),
      itemBuilder: (context, reversedIndex) {
        // reverse:true wants index 0 = newest (rendered at the visual
        // bottom), so translate back to chronological order for _turn/
        // _liveTurn, which already index into c.messages that way.
        final chronoIndex = itemCount - 1 - reversedIndex;
        if (hasLive && chronoIndex == messages.length) {
          return _liveTurn(messages);
        }
        return _turn(messages[chronoIndex], chronoIndex);
      },
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
