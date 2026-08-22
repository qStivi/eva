// Unit test for the Letta /messages reply parser — pure, no network.

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:eva/api/letta_api.dart';

void main() {
  test('parseReply collects assistant content and tool names, ignores reasoning', () {
    final body = jsonEncode({
      'messages': [
        {'message_type': 'reasoning_message', 'reasoning': 'thinking…'},
        {'message_type': 'tool_call_message', 'tool_call': {'name': 'searxng_web_search'}},
        {'message_type': 'assistant_message', 'content': '  *glances up* Fine. Here.  '},
      ],
    });
    final r = LettaApi.parseReply(body);
    expect(r.text, '*glances up* Fine. Here.');
    expect(r.tools, ['searxng_web_search']);
  });

  test('parseReply falls back when there is no assistant content', () {
    final r = LettaApi.parseReply(jsonEncode({'messages': []}));
    expect(r.text, '(no reply)');
    expect(r.tools, isEmpty);
  });

  test('parseReply handles list-style content parts', () {
    final body = jsonEncode({
      'messages': [
        {
          'message_type': 'assistant_message',
          'content': [
            {'type': 'text', 'text': 'one'},
            {'type': 'text', 'text': 'two'},
          ],
        },
      ],
    });
    expect(LettaApi.parseReply(body).text, 'one\ntwo');
  });

  test('parseHistory groups reasoning + tool calls under the assistant turn that follows', () {
    final raw = [
      {
        'message_type': 'user_message',
        'content': 'what level am I on Steam?',
        'date': '2026-08-22T10:00:00Z',
      },
      {'message_type': 'reasoning_message', 'reasoning': 'let me check'},
      {
        'message_type': 'tool_call_message',
        'tool_call': {
          'name': 'search_tools',
          'arguments': '{"query": "steam level"}',
          'tool_call_id': 'c1',
        },
      },
      {
        'message_type': 'tool_return_message',
        'tool_call_id': 'c1',
        'status': 'success',
        'tool_return': '{"matches": []}',
      },
      {
        'message_type': 'assistant_message',
        'content': "You're level 42.",
        'date': '2026-08-22T10:00:05Z',
      },
    ];
    final history = LettaApi.parseHistory(raw);
    expect(history.length, 2);
    expect(history[0].role, HistoryRole.user);
    expect(history[0].trace, isEmpty);
    final reply = history[1];
    expect(reply.role, HistoryRole.assistant);
    expect(reply.text, "You're level 42.");
    expect(reply.elapsedSeconds, 5.0);
    expect(reply.trace, hasLength(2));
    expect(reply.trace[0].kind, TraceKind.reasoning);
    expect(reply.trace[0].text, 'let me check');
    expect(reply.trace[1].kind, TraceKind.toolCall);
    expect(reply.trace[1].name, 'search_tools');
    expect(reply.trace[1].args, {'query': 'steam level'});
    expect(reply.trace[1].status, 'success');
  });

  test('parseHistory drops empty reasoning and starts a fresh trace per turn', () {
    final raw = [
      {'message_type': 'user_message', 'content': 'hi', 'date': '2026-08-22T10:00:00Z'},
      {'message_type': 'reasoning_message', 'reasoning': null},
      {'message_type': 'assistant_message', 'content': 'hey', 'date': '2026-08-22T10:00:01Z'},
      {'message_type': 'user_message', 'content': 'again', 'date': '2026-08-22T10:05:00Z'},
      {'message_type': 'assistant_message', 'content': 'sure', 'date': '2026-08-22T10:05:01Z'},
    ];
    final history = LettaApi.parseHistory(raw);
    // No stray trace entries leak from the first turn into the second.
    expect(history.where((h) => h.role == HistoryRole.assistant).every((h) => h.trace.isEmpty),
        isTrue);
  });
}
