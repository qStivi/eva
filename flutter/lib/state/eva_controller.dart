// EvaController — the shared engine behind every Eva surface. Owns the
// conversation, memory notebook, persona sheet, active model + prefs, plus the
// typewriter that reveals replies.
//
// It runs in one of two modes:
//   * LIVE  — talks to the real Letta agent (chat, model switch, notebook) when a
//             reachable server is configured (see connect()).
//   * MOCK  — the original canned, offline behaviour (also what tests use).
// Construct with an api + settings for live; with neither for mock.

import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../api/letta_api.dart';
import '../config/eva_settings.dart';
import '../data/mock_chat.dart';

enum ConnectionStatus { mock, connecting, live, error }

/// Curated daily-driver id -> Letta model handle.
const Map<String, String> _handleById = {
  'gpt-oss-20b': 'openai-proxy/openai/gpt-oss-20b',
  'qwen3-8b': 'openai-proxy/qwen/qwen3-8b',
  'qwen3.5-9b': 'openai-proxy/qwen/qwen3.5-9b',
  'qwen3-30b-a3b': 'openai-proxy/qwen3-30b-a3b-instruct-2507@q4_k_m',
};

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

  // ---- connection ----
  LettaApi? _api;
  EvaSettings? _settings;
  String? _agentId;
  String _agentName = 'eva';
  ConnectionStatus status = ConnectionStatus.mock;
  String? serverError;

  bool get live => status == ConnectionStatus.live && _api != null && _agentId != null;
  String get serverUrl => _settings?.serverUrl ?? kDefaultServerUrl;
  String get agentName => _agentName;

  final StreamController<String> _toasts = StreamController<String>.broadcast();
  Stream<String> get toasts => _toasts.stream;

  final List<Timer> _timers = [];
  final Random _rng = Random();
  int _replyIdx = 0;

  EvaController({LettaApi? api, EvaSettings? settings}) {
    _api = api;
    _settings = settings;
    _agentId = settings?.agentId;
  }

  bool get busy => thinking || typingText != null;

  @override
  void dispose() {
    for (final t in _timers) {
      t.cancel();
    }
    draft.dispose();
    _toasts.close();
    _api?.close();
    super.dispose();
  }

  void _emitToast(String text) {
    if (!_toasts.isClosed) _toasts.add(text);
  }

  String _now() {
    final d = TimeOfDay.now();
    final h = d.hourOfPeriod == 0 ? 12 : d.hourOfPeriod;
    final m = d.minute.toString().padLeft(2, '0');
    final ap = d.period == DayPeriod.am ? 'AM' : 'PM';
    return '$h:$m $ap';
  }

  // ---- connect / reconfigure ----

  /// Try to go live: health-check, resolve the agent, read its model + memory.
  /// Falls back to mock on any failure (the UI shows the error).
  Future<void> connect() async {
    final api = _api;
    if (api == null) {
      status = ConnectionStatus.mock;
      notifyListeners();
      return;
    }
    status = ConnectionStatus.connecting;
    serverError = null;
    notifyListeners();
    try {
      if (!await api.health()) throw const LettaException('server not reachable');
      final agents = await api.agents();
      if (agents.isEmpty) throw const LettaException('no agents on server');
      final agent = agents.firstWhere(
        (a) => a.id == _agentId || a.name == 'eva',
        orElse: () => agents.first,
      );
      _agentId = agent.id;
      _agentName = agent.name;
      _settings?.agentId = agent.id;
      unawaited(_settings?.save());
      if (agent.modelHandle != null) {
        model = _modelForHandle(agent.modelHandle!);
      }
      // Switch from the seeded conversation to a clean live slate.
      messages
        ..clear()
        ..add(ChatMessage(
          from: Speaker.eva,
          text: "*looks up* …Oh. It's you. Go on, then — I'm listening.",
          time: _now(),
        ));
      await _loadMemory();
      status = ConnectionStatus.live;
    } catch (e) {
      status = ConnectionStatus.error;
      serverError = e is LettaException ? e.message : e.toString();
    }
    notifyListeners();
  }

  /// Point at a different server URL (Settings) and reconnect.
  Future<void> reconfigure(String url) async {
    final settings = _settings;
    if (settings == null) return; // mock-only build
    settings.serverUrl = url.trim();
    settings.agentId = null;
    _agentId = null;
    await settings.save();
    _api?.close();
    _api = LettaApi(settings.serverUrl);
    await connect();
  }

  EvaModel _modelForHandle(String handle) {
    for (final m in evaModels) {
      if (_handleById[m.id] == handle) return m;
    }
    // Unknown model the agent is on — show it as-is so Settings isn't misleading.
    return EvaModel(id: handle, name: handle.split('/').last, note: 'current');
  }

  // ---- persona / prefs (local only for now) ----

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

  // ---- model switch ----

  Future<void> selectModel(EvaModel m) async {
    final previous = model;
    model = m;
    notifyListeners();
    if (live) {
      final handle = _handleById[m.id] ?? m.id;
      try {
        await _api!.setModel(_agentId!, handle);
        _emitToast('*shrugs* New brain. Same me. We’ll see how it goes.');
      } catch (e) {
        model = previous;
        _emitToast("Couldn't switch brains — ${_short(e)}");
        notifyListeners();
      }
    }
  }

  // ---- notebook ----

  Future<void> _loadMemory() async {
    if (_api == null || _agentId == null) return;
    final notes = <Memory>[];
    final blocks = await _api!.blocks(_agentId!);
    final human = blocks
        .firstWhere((b) => b.label == 'human', orElse: () => const MemoryBlock('human', ''))
        .value;
    var idx = 0;
    for (final line in human.split('\n')) {
      final t = line.trim();
      if (t.isEmpty) continue;
      notes.add(Memory(
        id: 'human:${idx++}',
        text: t,
        when: '',
        tag: 'note',
        context: 'From the notes she keeps about you.',
      ));
    }
    try {
      for (final p in await _api!.archival(_agentId!)) {
        if (p.text.trim().isEmpty) continue;
        notes.add(Memory(
          id: 'arch:${p.id}',
          text: p.text.trim(),
          when: '',
          tag: 'note',
          context: 'A note she filed away.',
        ));
      }
    } catch (_) {
      // archival is optional; ignore if the endpoint shape differs.
    }
    memories
      ..clear()
      ..addAll(notes);
    notifyListeners();
  }

  void forget(String id) {
    if (live) {
      unawaited(_forgetLive(id));
      return;
    }
    memories.removeWhere((m) => m.id == id);
    notifyListeners();
  }

  Future<void> _forgetLive(String id) async {
    try {
      if (id.startsWith('arch:')) {
        await _api!.deleteArchival(_agentId!, id.substring(5));
      } else {
        // Rebuild the human block without the forgotten line.
        final kept = memories
            .where((m) => m.id.startsWith('human:') && m.id != id)
            .map((m) => m.text)
            .join('\n');
        await _api!.updateBlock(_agentId!, 'human', kept);
      }
      await _loadMemory();
    } catch (e) {
      _emitToast("Couldn't forget that — ${_short(e)}");
    }
  }

  void editMemory(String id, String text) {
    final i = memories.indexWhere((m) => m.id == id);
    if (i == -1) return;
    memories[i] = memories[i].copyWith(text: text);
    notifyListeners();
    if (live && id.startsWith('human:')) {
      final kept = memories
          .where((m) => m.id.startsWith('human:'))
          .map((m) => m.text)
          .join('\n');
      unawaited(_api!.updateBlock(_agentId!, 'human', kept).catchError((_) {}));
    }
  }

  void togglePin(String id) {
    // Pinning is a mock-only nicety; Letta has no equivalent.
    if (live) return;
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

  // ---- conversation ----

  void send() {
    final text = draft.text.trim();
    if (text.isEmpty || busy) return;
    messages.add(ChatMessage(from: Speaker.you, text: text, time: _now()));
    draft.clear();
    thinking = true;
    evaMood = EvaMood.thinking;
    notifyListeners();
    if (live) {
      unawaited(_sendLive(text));
    } else {
      final reply = cannedReplies[_replyIdx % cannedReplies.length];
      _replyIdx++;
      _timers.add(Timer(
        Duration(milliseconds: 850 + _rng.nextInt(500)),
        () => _typewriteMock(text, reply),
      ));
    }
  }

  Future<void> _sendLive(String userText) async {
    final before = memories.length;
    try {
      final reply = await _api!.sendMessage(_agentId!, userText);
      _runTypewriter(reply.text, EvaMood.neutral, false, () async {
        await _loadMemory();
        if (memories.length > before) _emitToast(rememberedToast);
      });
    } catch (e) {
      thinking = false;
      evaMood = EvaMood.neutral;
      messages.add(ChatMessage(
        from: Speaker.system,
        text: "couldn't reach Eva — ${_short(e)}",
      ));
      notifyListeners();
    }
  }

  void _typewriteMock(String userText, CannedReply reply) {
    _runTypewriter(reply.text, reply.mood, reply.remembered, () {
      if (reply.remembered) {
        memories.insert(0, _deriveMemory(userText));
        _emitToast(rememberedToast);
      }
    });
  }

  /// Reveal [full] one calm chunk at a time, then commit the message + onDone.
  void _runTypewriter(String full, EvaMood mood, bool remembered, FutureOr<void> Function() onDone) {
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
            remembered: remembered,
            mood: mood,
          ));
          notifyListeners();
          onDone();
        }));
      }
    }

    tick();
  }

  String _short(Object e) {
    final s = e is LettaException ? e.message : e.toString();
    return s.length > 80 ? '${s.substring(0, 78)}…' : s;
  }
}
