"""Build the report, serve the graveyard UI on localhost, answer bury/restore."""
import json
import os
import time
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from . import job, quarantine
from .platforms import SYSTEM
from .scan import human

HOME_DIR = quarantine.HOME_DIR
REPORT = HOME_DIR / "report.json"
UI_DIR = Path(__file__).parent / "ui"
# The public page on GitHub Pages talks to this helper. Only that origin (and a local copy) may.
SITE = "https://raushanichaudhary77-create.github.io"
ALLOWED_ORIGINS = {SITE, os.environ.get("GRAVEYARD_ORIGIN", SITE), "null"}


def build(entries, meta, apps_count, seconds, raw_count=None):
    for e in entries:
        e["size"] = human(e["bytes"])
        e.setdefault("product", e["name"])
        e.setdefault("vendor", "")
        e.setdefault("category", "")
        e.setdefault("verdict", "")
        e.setdefault("confidence", None)
        e.setdefault("reason", "App is still installed: %s" % e["matched_app"] if e.get("matched_app") else "")
        e.setdefault("epitaph", "")
    buried_ids = {b["id"] for b in quarantine.buried()}
    for e in entries:
        if e["id"] in buried_ids:
            e["status"] = "buried"
    ghosts = [e for e in entries if e["status"] == "ghost"]
    unsure = [e for e in entries if e["status"] == "unsure"]
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M"),
        "platform": {"Darwin": "macOS", "Windows": "Windows", "Linux": "Linux"}.get(SYSTEM, SYSTEM),
        "model": meta.get("model"),
        "fallback": meta.get("fallback", False),
        "skipped": meta.get("skipped", False),
        "scan_seconds": round(seconds, 1),
        "totals": {
            "scanned": raw_count or len(entries),
            "apps_seen": len(entries),
            "installed_apps": apps_count,
            "living": sum(1 for e in entries if e["status"] == "living"),
            "protected": sum(1 for e in entries if e["status"] == "protected"),
            "keep": sum(1 for e in entries if e["status"] == "keep"),
            "ghosts": len(ghosts),
            "unsure": len(unsure),
            "buried": sum(1 for e in entries if e["status"] == "buried"),
            "ghost_bytes": sum(e["bytes"] for e in ghosts),
            "ghost_size": human(sum(e["bytes"] for e in ghosts)),
            "unsure_bytes": sum(e["bytes"] for e in unsure),
            "unsure_size": human(sum(e["bytes"] for e in unsure)),
        },
        "items": sorted(entries, key=lambda e: -e["bytes"]),
    }
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1))
    return report


def load():
    if REPORT.exists():
        return json.loads(REPORT.read_text())
    return None


def _save(report):
    REPORT.write_text(json.dumps(report, indent=1))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(UI_DIR), **kw)

    def log_message(self, *a):
        pass

    def _cors(self):
        origin = self.headers.get("Origin")
        if origin and origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Access-Control-Max-Age", "600")

    def end_headers(self):
        self._cors()
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/report"):
            return self._json(200, load() or {"error": "no report yet"})
        if self.path.startswith("/api/status"):
            return self._json(200, {"report": REPORT.exists(), "ollama": job.ollama_status(), "job": job.snapshot(), "platform": SYSTEM})
        if self.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/scan":
            started = job.start_scan(use_model=bool(body.get("use_model", True)))
            return self._json(200 if started else 409, {"started": started, "job": job.snapshot()})
        if self.path == "/api/pull":
            started = job.start_pull(body.get("model"))
            return self._json(200 if started else 409, {"started": started, "job": job.snapshot()})
        if job.busy():
            return self._json(409, {"error": "a scan is running; wait for it to finish"})
        report = load()
        if not report:
            return self._json(400, {"error": "no report"})
        by_id = {e["id"]: e for e in report["items"]}
        try:
            if self.path == "/api/bury":
                results = []
                for eid in body.get("ids", []):
                    e = by_id.get(eid)
                    if not e:
                        continue
                    dests = quarantine.bury(e)
                    e["status"] = "buried"
                    results.append({"id": eid, "quarantine": dests})
                _save(_recount(report))
                return self._json(200, {"buried": results, "totals": report["totals"]})
            if self.path == "/api/restore":
                e = by_id.get(body.get("id"))
                original = quarantine.restore(body.get("id"))
                if e:
                    e["status"] = "ghost" if e.get("verdict") == "ghost" else "unsure"
                _save(_recount(report))
                return self._json(200, {"restored": original, "totals": report["totals"]})
        except Exception as exc:
            return self._json(500, {"error": "%s: %s" % (type(exc).__name__, exc)})
        return self._json(404, {"error": "unknown endpoint"})


def _recount(report):
    items = report["items"]
    t = report["totals"]
    ghosts = [e for e in items if e["status"] == "ghost"]
    unsure = [e for e in items if e["status"] == "unsure"]
    t["ghosts"], t["unsure"] = len(ghosts), len(unsure)
    t["buried"] = sum(1 for e in items if e["status"] == "buried")
    t["ghost_bytes"] = sum(e["bytes"] for e in ghosts)
    t["ghost_size"] = human(t["ghost_bytes"])
    t["unsure_bytes"] = sum(e["bytes"] for e in unsure)
    t["unsure_size"] = human(t["unsure_bytes"])
    return report


def serve(port=7777, open_browser=True):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = "http://127.0.0.1:%d/" % port
    print("  graveyard open at %s   (Ctrl+C to close)" % url)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  the ghosts rest.")
