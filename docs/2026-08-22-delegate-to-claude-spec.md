# Delegate-to-harness + HITL approval — spec

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

**Pivoted same day (still 2026-08-22), before any of this was built:** the
original plan (and this doc's first draft) had the executor run `claude -p`
on the host — chosen specifically because Claude Code bundles file editing,
shell exec, search, and its own permission modes, so the HITL gate below
only has to answer "should this run at all," not "should every command
inside it run unchecked." That reasoning holds, but a genuinely comparable
option now exists: **DeepSeek Harness** (`dsh`), an open-source (MIT),
model-agnostic agent framework that launched in developer preview this same
month — same category of built-in capability (file inspect/edit, shell,
search, plans, subagent delegation, approval-policy enforcement), but
pointable at any OpenAI-compatible backend instead of locked to one vendor.
Decision: **build Phase 2 on DeepSeek Harness + Mistral models only, no
`claude -p` for now** — cheaper (fits the cost-tiering work done today —
see [[eva-with-hands-plan]]), and it's the harder thing to walk back later
if it doesn't pan out, so it's worth actually trying before defaulting to
the vendor-locked option. `claude -p` (or Claude Code as a harness subagent
— the harness supports that) stays a documented escalation option, not
built now.

## The idea, in one line

Eva can propose a real task ("go clean up that script", "check why the
CoolerControl service keeps failing") for DeepSeek Harness, running on
Mistral models, to carry out on the host with real file/tool access;
nothing executes until you explicitly approve it from your phone; when it's
done, she reports back in character the same way a research job does today.

## What's already there vs. what this adds

Two pieces already built (from Phase 1, confirmed live in
`eva-task-runner/runner.py`):

- **Job store** (SQLite, `~/.local/share/eva/tasks.db`) — generic `jobs`
  table already has `id`/`kind`/`spec`/`state`/`result`/`error`. Adding a
  `harness` kind needs **one new state**, `pending_approval`, ahead of
  `pending` in the existing `pending → running → done|failed` machine — the
  runner's docstring already calls this out as the only change needed
  outside `executors/`.
- **Injection + push on completion** — `_report()`/`_inject()`/`_push()`
  already exist and are kind-agnostic (`_format_report` branches on
  `job["kind"]`; a `harness` branch is a small addition, not new plumbing).
  Push is FCM (see the earlier ntfy→FCM deviation note in the plan doc).

What's new for this phase:

1. `executors/harness.py` — runs DeepSeek Harness headless on the host.
2. The `pending_approval` gate — a job of kind `harness` does **not** get
   dispatched to a thread on `POST /jobs` the way `research` does today; it
   sits until approved.
3. A pre-dispatch **moderation check** on the task text (Shieldstral and/or
   Mistral Moderation 2) — see Safety layer below; this is new precisely
   *because* Claude Code's own permission prompts are no longer in the loop.
4. An approve/deny surface reachable from your phone.
5. `delegate_to_harness`/`check_task` tools + a `work` toolset group, plus a
   persona note for how Eva talks about proposing/waiting.

## 1. The `harness` executor

`eva-task-runner/executors/harness.py`, matching `research.py`'s shape
(`run(spec) -> dict`, called by `_run_job`):

```python
def run(spec: dict) -> dict:
    """spec: {"task": str, "workdir": str?, "model": str?}. Runs DeepSeek
    Harness headless on the host as this user, in workdir (defaulting to
    somewhere safe — see Workdir below), captures stdout/exit code."""
```

- **Invocation.** Headless one-shot mode:
  `npx @deepseek-ai/dsh --profile headless "<task>"` — prints the final
  answer to stdout and exits, matching `research.py`'s existing pattern of
  a synchronous subprocess call inside the background thread `_run_job`
  already provides. Confirm the exact flag set (profile config, workdir
  arg) against the installed version at build time — this is a days-old
  project, docs are still catching up to the CLI.
- **Model backend.** Configured as a custom provider (provider ID, base
  URL, API type, model name — set via `dsh`'s Settings→Models, or its
  config file once located) pointed at Mistral's OpenAI-compatible API,
  same key-fetch pattern `research.py` already uses (pulled live from
  Letta's own provider store, never duplicated into a new env file).
  Two backend choices depending on task shape, both from today's tier
  work:
  - **`mistral-large-latest`** (the retuned "mid" tier model) as the
    general default — same reasoning as everywhere else it's used today:
    strong performance bar, a third/fifth the cost of Medium.
  - **`codestral-2508`** for tasks that are clearly code-focused (FIM/
    completion-shaped work) — Mistral's dedicated coding model, $0.30/$0.90
    per M tokens, 128k context. Worth a simple heuristic (or just a
    `model` field on the job spec Eva can set) rather than always paying
    for whichever is fancier.
- **Timeout.** A hard wall-clock cap (`HARNESS_JOB_TIMEOUT_S`), same
  reasoning as the research executor's `MAX_COST_USD`/`max_iterations` — an
  unattended agent run needs a backstop.
- **Workdir.** Defaults to a fixed, deliberately-scoped directory (e.g.
  `~/eva-workspace/`, created if missing) rather than `$HOME` — same
  instinct as `prepare-games-drive.sh`'s serial guard. Eva can pass a
  specific `workdir` when the task calls for it.
- **Output.** Full stdout + exit code captured into `result`.
  `_format_report` gets a `harness` branch: *"The task you delegated —
  '…' — finished. &lt;summary/last-N-lines&gt;."*
- **Cost.** Logged to the same `~/.config/eva-web/cost_log.jsonl`
  `research.py` writes to, using each backend's real per-M pricing (already
  known: Large $0.50/$1.50, Codestral $0.30/$0.90) against whatever usage
  numbers the harness's run surfaces — confirm the harness reports
  token usage in its headless output; if not, this may need to come from
  Mistral's own usage API instead.

## 2. Safety layer — moderation pre-check

**This is new specifically because `claude -p` is not in the loop.** The
original plan leaned on two layers: your approval, and Claude Code's own
permission prompts as a second line of defense inside the job. DeepSeek
Harness has its own approval-policy plugin (per its docs), but it's days
old and unproven here — not something to trust blind yet. So Phase 2 adds
an explicit, cheap pre-check instead of leaning on either:

- Before a `harness` job leaves `pending_approval` (i.e. right when you'd
  be shown the approve/deny prompt), run the task text through **Mistral
  Moderation 2** (`POST /v1/moderations`, free, dedicated classification
  endpoint — not a prompted chat call) and/or **Shieldstral 1.0** (yes/no
  policy questions, e.g. "does this task ask for something destructive or
  outside the intended scope?"). A flagged task still shows up for your
  approval, but with a visible warning — this doesn't replace your
  judgment, it surfaces something worth a second look before you tap
  approve.
- See [[mistral-shieldstral-moderation-model]] for the three models' exact
  specs/pricing/endpoints — this is the concrete use case that memory was
  written for.
- Once the harness's own approval-policy plugin has some real track record,
  worth revisiting whether the pre-check is still needed as a separate
  step or folds into that.

## 3. The `pending_approval` gate

Unchanged in mechanics from the original design — this part doesn't depend
on which executor is behind it. Today, `do_POST`'s `/jobs` handler always
does:

```python
job_id = create_job(kind, spec)
threading.Thread(target=_run_job, args=(job_id, kind, spec), daemon=True).start()
```

For `kind == "harness"`, this needs to branch: create the job in state
`pending_approval` instead of `pending`, run the moderation pre-check (§2),
**do not** start the executor thread, and fire the approval notification.
Two new endpoints, same shape as `/checkin/trigger`'s pattern
(thread-dispatched, answered immediately):

- `POST /jobs/<id>/approve` — flips `pending_approval → pending`, *then*
  dispatches `_run_job` exactly like a normal job would have on submission.
- `POST /jobs/<id>/deny` — flips `pending_approval → denied` (a new
  terminal state, distinct from `failed`), and still runs `_report()`'s
  injection path so Eva finds out ("Stephan didn't approve running that")
  instead of the request just vanishing.

Both need **auth** — the one truly destructive action in the whole system,
so it can't be a bare loopback POST reachable by anything that guesses a
job id. Route it through eva-web (already Cloudflare-Access-gated for the
phone) rather than exposing it on the runner directly, same as how
`/push/register` reaches the runner today via the tunnel.

## 4. The approval surface

**v1 (fastest to ship):** a tiny server-rendered HTML page at eva-web's
existing origin — `GET /jobs` renders pending approvals (including the
moderation flag from §2 if set) with Approve/Deny buttons that POST back to
the endpoints above. No new Flutter work, reachable from the phone via a
plain link in the FCM notification's data payload. Explicitly a stopgap —
Phase 3 promotes it to a real card in the app.

`eva-web` gets `GET /api/jobs/pending` (proxying
`GET /jobs?state=pending_approval` to the runner) and
`POST /api/jobs/<id>/approve|deny` (proxying through to the runner).

## 5. Eva's tools

New `work` toolset group in `toolsets.json` (alongside `research`, same
lazy-loading convention):

- `delegate_to_harness(task, workdir=None, model=None)` — thin HTTP POST to
  `EVA_RUNNER_URL/jobs` with `{"kind": "harness", "spec": {...}}`, same
  shape as `tools/create_timer.py`. Returns `{job_id, state:
  "pending_approval"}` immediately — docstring needs to be explicit
  (mirroring `create_timer`'s style) that this **never runs anything on its
  own**, it just proposes, and Stephan has to say yes on his phone first.
- `check_task(job_id)` — already exists for `research`; reusable as-is.

Persona note (`persona/eva.md`): how Eva talks about proposing a delegated
task and waiting — frame it as *asking*, not *doing*, and don't imply
something already happened until the completion report actually arrives.

## Open questions for build time

- **Exact `dsh` headless invocation and config format** — confirm against
  the installed version rather than trusting docs still catching up to a
  days-old CLI; the GitHub repo (`deepseek-ai/deepseek-harness`) is the
  source of truth over any blog tutorial.
- **Token usage reporting** — confirm whether headless output includes
  usage numbers for accurate cost logging, or whether that needs a
  separate call to Mistral's usage API.
- **Codestral vs. Large routing** — a real heuristic, an explicit `model`
  field Eva sets, or always-Large-unless-told-otherwise? Decide once real
  task shapes are seen.
- **Moderation-flag UX** — exactly what the approval page shows when
  Shieldstral/Moderation flags a task (a red banner? block approval
  entirely and require a second confirm?) — needs a decision, not just "it
  shows up."
- **Workdir scoping** — fixed `~/eva-workspace/` vs. allowing
  `~/projects/eva` itself from day one.
- **v1 approval page auth** — riding Cloudflare Access (already gating
  `eva.qstivi.com`) is probably enough, but confirm the same Access policy
  covers a new `eva-web` route before shipping it reachable from outside
  the LAN.
- **Multiple concurrent `harness` jobs** — same open question Phase 3
  already names for injection ordering/execution concurrency generally.
- **Claude Code escalation, deferred** — if Mistral-backed harness quality
  proves insufficient on hard tasks, the harness can call Claude Code as a
  subagent, or `claude -p` can be added back as a second executor kind
  later — not built now, by explicit choice.
