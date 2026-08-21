// LettaApi — a thin client for the local Letta server (the real Eva backend).
// Most calls (memory, models, archival) go straight to Letta (configurable base
// URL) since they don't need any routing. Chat messages go through eva-web's
// /api/chat instead (sendMessageViaWeb) — see EvaSettings.webBaseUrl/webHeaders
// and eva-web/app.py's docstring for why. parseReply mirrors
// eva-web/app.py:letta_send()'s own parsing of Letta's raw message list and is
// still used by sendMessage (kept for direct-to-Letta testing/fallback) — pure
// and unit-tested.

import 'dart:convert';

import 'package:http/http.dart' as http;

class LettaException implements Exception {
  final String message;
  const LettaException(this.message);
  @override
  String toString() => 'LettaException: $message';
}

/// One assistant turn: the reply text plus any tools Eva invoked.
class LettaReply {
  final String text;
  final List<String> tools;
  const LettaReply(this.text, this.tools);
}

class AgentSummary {
  final String id;
  final String name;
  final String? modelHandle; // llm_config.handle, e.g. openai-proxy/openai/gpt-oss-20b
  const AgentSummary({required this.id, required this.name, this.modelHandle});
}

/// A core-memory block (e.g. `human`, `persona`).
class MemoryBlock {
  final String label;
  final String value;
  const MemoryBlock(this.label, this.value);
}

/// An archival-memory passage.
class Passage {
  final String id;
  final String text;
  const Passage(this.id, this.text);
}

/// Eva's scheduled-check-in config, from eva-task-runner via eva-web's
/// /api/checkin/config proxy (see eva-task-runner/runner.py).
class CheckinConfig {
  final bool enabled;
  final int intervalMinutes;
  final String quietStart; // "HH:MM"
  final String quietEnd; // "HH:MM"
  final double nextDueAt; // epoch seconds
  const CheckinConfig({
    required this.enabled,
    required this.intervalMinutes,
    required this.quietStart,
    required this.quietEnd,
    required this.nextDueAt,
  });

  factory CheckinConfig.fromJson(Map<String, dynamic> j) => CheckinConfig(
        enabled: j['enabled'] == true || j['enabled'] == 1,
        intervalMinutes: (j['interval_minutes'] as num).toInt(),
        quietStart: j['quiet_start'] as String,
        quietEnd: j['quiet_end'] as String,
        nextDueAt: (j['next_due_at'] as num).toDouble(),
      );
}

class LettaApi {
  final String baseUrl;

  /// Extra headers attached to every request (e.g. Cloudflare Access service-token
  /// pair when reaching Letta over a public tunnel). Empty for LAN/tailnet.
  final Map<String, String> authHeaders;
  final http.Client _client;

  LettaApi(String baseUrl, {http.Client? client, Map<String, String>? authHeaders})
      : baseUrl = baseUrl.replaceAll(RegExp(r'/+$'), ''),
        authHeaders = authHeaders ?? const {},
        _client = client ?? http.Client();

  Uri _u(String path) => Uri.parse('$baseUrl$path');
  static const _jsonType = {'Content-Type': 'application/json'};
  // Headers for reads (auth only) and writes (auth + JSON content-type).
  Map<String, String> get _read => authHeaders;
  Map<String, String> get _json => {..._jsonType, ...authHeaders};
  static const _quick = Duration(seconds: 8);
  static const _slow = Duration(seconds: 300); // local models can be slow

  Future<bool> health() async {
    try {
      final r =
          await _client.get(_u('/v1/health/'), headers: _read).timeout(const Duration(seconds: 6));
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<List<AgentSummary>> agents() async {
    final r = await _client.get(_u('/v1/agents/'), headers: _read).timeout(_quick);
    _ensureOk(r.statusCode, r.body);
    final list = jsonDecode(r.body) as List;
    return [
      for (final a in list)
        if (a is Map)
          AgentSummary(
            id: a['id'] as String,
            name: (a['name'] ?? '') as String,
            modelHandle: (a['llm_config'] is Map) ? a['llm_config']['handle'] as String? : null,
          ),
    ];
  }

  /// Send one user turn through eva-web's /api/chat instead of straight to
  /// Letta. eva-web applies lazy-toolset preloading + cost-tiered model
  /// routing before forwarding to Letta — the same treatment its browser UI
  /// already gets (see eva-web/app.py's docstring) — then returns the reply
  /// in its own shape, not Letta's raw message list. [webBaseUrl] and
  /// [webHeaders] come from EvaSettings.
  Future<LettaReply> sendMessageViaWeb(
      String webBaseUrl, Map<String, String> webHeaders, String text) async {
    final url = Uri.parse('${webBaseUrl.replaceAll(RegExp(r'/+$'), '')}/api/chat');
    final r = await _client
        .post(url, headers: {..._jsonType, ...webHeaders}, body: jsonEncode({'message': text}))
        .timeout(_slow);
    _ensureOk(r.statusCode, r.body);
    final decoded = jsonDecode(r.body);
    if (decoded is! Map) throw const LettaException('unexpected /api/chat response shape');
    if (decoded['error'] != null) throw LettaException(decoded['error'].toString());
    final reply = (decoded['reply'] as String?) ?? '(no reply)';
    final tools = ((decoded['tools'] as List?) ?? const []).cast<String>();
    return LettaReply(reply, tools);
  }

  Future<LettaReply> sendMessage(String agentId, String text) async {
    final r = await _client
        .post(_u('/v1/agents/$agentId/messages'),
            headers: _json,
            body: jsonEncode({
              'messages': [
                {'role': 'user', 'content': text},
              ],
            }))
        .timeout(_slow);
    _ensureOk(r.statusCode, r.body);
    return parseReply(r.body);
  }

  Future<CheckinConfig> getCheckinConfig(String webBaseUrl, Map<String, String> webHeaders) async {
    final url = Uri.parse('${webBaseUrl.replaceAll(RegExp(r'/+$'), '')}/api/checkin/config');
    final r = await _client.get(url, headers: webHeaders).timeout(_quick);
    _ensureOk(r.statusCode, r.body);
    return CheckinConfig.fromJson(jsonDecode(r.body) as Map<String, dynamic>);
  }

  Future<CheckinConfig> setCheckinConfig(
    String webBaseUrl,
    Map<String, String> webHeaders, {
    bool? enabled,
    int? intervalMinutes,
    String? quietStart,
    String? quietEnd,
  }) async {
    final url = Uri.parse('${webBaseUrl.replaceAll(RegExp(r'/+$'), '')}/api/checkin/config');
    final body = <String, dynamic>{
      if (enabled != null) 'enabled': enabled,
      if (intervalMinutes != null) 'interval_minutes': intervalMinutes,
      if (quietStart != null) 'quiet_start': quietStart,
      if (quietEnd != null) 'quiet_end': quietEnd,
    };
    final r = await _client
        .post(url, headers: {..._jsonType, ...webHeaders}, body: jsonEncode(body))
        .timeout(_quick);
    _ensureOk(r.statusCode, r.body);
    return CheckinConfig.fromJson(jsonDecode(r.body) as Map<String, dynamic>);
  }

  /// Pure parser for a Letta /messages response. Mirrors eva-web's logic.
  static LettaReply parseReply(String body) {
    final decoded = jsonDecode(body);
    final List msgs = decoded is Map && decoded['messages'] is List
        ? decoded['messages'] as List
        : (decoded is List ? decoded : const []);
    final parts = <String>[];
    final tools = <String>[];
    for (final m in msgs) {
      if (m is! Map) continue;
      switch (m['message_type']) {
        case 'assistant_message':
          final c = m['content'];
          if (c is String && c.trim().isNotEmpty) {
            parts.add(c.trim());
          } else if (c is List) {
            // some builds return content as a list of {type,text} parts
            for (final part in c) {
              if (part is Map && part['text'] is String) parts.add((part['text'] as String).trim());
            }
          }
        case 'tool_call_message':
          final tc = m['tool_call'];
          if (tc is Map && tc['name'] is String) tools.add(tc['name'] as String);
      }
    }
    final reply = parts.where((p) => p.isNotEmpty).join('\n').trim();
    return LettaReply(reply.isEmpty ? '(no reply)' : reply, tools);
  }

  /// Non-embedding model handles available to switch to.
  Future<List<String>> modelHandles() async {
    final r = await _client.get(_u('/v1/models/'), headers: _read).timeout(_quick);
    _ensureOk(r.statusCode, r.body);
    final list = jsonDecode(r.body) as List;
    return [
      for (final m in list)
        if (m is Map && m['handle'] is String && !(m['handle'] as String).contains('embed'))
          m['handle'] as String,
    ];
  }

  Future<void> setModel(String agentId, String handle) async {
    final r = await _client
        .patch(_u('/v1/agents/$agentId'), headers: _json, body: jsonEncode({'model': handle}))
        .timeout(_quick);
    _ensureOk(r.statusCode, r.body);
  }

  Future<List<MemoryBlock>> blocks(String agentId) async {
    final r =
        await _client.get(_u('/v1/agents/$agentId/core-memory/blocks'), headers: _read).timeout(_quick);
    _ensureOk(r.statusCode, r.body);
    final list = jsonDecode(r.body) as List;
    return [
      for (final b in list)
        if (b is Map) MemoryBlock((b['label'] ?? '') as String, (b['value'] ?? '') as String),
    ];
  }

  Future<void> updateBlock(String agentId, String label, String value) async {
    final r = await _client
        .patch(_u('/v1/agents/$agentId/core-memory/blocks/$label'),
            headers: _json, body: jsonEncode({'value': value}))
        .timeout(_quick);
    _ensureOk(r.statusCode, r.body);
  }

  Future<List<Passage>> archival(String agentId) async {
    final r = await _client
        .get(_u('/v1/agents/$agentId/archival-memory?limit=100'), headers: _read)
        .timeout(_quick);
    _ensureOk(r.statusCode, r.body);
    final decoded = jsonDecode(r.body);
    final List list = decoded is List ? decoded : (decoded['passages'] as List? ?? const []);
    return [
      for (final p in list)
        if (p is Map)
          Passage((p['id'] ?? '') as String, ((p['text'] ?? p['content']) ?? '') as String),
    ];
  }

  /// Model ids LM Studio currently has loaded, via the tunnel's /lmstudio/status
  /// bridge. Returns null when the bridge isn't reachable (e.g. LAN without it,
  /// or the server is down) so the UI can distinguish "cold" from "unknown".
  Future<Set<String>?> loadedModels() async {
    try {
      final r = await _client.get(_u('/lmstudio/status'), headers: _read).timeout(_quick);
      if (r.statusCode != 200) return null;
      final d = jsonDecode(r.body);
      if (d is! Map || d['ok'] != true) return null;
      final loaded = (d['loaded'] as List?) ?? const [];
      return {for (final e in loaded) e.toString()};
    } catch (_) {
      return null;
    }
  }

  Future<void> deleteArchival(String agentId, String passageId) async {
    final r = await _client
        .delete(_u('/v1/agents/$agentId/archival-memory/$passageId'), headers: _read)
        .timeout(_quick);
    _ensureOk(r.statusCode, r.body);
  }

  void _ensureOk(int code, String body) {
    if (code >= 400) {
      throw LettaException('HTTP $code: ${body.length > 200 ? body.substring(0, 200) : body}');
    }
  }

  void close() => _client.close();
}
