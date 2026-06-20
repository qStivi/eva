// EvaController — the shared "engine" behind every Eva surface. Owns the
// conversation, the memory notebook, the persona sheet, the active model and
// prefs, plus the typewriter that reveals Eva's replies. Lifted above the
// screens (ChangeNotifier) so a memory she "jots down" in chat shows up in her
// notebook, and so state survives switching tabs. Mock-backed until the real
// Letta backend is wired in — sending cycles a canned in-character reply.

import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../data/mock_chat.dart';

class EvaController extends ChangeNotifier {
  final List<ChatMessage> messages = List.of(openingConversation);
  final List<Memory> memories = List.of(initialMemories);
  final TextEditingController draft = TextEditingController();

  final Persona persona = defaultPersona();
  EvaModel model = evaModels.first;
  String userName = 'Stephan';
  final Map<String, bool> prefs = {'initiative': true, 'voice': false, 'cues': true};

  EvaMood evaMood = EvaMood.neutral;
  bool thinking = false;
  String? typingText;
  EvaMood typingMood = EvaMood.neutral;

  /// Eva's "remembered" scribble — the shell listens and surfaces it as a toast.
  final StreamController<String> _toasts = StreamController<String>.broadcast();
  Stream<String> get toasts => _toasts.stream;

  final List<Timer> _timers = [];
  final Random _rng = Random();
  int _replyIdx = 0;

  bool get busy => thinking || typingText != null;

  @override
  void dispose() {
    for (final t in _timers) {
      t.cancel();
    }
    draft.dispose();
    _toasts.close();
    super.dispose();
  }

  String _now() {
    final d = TimeOfDay.now();
    final h = d.hourOfPeriod == 0 ? 12 : d.hourOfPeriod;
    final m = d.minute.toString().padLeft(2, '0');
    final ap = d.period == DayPeriod.am ? 'AM' : 'PM';
    return '$h:$m $ap';
  }

  void selectModel(EvaModel m) {
    model = m;
    notifyListeners();
  }

  void setPref(String key, bool value) {
    prefs[key] = value;
    notifyListeners();
  }

  void setUserName(String name) {
    userName = name;
    notifyListeners();
  }

  void setTrait(String key, double value) {
    persona.traits[key] = value;
    notifyListeners();
  }

  void setPersonaField({String? name, String? pronouns, String? backstory}) {
    if (name != null) persona.name = name;
    if (pronouns != null) persona.pronouns = pronouns;
    if (backstory != null) persona.backstory = backstory;
    notifyListeners();
  }

  // ---- Notebook ----

  void forget(String id) {
    memories.removeWhere((m) => m.id == id);
    notifyListeners();
  }

  void editMemory(String id, String text) {
    final i = memories.indexWhere((m) => m.id == id);
    if (i != -1) {
      memories[i] = memories[i].copyWith(text: text);
      notifyListeners();
    }
  }

  void togglePin(String id) {
    final i = memories.indexWhere((m) => m.id == id);
    if (i != -1) {
      memories[i] = memories[i].copyWith(pinned: !memories[i].pinned);
      notifyListeners();
    }
  }

  Memory _deriveMemory(String text) {
    final t = text.trim().replaceAll(RegExp(r'\s+'), ' ');
    final clipped = t.length > 90 ? '${t.substring(0, 88)}…' : t;
    return Memory(
      id: 'm-${DateTime.now().microsecondsSinceEpoch}',
      text: 'Stephan mentioned: "$clipped"',
      when: 'just now',
      tag: 'today',
      context: '"${t.length > 120 ? '${t.substring(0, 118)}…' : t}" — just now',
    );
  }

  // ---- Conversation ----

  void send() {
    final text = draft.text.trim();
    if (text.isEmpty || busy) return;
    messages.add(ChatMessage(from: Speaker.you, text: text, time: _now()));
    draft.clear();
    thinking = true;
    evaMood = EvaMood.thinking;
    notifyListeners();

    final reply = cannedReplies[_replyIdx % cannedReplies.length];
    _replyIdx++;
    _timers.add(Timer(
      Duration(milliseconds: 850 + _rng.nextInt(500)),
      () => _typewrite(text, reply),
    ));
  }

  void _typewrite(String userText, CannedReply reply) {
    final full = reply.text;
    final mood = reply.mood;
    final chunk = max(1, (full.length / 34).ceil());
    var i = 0;

    thinking = false;
    evaMood = mood;
    typingMood = mood;
    typingText = '';
    notifyListeners();

    void tick() {
      i = min(full.length, i + chunk);
      typingText = full.substring(0, i);
      notifyListeners();
      if (i < full.length) {
        _timers.add(Timer(const Duration(milliseconds: 42), tick));
      } else {
        _timers.add(Timer(const Duration(milliseconds: 140), () {
          typingText = null;
          messages.add(ChatMessage(
            from: Speaker.eva,
            text: full,
            time: _now(),
            remembered: reply.remembered,
            mood: mood,
          ));
          if (reply.remembered) {
            memories.insert(0, _deriveMemory(userText));
            if (!_toasts.isClosed) _toasts.add(rememberedToast);
          }
          notifyListeners();
        }));
      }
    }

    tick();
  }
}
