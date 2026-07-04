// PersonalityScreen — "Who she is." The editable character sheet: name &
// pronouns, four temperament sliders, a backstory in her own words, and a live
// sample line that shifts as you tune her. Ported from PersonalityScreen.jsx.

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../data/mock_chat.dart';
import '../eva_theme.dart';
import '../eva_tokens.dart';
import '../state/eva_controller.dart';
import '../widgets/bits.dart';
import '../widgets/message_bubble.dart';
import '../widgets/presence.dart';

class PersonalityScreen extends StatefulWidget {
  final EvaController controller;
  const PersonalityScreen({super.key, required this.controller});

  @override
  State<PersonalityScreen> createState() => _PersonalityScreenState();
}

class _PersonalityScreenState extends State<PersonalityScreen> {
  EvaController get c => widget.controller;
  late final TextEditingController _name =
      TextEditingController(text: c.persona.name);
  late final TextEditingController _pronouns =
      TextEditingController(text: c.persona.pronouns);
  late final TextEditingController _backstory =
      TextEditingController(text: c.persona.backstory);

  @override
  void dispose() {
    _name.dispose();
    _pronouns.dispose();
    _backstory.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: c,
      builder: (context, _) {
        final moodKey = c.thinking ? EvaMood.thinking : c.evaMood;
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 28),
          children: [
            Text('Who she is', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 6),
            _voiceIntro('Shape her, if you must. ', '*raises an eyebrow*',
                " I'll still be me underneath."),
            const SizedBox(height: EvaSpace.s4),

            // Identity card.
            _card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      PresenceOrb(mood: moodKey, size: 64),
                      const SizedBox(width: EvaSpace.s4),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(c.persona.name,
                                style: Theme.of(context).textTheme.titleMedium),
                            const SizedBox(height: 2),
                            Text(
                              c.persona.tagline,
                              style: GoogleFonts.newsreader(
                                textStyle: evaVoice(15.7,
                                    italic: true,
                                    color: EvaColors.accent3.withValues(alpha: 0.92)),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: EvaSpace.s4),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _name,
                          onChanged: (v) => c.setPersonaField(name: v),
                          decoration: const InputDecoration(labelText: 'Her name'),
                        ),
                      ),
                      const SizedBox(width: EvaSpace.s3),
                      Expanded(
                        child: TextField(
                          controller: _pronouns,
                          onChanged: (v) => c.setPersonaField(pronouns: v),
                          decoration: const InputDecoration(labelText: 'Pronouns'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: EvaSpace.s4),

            const Eyebrow('Temperament'),
            _card(
              child: Column(
                children: [
                  for (var i = 0; i < traitDefs.length; i++) ...[
                    if (i > 0) const Divider(height: 1),
                    _traitRow(traitDefs[i]),
                  ],
                ],
              ),
            ),
            const SizedBox(height: EvaSpace.s4),

            const Eyebrow("How she'd put it"),
            _sampleLine(moodKey),
            const SizedBox(height: EvaSpace.s4),

            const Eyebrow('In her own words'),
            _card(
              child: TextField(
                controller: _backstory,
                onChanged: (v) => c.setPersonaField(backstory: v),
                minLines: 3,
                maxLines: 6,
                style: GoogleFonts.newsreader(
                  textStyle: evaVoice(16.3, color: EvaColors.textPrimary),
                ),
                decoration: const InputDecoration(
                  filled: false,
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _card({required Widget child}) {
    return Container(
      padding: const EdgeInsets.all(EvaSpace.s4),
      decoration: BoxDecoration(
        color: EvaColors.surfaceCard,
        borderRadius: BorderRadius.circular(EvaRadii.md),
        border: Border.all(color: EvaColors.surfaceLine),
      ),
      child: child,
    );
  }

  Widget _traitRow(TraitDef def) {
    final value = c.persona.traits[def.key] ?? 50;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: EvaSpace.s3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(def.label,
                  style: const TextStyle(
                      fontSize: EvaType.base, fontWeight: EvaWeights.medium)),
              const SizedBox(width: EvaSpace.s2),
              Expanded(
                child: Text(def.desc,
                    style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.textMuted)),
              ),
            ],
          ),
          Slider(
            value: value,
            max: 100,
            onChanged: (v) => c.setTrait(def.key, v),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: EvaSpace.s2),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(def.low,
                    style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.textMuted)),
                Text(def.high,
                    style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.textMuted)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _sampleLine(EvaMood moodKey) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        EvaAvatar(mood: moodKey, size: 30),
        const SizedBox(width: EvaSpace.s2),
        Flexible(
          child: MessageBubble(
            speaker: Speaker.eva,
            text: personaPreviewLine(c.persona.traits),
            mood: moodKey,
          ),
        ),
      ],
    );
  }

  Widget _voiceIntro(String a, String aside, String b) {
    final base = GoogleFonts.newsreader(
      textStyle: evaVoice(16.3, color: EvaColors.textSecondary),
    );
    return Text.rich(TextSpan(style: base, children: [
      TextSpan(text: a),
      TextSpan(
        text: aside,
        style: base.copyWith(
          fontStyle: FontStyle.italic,
          color: EvaColors.accent3.withValues(alpha: 0.92),
        ),
      ),
      TextSpan(text: b),
    ]));
  }
}
