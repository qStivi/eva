// ChatScreen — the conversation. The heart of the product. Ported from the
// design export's ChatScreen.jsx + chat-logic.js. Until the real Letta backend
// is wired in, sending cycles a canned in-character reply, revealed with a calm
// typewriter; "remembered" replies surface Eva's scribble toast.

import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../data/mock_chat.dart';
import '../eva_theme.dart';
import '../eva_tokens.dart';
import '../widgets/composer.dart';
import '../widgets/message_bubble.dart';
import '../widgets/presence.dart';
import '../widgets/typing_indicator.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<ChatMessage> _messages = List.of(openingConversation);
  final TextEditingController _draft = TextEditingController();
  final ScrollController _scroll = ScrollController();
  final List<Timer> _timers = [];
  final Random _rng = Random();

  EvaMood _evaMood = EvaMood.neutral;
  bool _thinking = false;
  int _replyIdx = 0;

  // The reply currently being typed out, if any.
  String? _typingText;
  EvaMood _typingMood = EvaMood.neutral;

  bool get _busy => _thinking || _typingText != null;

  @override
  void dispose() {
    for (final t in _timers) {
      t.cancel();
    }
    _draft.dispose();
    _scroll.dispose();
    super.dispose();
  }

  String _now() {
    final d = TimeOfDay.now();
    final h = d.hourOfPeriod == 0 ? 12 : d.hourOfPeriod;
    final m = d.minute.toString().padLeft(2, '0');
    final ap = d.period == DayPeriod.am ? 'AM' : 'PM';
    return '$h:$m $ap';
  }

  void _scrollToBottom() {
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

  void _send() {
    final text = _draft.text.trim();
    if (text.isEmpty || _busy) return;
    setState(() {
      _messages.add(ChatMessage(from: Speaker.you, text: text, time: _now()));
      _draft.clear();
      _thinking = true;
      _evaMood = EvaMood.thinking;
    });
    _scrollToBottom();

    final reply = cannedReplies[_replyIdx % cannedReplies.length];
    _replyIdx++;
    _timers.add(Timer(
      Duration(milliseconds: 850 + _rng.nextInt(500)),
      () => _typewrite(reply),
    ));
  }

  void _typewrite(CannedReply reply) {
    if (!mounted) return;
    final full = reply.text;
    final mood = reply.mood;
    final chunk = max(1, (full.length / 34).ceil());
    var i = 0;

    setState(() {
      _thinking = false;
      _evaMood = mood;
      _typingMood = mood;
      _typingText = '';
    });

    void tick() {
      if (!mounted) return;
      i = min(full.length, i + chunk);
      setState(() => _typingText = full.substring(0, i));
      _scrollToBottom();
      if (i < full.length) {
        _timers.add(Timer(const Duration(milliseconds: 42), tick));
      } else {
        _timers.add(Timer(const Duration(milliseconds: 140), () {
          if (!mounted) return;
          setState(() {
            _typingText = null;
            _messages.add(ChatMessage(
              from: Speaker.eva,
              text: full,
              time: _now(),
              remembered: reply.remembered,
              mood: mood,
            ));
          });
          _scrollToBottom();
          if (reply.remembered) _showRememberedToast();
        }));
      }
    }

    tick();
  }

  void _showRememberedToast() {
    final messenger = ScaffoldMessenger.of(context);
    messenger.clearSnackBars();
    messenger.showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        backgroundColor: EvaColors.surfaceCard,
        elevation: 0,
        duration: const Duration(seconds: 4),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(EvaRadii.md),
          side: const BorderSide(color: EvaColors.remembered),
        ),
        content: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.edit_outlined, size: 16, color: EvaColors.remembered),
            const SizedBox(width: EvaSpace.s2),
            Flexible(
              child: Text(
                rememberedToast,
                style: GoogleFonts.newsreader(
                  textStyle: evaVoice(EvaType.base, italic: true, color: EvaColors.textPrimary),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final moodKey = _thinking ? EvaMood.thinking : _evaMood;
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            _header(moodKey),
            Expanded(child: _messageList()),
            Composer(controller: _draft, onSend: _send, busy: _busy),
          ],
        ),
      ),
    );
  }

  Widget _header(EvaMood moodKey) {
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
              AnimatedSwitcher(
                duration: EvaMotion.base,
                child: Text(
                  moodLine(moodKey),
                  key: ValueKey(moodKey),
                  style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.textMuted),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _messageList() {
    // Items: the settled messages, then an optional thinking/typing turn.
    final extra = (_thinking && _typingText == null) || _typingText != null ? 1 : 0;
    return ListView.separated(
      controller: _scroll,
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      itemCount: _messages.length + extra,
      separatorBuilder: (_, _) => const SizedBox(height: EvaSpace.s3),
      itemBuilder: (context, index) {
        if (index < _messages.length) {
          return _turn(_messages[index], index);
        }
        // The live thinking / typing turn.
        if (_typingText != null) {
          return _evaRow(
            MessageBubble(
              speaker: Speaker.eva,
              text: _typingText!,
              mood: _typingMood,
              caret: true,
            ),
            showAvatar: _messages.isEmpty || _messages.last.from != Speaker.eva,
            mood: _typingMood,
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
      final prev = index > 0 ? _messages[index - 1] : null;
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
    // ~46 characters of reading measure, capped to the viewport.
    final w = MediaQuery.of(context).size.width;
    return min(w * 0.86, 600);
  }
}
