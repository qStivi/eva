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
}
