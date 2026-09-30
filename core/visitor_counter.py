from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from filelock import FileLock


@dataclass
class CounterResult:
    count: int
    backend: str
    persistent: bool
    detail: str = ""


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _local_counter_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "visitor_count.json"


def read_local_counter() -> int:
    path = _local_counter_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _safe_int(payload.get("count"), 0)
    except Exception:
        return 0


def increment_local_counter() -> CounterResult:
    path = _local_counter_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(path) + ".lock", timeout=8)
    with lock:
        current = read_local_counter()
        updated = current + 1
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"count": updated}, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    return CounterResult(
        count=updated,
        backend="local-file",
        persistent=False,
        detail="Local file persists during normal app runtime but may reset if Streamlit Cloud rebuilds the container.",
    )


def _counter_settings(secrets: dict[str, Any] | None) -> dict[str, str]:
    secrets = secrets or {}
    section = secrets.get("visitor_counter", {}) if isinstance(secrets.get("visitor_counter", {}), dict) else {}
    token = str(section.get("github_token") or secrets.get("GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()
    repo = str(section.get("github_repo") or secrets.get("GITHUB_REPO") or os.getenv("GITHUB_REPO") or "").strip()
    path = str(section.get("counter_path") or "data/visitor_count.json").strip()
    branch = str(section.get("branch") or "main").strip()
    return {"token": token, "repo": repo, "path": path, "branch": branch}


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "energy-resource-shock-simulator-visitor-counter",
    }


def increment_github_counter(settings: dict[str, str], retries: int = 4) -> CounterResult:
    token, repo, path, branch = settings["token"], settings["repo"], settings["path"], settings["branch"]
    if not token or not repo or "/" not in repo:
        raise ValueError("GitHub counter is not configured")

    endpoint = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = _github_headers(token)

    for attempt in range(retries):
        response = requests.get(endpoint, headers=headers, params={"ref": branch}, timeout=12)
        sha: str | None = None
        if response.status_code == 404:
            current = 0
        else:
            response.raise_for_status()
            body = response.json()
            sha = str(body.get("sha") or "") or None
            raw = base64.b64decode(str(body.get("content") or "").encode("ascii")).decode("utf-8")
            current = _safe_int(json.loads(raw).get("count"), 0)

        updated = current + 1
        encoded = base64.b64encode((json.dumps({"count": updated}, indent=2) + "\n").encode("utf-8")).decode("ascii")
        payload: dict[str, Any] = {
            "message": f"chore: visitor count {updated}",
            "content": encoded,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        put = requests.put(endpoint, headers=headers, json=payload, timeout=12)
        if put.status_code in {200, 201}:
            return CounterResult(
                count=updated,
                backend="github-file",
                persistent=True,
                detail=f"Persisted in {repo}/{path} without a database.",
            )
        if put.status_code in {409, 422} and attempt < retries - 1:
            time.sleep(0.25 * (attempt + 1))
            continue
        put.raise_for_status()

    raise RuntimeError("Unable to update GitHub visitor counter after retries")


def count_visit_once(session_state: Any, secrets: dict[str, Any] | None = None) -> CounterResult:
    """Increment once per Streamlit browser session, not once per widget rerun.

    A browser refresh/new tab may start a new Streamlit session and therefore count as a new visit.
    This is intentionally a visit counter rather than identity tracking.
    """
    if session_state.get("visitor_counted"):
        return CounterResult(
            count=_safe_int(session_state.get("visitor_count"), 1),
            backend=str(session_state.get("visitor_counter_backend", "session")),
            persistent=bool(session_state.get("visitor_counter_persistent", False)),
            detail=str(session_state.get("visitor_counter_detail", "")),
        )

    settings = _counter_settings(secrets)
    result: CounterResult
    if settings["token"] and settings["repo"]:
        try:
            result = increment_github_counter(settings)
        except Exception as exc:
            result = increment_local_counter()
            result.detail += f" GitHub persistence failed for this visit: {type(exc).__name__}."
    else:
        result = increment_local_counter()

    session_state["visitor_counted"] = True
    session_state["visitor_count"] = max(1, result.count)
    session_state["visitor_counter_backend"] = result.backend
    session_state["visitor_counter_persistent"] = result.persistent
    session_state["visitor_counter_detail"] = result.detail
    return CounterResult(max(1, result.count), result.backend, result.persistent, result.detail)
