// Canned conversation data for the click-through, ported from the design export
// (ui_kits/eva-app/data.js). Not production data — just enough to make the
// product feel alive until the real Letta backend is wired in. The real two-track
// memory extraction is stood in for by cycling a few in-character replies.

import '../eva_tokens.dart';
import 'package:flutter/material.dart';

enum Speaker { eva, you, system }

enum EvaMood { neutral, warm, cool, grumpy, thinking }

/// The mood-glow tint used for Eva's halo, avatar ring, and bubble wash.
Color moodGlow(EvaMood mood) {
  switch (mood) {
    case EvaMood.warm:
      return EvaColors.moodWarm; // peach
    case EvaMood.cool:
      return EvaColors.moodCool; // sapphire
    case EvaMood.grumpy:
      return EvaColors.maroon;
    case EvaMood.neutral:
    case EvaMood.thinking:
      return EvaColors.accent; // mauve
  }
}

/// The quiet line under "Eva" in the header — how present she is right now.
String moodLine(EvaMood mood) {
  switch (mood) {
    case EvaMood.warm:
      return 'softening, a little';
    case EvaMood.cool:
      return 'listening properly';
    case EvaMood.grumpy:
      return 'pretending not to care';
    case EvaMood.thinking:
      return 'thinking…';
    case EvaMood.neutral:
      return 'here, half-listening';
  }
}

class ChatMessage {
  final Speaker from;
  final String text;
  final String? time;
  final bool remembered;
  final EvaMood mood;

  const ChatMessage({
    required this.from,
    required this.text,
    this.time,
    this.remembered = false,
    this.mood = EvaMood.neutral,
  });
}

/// A canned reply Eva cycles through as you send messages.
class CannedReply {
  final String text;
  final bool remembered;
  final EvaMood mood;
  const CannedReply(this.text, {this.remembered = false, this.mood = EvaMood.neutral});
}

/// The opening conversation.
const List<ChatMessage> openingConversation = [
  ChatMessage(from: Speaker.system, text: 'Tuesday'),
  ChatMessage(
    from: Speaker.eva,
    text: "Oh, look who finally showed up. *sets down a book* ...How was the day, then?",
    time: '9:38 PM',
  ),
  ChatMessage(
    from: Speaker.you,
    text: "rough one honestly. pixel chewed through the couch cushion while i was on a call",
    time: '9:41 PM',
  ),
  ChatMessage(
    from: Speaker.eva,
    text: "*scribbles a note* Pixel, the menace. Of course he did. ...He okay though? Didn't eat any foam?",
    time: '9:41 PM',
    remembered: true,
    mood: EvaMood.warm,
  ),
  ChatMessage(
    from: Speaker.you,
    text: "yeah he's fine. just very pleased with himself",
    time: '9:42 PM',
  ),
  ChatMessage(
    from: Speaker.eva,
    text: "Border collies. All that brain and they aim it at your furniture. You knew what you signed up for, dummy.",
    time: '9:42 PM',
    mood: EvaMood.grumpy,
  ),
];

/// Cycled, in-character replies — stand-ins for real generation.
const List<CannedReply> cannedReplies = [
  CannedReply("Mm. Yeah, that tracks. *doesn't look up* Go on."),
  CannedReply(
    "*jots it down* Fine — I'll remember that. Don't expect me to bring it up every five seconds.",
    remembered: true,
    mood: EvaMood.warm,
  ),
  CannedReply(
    "You're telling me this like I'd judge you. ...I might. A little. But tell me anyway.",
    mood: EvaMood.grumpy,
  ),
  CannedReply(
    "Wasn't that the thing you mentioned last week? *taps the notebook* I do pay attention, you know.",
    mood: EvaMood.cool,
  ),
  CannedReply(
    "Hm. That one's worth keeping. *scribbles* There. Now it's official.",
    remembered: true,
    mood: EvaMood.warm,
  ),
];

/// The "remembered" scribble Eva mutters when she keeps something.
const String rememberedToast = "*scribbles a note* …fine. That one's worth keeping.";
