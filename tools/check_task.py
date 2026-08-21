def check_task(job_id: str) -> str:
    """Check the current state of a background job you started earlier (e.g. with
    research_task). Use this only if you're asked about progress before the
    finished job's own write-up shows up in the conversation on its own.

    Args:
        job_id: the job id returned when the job was started.
    """
    import json
    import os
    import urllib.error
    import urllib.request

    base = (os.environ.get("EVA_RUNNER_URL") or "http://localhost:8286").rstrip("/")
    try:
        with urllib.request.urlopen(base + "/jobs/" + job_id, timeout=10) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "(no job with that id)"
        return "(couldn't check the job: %s)" % e
    except Exception as e:  # noqa: BLE001
        return "(couldn't check the job: %s)" % e
    return json.dumps(data)
