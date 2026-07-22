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

/// Whether LM Studio currently has Eva's model loaded (warm), not (cold — the
/// next message will pay a load), or we can't tell (bridge unreachable/offline).
enum ModelLoad { unknown, loaded, cold }

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
  ModelLoad modelLoad = ModelLoad.unknown;

  bool get live => status == ConnectionStatus.live && _api != null && _agentId != null;
  String get serverUrl => _settings?.serverUrl ?? kDefaultServerUrl;
  String get accessClientId => _settings?.accessClientId ?? '';
  String get accessClientSecret => _settings?.accessClientSecret ?? '';
  String get agentName => _agentName;

  final StreamController<String> _toasts = StreamController<String>.broadcast();
  Stream<String> get toasts => _toasts.stream;

  final List<Timer> _timers = [];
  final Random _rng = Random();
  int _replyIdx = 0;

  // Monotonic turn id: every send/cancel bumps it, so a slow or abandoned reply
  // that lands late can be dropped instead of re-freezing the UI in "thinking".
  int _turn = 0;
  // Health heartbeat: keeps `status` honest while idle and auto-recovers.
  Timer? _heartbeat;
  int _missedPulses = 0;
  bool _disposed = false;

  EvaController({LettaApi? api, EvaSettings? settings}) {
    _api = api;
    _settings = settings;
    _agentId = settings?.agentId;
  }

  bool get busy => thinking || typingText != null;

  @override
  void dispose() {
    _disposed = true;
    _heartbeat?.cancel();
    for (final t in _timers) {
      t.cancel();
    }
    draft.dispose();
    _toasts.close();
    _api?.close();
    super.dispose();
  }

  /// Stop waiting on the current turn and return to idle. Always safe to call —
  /// this is the escape hatch when a reply is slow or the connection stalled, so
  /// the composer never stays stuck in "thinking". Any reply still in flight is
  /// dropped via the turn guard.
  void cancelThinking() {
    _turn++;
    for (final t in _timers) {
      t.cancel();
    }
    _timers.clear();
    thinking = false;
    typingText = null;
    evaMood = EvaMood.neutral;
    notifyListeners();
  }

  // ---- health heartbeat ----------------------------------------------------

  void _startHeartbeat() {
    _heartbeat?.cancel();
    _missedPulses = 0;
    _heartbeat = Timer.periodic(const Duration(seconds: 20), (_) => _pulse());
  }

  /// Probe the server while idle so the connection dot reflects reality and a
  /// dropped link auto-recovers without a manual reconnect. Skips while busy so
  /// it never interferes with an in-flight turn; only flips to "error" after two
  /// consecutive misses so a single slow probe doesn't cause flapping.
  Future<void> _pulse() async {
    final api = _api;
    if (api == null || busy || status == ConnectionStatus.connecting) return;
    final ok = await api.health();
    if (_disposed) return;
    if (ok) {
      _missedPulses = 0;
      if (status == ConnectionStatus.error && _agentId != null) {
        status = ConnectionStatus.live;
        serverError = null;
        notifyListeners();
      }
    } else if (status == ConnectionStatus.live) {
      if (++_missedPulses >= 2) {
        status = ConnectionStatus.error;
        serverError = 'connection lost';
        notifyListeners();
      }
    }
    await _pollModelLoad();
  }

  /// Eva's model as LM Studio names it: the Letta handle minus its provider
  /// prefix (openai-proxy/openai/gpt-oss-20b -> openai/gpt-oss-20b).
  String? get _loadedTargetId {
    final handle = _handleById[model.id] ?? model.id;
    final slash = handle.indexOf('/');
    return slash < 0 ? handle : handle.substring(slash + 1);
  }

  /// Refresh whether LM Studio has Eva's model warm (via the /lmstudio/status
  /// bridge). Best-effort; unreachable bridge => unknown.
  Future<void> _pollModelLoad() async {
    final api = _api;
    if (api == null || status != ConnectionStatus.live) return;
    final loaded = await api.loadedModels();
    if (_disposed) return;
    final target = _loadedTargetId;
    final next = loaded == null
        ? ModelLoad.unknown
        : (target != null && loaded.contains(target))
            ? ModelLoad.loaded
            : ModelLoad.cold;
    if (next != modelLoad) {
      modelLoad = next;
      notifyListeners();
    }
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
    _startHeartbeat(); // keep status honest + auto-recover from here on
    unawaited(_pollModelLoad());
    notifyListeners();
  }

  /// Point at a different server URL (Settings) and reconnect. Optionally updates
  /// the Cloudflare Access service-token pair used for public-tunnel access.
  Future<void> reconfigure(String url, {String? accessClientId, String? accessClientSecret}) async {
    final settings = _settings;
    if (settings == null) return; // mock-only build
    settings.serverUrl = url.trim();
    if (accessClientId != null) settings.accessClientId = accessClientId.trim();
    if (accessClientSecret != null) settings.accessClientSecret = accessClientSecret.trim();
    settings.agentId = null;
    _agentId = null;
    await settings.save();
    _api?.close();
    _api = LettaApi(settings.serverUrl, authHeaders: settings.accessHeaders);
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
    modelLoad = ModelLoad.unknown; // new model — recheck whether it's warm
    notifyListeners();
    if (live) {
      final handle = _handleById[m.id] ?? m.id;
      try {
        await _api!.setModel(_agentId!, handle);
        _emitToast('*shrugs* New brain. Same me. We’ll see how it goes.');
        unawaited(_pollModelLoad());
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
    final myTurn = ++_turn;
    notifyListeners();
    if (live) {
      unawaited(_sendLive(text, myTurn));
    } else {
      final reply = cannedReplies[_replyIdx % cannedReplies.length];
      _replyIdx++;
      _timers.add(Timer(
        Duration(milliseconds: 850 + _rng.nextInt(500)),
        () {
          if (myTurn == _turn) _typewriteMock(text, reply);
        },
      ));
    }
  }

  Future<void> _sendLive(String userText, int myTurn) async {
    final before = memories.length;
    try {
      final reply = await _api!.sendMessage(_agentId!, userText);
      if (_disposed || myTurn != _turn) return; // disposed, cancelled, or superseded
      _runTypewriter(reply.text, EvaMood.neutral, false, () async {
        await _loadMemory();
        if (memories.length > before) _emitToast(rememberedToast);
        unawaited(_pollModelLoad()); // the model just ran — should read as loaded now
      }, tools: reply.tools);
      return;
    } catch (e) {
      if (_disposed || myTurn != _turn) return; // cancelled/disposed — user moved on
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
  void _runTypewriter(String full, EvaMood mood, bool remembered, FutureOr<void> Function() onDone,
      {List<String> tools = const []}) {
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
            tools: tools,
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
