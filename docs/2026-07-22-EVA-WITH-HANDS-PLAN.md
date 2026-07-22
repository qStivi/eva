# Eva with hands — design & build plan

_Planning session, 2026-07-22. Covers the roadmap's "big arc": Eva delegating real
work, running it in the background, and reporting back — plus sleep-time memory
consolidation. Supersedes the three loose bullets under "The big arc" in
[ROADMAP.md](ROADMAP.md)._

## The arc, in one line

Give Eva **hands** (she can do real work, not just talk), a **background** (that
work runs while you keep chatting or walk away), and a **voice that reaches you**
(she tells you when it's done, even if the app is closed) — without handing a local
model unsupervised power over your machine.

Three features from the roadmap converge here because they need the **same spine**:

1. **Delegate to Claude Code** — Eva hands a hard task to `claude -p "<task>"`.
2. **Background tasks + check-ins** — she kicks off work, you keep going, she reports
   back / notifies you.
3. **Sleep-time memory consolidation** — a background brain tidies her memory.

(1) and (2) are the same machine (an async runner + a way back into the conversation
+ a push channel + human approval). (3) is mostly **Letta-native** and rides alongside
rather than through that machine — it's the cheapest win, so it goes first.

## Decisions locked this session

- **Push transport → self-hosted `ntfy`.** A rootless container like SearXNG/Letta,
  bound to the LAN; the Flutter app subscribes and gets native push even when closed.
  No Google/Firebase dependency, fits the self-hosted stack.
- **Delegated `claude -p` runs on the host, directly.** Full access to real files and
  tools — maximum usefulness. Blast radius is contained by **human-in-the-loop
  approval** (nothing runs until you say yes) plus Claude Code's own permission
  guardrails, _not_ by a sandbox. This is a deliberate power-over-safety trade; see
  [Security posture](#security-posture).

## The current shape (what we're building onto)

- **Letta 0.16.8**, rootless Quadlet unit, `Network=host`, API on `:8283`. Agent
  `eva` (`agent-87f7dbff…`) on `gpt-oss-20b`; `eva-spike` throwaway on qwen3-8b.
- **Chat is synchronous request/reply.** A turn = `POST /v1/agents/<id>/messages`,
  block until the model finishes, parse the reply. There is **no** async path, no job
  concept, no notifications anywhere in the stack today.
- **Custom Letta tools** run in a sandbox that can reach `http://localhost:8283` and
  gets `LETTA_AGENT_ID` injected (verified). They talk to Letta over plain HTTP.
- **The Flutter app talks to Letta _directly_** (`lib/api/letta_api.dart`, base URL
  `:8283`), **not** through eva-web. Consequences for this arc:
  - There is **no server-side seam today** where a background event can reach the
    phone. We add one.
  - The app already knows how to read Letta message **history** — it just needs a
    reason to refresh and a way to be woken.
  - (Aside: because it bypasses eva-web it also misses the toolset router. Out of
    scope here, but the seam we add is a good place to fix that later.)

## Architecture — the spine

```
                        ┌──────────────────────────────────────────┐
   you (app / web / CLI)│                                           │
        │  chat turn     │             eva-task-runner              │
        ▼                │        (new systemd --user unit)         │
   ┌─────────┐  delegate │   ┌──────────┐   ┌───────────────────┐   │
   │  Letta  │──tool────▶│──▶│ job store │──▶│ executor:          │  │
   │  agent  │  (submit) │   │ (sqlite)  │   │  • claude -p (host)│  │
   │  "eva"  │◀──inject──│◀──│           │   │  • shell/other     │  │
   └─────────┘  result   │   └────┬─────┘    └───────────────────┘   │
        ▲                │        │ on state change                  │
        │ app reads      │        ▼                                  │
        │ history        │   ┌─────────┐   ┌────────┐                │
        │                └──▶│  ntfy   │   │ HITL   │                │
        │                    │ (push)  │   │ queue  │                │
   ┌────┴────┐               └────┬────┘   └────────┘                │
   │  phone  │◀── native push ────┘                                  │
   └─────────┘                                                       │
                        └──────────────────────────────────────────┘
```

Four new pieces, one existing one adjusted:

### 1. `eva-task-runner` (new systemd --user unit)

A small stdlib-only Python service (same posture as eva-web), rootless, boot-started
via the existing linger. Responsibilities:

- Owns a **job store** — SQLite at `~/.local/share/eva/tasks.db`. A job has: id,
  kind (`claude` | `shell` | …), the prompt/spec, requested-by agent id, **state**
  (`pending_approval → approved → running → done|failed|denied`), created/updated
  timestamps, and captured output + exit status.
- Exposes a tiny **HTTP API on `127.0.0.1`** (loopback only — never the LAN):
  `POST /jobs` (submit), `GET /jobs/<id>`, `POST /jobs/<id>/approve|deny`,
  `GET /jobs?state=…`. This is what Eva's tools and the approval UI call.
- Runs an **executor** per job. For `claude`: `claude -p "<task>" --output-format json`
  in a chosen working directory, with a **timeout** and full output capture. On the
  host, as the user — no container.
- On every terminal state change: (a) **injects a result message back into Eva's
  Letta conversation** so she narrates it in character, and (b) fires an **ntfy**
  push.

Why a separate service and not "just do it in the tool"? A Letta tool call is
**synchronous inside the turn** — if the tool blocks on a 4-minute `claude -p`, the
whole chat turn blocks (and Letta's turn timeout trips). The tool must **submit and
return immediately** with a job id; the runner does the slow work out-of-band. This
is the crux of "background."

### 2. The Letta tools (Eva's hands)

New custom tools registered like the existing ones, added to `toolsets.json` as a new
lazy group (`work`, loaded when the message looks like a task):

- `delegate_to_claude(task, workdir=None)` → submits a `claude` job, returns
  `{job_id, state: "pending_approval"}`. **Never blocks.** Docstring makes clear to
  Eva that the work happens in the background and she'll be told when it's done.
- `spawn_task(command, ...)` → generic background job (later; same machinery).
- `check_task(job_id)` → reads current state/output, so Eva can answer "is it done?"
  if you ask before the push arrives.

All three are thin HTTP calls to the runner's loopback API. (Reminder from the
lazy-toolset work: every `def` in a tool's source needs a docstring, and the tool
sandbox reaches Letta over HTTP, not the Cloud `client` object.)

### 3. Re-injecting results into the conversation

When a job finishes, the runner does `POST /v1/agents/<eva-id>/messages` with a
message describing the outcome ("The task you delegated — '…' — finished. Result: …").
Use the **`system` role**, not `user`: this is an *event* the runner is reporting, not
something you said, so it must not be attributed to you in the transcript or mislead her
memory about who told her. (Verify Letta 0.16.8's exact handling of `system`-role
messages during Phase 1 — that it's delivered as an event the agent reacts to and turns
into a normal reply; fall back to a clearly-prefixed `user` event only if `system`
doesn't behave.) Letta then processes it as a normal turn: Eva reads it, reacts **in
character**, maybe scribbles a memory, and produces a reply. That reply lands in
Letta's message history like any other turn.

This is the elegant part: **the conversation stays the single source of truth.** The
app doesn't need a separate "notifications" data model — a check-in is just another
Eva turn it hasn't shown yet. The app refreshes history (on push, on foreground, or on
a light poll) and the new turn appears.

### 4. `ntfy` (self-hosted push)

- New rootless Quadlet unit `~/.config/containers/systemd/ntfy.container`, bound to
  the LAN (or loopback + reverse-proxy, matching the HA pattern), one **topic** for Eva.
- **Real auth, not an obscure topic name.** A topic name is at best a shared secret, so
  it's defense-in-depth only — the actual control is ntfy's **access-control (users +
  tokens / ACL)** with the topic locked down (a required publish token for the runner, a
  required subscribe token for the app), and **TLS** whenever it's reachable beyond
  loopback (i.e. via the reverse proxy, same as HA). Tokens live in a chmod-600 env file
  (`~/.config/eva/ntfy.env`), never in the repo — matching the `ha.env` pattern.
- Runner publishes on job completion / check-in: title = Eva's voice, body = short
  summary, with a tap-action deep-link into the app.
- **Flutter** subscribes: the `ntfy` app can forward to the phone with zero code, but
  for a first-class in-app experience we add an ntfy subscription (WebSocket/SSE to
  `/<topic>/ws`) + a local-notification plugin. When tapped/foregrounded → refresh
  Letta history.

### 5. HITL approval

Because `claude -p` runs on the host with real power, **no `claude` job runs until you
approve it.** Flow:

1. Eva calls `delegate_to_claude` → job is `pending_approval`. Eva tells you, in
   character, what she wants to run.
2. Runner pushes an **approval** ntfy ("Eva wants to run: …  [Approve] [Deny]").
3. You approve — via an **approval surface** (simplest first: an eva-web page /
   endpoint the ntfy action deep-links to; later, a proper card in the Flutter app).
4. Runner flips to `approved`, executes, reports back as above.

Approval is per-job. A later refinement: "trust this kind of task" allowlists, or a
dry-run/plan-only default for `claude -p`.

## Feature 3 first: sleep-time memory consolidation (Letta-native, no spine needed)

This one doesn't touch the runner/ntfy machinery at all, and it directly fixes a known
problem: gpt-oss-20b/qwen3-8b save memories proactively but in the **wrong perspective**
and sometimes **embellished** (see `eva-letta-local-stack` memory). Letta's
**sleeptime** agents exist for exactly this: a background agent that shares Eva's
memory blocks and consolidates them after turns.

Plan:

- Verify the exact 0.16.8 surface (`enable_sleeptime` on the agent vs. a sleeptime
  multi-agent group; how the sleeptime agent's model/frequency are configured) against
  the running server's `/openapi.json` before writing anything.
- Give the sleeptime agent the **30B-A3B-Thinking** model (the earlier scorecard's only
  all-green on faithfulness/perspective/dedup) — it's slow, but background is where slow
  is fine. It only spins up when Eva's foreground brain is idle, so VRAM hand-off with
  LM Studio needs a look (same class of problem as the ComfyUI↔LLM hand-off).
- Job of the consolidator: fix first-person→third-person drift, de-embellish, dedup,
  and **route dated/episodic facts to archival** (which is timestamped) while keeping
  stable facts in core (which isn't). This matches the memory-layer split already
  documented.
- Ship behind a switch; A/B against no-consolidation on the `eva-spike` agent first.

## Build sequence

**Phase 0 — sleeptime consolidation.** Letta-native, self-contained, high value, no new
infra. Validate on `eva-spike`, then enable on `eva`. _Deliverable: a background
consolidator + a short doc of the exact 0.16.8 knobs used._

**Phase 1 — the runner + ntfy, on a trivial job kind.** Stand up `eva-task-runner`
(job store + loopback API + systemd unit) and `ntfy`. Prove the spine end-to-end with a
**safe toy executor** (e.g. `sleep N` / echo) — no `claude` yet: submit → background →
result injected into Eva's conversation → ntfy push → app shows the turn. _This is the
riskiest integration; prove it before adding power._

**Phase 2 — `delegate_to_claude` + HITL.** Add the `claude` executor (host, timeout,
output capture), the `pending_approval` gate, and the approval surface (eva-web endpoint
first). Register the `work` toolset + tools; persona directive for how Eva talks about
delegating and waiting. _End state: you can ask Eva to do a real task, approve it, walk
away, and get pinged when it's done._

**Phase 3 — polish & generalize.** First-class Flutter approval/notification cards
(replace the eva-web stopgap); `spawn_task` generic jobs; concurrency/queueing; trust
allowlists / plan-only default; job history view. Fold in the eva-web-router-bypass fix
for the app while we're in that seam.

## Open questions / to resolve while building

- **Sleeptime VRAM contention:** running 30B-Thinking for consolidation vs. keeping
  gpt-oss-20b hot for chat on 16 GB. Sequential hand-off, a smaller consolidator, or
  cloud-escalate consolidation? (Ties into the separate cloud-escalation roadmap item.)
- **App refresh model:** pure push-triggered history fetch, or a low-frequency poll as
  well for when push is missed (doze)? Probably both.
- **Approval UX latency:** if you're at your desk, approving via a web page is fine; on
  the phone the ntfy action → eva-web round-trip should still be one tap. Confirm ntfy
  action buttons can hit an authenticated endpoint cleanly.
- **Multiple concurrent jobs & one Eva:** injecting several result-turns close together
  — serialize injections so her conversation doesn't interleave confusingly.

## Security posture

The chosen "on the host, directly" executor means a **local model's suggestion can lead
to real commands running as you**. The safety model is explicit and layered:

- **Eva can only ever _propose_.** `delegate_to_claude` submits; it cannot execute.
- **You are the gate.** No `claude` job leaves `pending_approval` without an explicit
  approve action from you. Deny is one tap.
- **Claude Code's own guardrails** apply inside the job (its permission prompts / mode).
- **The runner's control API is loopback-only** (`127.0.0.1`); only ntfy and the app
  touch the LAN, and ntfy is push-out only.
- **Everything is logged** — every job's prompt, approver decision, command, and output
  is in the job store for after-the-fact review.

Future hardening if the trade feels too loose in practice: a plan-only/dry-run default,
per-task-kind allowlists, or moving the executor into the "dedicated distrobox" option
we deferred — the runner's executor is intentionally pluggable so that swap is cheap.
