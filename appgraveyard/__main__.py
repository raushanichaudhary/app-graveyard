"""app-graveyard: the apps you uninstalled left ghosts behind.

  python -m appgraveyard            scan, consult the local model, open the graveyard
  python -m appgraveyard scan       scan only, write ~/.app-graveyard/report.json, print summary
  python -m appgraveyard open       open the graveyard page; scan from the page (what the launchers do)
  python -m appgraveyard serve      open the graveyard from the last report
  python -m appgraveyard restore ID put a buried folder back where it was
"""
import argparse
import sys
import time

from . import group, match, oracle, platforms, quarantine, report, scan
from .progress import tick


def run_scan(no_model=False, progress=True):
    """progress: True prints to the terminal, a callable gets (stage, done, total, detail)."""
    quiet = callable(progress)
    say = (lambda *a: None) if quiet else print
    t0 = time.time()
    say("  summoning installed apps...")
    tick(progress, "summoning installed apps", 0, 0, "")
    apps = platforms.installed_apps()
    say("  %d installed apps found" % len(apps))
    entries = scan.scan(progress=progress)
    tick(progress, "matching", 0, 0, "%d installed apps" % len(apps))
    match.match(entries, apps)
    raw = len(entries)
    entries = group.group(entries)
    orphans = sum(1 for e in entries if e["status"] == "orphan")
    say("  %d leftovers scanned, folded into %d apps, %d belong to nothing installed" % (raw, len(entries), orphans))
    if no_model:
        meta = {"model": None, "fallback": True, "skipped": True}
        for e in entries:
            if e["status"] == "orphan":
                e.update(oracle._heuristic(e))
                e["status"] = "ghost" if e["verdict"] == "ghost" else "unsure"
    else:
        ok, _ = oracle.available()
        if not ok:
            say("  Ollama or model %s not reachable at %s; judging by idle time only." % (oracle.MODEL, oracle.HOST))
        meta = oracle.consult(entries, progress=progress)
    tick(progress, "writing report", 0, 0, "")
    rep = report.build(entries, meta, len(apps), time.time() - t0, raw)
    t = rep["totals"]
    say("  %d ghosts haunting %s, %d unsure (%s), %d still living, %d protected"
          % (t["ghosts"], t["ghost_size"], t["unsure"], t["unsure_size"], t["living"], t["protected"]))
    say("  report: %s" % report.REPORT)
    return rep


def main(argv=None):
    p = argparse.ArgumentParser(prog="appgraveyard", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", nargs="?", default="haunt", choices=["haunt", "scan", "open", "serve", "restore", "buried"])
    p.add_argument("id", nargs="?", help="entry id for restore")
    p.add_argument("--no-model", action="store_true", help="skip the local model, use idle-time heuristic only")
    p.add_argument("--port", type=int, default=7777)
    p.add_argument("--no-browser", action="store_true")
    a = p.parse_args(argv)

    if a.command in ("haunt", "scan"):
        run_scan(no_model=a.no_model)
        if a.command == "haunt":
            report.serve(a.port, open_browser=not a.no_browser)
    elif a.command == "open":
        report.serve(a.port, open_browser=not a.no_browser)
    elif a.command == "serve":
        if not report.load():
            sys.exit("  no report yet; run: python -m appgraveyard scan   (or: python -m appgraveyard open, and scan from the page)")
        report.serve(a.port, open_browser=not a.no_browser)
    elif a.command == "restore":
        if not a.id:
            sys.exit("  usage: python -m appgraveyard restore <id>")
        print("  restored to %s" % quarantine.restore(a.id))
    elif a.command == "buried":
        for b in quarantine.buried():
            print("  %s  %s  <- %s" % (b["buried_at"], b["product"], b["original"]))


if __name__ == "__main__":
    main()
