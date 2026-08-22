# Delegate-to-Claude + HITL approval — spec

_Design session, 2026-08-22. This is Phase 2 of the "with hands" arc
([full plan](2026-07-22-EVA-WITH-HANDS-PLAN.md), PR #7, merged docs-only,
nothing built yet). Phase 0 (sleeptime) and Phase 1 (the `eva-task-runner`
spine — job store, executors, injection, push) are both done and running
live; this phase adds the first job kind that actually **does** something on
the host, gated behind your approval. Not started. See also today's other
specs: [situational context](2026-08-22-situational-context-spec.md),
[timers/reminders](2026-08-22-timers-reminders-spec.md),
[tool-discovery](2026-08-22-tool-discovery-spec.md),
[tool-trace transparency](2026-08-22-tool-trace-transparency-spec.md), and
[admin panel](2026-08-22-eva-admin-panel-spec.md). Phase 3 — Flutter
approval cards, `spawn_task`, queueing, trust allowlists, job history, and
the eva-web-router-bypass fix — has its own spec:
[hands-phase3](2026-08-22-hands-phase3-spec.md)._

## The idea, in one line

Eva can propose a real task ("go clean up that script", "check why the
CoolerControl service keeps failing") for `claude -p` to run on the host with
real file/tool access; nothing executes until you explicitly approve it from
your phone; when it's done, she reports back in character the same way a
research job does today.

## What's already there vs. what this adds

The plan's diagram named five pieces. Two are already built (from Phase 1,
confirmed live in `eva-task-runner/runner.py`):

- **Job store** (SQLite, `~/.local/share/eva/tasks.db`) — generic `jobs`
  table already has `id`/`kind`/`spec`/`state`/`result`/`error`. Adding a
  `claude` kind needs **one new state**, `pending_approval`, ahead of
  `pending` in the existing `pending → running → done|failed` machine — the
  runner's docstring already calls this out as the only change needed outside
  `executors/`.
- **Injection + push on completion** — `_report()`/`_inject()`/`_push()`
  already exist and are kind-agnostic (`_format_report` branches on
  `job["kind"]`; a `claude` branch is a small addition, not new plumbing).
  Push is **FCM**, not the plan's originally-decided ntfy (see
  [ROADMAP.md](ROADMAP.md) staleness note — this is the one real deviation
  from the locked plan, and it's already in production for research jobs and
  timers, so `claude` rides the same rail for free).

What's actually new for this phase:

1. `executors/claude_code.py` — runs `claude -p` on the host.
2. The `pending_approval` gate — a job of kind `claude` does **not** get
   dispatched to a thread on `POST /jobs` the way `research` does today; it
   sits until approved.
3. An approve/deny surface reachable from your phone.
4. `delegate_to_claude` / `check_task` tools + a `work` toolset group, plus a
   persona note for how Eva talks about proposing/waiting.

## 1. The `claude` executor

`eva-task-runner/executors/claude_code.py`, matching `research.py`'s shape
(`run(spec) -> dict`, called by `_run_job`):

```python
def run(spec: dict) -> dict:
    """spec: {"task": str, "workdir": str?}. Runs `claude -p <task>
    --output-format json` on the host as this user, in workdir (defaulting to
    somewhere safe — see Workdir below), captures stdout/stderr/exit code."""
```

- **Timeout.** A hard wall-clock cap (`CLAUDE_JOB_TIMEOUT_S`, something like
  900s to start) — an unattended `claude -p` run needs a backstop the way the
  research executor's `MAX_COST_USD`/`max_iterations` do, for the same
  reason: a bad run must terminate instead of running forever unsupervised.
- **Workdir.** Defaults to a fixed, deliberately-scoped directory (e.g.
  `~/eva-workspace/`, created if missing) rather than `$HOME` — same instinct
  as `prepare-games-drive.sh`'s serial guard: default to the narrow safe
  choice, require an explicit override to go wider. Eva can pass a specific
  `workdir` when the task calls for it (e.g. `~/projects/eva` for This Very
  Repo), but nothing defaults to "wherever" only because the tool doesn't
  say.
- **`--permission-mode`.** Since Claude Code's own guardrails are one of the
  two layers the plan names (the other being your approval), start the
  executor pinned to a mode that still prompts/declines on genuinely
  destructive actions rather than `--dangerously-skip-permissions` — your
  approval gate covers "should this task run at all," not "should every
  individual command inside it run unchecked." Worth an explicit choice at
  build time, not a default inherited from whatever `claude` picks alone.
- **Output.** Full `stdout`/`stderr`/exit code captured into `result` — same
  "everything's in the job store for after-the-fact review" property the
  plan's Security posture section calls for. `_format_report` gets a
  `claude` branch: something like *"The task you delegated — '…' — finished.
  &lt;last N lines of output, or a one-line exit-code note if it's mostly
  silent&gt;."*
- **Cost.** Unlike `research_task`'s Mistral API metering, a host `claude -p`
  run bills against your own Claude subscription/API usage the normal CLI
  way — no separate cost-log entry needed here, but worth a mention in the
  job record (e.g. session/turn count from `--output-format json`) so a job
  history view can show it later.

## 2. The `pending_approval` gate

Smallest change with the biggest safety payoff. Today, `do_POST`'s `/jobs`
handler always does:

```python
job_id = create_job(kind, spec)
threading.Thread(target=_run_job, args=(job_id, kind, spec), daemon=True).start()
```

For `kind == "claude"`, this needs to branch: create the job in state
`pending_approval` instead of `pending`, **do not** start the executor
thread, and instead fire the approval notification (see below). Two new
endpoints, same shape as `/checkin/trigger`'s pattern (thread-dispatched,
answered immediately):

- `POST /jobs/<id>/approve` — flips `pending_approval → pending`, *then*
  dispatches `_run_job` exactly like a normal job would have on submission.
- `POST /jobs/<id>/deny` — flips `pending_approval → denied` (a new terminal
  state, distinct from `failed` — a denied job isn't an error, it's a
  decision), and still runs `_report()`'s injection path so Eva finds out
  ("Stephan didn't approve running that") instead of just... never hearing
  back, which would read as her request vanishing into a void.

Both need **auth** — this is the one truly destructive action in the whole
system, so it can't be a bare loopback POST reachable by anything that
guesses a job id. Simplest fit with the existing stack: route it through
eva-web (already Cloudflare-Access-gated for the phone) rather than exposing
it on the runner directly, same as how `/push/register` reaches the runner
today via the tunnel.

## 3. The approval surface

The plan flagged "simplest first: an eva-web page/endpoint the push action
deep-links to; later, a proper Flutter card." Given FCM (not ntfy) is
already the push rail, and eva-web already serves a couple of small JSON
endpoints (`/api/checkin/config`, `/api/checkin/trigger`), the shape:

- `eva-web` gets `GET /api/jobs/pending` (list jobs in `pending_approval`,
  proxying `GET /jobs?state=pending_approval` to the runner) and
  `POST /api/jobs/<id>/approve|deny` (proxying through to the runner's new
  endpoints). This keeps the runner loopback-only and untouched by anything
  beyond eva-web, matching every other cross-boundary call in the stack.
- **v1 (fastest to ship):** a tiny server-rendered HTML page at
  `eva-web`'s existing origin — `GET /jobs` renders pending approvals with
  Approve/Deny buttons that POST back to the endpoints above. No new Flutter
  work, reachable from the phone via a plain link in the FCM notification
  (FCM notifications can carry a data payload with a URL the OS opens on
  tap, the same way ntfy's action buttons would have). This is explicitly a
  stopgap — Phase 3 promotes it to a real card in the app — but it's enough
  to actually use the feature end to end.
- **What the notification says.** When Eva calls `delegate_to_claude`, the
  runner pushes an approval-flavored FCM message: title "Eva wants to run a
  task", body = the task text (truncated), tapping it opens the v1 page.

## 4. Eva's tools

New `work` toolset group in `toolsets.json` (alongside `research`, same
lazy-loading convention — `search_tools`/`call_tool`, not core-attached):

- `delegate_to_claude(task, workdir=None)` — thin HTTP POST to
  `EVA_RUNNER_URL/jobs` with `{"kind": "claude", "spec": {...}}`, same shape
  as `tools/create_timer.py`. Returns `{job_id, state: "pending_approval"}`
  immediately — the docstring needs to be explicit (mirroring
  `create_timer`'s own docstring style) that this **never runs anything on
  its own**, it just proposes, and Stephan has to say yes on his phone before
  anything happens. This is as much a prompt-engineering guard as a
  mechanical one — the same category of lesson as today's situational-context
  incident: what the tool *can* do and what Eva *believes* it does need to
  match, stated plainly in the docstring she reads.
- `check_task(job_id)` — already exists for `research` (per `toolsets.json`'s
  `research` group); reusable as-is for `claude` jobs too, since it just
  reads job state/result generically. Might just move to `core` or get
  duplicated into `work`'s group list — small toolsets.json edit either way.

Persona note (`persona/eva.md`, "How I check in on my own"-style addition):
how Eva talks about proposing a delegated task and then waiting — she should
frame it as *asking*, not *doing* ("I'd like to have Claude look into X — I
sent you the approval request"), and shouldn't imply something already
happened until the completion report actually arrives.

## Open questions for build time

- **Timeout value and `--permission-mode` choice** — needs a real decision,
  not a default inherited silently; propose a starting value, tune from
  actual use.
- **Workdir scoping** — is a single fixed `~/eva-workspace/` enough, or does
  this need to work against `~/projects/eva` itself from day one (self-
  modifying the project that built it)? Affects whether `workdir` needs
  validation/allowlisting or stays a free-text field.
- **v1 approval page auth** — riding Cloudflare Access (already gating
  `eva.qstivi.com`) is probably enough without adding a second auth layer,
  but worth confirming the same Access policy actually covers a new
  `eva-web` route before shipping it reachable from outside the LAN.
- **Multiple concurrent `claude` jobs** — the plan already flags serializing
  *injections* so Eva's replies don't interleave; a second, separate
  question specific to this executor is whether two `claude -p` runs should
  be allowed to run concurrently at all, given they share the host's real
  filesystem.
