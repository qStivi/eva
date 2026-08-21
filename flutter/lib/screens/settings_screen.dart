// SettingsScreen — quiet and minimal. The daily-driver model switcher lives
// here. Ported from SettingsScreen.jsx.

import 'package:flutter/material.dart';

import '../api/letta_api.dart' show CheckinConfig;
import '../data/mock_chat.dart';
import '../eva_tokens.dart';
import '../state/eva_controller.dart';
import '../widgets/bits.dart';

// Interval options offered for scheduled check-ins, in minutes.
const List<int> _kCheckinIntervals = [60, 120, 240, 480, 720, 1080, 1440];

String _intervalLabel(int minutes) {
  if (minutes % 1440 == 0) return '${minutes ~/ 1440}d';
  if (minutes % 60 == 0) return '${minutes ~/ 60}h';
  return '${minutes}m';
}

final RegExp _kHhMm = RegExp(r'^([01]\d|2[0-3]):[0-5]\d$');

class SettingsScreen extends StatefulWidget {
  final EvaController controller;
  const SettingsScreen({super.key, required this.controller});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _modelOpen = false;
  bool _accessOpen = false;
  late final TextEditingController _name = TextEditingController(text: widget.controller.userName);
  late final TextEditingController _server = TextEditingController(text: widget.controller.serverUrl);
  late final TextEditingController _accessId =
      TextEditingController(text: widget.controller.accessClientId);
  late final TextEditingController _accessSecret =
      TextEditingController(text: widget.controller.accessClientSecret);
  late final TextEditingController _chatUser =
      TextEditingController(text: widget.controller.chatUser);
  late final TextEditingController _chatPassword =
      TextEditingController(text: widget.controller.chatPassword);
  final TextEditingController _quietStart = TextEditingController();
  final TextEditingController _quietEnd = TextEditingController();
  final TextEditingController _dailyTime = TextEditingController();
  bool _quietInitialized = false;
  bool _dailyTimeInitialized = false;

  EvaController get c => widget.controller;

  void _maybeInitQuietHours(CheckinConfig cfg) {
    if (_quietInitialized) return;
    _quietStart.text = cfg.quietStart;
    _quietEnd.text = cfg.quietEnd;
    _quietInitialized = true;
  }

  void _maybeInitDailyTime(CheckinConfig cfg) {
    if (_dailyTimeInitialized) return;
    _dailyTime.text = cfg.dailyTime;
    _dailyTimeInitialized = true;
  }

  void _saveQuietHours() {
    if (!_kHhMm.hasMatch(_quietStart.text) || !_kHhMm.hasMatch(_quietEnd.text)) return;
    c.setCheckinQuietHours(_quietStart.text, _quietEnd.text);
  }

  void _saveDailyTime() {
    if (!_kHhMm.hasMatch(_dailyTime.text)) return;
    c.setCheckinDailyTime(_dailyTime.text);
  }

  void _reconnect() => c.reconfigure(
        _server.text,
        accessClientId: _accessId.text,
        accessClientSecret: _accessSecret.text,
        chatUser: _chatUser.text,
        chatPassword: _chatPassword.text,
      );

  @override
  void dispose() {
    _name.dispose();
    _server.dispose();
    _accessId.dispose();
    _accessSecret.dispose();
    _chatUser.dispose();
    _chatPassword.dispose();
    _quietStart.dispose();
    _quietEnd.dispose();
    _dailyTime.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: c,
      builder: (context, _) => ListView(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 28),
        children: [
          Text('Settings', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: EvaSpace.s5),

          const Eyebrow('Connection'),
          _card(child: _serverSection()),
          const SizedBox(height: EvaSpace.s5),

          const Eyebrow('Her brain'),
          _card(child: _modelSection()),
          const SizedBox(height: EvaSpace.s5),

          const Eyebrow('Check-ins'),
          _card(child: _checkinSection()),
          const SizedBox(height: EvaSpace.s5),

          const Eyebrow('How she shows up'),
          _card(
            child: Column(
              children: [
                _switchRow('Voice replies', 'Optional layer on top of text', 'voice'),
                const Divider(height: 1),
                _switchRow('Show memory cues',
                    "The little 'jotted it down' note when she saves something", 'cues'),
              ],
            ),
          ),
          const SizedBox(height: EvaSpace.s5),

          const Eyebrow('You'),
          _card(
            child: TextField(
              controller: _name,
              onChanged: c.setUserName,
              decoration: const InputDecoration(labelText: 'What she calls you'),
            ),
          ),
          const SizedBox(height: EvaSpace.s5),

          const Center(
            child: Text('Self-hosted · your data stays on your server',
                style: TextStyle(fontSize: EvaType.xs, color: EvaColors.textFaint)),
          ),
        ],
      ),
    );
  }

  Widget _card({required Widget child}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: EvaSpace.s4, vertical: EvaSpace.s2),
      decoration: BoxDecoration(
        color: EvaColors.surfaceCard,
        borderRadius: BorderRadius.circular(EvaRadii.md),
        border: Border.all(color: EvaColors.surfaceLine),
      ),
      child: child,
    );
  }

  Widget _serverSection() {
    final (label, color) = switch (c.status) {
      ConnectionStatus.live => ('Connected · agent "${c.agentName}"', EvaColors.remembered),
      ConnectionStatus.connecting => ('Connecting…', EvaColors.accent),
      ConnectionStatus.error => ('Not connected — ${c.serverError ?? 'unknown error'}', EvaColors.danger),
      ConnectionStatus.mock => ('Offline — running on canned demo data', EvaColors.textMuted),
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: EvaSpace.s2),
          child: Row(
            children: [
              Container(
                width: 8,
                height: 8,
                margin: const EdgeInsets.only(top: 1),
                decoration: BoxDecoration(color: color, shape: BoxShape.circle),
              ),
              const SizedBox(width: EvaSpace.s2),
              Expanded(
                child: Text(label, style: TextStyle(fontSize: EvaType.sm, color: color)),
              ),
            ],
          ),
        ),
        TextField(
          controller: _server,
          keyboardType: TextInputType.url,
          autocorrect: false,
          decoration: const InputDecoration(
            labelText: 'Eva server',
            hintText: 'https://eva.qstivi.com  ·  LAN: http://<PC-IP>:8283',
          ),
          onSubmitted: (_) => _reconnect(),
        ),
        const SizedBox(height: EvaSpace.s2),
        // eva-web's own login — chat always goes through eva-web now (not
        // straight to Letta) so it gets the same toolset/model routing the
        // browser UI has. Not optional the way Access is: without this,
        // every send fails with 401. Username defaults to eva-web's own
        // default ("eva"); password has no sane default, always shown.
        TextField(
          controller: _chatUser,
          autocorrect: false,
          decoration: const InputDecoration(labelText: 'eva-web username'),
          onSubmitted: (_) => _reconnect(),
        ),
        const SizedBox(height: EvaSpace.s2),
        TextField(
          controller: _chatPassword,
          autocorrect: false,
          obscureText: true,
          decoration: const InputDecoration(labelText: 'eva-web password'),
          onSubmitted: (_) => _reconnect(),
        ),
        // Cloudflare Access token — only needed for the public tunnel. Tucked away
        // so LAN users never see it.
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: () => setState(() => _accessOpen = !_accessOpen),
            icon: Icon(_accessOpen ? Icons.expand_less : Icons.expand_more, size: 18),
            label: Text(
              'Cloudflare Access (remote)',
              style: TextStyle(fontSize: EvaType.sm, color: EvaColors.textMuted),
            ),
          ),
        ),
        if (_accessOpen) ...[
          TextField(
            controller: _accessId,
            autocorrect: false,
            decoration: const InputDecoration(
              labelText: 'Access Client ID',
              hintText: '…….access',
            ),
            onSubmitted: (_) => _reconnect(),
          ),
          const SizedBox(height: EvaSpace.s2),
          TextField(
            controller: _accessSecret,
            autocorrect: false,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'Access Client Secret'),
            onSubmitted: (_) => _reconnect(),
          ),
        ],
        const SizedBox(height: EvaSpace.s2),
        Align(
          alignment: Alignment.centerRight,
          child: ElevatedButton.icon(
            onPressed: c.status == ConnectionStatus.connecting ? null : _reconnect,
            icon: const Icon(Icons.sync, size: 16),
            label: Text(c.status == ConnectionStatus.live ? 'Reconnect' : 'Connect'),
          ),
        ),
      ],
    );
  }

  Widget _checkinSection() {
    final cfg = c.checkinConfig;
    if (cfg == null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: EvaSpace.s3),
        child: Text(
          c.live ? 'Loading…' : 'Connect above to load check-in settings',
          style: const TextStyle(fontSize: EvaType.sm, color: EvaColors.textMuted),
        ),
      );
    }
    _maybeInitQuietHours(cfg);
    _maybeInitDailyTime(cfg);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _row(
          'Let Eva take initiative',
          'A quiet nudge, on a schedule — she only actually reaches out if '
              'she has something worth saying',
          Switch(
            value: cfg.enabled,
            onChanged: c.checkinBusy ? null : (v) => c.setCheckinEnabled(v),
          ),
        ),
        if (cfg.enabled) ...[
          const Divider(height: 1),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: EvaSpace.s3),
            child: Row(
              children: [
                const Expanded(child: Text('When', style: TextStyle(fontSize: EvaType.base))),
                DropdownButton<String>(
                  value: cfg.mode,
                  underline: const SizedBox.shrink(),
                  items: const [
                    DropdownMenuItem(value: 'interval', child: Text('every N hours')),
                    DropdownMenuItem(value: 'daily', child: Text('once a day')),
                  ],
                  onChanged: c.checkinBusy
                      ? null
                      : (v) {
                          if (v != null) c.setCheckinMode(v);
                        },
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          if (cfg.mode == 'daily')
            Padding(
              padding: const EdgeInsets.symmetric(vertical: EvaSpace.s3),
              child: Row(
                children: [
                  const Expanded(child: Text('At', style: TextStyle(fontSize: EvaType.base))),
                  SizedBox(
                    width: 90,
                    child: TextField(
                      controller: _dailyTime,
                      textAlign: TextAlign.end,
                      autocorrect: false,
                      decoration: const InputDecoration(hintText: 'HH:MM'),
                      onSubmitted: (_) => _saveDailyTime(),
                      onTapOutside: (_) => _saveDailyTime(),
                    ),
                  ),
                ],
              ),
            )
          else
            Padding(
              padding: const EdgeInsets.symmetric(vertical: EvaSpace.s3),
              child: Row(
                children: [
                  const Expanded(child: Text('How often', style: TextStyle(fontSize: EvaType.base))),
                  DropdownButton<int>(
                    value: _kCheckinIntervals.contains(cfg.intervalMinutes)
                        ? cfg.intervalMinutes
                        : _kCheckinIntervals.first,
                    underline: const SizedBox.shrink(),
                    items: [
                      for (final m in _kCheckinIntervals)
                        DropdownMenuItem(value: m, child: Text('every ${_intervalLabel(m)}')),
                    ],
                    onChanged: c.checkinBusy
                        ? null
                        : (v) {
                            if (v != null) c.setCheckinInterval(v);
                          },
                  ),
                ],
              ),
            ),
          const Divider(height: 1),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: EvaSpace.s3),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _quietStart,
                    autocorrect: false,
                    decoration: const InputDecoration(labelText: 'Quiet from', hintText: 'HH:MM'),
                    onSubmitted: (_) => _saveQuietHours(),
                    onTapOutside: (_) => _saveQuietHours(),
                  ),
                ),
                const SizedBox(width: EvaSpace.s3),
                Expanded(
                  child: TextField(
                    controller: _quietEnd,
                    autocorrect: false,
                    decoration: const InputDecoration(labelText: 'until', hintText: 'HH:MM'),
                    onSubmitted: (_) => _saveQuietHours(),
                    onTapOutside: (_) => _saveQuietHours(),
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(top: EvaSpace.s1, bottom: EvaSpace.s2),
            child: Text(_nextDueLabel(cfg.nextDueAt),
                style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.textFaint)),
          ),
        ],
      ],
    );
  }

  String _nextDueLabel(double nextDueAtEpoch) {
    final due = DateTime.fromMillisecondsSinceEpoch((nextDueAtEpoch * 1000).round());
    final diff = due.difference(DateTime.now());
    if (diff.isNegative) return 'Next check-in: due now (may be waiting out quiet hours)';
    if (diff.inHours >= 1) return 'Next check-in: in about ${diff.inHours}h';
    return 'Next check-in: in about ${diff.inMinutes}m';
  }

  Widget _modelSection() {
    return Column(
      children: [
        _row(
          'Model',
          'Which brain Eva runs on today',
          ModelPill(
            name: c.model.name,
            open: _modelOpen,
            onPressed: () => setState(() => _modelOpen = !_modelOpen),
          ),
        ),
        if (_modelOpen) ...[
          const Divider(height: 1),
          const SizedBox(height: 6),
          for (final m in evaModels) _modelOption(m),
        ],
      ],
    );
  }

  Widget _modelOption(EvaModel m) {
    final active = m.id == c.model.id;
    return Material(
      color: active ? EvaColors.accentSoft : Colors.transparent,
      borderRadius: BorderRadius.circular(EvaRadii.sm),
      child: InkWell(
        onTap: () {
          c.selectModel(m);
          setState(() => _modelOpen = false);
        },
        borderRadius: BorderRadius.circular(EvaRadii.sm),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: EvaSpace.s2, vertical: 9),
          child: Row(
            children: [
              Icon(active ? Icons.check_circle : Icons.circle_outlined,
                  size: 16, color: active ? EvaColors.accent : EvaColors.textFaint),
              const SizedBox(width: EvaSpace.s3),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(m.name,
                        style: const TextStyle(
                            fontSize: EvaType.sm, fontWeight: EvaWeights.medium)),
                    Text(m.note,
                        style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.textMuted)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _switchRow(String title, String desc, String prefKey) {
    return _row(
      title,
      desc,
      Switch(
        value: c.prefs[prefKey] ?? false,
        onChanged: (v) => c.setPref(prefKey, v),
      ),
    );
  }

  Widget _row(String title, String desc, Widget control) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: EvaSpace.s3),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: const TextStyle(
                        fontSize: EvaType.base, fontWeight: EvaWeights.medium)),
                const SizedBox(height: 2),
                Text(desc, style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.textMuted)),
              ],
            ),
          ),
          const SizedBox(width: EvaSpace.s4),
          control,
        ],
      ),
    );
  }
}
