"""Decide, without any AI, which leftovers belong to an app that is still installed."""
import re
from collections import Counter

from .platforms import tokens, normalize, GENERIC, is_dev_cache

TEAM = re.compile(r"^([A-Z0-9]{10})\.")

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
    norm_keys = sorted((k for k in norm_index if len(k) >= 5 and k not in GENERIC), key=len, reverse=True)

    # Apple team-id prefixes seen on folders of installed apps: UBF8T346G9 -> Microsoft Teams, ...
    team_apps = {}
    for e in entries:
        m = TEAM.match(e["name"])
        if m:
            for t in tokens(e["name"]):
                if t in token_index:
                    team_apps.setdefault(m.group(1), set()).add(token_index[t])
                    break

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
            if len(n) >= 5:
                for k in norm_keys:
                    # an app's name at the start of the folder name (zoomus -> zoomusinstall),
                    # or anywhere inside it when the app name is long enough to be unambiguous
                    if n.startswith(k) or (len(k) >= 7 and (k in n or n in k)):
                        hit = norm_index[k]
                        break
        e["matched_app"] = hit
        e["status"] = "living" if hit else "orphan"
        if hit:
            continue
        if is_dev_cache(e["name"]):
            e["status"] = "keep"
            e["product"] = e["name"]
            e["vendor"] = ""
            e["category"] = "dev-tool"
            e["verdict"] = "keep"
            e["confidence"] = 1.0
            e["reason"] = "Cache or state of a command-line developer tool. Kept by rule, no model involved."
            e["epitaph"] = "Not dead, only sleeping between builds."
            continue
        kin = set()
        for t in tokens(e["name"]):
            if t in vendor_words:
                kin |= token_apps[t]
        m = TEAM.match(e["name"])
        if m and m.group(1) in team_apps:
            # a container signed by the same developer team as an installed app: shared vendor data
            owners = sorted(team_apps[m.group(1)])
            e["status"] = "keep"
            e["product"] = e["name"].split(".", 1)[1] if "." in e["name"] else e["name"]
            e["vendor"] = ""
            e["category"] = "shared"
            e["verdict"] = "keep"
            e["confidence"] = 1.0
            e["reason"] = "Shared container of a developer team that still has apps installed: %s. Kept by rule." % ", ".join(owners[:3])
            e["epitaph"] = "Not a ghost. It still has family here."
            continue
        e["vendor_installed"] = sorted(kin)[:8]
    return entries
