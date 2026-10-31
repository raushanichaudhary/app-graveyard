"""residue: the apps you uninstalled left ghosts behind.

  python -m residue            scan, consult the local model, open the graveyard
  python -m residue scan       scan only, write ~/.residue/report.json, print summary
  python -m residue serve      open the graveyard from the last report
  python -m residue restore ID put a buried folder back where it was
"""
import argparse
import sys
import time

from . import group, match, oracle, platforms, quarantine, report, scan


def run_scan(no_model=False):
    t0 = time.time()
    print("  summoning installed apps...")
    apps = platforms.installed_apps()
    print("  %d installed apps found" % len(apps))
    entries = scan.scan()
    match.match(entries, apps)
    raw = len(entries)
    entries = group.group(entries)
    orphans = sum(1 for e in entries if e["status"] == "orphan")
    print("  %d leftovers scanned, folded into %d apps, %d belong to nothing installed" % (raw, len(entries), orphans))
    if no_model:
        meta = {"model": None, "fallback": True}
        for e in entries:
            if e["status"] == "orphan":
                e.update(oracle._heuristic(e))
                e["status"] = "ghost" if e["verdict"] == "ghost" else "unsure"
    else:
        ok, _ = oracle.available()
        if not ok:
            print("  Ollama or model %s not reachable at %s; judging by idle time only." % (oracle.MODEL, oracle.HOST))
        meta = oracle.consult(entries)
    rep = report.build(entries, meta, len(apps), time.time() - t0, raw)
    t = rep["totals"]
    print("  %d ghosts haunting %s, %d unsure (%s), %d still living, %d protected"
          % (t["ghosts"], t["ghost_size"], t["unsure"], t["unsure_size"], t["living"], t["protected"]))
    print("  report: %s" % report.REPORT)
    return rep


def main(argv=None):
    p = argparse.ArgumentParser(prog="residue", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", nargs="?", default="haunt", choices=["haunt", "scan", "serve", "restore", "buried"])
    p.add_argument("id", nargs="?", help="entry id for restore")
    p.add_argument("--no-model", action="store_true", help="skip the local model, use idle-time heuristic only")
    p.add_argument("--port", type=int, default=7777)
    p.add_argument("--no-browser", action="store_true")
    a = p.parse_args(argv)

    if a.command in ("haunt", "scan"):
        run_scan(no_model=a.no_model)
        if a.command == "haunt":
            report.serve(a.port, open_browser=not a.no_browser)
    elif a.command == "serve":
        if not report.load():
            sys.exit("  no report yet; run: python -m residue scan")
        report.serve(a.port, open_browser=not a.no_browser)
    elif a.command == "restore":
        if not a.id:
            sys.exit("  usage: python -m residue restore <id>")
        print("  restored to %s" % quarantine.restore(a.id))
    elif a.command == "buried":
        for b in quarantine.buried():
            print("  %s  %s  <- %s" % (b["buried_at"], b["product"], b["original"]))


if __name__ == "__main__":
    main()
