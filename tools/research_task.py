def research_task(topic: str) -> str:
    """Kick off a background research pass: loops several web searches, reads
    the results, and writes up a summary with sources. Returns immediately with
    a job id — never blocks. You'll get the write-up injected into this
    conversation on its own once it's done; use check_task(job_id) if you're
    asked about progress before then.

    Args:
        topic: what to research, as a clear question or subject.
    """
    import json
    import os
    import urllib.request

    base = (os.environ.get("EVA_RUNNER_URL") or "http://localhost:8286").rstrip("/")
    body = json.dumps({"kind": "research", "spec": {"topic": topic}}).encode()
    req = urllib.request.Request(base + "/jobs", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001 — surface as a normal reply, not a crash
        return "(couldn't start the research job: %s)" % e
    return json.dumps(data)
