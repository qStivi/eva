// Canned conversation data for the click-through, ported from the design export
// (ui_kits/eva-app/data.js). Not production data — just enough to make the
// product feel alive until the real Letta backend is wired in. The real two-track
// memory extraction is stood in for by cycling a few in-character replies.

import '../api/letta_api.dart' show TraceEntry;
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

  /// Tool names Eva invoked on this turn (e.g. a web search), surfaced as a tag.
  final List<String> tools;

  /// Full step-by-step trace (reasoning + tool calls) behind the "N tools
  /// used · thought for Ns" disclosure. Empty for a plain-text reply.
  final List<TraceEntry> trace;
  final double? elapsedSeconds;

  const ChatMessage({
    required this.from,
    required this.text,
    this.time,
    this.remembered = false,
    this.mood = EvaMood.neutral,
    this.tools = const [],
    this.trace = const [],
    this.elapsedSeconds,
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

/// One entry in Eva's notebook — written in the third person, the way she keeps
/// it. `context` is the moment she wrote it down.
class Memory {
  final String id;
  final String text;
  final String when;
  final String tag;
  final bool pinned;
  final String context;

  const Memory({
    required this.id,
    required this.text,
    required this.when,
    required this.tag,
    required this.context,
    this.pinned = false,
  });

  Memory copyWith({String? text, bool? pinned}) => Memory(
        id: id,
        text: text ?? this.text,
        when: when,
        tag: tag,
        context: context,
        pinned: pinned ?? this.pinned,
      );
}

/// What Eva remembers — her notebook, third person.
const List<Memory> initialMemories = [
  Memory(
    id: 'm-pixel',
    text: "Stephan has a border collie named Pixel — smart, and a menace to upholstery.",
    when: 'just now',
    tag: 'pets',
    pinned: true,
    context: '"pixel chewed through the couch cushion while i was on a call" — Tuesday, 9:41 PM',
  ),
  Memory(
    id: 'm-nightowl',
    text: "Stephan's a night owl; the real talks happen after 9pm.",
    when: 'last week',
    tag: 'rhythms',
    context: "Noticed over a few late check-ins — he's never around before nine.",
  ),
  Memory(
    id: 'm-launch',
    text: "Work's been heavy lately — something with a launch he keeps circling back to.",
    when: 'last week',
    tag: 'work',
    context: '"the launch is eating me alive, honestly" — last Thursday',
  ),
  Memory(
    id: 'm-tells',
    text: "He downplays it when he's stressed. Says 'fine' and means 'not fine.'",
    when: '2 weeks ago',
    tag: 'tells',
    pinned: true,
    context: 'A pattern, not one line. He goes quiet and clipped.',
  ),
  Memory(
    id: 'm-coffee',
    text: "Drinks his coffee black. Judged me for suggesting otherwise.",
    when: '3 weeks ago',
    tag: 'small things',
    context: '"oat milk in coffee is a war crime" — his words, not mine.',
  ),
];

/// A daily-driver "brain" Eva can run on. Names/ids mirror the real local stack
/// (LM Studio model ids); switching here is wired to the agent's model later.
class EvaModel {
  final String id;
  final String name;
  final String note;
  const EvaModel({required this.id, required this.name, required this.note});
}

/// The curated switcher list — the keepers from the model gauntlet.
const List<EvaModel> evaModels = [
  EvaModel(id: 'gpt-oss-20b', name: 'gpt-oss · 20B', note: 'daily driver · fast, warm'),
  EvaModel(id: 'qwen3-8b', name: 'Qwen3 · 8B', note: 'steady · the safe default'),
  EvaModel(id: 'qwen3.5-9b', name: 'Qwen3.5 · 9B', note: 'sharper third-person recall'),
  EvaModel(id: 'qwen3-30b-a3b', name: 'Qwen3 · 30B-A3B', note: 'deepest · needs offload'),
];

/// One temperament dial on the "Who she is" sheet.
class TraitDef {
  final String key;
  final String label;
  final String low;
  final String high;
  final String desc;
  const TraitDef(this.key, this.label, this.low, this.high, this.desc);
}

const List<TraitDef> traitDefs = [
  TraitDef('warmth', 'Warmth', 'Cool', 'Devoted', 'How openly she shows she cares.'),
  TraitDef('wit', 'Wit', 'Gentle', 'Sharp', 'How much bite is in the banter.'),
  TraitDef('talk', 'Talkativeness', 'Sparse', 'Chatty', 'How much she says, unprompted.'),
  TraitDef('candor', 'Candor', 'Diplomatic', 'Blunt', 'How directly she tells you the truth.'),
];

/// Eva's editable character sheet.
class Persona {
  String name;
  String pronouns;
  String tagline;
  Map<String, double> traits;
  String backstory;

  Persona({
    required this.name,
    required this.pronouns,
    required this.tagline,
    required this.traits,
    required this.backstory,
  });
}

Persona defaultPersona() => Persona(
      name: 'Eva',
      pronouns: 'she/her',
      tagline: 'Prickly on the outside. Pays attention to everything.',
      traits: {'warmth': 66, 'wit': 78, 'talk': 44, 'candor': 72},
      backstory:
          "You set me up on your own server, so I'm not going anywhere — and I'm not pretending to be cheerful about it. I keep a notebook on you. I remember the small things. Don't make it weird.",
    );

/// A live sample line for the personality sheet — a tiny stand-in for real
/// prompt-shaping, so tuning her traits feels alive.
String personaPreviewLine(Map<String, double> t) {
  final warmth = t['warmth'] ?? 0;
  final wit = t['wit'] ?? 0;
  final talk = t['talk'] ?? 0;
  final candor = t['candor'] ?? 0;
  if (wit >= 70 && warmth < 45) {
    return "Oh. You're back. *doesn't look up from the book* ...Sit. Tell me what broke this time.";
  }
  if (wit >= 65 && warmth >= 45) {
    return "There you are. *sets the book down* Rough one, was it? Out with it — I don't bite. Much.";
  }
  if (warmth >= 72) {
    return "Hey, you. I was hoping you'd come by tonight. *softens* How are you, really?";
  }
  if (candor >= 75 && wit < 55) {
    return "You look tired. I'm not going to pretend otherwise. What happened?";
  }
  if (talk < 35) return "Mm. You're back. ...Good.";
  return "Back, are you? *glances up* Go on, then — how'd it go.";
}
