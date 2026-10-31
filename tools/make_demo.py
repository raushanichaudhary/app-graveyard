#!/usr/bin/env python3
"""Build docs/demo.html: the graveyard UI with a scrubbed copy of a real report
embedded, so GitHub Pages can show a replay without a backend.

    python tools/make_demo.py [~/.app-graveyard/report.json]

Paths are rewritten to a generic home directory and the user name is removed.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".app-graveyard" / "report.json"
report = json.loads(src.read_text())

home = str(Path.home())
user = os.path.basename(home)
fake_home = {"macOS": "/Users/you", "Windows": "C:\\Users\\you", "Linux": "/home/you"}.get(report["platform"], "/home/you")


def scrub(s):
    if not isinstance(s, str):
        return s
    return s.replace(home, fake_home).replace(user, "you")


def deep(o):
    if isinstance(o, dict):
        return {k: deep(v) for k, v in o.items()}
    if isinstance(o, list):
        return [deep(v) for v in o]
    return scrub(o)


report = deep(report)
# Only the story goes public: ghosts, unsure, and the keeps the model judged.
# Living and protected items are an inventory of the machine; keep the counts, drop the rows.
report["items"] = [e for e in report["items"] if e["status"] in ("ghost", "unsure", "buried") or (e["status"] == "keep" and "rule" not in (e.get("reason") or ""))]
report["trimmed"] = True
report["quarantine"] = scrub(str(Path.home() / ".app-graveyard" / "quarantine"))

html = (ROOT / "appgraveyard" / "ui" / "index.html").read_text()
payload = "<script>window.GRAVEYARD_DEMO = " + json.dumps(report).replace("</", "<\\/") + ";</script>\n</head>"
html = html.replace("</head>", payload, 1)
html = html.replace("<title>App Graveyard</title>", "<title>App Graveyard (demo replay)</title>")
out = ROOT / "docs" / "demo.html"
out.parent.mkdir(exist_ok=True)
out.write_text(html)
print("wrote", out, "with", len(report["items"]), "items")
