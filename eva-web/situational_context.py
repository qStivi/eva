"""situational_context — small, live facts about right now (time, weather,
location, what's playing) that eva-web bundles into Eva's context before
every send, so she has this without spending a tool call to go check.

See docs/2026-08-22-situational-context-spec.md. This builds only the
HA-sourced half of that spec (time/date/day, weather, location, Spotify,
Steam) — the conversational-recall half is separate, not yet built.

Reads Home Assistant's own URL/token from ~/.config/letta/ha.env (the same
file scripts/register-ha-mcp.sh uses for the MCP registration) rather than
eva-web's own env file, since eva-web's systemd unit only sources
~/.config/eva-web/eva-web.env, not that one.
"""
import datetime
import json
import os
import urllib.request

HA_ENV_FILE = os.path.expanduser(os.environ.get("HA_ENV_FILE", "~/.config/letta/ha.env"))


def _read_ha_env():
    """Best-effort KEY=VALUE parse of ha.env — stdlib only, no dotenv dep.
    Env vars (if already set) win, so a test run can override without editing
    the file.
    """
    url = os.environ.get("HA_URL", "")
    token = os.environ.get("HA_TOKEN", "")
    try:
        with open(HA_ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k == "HA_URL" and not url:
                    url = v
                elif k == "HA_TOKEN" and not token:
                    token = v
    except OSError:
        pass
    return url.rstrip("/"), token


def _ha_state(base: str, token: str, entity_id: str, timeout: float = 4):
    req = urllib.request.Request(
        f"{base}/api/states/{entity_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _location_line(person: dict) -> str | None:
    """HA's person.state IS the zone — 'home' when in the home zone,
    'not_home' when in no configured zone, or a configured zone's own name
    otherwise (only 'home' is configured right now — see the spec's open
    questions). 'unknown'/'unavailable' means don't guess, say nothing.
    """
    zone = person.get("state", "")
    if zone == "home":
        return "Stephan is: home."
    if zone == "not_home":
        return "Stephan is: out and about."
    if zone in ("", "unknown", "unavailable"):
        return None
    return f"Stephan is: {zone}."  # a named zone, if one ever gets configured


def build() -> str:
    """One short plain-text block of live facts — degrading per-field on any
    individual failure. A dead HA integration or slow network must never
    block the actual chat message from going through.
    """
    lines = [
        "Right now: "
        + datetime.datetime.now().strftime("%A, %B %-d, %Y, %-I:%M %p") + "."
    ]

    base, token = _read_ha_env()
    if not base or not token:
        lines.append("(Home Assistant not reachable from eva-web — no weather/location/media below.)")
        return "\n".join(lines)

    def state(entity_id):
        try:
            return _ha_state(base, token, entity_id)
        except Exception:  # noqa: BLE001 — one dead entity must not blank the whole block
            return None

    w = state("weather.forecast_home")
    if w:
        cond = w.get("state")
        attrs = w.get("attributes", {})
        temp = attrs.get("temperature")
        unit = attrs.get("temperature_unit", "")
        if cond and temp is not None:
            lines.append(f"Weather: {cond}, {temp}{unit}.")

    p = state("person.stephan_glaue")
    if p:
        loc = _location_line(p)
        if loc:
            lines.append(loc)

    sp = state("media_player.spotify")
    if sp:
        st = sp.get("state")
        attrs = sp.get("attributes", {})
        title = attrs.get("media_title")
        artist = attrs.get("media_artist")
        if title and st in ("playing", "paused"):
            who = f" by {artist}" if artist else ""
            verb = "playing" if st == "playing" else "paused on"
            lines.append(f'Spotify: {verb} "{title}"{who}.')

    steam = state("sensor.steam_now_playing")
    if steam and steam.get("state") not in (None, "", "unknown", "unavailable"):
        lines.append(f"Steam: playing {steam['state']}.")

    return "\n".join(lines)


if __name__ == "__main__":
    print(build())
