"""The ghost whisperer: asks a local open-weight model what each orphan was.

Talks only to an Ollama server on localhost. Standard library only.
If the model is unreachable, falls back to a plain heuristic so the scan
still completes, and says so in the report.
"""
import json
import os
import sys
import urllib.request

from .platforms import SYSTEM
from .progress import clear, tick
from .scan import human

HOST = os.environ.get("GRAVEYARD_HOST", "http://127.0.0.1:11434")
MODEL = os.environ.get("GRAVEYARD_MODEL", "gemma3:4b")
TIMEOUT = float(os.environ.get("GRAVEYARD_TIMEOUT", "180"))
BATCH = 4

OS_NAME = {"Darwin": "macOS", "Windows": "Windows", "Linux": "Linux"}.get(SYSTEM, SYSTEM)

SYSTEM_PROMPT = """You are a meticulous %s support engineer who identifies leftover application data.
You will receive folders found in the user's application-data directories. The app that created each
folder is NOT in the list of installed applications, so it was probably uninstalled, or it belongs to a
background tool, a developer SDK, a system component, or a browser extension that is still in use.

For each folder decide:
- product: the real product name that created it (e.g. "Zoom", "Spotify", "Visual Studio Code", "Node.js npm cache"). If unknown, say "Unknown".
- vendor: company or project behind it, or "Unknown".
- category: one of: app, dev-tool, system, browser, game, driver, launcher, cache, unknown.
- verdict:
    "ghost"  = leftover of an app that is gone; safe to move to quarantine.
    "keep"   = still in use by something that is not an app bundle (shells, package managers, SDKs, cloud sync, system components, licenses, keys, credentials).
    "unsure" = you cannot tell.
- confidence: 0.0 to 1.0.
- reason: under 20 words, factual.
- epitaph: one short darkly funny tombstone line for the dead app, under 14 words, no emoji, no quotes. For "keep" or "unsure" items write a one-line note instead.

Rules of thumb:
- A normal desktop app (browser, terminal emulator, clipboard manager, chat or video app, editor, game) whose app is not installed is a "ghost", even if its folder holds a database or preferences: the app that could read them is gone.
- Judge a folder by ITS OWN product. "Microsoft Edge" is a ghost if Edge is gone, even if other Microsoft apps are installed.
- Shared vendor services (updaters, auth brokers, licence and preference stores such as an Office group container) are "keep" when "other_installed_apps_from_same_vendor" lists apps that still use them.
- Package-manager and build caches are "keep": they belong to tools on the PATH, not to app bundles.
Be conservative: anything that could hold credentials, licenses, SSH keys, package caches that are cheap to lose but used by developer tools, or data for a tool run from the terminal should be "keep" or "unsure", not "ghost".
Respond with JSON only: {"items":[{"name":..., "product":..., "vendor":..., "category":..., "verdict":..., "confidence":..., "reason":..., "epitaph":...}]}
Return exactly one item per input, in the same order, with the same "name".""" % OS_NAME


def _post(payload):
    req = urllib.request.Request(
        HOST + "/api/chat", json.dumps(payload).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def available():
    try:
        with urllib.request.urlopen(HOST + "/api/tags", timeout=3) as r:
            names = [m["name"] for m in json.load(r).get("models", [])]
        return any(n == MODEL or n.split(":")[0] == MODEL.split(":")[0] for n in names), names
    except Exception:
        return False, []


def _describe(e):
    return {
        "name": e["name"],
        "folders": ["%s/%s (%s)" % (p["root"], p["name"], human(p["bytes"])) for p in e.get("parts", [])][:8],
        "total_size": human(e["bytes"]),
        "files": e["files"],
        "last_modified": e["last_modified"],
        "days_idle": e["days_idle"],
        "contains": e["samples"],
        "product_installed": "No installed application matched this name.",
        "other_installed_apps_from_same_vendor": e.get("vendor_installed") or "none",
    }


def _heuristic(e):
    idle = e.get("days_idle") or 0
    if idle > 90:
        verdict, conf = "ghost", 0.4
    else:
        verdict, conf = "unsure", 0.3
    return {
        "product": e["name"], "vendor": "Unknown", "category": "unknown", "verdict": verdict,
        "confidence": conf, "reason": "No model available; judged by idle time only.",
        "epitaph": "Untouched for %d days. Nobody came back for it." % idle,
    }


def consult(entries, progress=True):
    """Fill in product/vendor/verdict/epitaph for every entry with status 'orphan'."""
    orphans = [e for e in entries if e["status"] == "orphan"]
    ok, models = available()
    meta = {"model": MODEL if ok else None, "fallback": not ok, "models_seen": models}
    if not ok:
        for e in orphans:
            e.update(_heuristic(e))
            e["status"] = "ghost" if e["verdict"] == "ghost" else "unsure"
        return meta

    for i in range(0, len(orphans), BATCH):
        batch = orphans[i:i + BATCH]
        tick(progress, "consulting " + MODEL, i, len(orphans), ", ".join(e["name"] for e in batch))
        payload = {
            "model": MODEL,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_ctx": 8192, "num_predict": 2000},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"folders": [_describe(e) for e in batch]}, indent=1)},
            ],
        }
        items = []
        try:
            content = _post(payload)["message"]["content"]
            items = json.loads(content).get("items", [])
        except Exception:
            items = []
        by_name = {str(it.get("name")): it for it in items if isinstance(it, dict)}
        for j, e in enumerate(batch):
            it = by_name.get(e["name"])
            if not it and len(items) == len(batch) and isinstance(items[j], dict) and items[j].get("name") not in by_name:
                it = items[j]
            if not it:
                e["_retry"] = True
                continue
            _apply(e, it)
    # second pass: anything the model skipped or mislabeled gets asked about on its own
    for e in [o for o in orphans if o.get("_retry")]:
        tick(progress, "asking again", len(orphans), len(orphans), e["name"])
        payload["messages"][1] = {"role": "user", "content": json.dumps({"folders": [_describe(e)]}, indent=1)}
        it = None
        try:
            content = _post(payload)["message"]["content"]
            got = json.loads(content).get("items", [])
            it = got[0] if got and isinstance(got[0], dict) else None
        except Exception:
            it = None
        del e["_retry"]
        if not it:
            e.update(_heuristic(e))
            e["reason"] = "Model gave no answer; judged by idle time only."
            e["status"] = "unsure"
            continue
        _apply(e, it)
    tick(progress, "consulting " + MODEL, len(orphans), len(orphans), "")
    clear(progress)
    return meta


def _apply(e, it):
    verdict = str(it.get("verdict", "unsure")).lower()
    if verdict not in ("ghost", "keep", "unsure"):
        verdict = "unsure"
    try:
        conf = max(0.0, min(1.0, float(it.get("confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5
    e.update({
        "product": str(it.get("product") or e["name"]),
        "vendor": str(it.get("vendor") or "Unknown"),
        "category": str(it.get("category") or "unknown"),
        "verdict": verdict,
        "confidence": conf,
        "reason": str(it.get("reason") or ""),
        "epitaph": str(it.get("epitaph") or ""),
    })
    if verdict == "ghost" and conf >= 0.6:
        e["status"] = "ghost"
    elif verdict == "keep" and conf >= 0.6:
        e["status"] = "keep"
    else:
        e["status"] = "unsure"
