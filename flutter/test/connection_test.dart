// Connection & disconnection behaviour of EvaController against a simulated
// Letta backend. Uses http's MockClient (injected into LettaApi) to flip the
// "server" between reachable / unreachable / recovered, so we can assert how the
// app degrades and recovers without a real server. These document the current
// behaviour (including its reliability gaps) and guard against regressions.

import 'dart:async';
import 'dart:convert';

import 'package:eva/api/letta_api.dart';
import 'package:eva/config/eva_settings.dart';
import 'package:eva/data/mock_chat.dart';
import 'package:eva/state/eva_controller.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _agentId = 'agent-eva-1';

/// A mock Letta whose reachability we can toggle at runtime.
class FakeLetta {
  bool up;
  int messageCalls = 0;
  FakeLetta({this.up = true});

  http.Client client() => MockClient((req) async {
        if (!up) {
          // Simulate a refused/closed connection (what http throws on failure).
          throw http.ClientException('Connection refused', req.url);
        }
        final path = req.url.path;
        if (path == '/v1/health/') {
          return http.Response('{"status":"ok"}', 200);
        }
        if (path == '/v1/agents/' && req.method == 'GET') {
          return http.Response(
              jsonEncode([
                {
                  'id': _agentId,
                  'name': 'eva',
                  'llm_config': {'handle': 'openai-proxy/openai/gpt-oss-20b'},
                }
              ]),
              200);
        }
        if (path.endsWith('/core-memory/blocks')) {
          return http.Response(
              jsonEncode([
                {'label': 'human', 'value': 'Stephan likes strong coffee.'},
                {'label': 'persona', 'value': 'I am Eva.'},
              ]),
              200);
        }
        if (path.contains('/archival-memory')) {
          return http.Response(jsonEncode([]), 200);
        }
        if (path.endsWith('/messages') && req.method == 'POST') {
          messageCalls++;
          return http.Response(
              jsonEncode({
                'messages': [
                  {'message_type': 'assistant_message', 'content': 'Hey.'}
                ]
              }),
              200);
        }
        return http.Response('not found', 404);
      });
}

EvaController controllerFor(FakeLetta fake) {
  final settings = EvaSettings(serverUrl: 'http://test.local:8283', agentId: _agentId);
  final api = LettaApi(settings.serverUrl, client: fake.client());
  final c = EvaController(api: api, settings: settings);
  addTearDown(c.dispose); // cancels the health heartbeat timer
  return c;
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  group('connect()', () {
    test('server down -> error status, not live, error surfaced', () async {
      final fake = FakeLetta(up: false);
      final c = controllerFor(fake);

      await c.connect();

      expect(c.status, ConnectionStatus.error);
      expect(c.live, isFalse);
      expect(c.serverError, isNotNull);
    });

    test('server up -> live, agent + memory loaded', () async {
      final fake = FakeLetta(up: true);
      final c = controllerFor(fake);

      await c.connect();

      expect(c.status, ConnectionStatus.live);
      expect(c.live, isTrue);
      // memory notebook populated from the human block
      expect(c.memories.any((m) => m.text.contains('coffee')), isTrue);
    });
  });

  group('disconnection mid-session', () {
    test('send while server is down -> graceful system message, not stuck thinking',
        () async {
      final fake = FakeLetta(up: true);
      final c = controllerFor(fake);
      await c.connect();
      expect(c.live, isTrue);

      // Server drops after we were live.
      fake.up = false;
      c.draft.text = 'you there?';
      c.send();
      await Future<void>.delayed(const Duration(milliseconds: 50));

      // The app must not hang in the "thinking" state.
      expect(c.thinking, isFalse);
      // A system line explains the failure.
      expect(c.messages.where((m) => m.from == Speaker.system).isNotEmpty, isTrue);
      expect(
          c.messages.any((m) => m.text.toLowerCase().contains("couldn't reach eva")), isTrue);
    });

    test('DOCUMENTS current gap: a failed send does NOT flip status off live', () async {
      final fake = FakeLetta(up: true);
      final c = controllerFor(fake);
      await c.connect();

      fake.up = false;
      c.draft.text = 'ping';
      c.send();
      await Future<void>.delayed(const Duration(milliseconds: 50));

      // Reliability gap: status stays `live` even though the send failed — the
      // app has no heartbeat, so it only "notices" a drop on the next send.
      expect(c.status, ConnectionStatus.live);
    });
  });

  group('stuck-thinking guard', () {
    test('cancelThinking frees the composer and drops a late reply', () async {
      final gate = Completer<http.Response>();
      final settings = EvaSettings(serverUrl: 'http://t.local:8283', agentId: _agentId);
      final api = LettaApi(
        settings.serverUrl,
        client: MockClient((req) async {
          final p = req.url.path;
          if (p == '/v1/health/') return http.Response('{"status":"ok"}', 200);
          if (p == '/v1/agents/') {
            return http.Response(
                jsonEncode([
                  {'id': _agentId, 'name': 'eva', 'llm_config': {'handle': 'h'}}
                ]),
                200);
          }
          if (p.endsWith('/core-memory/blocks')) {
            return http.Response(jsonEncode([{'label': 'human', 'value': 'x'}]), 200);
          }
          if (p.contains('/archival-memory')) return http.Response('[]', 200);
          if (p.endsWith('/messages')) return gate.future; // hangs until we release it
          return http.Response('{}', 200);
        }),
      );
      final c = EvaController(api: api, settings: settings);
      addTearDown(c.dispose);
      await c.connect();

      c.draft.text = 'you there?';
      c.send();
      await Future<void>.delayed(const Duration(milliseconds: 20));
      expect(c.busy, isTrue); // stuck waiting on the hung reply

      c.cancelThinking();
      expect(c.busy, isFalse); // composer freed immediately — the actual bug fix

      // The hung reply lands late; the turn guard must drop it (no re-block, no
      // stray Eva message from the abandoned turn).
      final evaBefore = c.messages.where((m) => m.from == Speaker.eva).length;
      gate.complete(http.Response(
          jsonEncode({
            'messages': [
              {'message_type': 'assistant_message', 'content': 'too late'}
            ]
          }),
          200));
      await Future<void>.delayed(const Duration(milliseconds: 20));
      expect(c.busy, isFalse);
      expect(c.messages.where((m) => m.from == Speaker.eva).length, evaBefore);
    });
  });

  group('cloudflare access headers', () {
    test('authHeaders are sent on both reads and writes', () async {
      final seen = <String, Map<String, String>>{};
      final api = LettaApi(
        'https://eva.qstivi.com',
        authHeaders: const {
          'CF-Access-Client-Id': 'id.access',
          'CF-Access-Client-Secret': 'secret',
        },
        client: MockClient((req) async {
          seen[req.url.path] = req.headers;
          if (req.url.path == '/v1/agents/') {
            return http.Response(
                jsonEncode([
                  {'id': _agentId, 'name': 'eva', 'llm_config': {'handle': 'h'}}
                ]),
                200);
          }
          return http.Response('{}', 200);
        }),
      );

      await api.agents(); // a read
      await api.sendMessage(_agentId, 'hi'); // a write

      for (final path in ['/v1/agents/', '/v1/agents/$_agentId/messages']) {
        expect(seen[path]?['cf-access-client-id'], 'id.access', reason: path);
        expect(seen[path]?['cf-access-client-secret'], 'secret', reason: path);
      }
      // writes still carry JSON content-type alongside the auth headers
      expect(seen['/v1/agents/$_agentId/messages']?['content-type'], contains('application/json'));
    });
  });

  group('recovery', () {
    test('connect again after the server comes back -> live', () async {
      final fake = FakeLetta(up: false);
      final c = controllerFor(fake);
      await c.connect();
      expect(c.status, ConnectionStatus.error);

      // Server comes back; a fresh connect() recovers.
      fake.up = true;
      await c.connect();

      expect(c.status, ConnectionStatus.live);
      expect(c.live, isTrue);
    });

    test('sending works again after a drop-then-recover (no manual reconnect needed)',
        () async {
      final fake = FakeLetta(up: true);
      final c = controllerFor(fake);
      await c.connect();

      fake.up = false; // drop
      c.draft.text = 'first';
      c.send();
      await Future<void>.delayed(const Duration(milliseconds: 50));

      fake.up = true; // recover
      final before = fake.messageCalls;
      c.draft.text = 'second';
      c.send();
      await Future<void>.delayed(const Duration(milliseconds: 50));

      // The next send reaches the server again.
      expect(fake.messageCalls, greaterThan(before));
    });
  });
}
