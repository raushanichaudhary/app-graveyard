"""Decide, without any AI, which leftovers belong to an app that is still installed."""
import re
from collections import Counter

from .platforms import tokens, normalize, GENERIC

UUID_RE = re.compile(r"^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$", re.I)


def match(entries, apps):
    """Annotate each entry with status 'living' (app found) or 'orphan' (not found).

    A token shared by three or more installed apps (microsoft, google, zoom...) is a
    vendor word, not a product, and on its own never proves an app is installed.
    """
    token_apps = {}
    for app in apps:
        for t in app["tokens"]:
            token_apps.setdefault(t, set()).add(app["name"])
    vendor_words = {t for t, names in token_apps.items() if len(names) >= 3}
    token_index = {t: sorted(names)[0] for t, names in token_apps.items() if t not in vendor_words}

    norm_index = {}
    for app in apps:
        for n in app["norms"]:
            norm_index.setdefault(n, app["name"])
    norm_keys = sorted((k for k in norm_index if len(k) >= 7 and k not in GENERIC), key=len, reverse=True)

    for e in entries:
        if UUID_RE.match(e["name"]):
            e["protected"] = True
        if e["protected"]:
            e["status"] = "protected"
            e["matched_app"] = None
            continue
        hit = None
        for t in tokens(e["name"]):
            if t in token_index:
                hit = token_index[t]
                break
        if not hit:
            n = normalize(e["name"])
            if len(n) >= 7:
                for k in norm_keys:
                    if k in n or n in k:
                        hit = norm_index[k]
                        break
        e["matched_app"] = hit
        e["status"] = "living" if hit else "orphan"
    return entries
