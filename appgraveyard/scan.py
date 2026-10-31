"""Walk the leftover roots and measure what is there. Read-only."""
import os
import sys
import time
from datetime import datetime

from .platforms import leftover_roots, is_protected


def _measure(path, max_files=200000):
    """(bytes, file_count, newest_mtime, oldest_mtime, sample_children)."""
    size = 0
    files = 0
    newest = 0.0
    oldest = time.time()
    samples = []
    try:
        st = os.lstat(path)
    except OSError:
        return 0, 0, 0.0, 0.0, []
    if not os.path.isdir(path) or os.path.islink(path):
        return st.st_size, 1, st.st_mtime, st.st_mtime, []
    for root, dirs, fnames in os.walk(path, onerror=lambda e: None):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
        if root == path:
            samples = sorted(dirs + fnames)[:6]
        for f in fnames:
            try:
                fst = os.lstat(os.path.join(root, f))
            except OSError:
                continue
            size += fst.st_size
            files += 1
            if fst.st_mtime > newest:
                newest = fst.st_mtime
            if 0 < fst.st_mtime < oldest:
                oldest = fst.st_mtime
            if files >= max_files:
                return size, files, newest, oldest, samples
    if files == 0:
        newest = oldest = st.st_mtime
    return size, files, newest, oldest, samples


def scan(progress=True):
    """Return a list of entry dicts, one per direct child of each leftover root."""
    entries = []
    roots = [(label, p) for label, p in leftover_roots() if p.is_dir()]
    total = sum(len(os.listdir(p)) for _, p in roots)
    done = 0
    for label, root in roots:
        for name in sorted(os.listdir(root)):
            done += 1
            if progress:
                sys.stderr.write("\r  scanning %d/%d  %-40s" % (done, total, name[:40]))
                sys.stderr.flush()
            path = os.path.join(root, name)
            size, files, newest, oldest, samples = _measure(path)
            entries.append({
                "id": "%s:%s" % (label, name),
                "name": name,
                "root": label,
                "path": path,
                "is_dir": os.path.isdir(path),
                "bytes": size,
                "files": files,
                "last_modified": datetime.fromtimestamp(newest).strftime("%Y-%m-%d") if newest else None,
                "first_seen": datetime.fromtimestamp(oldest).strftime("%Y-%m-%d") if oldest else None,
                "days_idle": int((time.time() - newest) / 86400) if newest else None,
                "samples": samples,
                "protected": is_protected(name),
            })
    if progress:
        sys.stderr.write("\r" + " " * 70 + "\r")
    return entries


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return ("%.0f %s" if unit == "B" else "%.1f %s") % (n, unit)
        n /= 1024.0
    return "%d B" % n
