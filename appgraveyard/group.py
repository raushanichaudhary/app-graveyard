"""Fold leftovers that belong to the same app into one group, so the model
judges an app once and the graveyard shows one tombstone per app."""
import re

from .platforms import normalize, tokens

TEAM_ID = re.compile(r"^[A-Z0-9]{10}\.")
PREFIXES = ("group.", "systemgroup.", "com.", "org.", "net.", "io.", "dev.", "app.", "us.", "ru.", "de.", "co.")
EXT = re.compile(r"\.(plist|json|db|sqlite|log|ini|xml|lock|savedState|txt|shm|wal|aapbz)$", re.I)


def key_for(name):
    """'com.clipy-app.Clipy.plist' -> 'clipy'; 'Microsoft Edge Beta' -> 'microsoftedgebeta'."""
    n = EXT.sub("", name)
    n = TEAM_ID.sub("", n)
    for p in ("group.", "systemgroup."):
        if n.lower().startswith(p):
            n = n[len(p):]
    if "." in n and " " not in n:
        parts = [p for p in n.split(".") if len(normalize(p)) >= 4]
        if parts:
            return normalize(parts[-1])
    return normalize(n) or name.lower()


def group(entries):
    """Return a list of group dicts. Protected entries stay as singletons."""
    buckets = {}
    order = []
    for e in entries:
        k = ("protected:" + e["id"]) if e["status"] == "protected" else key_for(e["name"])
        if k not in buckets:
            buckets[k] = []
            order.append(k)
        buckets[k].append(e)

    groups = []
    for k in order:
        parts = sorted(buckets[k], key=lambda p: -p["bytes"])
        statuses = {p["status"] for p in parts}
        if "protected" in statuses:
            status = "protected"
        elif "living" in statuses:
            status = "living"
        else:
            status = "orphan"
        matched = next((p["matched_app"] for p in parts if p.get("matched_app")), None)
        display = sorted((p["name"] for p in parts), key=lambda s: (("." in s and " " not in s), len(s)))[0]
        samples = []
        for p in parts:
            for s in p["samples"]:
                if s not in samples and len(samples) < 8:
                    samples.append(s)
        last = max((p["last_modified"] or "") for p in parts) or None
        first = min((p["first_seen"] or "9999") for p in parts)
        groups.append({
            "id": k if status != "protected" else parts[0]["id"],
            "key": k,
            "name": display,
            "roots": sorted({p["root"] for p in parts}),
            "parts": [{"id": p["id"], "root": p["root"], "name": p["name"], "path": p["path"], "bytes": p["bytes"], "files": p["files"]} for p in parts],
            "path": parts[0]["path"],
            "bytes": sum(p["bytes"] for p in parts),
            "files": sum(p["files"] for p in parts),
            "last_modified": last,
            "first_seen": None if first == "9999" else first,
            "days_idle": min((p["days_idle"] for p in parts if p["days_idle"] is not None), default=None),
            "samples": samples,
            "protected": status == "protected",
            "status": status,
            "matched_app": matched,
        })
    return groups
