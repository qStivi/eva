# Proactive check-ins — Home Assistant trigger

Eva can now start a conversation instead of only answering one, via
`eva-task-runner`'s check-in scheduler (see `eva-task-runner/runner.py`'s
docstring). Two trigger sources:

- **Scheduled** — a background loop in the runner, on/off + interval + quiet
  hours, all configurable from the Flutter app's Settings screen.
- **On demand** — `POST /checkin/trigger` on the runner, proxied through
  eva-web at `/api/checkin/trigger`. This is what Home Assistant calls.

Either way, Eva only actually replies (and pushes to the phone) if she
decides there's something worth saying — see persona/eva.md's "How I check
in on my own" section. A nudge that gets no reply is a normal, expected
outcome, not a bug.

## Wiring it into Home Assistant

`/api/checkin/trigger` reuses the **same Bearer key** Eva's conversation
agent integration already uses (`EVA_API_KEY`) — no second credential to
manage in HA.

Add to `configuration.yaml` (or wherever you keep `rest_command:`):

```yaml
rest_command:
  eva_checkin:
    url: "http://192.168.128.126:8284/api/checkin/trigger"
    method: POST
    content_type: "application/json"
    headers:
      Authorization: "Bearer eva-xd7OWrnHCuTPaZULFlwcdkCC2qyNl2jB2aXNr2iYUOE"
    payload: '{"reason": "{{ reason | default("manual") }}"}'
```

Then any automation can call it with whatever context you want Eva to have:

```yaml
automation:
  - alias: "Eva check-in: got home"
    trigger:
      - platform: state
        entity_id: person.stephan
        to: "home"
    action:
      - service: rest_command.eva_checkin
        data:
          reason: "Stephan just got home"
```

`reason` is free text — it's dropped straight into the nudge Eva sees (never
shown to her as something you said, always framed as background context; see
`runner.py`'s `_checkin_nudge_text`). Fire it from as many automations as you
want — arriving home, a long idle period, whatever trigger makes sense — each
just needs its own `reason` string describing what happened.

**LAN only.** `192.168.128.126:8284` assumes HA and this host are on the same
network — this endpoint isn't exposed over the Cloudflare tunnel (matching
the rest of eva-web's `/v1/*` HA routes, which are explicitly LAN-only per
`app.py`'s docstring). If HA and this host are ever on different networks,
this URL needs revisiting.

## Testing without spamming yourself

`/api/checkin/trigger` fires against the **live** Eva agent — there's no way
to redirect a single HTTP call to `eva-spike` short of temporarily editing
`eva-task-runner`'s `EVA_AGENT_ID` env var and restarting the service. Test
sparingly, and expect it to sometimes produce a real reply + push, by design.
