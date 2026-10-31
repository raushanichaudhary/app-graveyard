"""One tiny progress channel shared by the CLI (stderr) and the UI (background job)."""
import sys


def tick(progress, stage, done, total, detail=""):
    """progress may be False (quiet), True (print to stderr) or a callable."""
    if callable(progress):
        progress(stage, done, total, detail)
    elif progress:
        sys.stderr.write("\r  %s %d/%d  %-40s" % (stage, done, total, detail[:40]))
        sys.stderr.flush()


def clear(progress):
    if progress is True:
        sys.stderr.write("\r" + " " * 78 + "\r")
        sys.stderr.flush()
