"""Background jobs started from the graveyard page: a scan, or a model download.
State lives in memory; the page polls /api/status."""
import json
import threading
import time
import urllib.request

from . import oracle

_lock = threading.Lock()
state = {"kind": None, "status": "idle", "stage": "", "done": 0, "total": 0, "detail": "", "error": None, "started": None, "finished": None}


def snapshot():
    with _lock:
        return dict(state)


def _set(**kw):
    with _lock:
        state.update(kw)


def busy():
    return state["status"] == "running"


def _progress(stage, done, total, detail=""):
    _set(stage=stage, done=done, total=total, detail=detail)


def start_scan(use_model=True):
    """Run the whole pipeline in a thread. Returns False if a job is already running."""
    from .__main__ import run_scan
    with _lock:
        if state["status"] == "running":
            return False
        state["status"] = "running"
    _set(kind="scan", status="running", stage="starting", done=0, total=0, detail="", error=None, started=time.time(), finished=None)

    def work():
        try:
            run_scan(no_model=not use_model, progress=_progress)
            _set(status="done", stage="done", finished=time.time())
        except Exception as exc:
            _set(status="error", error="%s: %s" % (type(exc).__name__, exc), finished=time.time())

    threading.Thread(target=work, daemon=True).start()
    return True


def start_pull(model=None):
    """Ask Ollama to download the model (needs internet once). Streams progress."""
    model = model or oracle.MODEL
    with _lock:
        if state["status"] == "running":
            return False
        state["status"] = "running"
    _set(kind="pull", status="running", stage="downloading %s" % model, done=0, total=0, detail="", error=None, started=time.time(), finished=None)

    def work():
        try:
            req = urllib.request.Request(oracle.HOST + "/api/pull", json.dumps({"name": model, "stream": True}).encode(), {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                for line in r:
                    try:
                        m = json.loads(line)
                    except ValueError:
                        continue
                    if m.get("error"):
                        raise RuntimeError(m["error"])
                    _set(detail=m.get("status", ""), done=m.get("completed", 0) or 0, total=m.get("total", 0) or 0)
            ok, _ = oracle.available()
            if not ok:
                raise RuntimeError("download finished but the model is still not listed by Ollama")
            _set(status="done", stage="done", finished=time.time())
        except Exception as exc:
            _set(status="error", error="%s: %s" % (type(exc).__name__, exc), finished=time.time())

    threading.Thread(target=work, daemon=True).start()
    return True


def ollama_status():
    """What the page needs to decide which button to show."""
    try:
        with urllib.request.urlopen(oracle.HOST + "/api/tags", timeout=2) as r:
            names = [m["name"] for m in json.load(r).get("models", [])]
        running = True
    except Exception:
        names, running = [], False
    want = oracle.MODEL
    present = any(n == want or n.split(":")[0] == want.split(":")[0] for n in names)
    return {"running": running, "host": oracle.HOST, "model": want, "model_present": present, "models": names}
