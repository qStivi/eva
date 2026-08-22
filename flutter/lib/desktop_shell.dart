// DesktopShell — Eva in landscape. A collapsible, drag-resizable left rail
// carries her presence (big breathing orb + mood), a model shortcut, "Who she
// is", and a live peek at her notebook; the main column is the conversation.
// Settings / Her / Notebook open as overlay panels over the chat. Reuses the
// shared EvaController and the same screen widgets as the phone shell. Ported
// from the design export's DesktopShell.jsx.

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'data/mock_chat.dart';
import 'eva_theme.dart';
import 'eva_tokens.dart';
import 'screens/approvals_screen.dart';
import 'screens/chat_screen.dart';
import 'screens/memory_screen.dart';
import 'screens/personality_screen.dart';
import 'screens/settings_screen.dart';
import 'state/eva_controller.dart';
import 'widgets/bits.dart';
import 'widgets/presence.dart';

enum _Panel { none, settings, personality, notebook, approvals }

String _moodWord(EvaMood m) {
  switch (m) {
    case EvaMood.warm:
      return 'warm';
    case EvaMood.cool:
      return 'listening';
    case EvaMood.grumpy:
      return 'prickly';
    case EvaMood.thinking:
      return 'thinking';
    case EvaMood.neutral:
      return 'present';
  }
}

class DesktopShell extends StatefulWidget {
  final EvaController controller;
  const DesktopShell({super.key, required this.controller});

  @override
  State<DesktopShell> createState() => _DesktopShellState();
}

class _DesktopShellState extends State<DesktopShell> {
  static const double _railMin = 232;
  static const double _railMax = 420;

  bool _collapsed = false;
  double _railW = 268;
  _Panel _panel = _Panel.none;

  EvaController get c => widget.controller;

  void _openPanel(_Panel p) => setState(() => _panel = p);
  void _togglePanel(_Panel p) => setState(() => _panel = _panel == p ? _Panel.none : p);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: EvaColors.bgApp,
      body: SafeArea(
        child: Row(
          children: [
            // Left rail (animated collapse).
            AnimatedContainer(
              duration: EvaMotion.base,
              curve: EvaMotion.easeOut,
              width: _collapsed ? 0 : _railW,
              decoration: const BoxDecoration(
                color: EvaColors.bgBar,
                border: Border(right: BorderSide(color: EvaColors.surfaceLine)),
              ),
              child: ClipRect(
                child: OverflowBox(
                  minWidth: _railMin,
                  maxWidth: _railMax,
                  alignment: Alignment.centerLeft,
                  child: SizedBox(width: _railW, child: _rail()),
                ),
              ),
            ),
            // Drag-to-resize handle.
            if (!_collapsed)
              MouseRegion(
                cursor: SystemMouseCursors.resizeColumn,
                child: GestureDetector(
                  behavior: HitTestBehavior.translucent,
                  onHorizontalDragUpdate: (d) => setState(() {
                    _railW = (_railW + d.delta.dx).clamp(_railMin, _railMax);
                  }),
                  child: const SizedBox(width: 8, height: double.infinity),
                ),
              ),
            // Conversation + overlay panels.
            Expanded(child: _main()),
          ],
        ),
      ),
    );
  }

  // ---- Left rail ----

  Widget _rail() {
    return ListenableBuilder(
      listenable: c,
      builder: (context, _) {
        final mood = c.thinking ? EvaMood.thinking : c.evaMood;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 13, 12, 6),
              child: Row(
                children: [
                  _wordmark(),
                  const Spacer(),
                  IconButton(
                    tooltip: 'Collapse sidebar',
                    iconSize: 18,
                    color: EvaColors.textMuted,
                    onPressed: () => setState(() => _collapsed = true),
                    icon: const Icon(Icons.view_sidebar_outlined),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 6, 18, 16),
              child: Column(
                children: [
                  PresenceOrb(mood: mood, size: 92),
                  const SizedBox(height: 11),
                  Text(c.persona.name,
                      style: Theme.of(context).textTheme.titleMedium,
                      textAlign: TextAlign.center),
                  const SizedBox(height: 4),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      StatusDot(thinking: c.thinking),
                      const SizedBox(width: 6),
                      Text(_moodWord(mood),
                          style: const TextStyle(fontSize: EvaType.sm, color: EvaColors.textMuted)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TextButton.icon(
                    onPressed: () => _openPanel(_Panel.settings),
                    style: TextButton.styleFrom(
                      foregroundColor: EvaColors.textMuted,
                      textStyle: const TextStyle(fontSize: EvaType.sm),
                    ),
                    icon: const Icon(Icons.auto_awesome, size: 13, color: EvaColors.accent),
                    label: Text('running ${c.model.name}'),
                  ),
                  const SizedBox(height: 2),
                  OutlinedButton.icon(
                    onPressed: () => _openPanel(_Panel.personality),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: EvaColors.textSecondary,
                      side: const BorderSide(color: EvaColors.surfaceLine),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(EvaRadii.pill)),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      minimumSize: Size.zero,
                      textStyle: const TextStyle(fontSize: EvaType.sm),
                    ),
                    icon: const Icon(Icons.auto_awesome, size: 13),
                    label: const Text('Who she is'),
                  ),
                ],
              ),
            ),
            const Divider(height: 1, indent: 18, endIndent: 18),
            Expanded(child: _notebookPeek()),
          ],
        );
      },
    );
  }

  Widget _wordmark() {
    return Text.rich(
      TextSpan(
        style: const TextStyle(
          fontSize: 22,
          fontWeight: EvaWeights.bold,
          letterSpacing: -0.6,
          color: EvaColors.textPrimary,
        ),
        children: const [
          TextSpan(text: 'ev'),
          TextSpan(text: 'a', style: TextStyle(color: EvaColors.accent)),
        ],
      ),
    );
  }

  Widget _notebookPeek() {
    final mems = List<Memory>.of(c.memories)
      ..sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));
    final top = mems.take(6).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        InkWell(
          onTap: () => _openPanel(_Panel.notebook),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 15, 18, 6),
            child: Row(
              children: [
                const Icon(Icons.menu_book_outlined, size: 15, color: EvaColors.accent),
                const SizedBox(width: 8),
                const Text('HER NOTEBOOK',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: EvaWeights.bold,
                      letterSpacing: 1.2,
                      color: EvaColors.textMuted,
                    )),
                const Spacer(),
                Text('${c.memories.length}',
                    style: const TextStyle(
                      fontSize: EvaType.sm,
                      fontWeight: EvaWeights.semibold,
                      color: EvaColors.remembered,
                    )),
                const Icon(Icons.chevron_right, size: 14, color: EvaColors.textFaint),
              ],
            ),
          ),
        ),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(14, 4, 14, 16),
            itemCount: top.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, i) => _peekCard(top[i]),
          ),
        ),
      ],
    );
  }

  Widget _peekCard(Memory m) {
    return Material(
      color: EvaColors.surfaceCard,
      borderRadius: BorderRadius.circular(EvaRadii.md),
      child: InkWell(
        onTap: () => _openPanel(_Panel.notebook),
        borderRadius: BorderRadius.circular(EvaRadii.md),
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 9, 11, 9),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(EvaRadii.md),
            border: Border.all(
              color: m.pinned ? EvaColors.rememberedSoft : EvaColors.surfaceLine,
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  m.text,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.newsreader(
                    textStyle: evaVoice(13.5, height: 1.45, color: EvaColors.textSecondary),
                  ),
                ),
              ),
              if (m.pinned)
                const Padding(
                  padding: EdgeInsets.only(left: 6),
                  child: Icon(Icons.push_pin, size: 11, color: EvaColors.remembered),
                ),
            ],
          ),
        ),
      ),
    );
  }

  // ---- Main column ----

  Widget _main() {
    return Stack(
      children: [
        Column(
          children: [
            _mainHeader(),
            Expanded(child: ChatScreen(controller: c)),
          ],
        ),
        if (_panel != _Panel.none) _overlayPanel(),
      ],
    );
  }

  Widget _mainHeader() {
    return ListenableBuilder(
      listenable: c,
      builder: (context, _) {
        final mood = c.thinking ? EvaMood.thinking : c.evaMood;
        final title = _collapsed ? c.persona.name : 'Tuesday evening';
        final subtitle = c.thinking
            ? 'Eva is thinking…'
            : (_collapsed ? _moodWord(mood) : 'just the two of you');
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 13),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: EvaColors.surfaceLine)),
          ),
          child: Row(
            children: [
              if (_collapsed) ...[
                IconButton(
                  tooltip: 'Expand sidebar',
                  iconSize: 18,
                  color: EvaColors.textMuted,
                  onPressed: () => setState(() => _collapsed = false),
                  icon: const Icon(Icons.view_sidebar_outlined),
                ),
                EvaAvatar(mood: mood, size: 36),
                const SizedBox(width: EvaSpace.s3),
              ],
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: EvaType.base,
                            fontWeight: EvaWeights.semibold,
                            color: EvaColors.textPrimary)),
                    Text(subtitle,
                        style: const TextStyle(fontSize: EvaType.sm, color: EvaColors.textMuted)),
                  ],
                ),
              ),
              _approvalsButton(),
              IconButton(
                tooltip: 'Settings',
                iconSize: 18,
                color: _panel == _Panel.settings ? EvaColors.accent : EvaColors.textMuted,
                onPressed: () => _togglePanel(_Panel.settings),
                icon: const Icon(Icons.settings_outlined),
              ),
            ],
          ),
        );
      },
    );
  }

  /// Bell-style entry point for pending approvals (delegate_to_harness) — a
  /// small badge whenever something's waiting, so it's visible without
  /// hunting for it. See docs/2026-08-22-delegate-to-claude-spec.md.
  Widget _approvalsButton() {
    final pending = c.pendingJobs.length;
    return IconButton(
      tooltip: 'Approvals',
      iconSize: 18,
      color: _panel == _Panel.approvals ? EvaColors.accent : EvaColors.textMuted,
      onPressed: () => _togglePanel(_Panel.approvals),
      icon: Badge(
        isLabelVisible: pending > 0,
        label: Text('$pending'),
        backgroundColor: EvaColors.warning,
        textColor: EvaColors.crust,
        child: const Icon(Icons.fact_check_outlined),
      ),
    );
  }

  Widget _overlayPanel() {
    final Widget child;
    switch (_panel) {
      case _Panel.settings:
        child = SettingsScreen(controller: c);
      case _Panel.personality:
        child = PersonalityScreen(controller: c);
      case _Panel.notebook:
        child = MemoryScreen(controller: c);
      case _Panel.approvals:
        child = ApprovalsScreen(controller: c);
      case _Panel.none:
        child = const SizedBox.shrink();
    }
    return Positioned.fill(
      child: Container(
        color: EvaColors.bgApp,
        child: Stack(
          children: [
            Positioned.fill(child: child),
            Positioned(
              top: 14,
              right: 16,
              child: IconButton(
                tooltip: 'Close',
                iconSize: 18,
                color: EvaColors.textMuted,
                onPressed: () => _openPanel(_Panel.none),
                icon: const Icon(Icons.close),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
