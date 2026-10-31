"""Bury and restore. Nothing is ever deleted: burying moves a folder into a
quarantine directory with a manifest that lets you put it back."""
import json
import os
import shutil
import time
from pathlib import Path

HOME_DIR = Path(os.environ.get("RESIDUE_HOME", Path.home() / ".residue"))
GRAVEYARD = HOME_DIR / "quarantine"
MANIFEST = GRAVEYARD / "manifest.json"


def _load():
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text())
        except Exception:
            pass
    return {"buried": []}


def _save(data):
    GRAVEYARD.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, indent=2))


def bury(entry):
    """Move every folder of this app (entry['parts']) into the quarantine.
    Returns the list of new locations. Never deletes anything."""
    if entry.get("protected") or entry.get("status") not in ("ghost", "unsure"):
        raise PermissionError("Refusing to bury a %s entry" % entry.get("status"))
    parts = entry.get("parts") or [{"path": entry["path"], "root": "", "name": entry["name"]}]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest_dir = GRAVEYARD / stamp / entry["id"].replace("/", "_").replace(":", "_")
    data = _load()
    moved = []
    for part in parts:
        src = part["path"]
        if not os.path.exists(src):
            continue
        sub = dest_dir / part["root"].replace("\\", "_").replace("/", "_")
        sub.mkdir(parents=True, exist_ok=True)
        dest = sub / os.path.basename(src)
        shutil.move(src, str(dest))
        moved.append(str(dest))
        data["buried"].append({
            "id": entry["id"], "original": src, "quarantine": str(dest),
            "buried_at": stamp, "bytes": part.get("bytes", 0), "product": entry.get("product", entry["name"]),
        })
    _save(data)
    return moved


def restore(entry_id):
    """Put every folder buried under this id back where it came from."""
    data = _load()
    mine = [b for b in data["buried"] if b["id"] == entry_id]
    if not mine:
        raise FileNotFoundError(entry_id)
    restored = []
    for item in mine:
        if not os.path.exists(item["quarantine"]):
            continue
        if os.path.exists(item["original"]):
            raise FileExistsError(item["original"])
        os.makedirs(os.path.dirname(item["original"]), exist_ok=True)
        shutil.move(item["quarantine"], item["original"])
        restored.append(item["original"])
    data["buried"] = [b for b in data["buried"] if b["id"] != entry_id]
    _save(data)
    return restored


def buried():
    return _load()["buried"]
