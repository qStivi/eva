// EvaSettings — persisted connection config (where Eva's Letta server lives and
// which agent to talk to). Stored via shared_preferences. Desktop works with the
// localhost default; on the phone the user points it at the PC's LAN IP.

import 'package:shared_preferences/shared_preferences.dart';

const String kDefaultServerUrl = 'http://localhost:8283';

class EvaSettings {
  String serverUrl;
  String? agentId;

  // Cloudflare Access service-token credentials. Only needed when the server is
  // reached over a public Cloudflare Tunnel (eva.qstivi.com); empty for LAN/tailnet
  // access. When set, they're sent as CF-Access-Client-Id / CF-Access-Client-Secret
  // on every request so Access lets us through to Letta.
  String accessClientId;
  String accessClientSecret;

  EvaSettings({
    this.serverUrl = kDefaultServerUrl,
    this.agentId,
    this.accessClientId = '',
    this.accessClientSecret = '',
  });

  static const _kUrl = 'eva.serverUrl';
  static const _kAgent = 'eva.agentId';
  static const _kAccessId = 'eva.cfAccessClientId';
  static const _kAccessSecret = 'eva.cfAccessClientSecret';

  /// Headers to attach to every request; empty unless an Access token is set.
  Map<String, String> get accessHeaders => accessClientId.isEmpty
      ? const {}
      : {
          'CF-Access-Client-Id': accessClientId,
          'CF-Access-Client-Secret': accessClientSecret,
        };

  static Future<EvaSettings> load() async {
    final p = await SharedPreferences.getInstance();
    return EvaSettings(
      serverUrl: p.getString(_kUrl) ?? kDefaultServerUrl,
      agentId: p.getString(_kAgent),
      accessClientId: p.getString(_kAccessId) ?? '',
      accessClientSecret: p.getString(_kAccessSecret) ?? '',
    );
  }

  Future<void> save() async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kUrl, serverUrl);
    await p.setString(_kAccessId, accessClientId);
    await p.setString(_kAccessSecret, accessClientSecret);
    if (agentId != null) {
      await p.setString(_kAgent, agentId!);
    } else {
      await p.remove(_kAgent);
    }
  }
}
