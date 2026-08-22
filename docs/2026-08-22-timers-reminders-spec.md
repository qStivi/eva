# Reminders/timers ("set an alarm") — spec

_Design session, 2026-08-22. Not yet built. One of three specs from the same
session — see also
[tool-discovery](2026-08-22-tool-discovery-spec.md) and
[situational-context](2026-08-22-situational-context-spec.md)._

## The idea, in one line

An alarm/reminder, the way you'd set one on your phone — either you ask Eva to
set it ("remind me to hang up the laundry in 40 minutes") or she decides to set
one herself mid-conversation. When it fires, **both of you get notified**: your
phone gets a push, and Eva "remembers" it fired so she can bring it up naturally
next time you talk — not just a silent ping to your phone.

## Why custom, not Home Assistant

HA's Assist *does* already have native ad-hoc timer intents
(`HassStartTimer`/`HassCancelAllTimers` — the latter is already in
`toolsets.json`'s `house_extras` group, wired for a different purpose: cancelling
things Eva or you started via voice on a speaker). These are genuinely ad-hoc
(no pre-declared timer entity needed) and would work for "set a timer," but:

- they announce via TTS/notification on whatever HA surface started them, not
  your phone specifically, and not through the FCM channel your phone actually
  gets Eva's other pushes through;
- they have no path back into Eva's Letta conversation — firing one doesn't
  make her "remember" the reminder happened, so she can't bring it up later.

Since both of those are the point, build it where the plumbing already exists:
`eva-task-runner` already has a poll-loop scheduler, FCM push (`_push`), and a
way to inject a nudge into Eva's conversation and read back her reply
(`_inject_and_get_reply`) — all built this session for check-ins. A timer is
just a generalized, one-off, user-labeled check-in.

## Data model

New table in `eva-task-runner`'s sqlite db, alongside `checkin_config`:

```sql
CREATE TABLE IF NOT EXISTS timers (
    id TEXT PRIMARY KEY,          -- uuid
    reminder TEXT NOT NULL,       -- "hang up the laundry" — becomes the nudge text
    due_at REAL NOT NULL,         -- unix epoch seconds
    created_by TEXT NOT NULL,     -- 'eva' | 'user' — cosmetic, for the nudge wording
    created_at REAL NOT NULL,
    fired_at REAL                 -- NULL until fired; poll loop's dedupe key
)
```

No recurrence for v1 — one-shot only, matching "set an alarm." Recurring
reminders (if ever wanted) are a separate future feature, not this spec.

## Firing

Reuse the existing `CHECKIN_POLL_S` (5 min) poll loop pattern — or fold timer
checks into the same loop that already wakes every 5 min for check-ins, since
5-minute granularity is fine for "remind me in 40 minutes" (worst case ±5 min,
same tolerance check-ins already accept). A dedicated shorter-interval loop
isn't worth the complexity unless minute-level precision is requested later.

On fire (`due_at <= now and fired_at is NULL`):
1. Mark `fired_at = now` immediately (dedupe against a slow tick).
2. `_push(reminder, title="Eva")` — same FCM path as check-ins/job results.
3. `_inject(...)` a system-role nudge along the lines of: *"A reminder you set
   just fired: '{reminder}'. Bring it up if it's natural, otherwise let it be —
   your call."* — reuse `_do_checkin`'s pattern of only actually surfacing it
   in-conversation if Eva has something to say, not forcing a reply. Unlike
   check-ins, the phone push always fires regardless of whether Eva replies
   in-band (the point is a real alarm, not a maybe-alarm).

## Surfacing to Eva as a tool

New tool, `create_timer(minutes: int, reminder: str)`, always attached (small,
core-ish — not gated behind the toolset router; alarms should never be
"missable" because a toolset wasn't loaded). Inserts a row, returns
confirmation text. No `cancel_timer`/`list_timers` in v1 — add if it turns out
to be needed once real usage shows the gap.

## HTTP surface (for the app / HA, mirroring the check-in routes)

- `POST /timers` `{minutes, reminder}` → create (used by the tool; also lets
  the Flutter app offer a manual "set a reminder" UI later if wanted)
- `GET /timers` → list pending, for a future "your reminders" screen
- (proxied through eva-web the same way `/api/checkin/*` is, if the app or HA
  ever needs to reach it directly rather than through Eva deciding)

## Open questions for build time

- Exact wording/persona voice for the in-conversation nudge — check against
  `persona/eva.md`'s "How I check in on my own" section, likely wants a
  sibling section.
- Whether `create_timer` needs a cap (e.g. no reminder more than N days out) —
  probably not worth gating for v1.
