#!/usr/bin/env python3
"""Build docs/index.html: the graveyard UI with a scrubbed copy of a real report
embedded, so GitHub Pages can show a replay without a backend.

    python tools/make_demo.py [~/.residue/report.json]

Paths are rewritten to a generic home directory and the user name is removed.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".residue" / "report.json"
report = json.loads(src.read_text())

home = str(Path.home())
user = os.path.basename(home)
fake_home = {"macOS": "/Users/you", "Windows": "C:\\Users\\you", "Linux": "/home/you"}.get(report["platform"], "/home/you")


def scrub(s):
    if not isinstance(s, str):
        return s
    return s.replace(home, fake_home).replace(user, "you")


for e in report["items"]:
    for k in ("path", "reason", "epitaph", "name", "product"):
        e[k] = scrub(e.get(k))
    e["samples"] = [scrub(x) for x in e.get("samples", [])]
    e["id"] = scrub(e["id"])
report["quarantine"] = scrub(str(Path.home() / ".residue" / "quarantine"))

html = (ROOT / "residue" / "ui" / "index.html").read_text()
payload = "<script>window.RESIDUE_DEMO = " + json.dumps(report).replace("</", "<\\/") + ";</script>\n</head>"
html = html.replace("</head>", payload, 1)
html = html.replace("<title>Residue</title>", "<title>Residue (demo replay)</title>")
out = ROOT / "docs" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(html)
print("wrote", out, "with", len(report["items"]), "items")
