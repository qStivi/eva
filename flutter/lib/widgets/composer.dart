// Composer — the message input. Auto-growing field + a send button on a calm
// bar. Enter sends, Shift+Enter newlines. The mic toggles a cosmetic "listening"
// state (Eva is local — no transcription is faked). Ported from Composer.jsx;
// the most important control in the app.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../eva_tokens.dart';

class Composer extends StatefulWidget {
  final TextEditingController controller;
  final VoidCallback onSend;
  final bool busy;
  final String placeholder;

  /// Called when the user taps Stop while Eva is composing. When null, the busy
  /// button is a plain (non-interactive) spinner.
  final VoidCallback? onCancel;

  const Composer({
    super.key,
    required this.controller,
    required this.onSend,
    this.busy = false,
    this.onCancel,
    this.placeholder = 'Say something to Eva…',
  });

  @override
  State<Composer> createState() => _ComposerState();
}

class _ComposerState extends State<Composer> {
  bool _listening = false;

  bool get _canSend => widget.controller.text.trim().isNotEmpty && !widget.busy;

  void _trySend() {
    if (_canSend) widget.onSend();
  }

  KeyEventResult _onKey(FocusNode node, KeyEvent event) {
    if (event is KeyDownEvent &&
        event.logicalKey == LogicalKeyboardKey.enter &&
        !HardwareKeyboard.instance.isShiftPressed) {
      _trySend();
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: const BoxDecoration(
        color: EvaColors.bgBar,
        border: Border(top: BorderSide(color: EvaColors.surfaceLine)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: AnimatedContainer(
              duration: EvaMotion.fast,
              curve: EvaMotion.easeOut,
              padding: const EdgeInsets.fromLTRB(10, 6, 8, 6),
              decoration: BoxDecoration(
                color: EvaColors.surfaceInset,
                borderRadius: BorderRadius.circular(EvaRadii.lg),
                border: Border.all(
                  color: _listening ? EvaColors.accentLine : EvaColors.surfaceLine,
                ),
                boxShadow: _listening
                    ? [const BoxShadow(color: EvaColors.accentSoft, blurRadius: 0, spreadRadius: 3)]
                    : null,
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  _PillButton(
                    icon: Icons.attach_file,
                    tooltip: 'Attach',
                    onPressed: () {},
                  ),
                  Expanded(
                    child: Focus(
                      onKeyEvent: _onKey,
                      child: TextField(
                        controller: widget.controller,
                        minLines: 1,
                        maxLines: 6,
                        keyboardType: TextInputType.multiline,
                        textInputAction: TextInputAction.newline,
                        onChanged: (_) => setState(() {}),
                        style: Theme.of(context).textTheme.bodyLarge,
                        cursorColor: EvaColors.accent,
                        decoration: InputDecoration(
                          isCollapsed: true,
                          filled: false,
                          border: InputBorder.none,
                          enabledBorder: InputBorder.none,
                          focusedBorder: InputBorder.none,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                          hintText: _listening ? 'listening…' : widget.placeholder,
                          hintStyle: const TextStyle(color: EvaColors.textFaint),
                        ),
                      ),
                    ),
                  ),
                  _PillButton(
                    icon: Icons.mic_none,
                    tooltip: _listening ? 'Stop listening' : 'Voice',
                    active: _listening,
                    onPressed: () => setState(() => _listening = !_listening),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: EvaSpace.s2),
          _SendButton(
            canSend: _canSend,
            busy: widget.busy,
            onPressed: _trySend,
            onCancel: widget.onCancel,
          ),
        ],
      ),
    );
  }
}

class _PillButton extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final bool active;
  final VoidCallback onPressed;

  const _PillButton({
    required this.icon,
    required this.tooltip,
    required this.onPressed,
    this.active = false,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 32,
      height: 32,
      child: IconButton(
        padding: EdgeInsets.zero,
        iconSize: 18,
        tooltip: tooltip,
        onPressed: onPressed,
        icon: Icon(icon),
        style: IconButton.styleFrom(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(EvaRadii.sm)),
          backgroundColor: active ? EvaColors.accentSoft : Colors.transparent,
          foregroundColor: active ? EvaColors.danger : EvaColors.textMuted,
        ),
      ),
    );
  }
}

class _SendButton extends StatelessWidget {
  final bool canSend;
  final bool busy;
  final VoidCallback onPressed;
  final VoidCallback? onCancel;

  const _SendButton({
    required this.canSend,
    required this.busy,
    required this.onPressed,
    this.onCancel,
  });

  @override
  Widget build(BuildContext context) {
    // While busy, become a tappable Stop (spinner + square) so a slow or stalled
    // turn can always be abandoned — never a dead, un-cancellable spinner.
    final canStop = busy && onCancel != null;
    return AnimatedContainer(
      duration: EvaMotion.fast,
      width: EvaLayout.tapMin,
      height: EvaLayout.tapMin,
      decoration: BoxDecoration(
        color: canStop
            ? EvaColors.surfaceInset
            : (canSend ? EvaColors.accent : EvaColors.surfaceInset),
        borderRadius: BorderRadius.circular(EvaRadii.md),
      ),
      child: IconButton(
        onPressed: busy ? onCancel : (canSend ? onPressed : null),
        tooltip: busy ? 'Stop' : 'Send',
        color: canSend ? EvaColors.textOnAccent : EvaColors.textFaint,
        disabledColor: EvaColors.textFaint,
        icon: busy
            ? Stack(
                alignment: Alignment.center,
                children: [
                  const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2, color: EvaColors.textMuted),
                  ),
                  Icon(canStop ? Icons.stop : Icons.more_horiz,
                      size: 12, color: EvaColors.textMuted),
                ],
              )
            : const Icon(Icons.arrow_upward, size: 20),
      ),
    );
  }
}
