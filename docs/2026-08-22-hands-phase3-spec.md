# "With hands" Phase 3 — polish & generalize — spec

_Design session, 2026-08-22. This is Phase 3, the last phase of the "with
hands" arc ([full plan](2026-07-22-EVA-WITH-HANDS-PLAN.md), PR #7). It only
makes sense once [Phase 2](2026-08-22-delegate-to-claude-spec.md) actually
exists and is being used for a while — this spec exists now so the backlog
is fully mapped, not because it's next in line. Not started._

## What the plan actually asked for

The plan's own Phase 3 line: *"First-class Flutter approval/notification
cards (replace the eva-web stopgap); `spawn_task` generic jobs;
concurrency/queueing; trust allowlists / plan-only default; job history
view. Fold in the eva-web-router-bypass fix for the app while we're in that
seam."*

Six distinct items, none of them blocking each other — this reads as a
punch list to pick from once Phase 2 is live and its rough edges are known,
not a single feature. Below is each one grounded in the code as it stands
today (post Phase 1, assuming Phase 2 lands roughly as specced).

## 1. Flutter approval/notification cards

Replaces Phase 2's v1 stopgap (a server-rendered eva-web HTML page reached
by tapping the FCM notification). The infra is already most of the way
there:

- `PushService` (`flutter/lib/services/push_service.dart`) already parses
  `RemoteMessage.data` and shows a local notification; today `_showJobNotification`
  just displays title/body. An approval push needs a `type: "approval"` (or
  similar) field in the FCM data payload so the handler can branch — show an
  actionable notification (Android supports action buttons on a local
  notification) or at minimum deep-link into a new in-app screen instead of
  the eva-web page.
- New screen, e.g. `flutter/lib/screens/approvals_screen.dart` — mirrors
  `memory_screen.dart`'s existing list-of-cards pattern (see
  `widgets/memory_note.dart` for the card-widget convention already in the
  app). Lists jobs in `pending_approval` (`GET /api/jobs/pending`, defined in
  Phase 2's spec), each card showing the task text + Approve/Deny buttons
  that POST straight to eva-web's proxy endpoints.
- `onForegroundPush` (already wired in `push_service.dart` to
  `EvaController.refreshMessages()`) gets a sibling hook for "refresh the
  pending-approvals list," so a card doesn't need a manual pull-to-refresh
  if the app happens to be open when the push lands.
- Once this exists, the v1 eva-web HTML page can be deleted outright — it
  was explicitly a stopgap, not something to keep maintaining in parallel.

## 2. `spawn_task` — generic background jobs

Today every job kind is bespoke (`research`, and Phase 2's `harness`), each
with its own executor module and its own tool
(`delegate_to_harness`/`research_task`). A `spawn_task(command, ...)` tool
would let Eva run an arbitrary host command as a background job without a
new executor per use case — e.g. `spawn_task("rpm-ostree status")` instead
of needing a purpose-built tool for every possible host query.

- Needs its own `pending_approval` treatment too — arguably *more*
  cautious than `harness` jobs, since a bare shell command has neither
  DeepSeek Harness's own tooling nor the Phase 2 moderation pre-check as a
  second line of defense (see Phase 2's Safety layer section). Worth
  deciding whether `spawn_task` inherits the same trust-allowlist mechanism
  (item 4 below) as a hard requirement rather than an optional refinement,
  given it has fewer guardrails than `delegate_to_harness`.
- Executor shape matches `harness.py`'s (timeout, captured stdout/exit
  code, workdir) minus the harness-specific bits.

## 3. Concurrency / queueing

The plan already flags one specific angle: *"injecting several result-turns
close together — serialize injections so her conversation doesn't
interleave confusingly."* Two related but separate problems once multiple
job kinds exist side by side:

- **Injection ordering** — `_run_job`/`_report` today run on their own
  daemon thread per job with no coordination between them; two jobs
  finishing seconds apart could `POST /v1/agents/{id}/messages` interleaved.
  A simple fix: a single-writer lock (or a small queue drained by one
  worker) around `_inject`/`_inject_and_get_reply`, so result turns land in
  Eva's conversation strictly one at a time regardless of how many executor
  threads are running concurrently.
- **Execution concurrency** — a separate question of whether two `harness`
  (or `spawn_task`) jobs should be allowed to run against the host
  filesystem at the same time at all (flagged as open in the Phase 2 spec).
  If the answer ends up "no," this item is where an actual job queue (cap
  concurrent `running` jobs at 1, or per-kind) gets built — today's
  `_run_job` dispatch has no such cap, every submitted/approved job starts
  its thread immediately.

## 4. Trust allowlists / plan-only default

Refinement to Phase 2's per-job approval gate, named directly in the plan's
Security posture "future hardening" list:

- **Plan-only/dry-run default** — if DeepSeek Harness's own plan-mode
  proves reliable (or `claude -p`'s, if that escalation path ever gets
  built), wiring the executor to default there and only escalate to real
  execution once *that* plan is separately approved would turn one approval
  into two, trading speed for a tighter loop. Worth exposing as a per-job
  or global toggle rather than hardcoding one way.
- **Trust allowlists** — some task *kinds* or workdirs could be marked
  "always auto-approve" once you've seen enough of them go fine (e.g.
  read-only research-style asks in `~/eva-workspace/`), while anything
  touching `~/projects/*` or making writes still gates on approval. This is
  explicitly the plan's own suggested next step if the "approve everything"
  friction turns out to be too high in practice — not something to
  pre-build speculatively before Phase 2 has real usage to judge that from.

## 5. Job history view

`GET /jobs`/`GET /jobs/<id>` already exist and return everything needed
(spec, state, result, error, timestamps) — this item is purely a
presentation layer, likely folded into the [admin panel](2026-08-22-eva-admin-panel-spec.md)
rather than built as its own screen, since that's already the place
speced for "things Stephan wants to inspect that aren't part of normal
chat." Worth resolving whether this lives there or gets its own Flutter tab
once both specs are further along — not a technical question, just an IA
one.

## 6. The eva-web-router-bypass fix

Documented gap, not new work invented for this spec: the Flutter app talks
to Letta **directly** (`lib/api/letta_api.dart`, `baseUrl` pointed straight
at `:8283`) for `agents()`, `blocks()`, `history()`, `archival()`,
`setModel()` — only the live chat-send path goes through eva-web
(`sendMessageViaWeb`, confirmed still the case: `letta_api.dart` line 4's
own comment references it, `_u()`/`baseUrl` used for everything else).
Consequence: anything eva-web adds sits *only* on the send path —
`situational_context` refresh, `model_router` cost-tiering, and today's
tool-trace building all only apply when a message is actually sent through
`/api/chat`, never on a bare `history()`/`blocks()` read.

This item existed before Phase 3 was ever named — the plan flagged it back
in July as something to "fold in ... while we're in that seam," i.e.
opportunistic cleanup once other Flutter-side work (this phase's approval
cards) already has the app's networking code open, not something requiring
its own dedicated pass. Concretely: route `agents()`/`blocks()`/`history()`/
`archival()`/`setModel()` through eva-web proxy endpoints the same shape as
`/api/checkin/config` today, so the app has exactly one path to Letta and
eva-web is genuinely the single front door the plan originally described it
as.

## Sequencing note

None of items 1–6 depend on each other structurally, but 1 (approval cards)
is the one Phase 2 actually needs to feel finished for daily use — the
others (2, 3, 4, 6) are hardening/generalization that matter more the
longer Phase 2 runs in the wild, and 5 mostly rides on the admin panel spec
landing first. Reasonable order once this phase is picked up: 1, then
whichever of 3/4 real Phase-2 usage actually surfaces as painful, with 2/6
picked up opportunistically alongside.
