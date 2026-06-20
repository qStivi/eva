// SettingsScreen — quiet and minimal. The daily-driver model switcher lives
// here. Ported from SettingsScreen.jsx.

import 'package:flutter/material.dart';

import '../data/mock_chat.dart';
import '../eva_tokens.dart';
import '../state/eva_controller.dart';
import '../widgets/bits.dart';

class SettingsScreen extends StatefulWidget {
  final EvaController controller;
  const SettingsScreen({super.key, required this.controller});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _modelOpen = false;
  late final TextEditingController _name = TextEditingController(text: widget.controller.userName);

  EvaController get c => widget.controller;

  @override
  void dispose() {
    _name.dispose();
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

          const Eyebrow('Her brain'),
          _card(child: _modelSection()),
          const SizedBox(height: EvaSpace.s5),

          const Eyebrow('How she shows up'),
          _card(
            child: Column(
              children: [
                _switchRow('Let Eva take initiative',
                    'She can start the conversation, not just answer', 'initiative'),
                const Divider(height: 1),
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
