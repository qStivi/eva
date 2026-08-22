// ApprovalsScreen — the real, in-app "verification queue" for jobs Eva has
// proposed but can't run without a yes first (delegate_to_harness — see
// docs/2026-08-22-delegate-to-claude-spec.md). Replaces the v1 server-rendered
// eva-web /jobs page as the actual way to approve/deny from the phone: that
// page sat behind Cloudflare Access, which blocks a bare browser tap (no
// service-token headers) before it ever reaches eva-web — confirmed live,
// 403 straight from Cloudflare. The app already carries those headers on
// every request, so doing this in-app sidesteps the problem entirely instead
// of working around it.

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../api/letta_api.dart';
import '../eva_theme.dart';
import '../eva_tokens.dart';
import '../state/eva_controller.dart';

/// Bare content widget — no Scaffold/AppBar of its own, matching
/// MemoryScreen/SettingsScreen/PersonalityScreen's convention. Desktop embeds
/// it directly as a panel (its own close button is provided by the panel
/// chrome); the phone pushes it as a full route with a Scaffold+AppBar added
/// at that call site (see app_shell.dart).
class ApprovalsScreen extends StatelessWidget {
  final EvaController controller;
  const ApprovalsScreen({super.key, required this.controller});

  EvaController get c => controller;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: c,
      builder: (context, _) {
        return RefreshIndicator(
          onRefresh: c.refreshPendingJobs,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 18, 16, 28),
            children: [
              _voiceIntro(
                "Nothing here happens until you say so. I can only ask. ",
                '*taps the notebook*',
              ),
              const SizedBox(height: EvaSpace.s4),
              if (c.jobsError != null) _errorBanner(c.jobsError!),
              if (c.pendingJobs.isEmpty && c.jobsError == null)
                _emptyState()
              else
                for (final job in c.pendingJobs)
                  Padding(
                    padding: const EdgeInsets.only(bottom: EvaSpace.s3),
                    child: _JobCard(job: job, busy: c.jobsBusy, controller: c),
                  ),
            ],
          ),
        );
      },
    );
  }

  Widget _voiceIntro(String body, String aside) {
    final base = GoogleFonts.newsreader(textStyle: evaVoice(16.3, color: EvaColors.textSecondary));
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 460),
      child: Text.rich(TextSpan(style: base, children: [
        TextSpan(text: body),
        TextSpan(
          text: aside,
          style: base.copyWith(fontStyle: FontStyle.italic, color: EvaColors.accent3.withValues(alpha: 0.92)),
        ),
      ])),
    );
  }

  Widget _errorBanner(String message) {
    return Container(
      margin: const EdgeInsets.only(bottom: EvaSpace.s4),
      padding: const EdgeInsets.all(EvaSpace.s3),
      decoration: BoxDecoration(
        color: EvaColors.dangerSoft,
        borderRadius: BorderRadius.circular(EvaRadii.md),
        border: Border.all(color: EvaColors.danger.withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, size: 16, color: EvaColors.danger),
          const SizedBox(width: EvaSpace.s2),
          Expanded(
            child: Text("Couldn't reach eva-web: $message",
                style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.danger)),
          ),
        ],
      ),
    );
  }

  Widget _emptyState() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: EvaSpace.s7),
      child: Column(
        children: [
          Icon(Icons.check_circle_outline, size: 32, color: EvaColors.textMuted.withValues(alpha: 0.5)),
          const SizedBox(height: EvaSpace.s3),
          Text('Nothing waiting on you right now.',
              style: TextStyle(color: EvaColors.textMuted, fontSize: EvaType.sm)),
        ],
      ),
    );
  }
}

class _JobCard extends StatelessWidget {
  final PendingJob job;
  final bool busy;
  final EvaController controller;
  const _JobCard({required this.job, required this.busy, required this.controller});

  @override
  Widget build(BuildContext context) {
    final flagged = job.moderationFlags.isNotEmpty;
    return Container(
      padding: const EdgeInsets.all(EvaSpace.s4),
      decoration: BoxDecoration(
        color: EvaColors.surfaceCard,
        borderRadius: BorderRadius.circular(EvaRadii.md),
        border: Border.all(color: flagged ? EvaColors.warning.withValues(alpha: 0.5) : EvaColors.surfaceLine),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(job.kind.toUpperCase(),
              style: const TextStyle(
                  fontSize: 11, fontWeight: EvaWeights.semibold, color: EvaColors.accent, letterSpacing: 0.4)),
          const SizedBox(height: EvaSpace.s2),
          Text(job.task, style: const TextStyle(fontSize: EvaType.base, color: EvaColors.textPrimary)),
          if (flagged) ...[
            const SizedBox(height: EvaSpace.s2),
            Row(
              children: [
                const Icon(Icons.warning_amber_rounded, size: 14, color: EvaColors.warning),
                const SizedBox(width: 4),
                Expanded(
                  child: Text('flagged: ${job.moderationFlags.join(', ')}',
                      style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.warning)),
                ),
              ],
            ),
          ],
          const SizedBox(height: EvaSpace.s2),
          Text(
            [
              if (job.workdir != null) 'workdir: ${job.workdir}',
              if (job.model != null) 'model: ${job.model}',
            ].join(' · '),
            style: const TextStyle(fontSize: EvaType.xs, color: EvaColors.textMuted),
          ),
          const SizedBox(height: EvaSpace.s3),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  onPressed: busy ? null : () => controller.respondToJob(job.id, approve: true),
                  style: FilledButton.styleFrom(backgroundColor: EvaColors.remembered, foregroundColor: EvaColors.crust),
                  child: const Text('Approve'),
                ),
              ),
              const SizedBox(width: EvaSpace.s2),
              Expanded(
                child: OutlinedButton(
                  onPressed: busy ? null : () => controller.respondToJob(job.id, approve: false),
                  style: OutlinedButton.styleFrom(foregroundColor: EvaColors.danger, side: const BorderSide(color: EvaColors.danger)),
                  child: const Text('Deny'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
