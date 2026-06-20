// PresenceOrb + EvaAvatar — Eva, present in the room. Ported from the design
// export's PresenceOrb.jsx / Avatar.jsx. The orb shows her portrait inside a
// soft, mood-tinted halo that breathes slowly (4s, or 2.2s when thinking);
// the avatar is the small circular mark beside her message runs.

import 'package:flutter/material.dart';

import '../data/mock_chat.dart';
import '../eva_tokens.dart';

const String evaAsset = 'assets/eva.webp';

/// Eva's breathing presence — portrait + mood-tinted halo.
class PresenceOrb extends StatefulWidget {
  final EvaMood mood;
  final double size;
  final bool breathing;

  const PresenceOrb({
    super.key,
    this.mood = EvaMood.neutral,
    this.size = 96,
    this.breathing = true,
  });

  @override
  State<PresenceOrb> createState() => _PresenceOrbState();
}

class _PresenceOrbState extends State<PresenceOrb> with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  Duration get _dur =>
      widget.mood == EvaMood.thinking ? const Duration(milliseconds: 2200) : EvaMotion.breath;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: _dur);
    if (widget.breathing) _c.repeat(reverse: true);
  }

  @override
  void didUpdateWidget(PresenceOrb old) {
    super.didUpdateWidget(old);
    if ((old.mood == EvaMood.thinking) != (widget.mood == EvaMood.thinking)) {
      _c.duration = _dur;
      if (widget.breathing) _c.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final glow = moodGlow(widget.mood);
    final px = widget.size;
    final pad = px * 0.2;
    final curve = CurvedAnimation(parent: _c, curve: EvaMotion.easeSoft);

    return SizedBox(
      width: px,
      height: px,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          // Breathing mood halo (blurred radial glow).
          Positioned(
            left: -pad,
            top: -pad,
            right: -pad,
            bottom: -pad,
            child: FadeTransition(
              opacity: Tween<double>(begin: 0.5, end: 0.92).animate(curve),
              child: ScaleTransition(
                scale: Tween<double>(begin: 1.0, end: 1.05).animate(curve),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      center: const Alignment(0, -0.04),
                      radius: 0.66,
                      colors: [glow, glow.withValues(alpha: 0)],
                    ),
                  ),
                ),
              ),
            ),
          ),
          // Portrait.
          Positioned.fill(
            child: Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: glow, width: 1.5),
                image: const DecorationImage(
                  image: AssetImage(evaAsset),
                  fit: BoxFit.cover,
                  alignment: Alignment(0, -0.56),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Small circular identity mark. For Eva: portrait with a mood-tinted ring.
/// For you: an initial on an inset surface.
class EvaAvatar extends StatelessWidget {
  final Speaker who;
  final EvaMood mood;
  final double size;
  final String initial;

  const EvaAvatar({
    super.key,
    this.who = Speaker.eva,
    this.mood = EvaMood.neutral,
    this.size = 30,
    this.initial = 'S',
  });

  @override
  Widget build(BuildContext context) {
    if (who == Speaker.eva) {
      return Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: moodGlow(mood), width: 1.5),
          image: const DecorationImage(
            image: AssetImage(evaAsset),
            fit: BoxFit.cover,
            alignment: Alignment(0, -0.56),
          ),
        ),
      );
    }
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: EvaColors.surfaceInset,
        border: Border.all(color: EvaColors.surfaceLine),
      ),
      child: Text(
        initial,
        style: TextStyle(
          color: EvaColors.textSecondary,
          fontSize: size * 0.42,
          fontWeight: EvaWeights.semibold,
        ),
      ),
    );
  }
}
