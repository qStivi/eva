def delegate_to_harness(task: str, workdir: str = None, model: str = None) -> str:
    """Propose a real task for DeepSeek Harness to carry out on the host — real
    file edits, real commands, running on a Mistral model. This NEVER runs
    anything on its own: it only submits the proposal, which sits waiting for
    Stephan to approve it on his phone. Nothing happens until he says yes —
    treat this the same as asking him, not as doing something yourself. Tell
    him what you're proposing and that you sent the approval request; don't
    imply the task ran until its result actually gets reported back to you
    later in this conversation. Use check_task(job_id) if he asks about
    progress before then.

    Args:
        task: the task itself, written as a clear instruction — what to do,
            not just a topic (e.g. "fix the typo in README.md's install
            section", not "the README").
        workdir: optional — leave this unset almost always; it already
            defaults to a real, working scratch directory on its own. Never
            guess a path here (like something under a guessed home
            directory) — you don't actually know Stephan's system username
            or exact directory layout, and a guessed path fails outright
            rather than silently going somewhere else. Only pass this as an
            explicit subdirectory *name* if the task genuinely needs its own
            separate space (e.g. "myproject", not a full path) — it can only
            ever be the default scratch directory or somewhere inside it,
            never anywhere else on the system.
        model: optional — "codestral-2508" for a task that's purely
            code-completion-shaped; otherwise leave unset for the default
            general-purpose model.
    """
    import json
    import os
    import urllib.request

    base = (os.environ.get("EVA_RUNNER_URL") or "http://localhost:8286").rstrip("/")
    spec = {"task": task}
    if workdir:
        spec["workdir"] = workdir
    if model:
        spec["model"] = model
    body = json.dumps({"kind": "harness", "spec": spec}).encode()
    req = urllib.request.Request(base + "/jobs", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001 — surface as a normal reply, not a crash
        return "(couldn't submit that task: %s)" % e
    return json.dumps(data)
