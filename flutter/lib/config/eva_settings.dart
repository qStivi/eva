// EvaSettings — persisted connection config (where Eva's Letta server lives and
// which agent to talk to). Stored via shared_preferences. Desktop works with the
// localhost default; on the phone the user points it at the PC's LAN IP.

import 'package:shared_preferences/shared_preferences.dart';

const String kDefaultServerUrl = 'http://localhost:8283';

class EvaSettings {
  String serverUrl;
  String? agentId;

  EvaSettings({this.serverUrl = kDefaultServerUrl, this.agentId});

  static const _kUrl = 'eva.serverUrl';
  static const _kAgent = 'eva.agentId';

  static Future<EvaSettings> load() async {
    final p = await SharedPreferences.getInstance();
    return EvaSettings(
      serverUrl: p.getString(_kUrl) ?? kDefaultServerUrl,
      agentId: p.getString(_kAgent),
    );
  }

  Future<void> save() async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kUrl, serverUrl);
    if (agentId != null) {
      await p.setString(_kAgent, agentId!);
    } else {
      await p.remove(_kAgent);
    }
  }
}
