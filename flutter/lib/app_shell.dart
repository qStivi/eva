// AppShell — the app frame: a single title bar (Eva's presence + name + live
// mood/status), the active screen, and a bottom nav. Owns nothing but the tab
// index; all real state lives in the shared EvaController. Mobile-first, but
// the content column is centred and capped on wide screens. Ported from
// AppShell.jsx + DesktopShell's responsive intent.

import 'package:flutter/material.dart';

import 'data/mock_chat.dart';
import 'eva_tokens.dart';
import 'screens/chat_screen.dart';
import 'screens/memory_screen.dart';
import 'screens/personality_screen.dart';
import 'screens/settings_screen.dart';
import 'state/eva_controller.dart';
import 'widgets/bits.dart';
import 'widgets/presence.dart';

class AppShell extends StatefulWidget {
  final EvaController controller;
  const AppShell({super.key, required this.controller});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _tab = 0;

  EvaController get c => widget.controller;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _header(),
            Expanded(child: _body()),
          ],
        ),
      ),
      bottomNavigationBar: _bottomNav(),
    );
  }

  /// Cap the *reading* surfaces (notebook / her / settings) on wide screens so
  /// forms and lists don't stretch awkwardly. The chat is deliberately left
  /// full-width: its message bubbles self-cap to a reading measure, but the
  /// composer should grow with the screen (it looks pinched otherwise on tablets).
  Widget _capped(Widget child) {
    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 560),
        child: child,
      ),
    );
  }

  Widget _body() {
    return IndexedStack(
      index: _tab,
      children: [
        ChatScreen(controller: c),
        _capped(MemoryScreen(controller: c)),
        _capped(PersonalityScreen(controller: c)),
        _capped(SettingsScreen(controller: c)),
      ],
    );
  }

  Widget _header() {
    return ListenableBuilder(
      listenable: c,
      builder: (context, _) {
        final moodKey = c.thinking ? EvaMood.thinking : c.evaMood;
        final subtitle = c.thinking
            ? 'thinking…'
            : (_tab == 0 ? moodLine(c.evaMood) : 'online');
        return Container(
          padding: const EdgeInsets.fromLTRB(14, 11, 14, 11),
          decoration: const BoxDecoration(
            color: EvaColors.bgBar,
            border: Border(bottom: BorderSide(color: EvaColors.surfaceLine)),
          ),
          child: Row(
            children: [
              EvaAvatar(mood: moodKey, size: 38),
              const SizedBox(width: 11),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(c.persona.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleMedium),
                    AnimatedSwitcher(
                      duration: EvaMotion.base,
                      child: Text(subtitle,
                          key: ValueKey(subtitle),
                          style: const TextStyle(fontSize: 11.5, color: EvaColors.textMuted)),
                    ),
                  ],
                ),
              ),
              StatusDot(thinking: c.thinking),
            ],
          ),
        );
      },
    );
  }

  Widget _bottomNav() {
    // Full-width bar (so the bgBar + top hairline span the screen), but the nav
    // items themselves are capped and centred to match the 560px content column
    // — otherwise on tablets/wide screens they sprawl across the whole width.
    return Container(
      decoration: const BoxDecoration(
        color: EvaColors.bgBar,
        border: Border(top: BorderSide(color: EvaColors.surfaceLine)),
      ),
      // Align (not Center) with heightFactor so it shrink-wraps vertically —
      // the bottom-bar slot is unbounded in height, which would make Center
      // expand to infinity.
      child: Align(
        alignment: Alignment.center,
        heightFactor: 1,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: _navBar(),
        ),
      ),
    );
  }

  Widget _navBar() {
    return NavigationBarTheme(
      data: NavigationBarThemeData(
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        indicatorColor: EvaColors.accentSoft,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return TextStyle(
            fontSize: 11,
            fontWeight: selected ? EvaWeights.semibold : EvaWeights.medium,
            color: selected ? EvaColors.accent : EvaColors.textMuted,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(
            size: 22,
            color: selected ? EvaColors.accent : EvaColors.textMuted,
          );
        }),
      ),
      child: NavigationBar(
        height: 62,
        backgroundColor: Colors.transparent,
        elevation: 0,
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.chat_bubble_outline),
              selectedIcon: Icon(Icons.chat_bubble),
              label: 'Talk'),
          NavigationDestination(
              icon: Icon(Icons.menu_book_outlined),
              selectedIcon: Icon(Icons.menu_book),
              label: 'Notebook'),
          NavigationDestination(
              icon: Icon(Icons.auto_awesome_outlined),
              selectedIcon: Icon(Icons.auto_awesome),
              label: 'Her'),
          NavigationDestination(
              icon: Icon(Icons.settings_outlined),
              selectedIcon: Icon(Icons.settings),
              label: 'Settings'),
        ],
      ),
    );
  }
}
