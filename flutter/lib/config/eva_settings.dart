// EvaSettings — persisted connection config (where Eva's Letta server lives and
// which agent to talk to). Stored via shared_preferences. Desktop works with the
// localhost default; on the phone the user points it at the PC's LAN IP.

import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

const String kDefaultServerUrl = 'http://localhost:8283';

class EvaSettings {
  String serverUrl;
  String? agentId;

  // Cloudflare Access service-token credentials. Only needed when the server is
  // reached over a public Cloudflare Tunnel (eva.qstivi.com); empty for LAN/tailnet
  // access. When set, they're sent as CF-Access-Client-Id / CF-Access-Client-Secret
  // on every request so Access lets us through to Letta (and eva-web, below).
  String accessClientId;
  String accessClientSecret;

  // eva-web's own Basic-auth credentials (separate from Cloudflare Access —
  // this gates eva-web itself, on the LAN too, not just over the tunnel).
  // Chat messages go through eva-web rather than straight to Letta so the
  // app gets the same lazy-toolset + cost-tiered model routing the browser
  // UI already has (see eva-web/app.py's docstring). Defaults match
  // eva-web's own default username.
  String chatUser;
  String chatPassword;

  EvaSettings({
    this.serverUrl = kDefaultServerUrl,
    this.agentId,
    this.accessClientId = '',
    this.accessClientSecret = '',
    this.chatUser = 'eva',
    this.chatPassword = '',
  });

  static const _kUrl = 'eva.serverUrl';
  static const _kAgent = 'eva.agentId';
  static const _kAccessId = 'eva.cfAccessClientId';
  static const _kAccessSecret = 'eva.cfAccessClientSecret';
  static const _kChatUser = 'eva.chatUser';
  static const _kChatPassword = 'eva.chatPassword';

  /// Headers to attach to every request; empty unless an Access token is set.
  Map<String, String> get accessHeaders => accessClientId.isEmpty
      ? const {}
      : {
          'CF-Access-Client-Id': accessClientId,
          'CF-Access-Client-Secret': accessClientSecret,
        };

  /// Where eva-web lives: same host as Letta, but its own port on the LAN
  /// (eva-web and Letta are always separate fixed ports — 8284 vs 8283), or
  /// the same tunnel origin when reached over https (eva.qstivi.com routes
  /// /api/* to eva-web alongside Letta's own routes).
  String get webBaseUrl {
    final uri = Uri.tryParse(serverUrl);
    if (uri == null || uri.scheme == 'https') return serverUrl;
    return '${uri.scheme}://${uri.host}:8284';
  }

  /// Headers for eva-web's /api/chat: Cloudflare Access (when over the
  /// tunnel) plus eva-web's own Basic auth (always — it gates the LAN path
  /// too, not just the tunnel).
  Map<String, String> get webHeaders {
    final h = {...accessHeaders};
    if (chatUser.isNotEmpty || chatPassword.isNotEmpty) {
      h['Authorization'] = 'Basic ${base64Encode(utf8.encode('$chatUser:$chatPassword'))}';
    }
    return h;
  }

  static Future<EvaSettings> load() async {
    final p = await SharedPreferences.getInstance();
    return EvaSettings(
      serverUrl: p.getString(_kUrl) ?? kDefaultServerUrl,
      agentId: p.getString(_kAgent),
      accessClientId: p.getString(_kAccessId) ?? '',
      accessClientSecret: p.getString(_kAccessSecret) ?? '',
      chatUser: p.getString(_kChatUser) ?? 'eva',
      chatPassword: p.getString(_kChatPassword) ?? '',
    );
  }

  Future<void> save() async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kUrl, serverUrl);
    await p.setString(_kAccessId, accessClientId);
    await p.setString(_kAccessSecret, accessClientSecret);
    await p.setString(_kChatUser, chatUser);
    await p.setString(_kChatPassword, chatPassword);
    if (agentId != null) {
      await p.setString(_kAgent, agentId!);
    } else {
      await p.remove(_kAgent);
    }
  }
}
