"""Where leftovers live, and what is actually installed, per operating system.

Everything here is read-only. Nothing is ever deleted by this module.
"""
import glob
import os
import platform
import plistlib
import re
import subprocess
from pathlib import Path

SYSTEM = platform.system()  # "Darwin", "Windows", "Linux"
HOME = Path.home()

# Words that match too many things to be useful when matching folders to apps.
GENERIC = {
    "app", "apps", "application", "applications", "support", "cache", "caches",
    "data", "helper", "com", "org", "net", "io", "inc", "ltd", "llc", "co",
    "mac", "macos", "osx", "win", "windows", "linux", "the", "and", "for",
    "software", "systems", "studio", "labs", "lab", "team", "tools", "tool",
    "pro", "lite", "free", "plus", "web", "desktop", "client", "launcher",
    "update", "updater", "service", "services", "local", "roaming", "user",
    "users", "default", "temp", "tmp", "logs", "log", "preferences", "plist",
    "json", "db", "sqlite", "bin", "lib", "share", "config", "state",
    "phone", "family", "assistant", "agent", "store", "shared", "group",
    "groups", "helper", "extension", "ext", "plugin", "daemon", "nodejs",
}


def normalize(text):
    """lowercase, alphanumerics only: 'Visual Studio Code' -> 'visualstudiocode'."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def tokens(text):
    """Meaningful name pieces: 'com.microsoft.VSCode' -> {'microsoft', 'vscode'}."""
    out = set()
    text = text.strip()
    # strip common file extensions
    text = re.sub(r"\.(plist|json|db|sqlite|log|ini|xml|lock|savedState|txt)$", "", text, flags=re.I)
    parts = re.split(r"[.\s_\-/\\+()\[\],]+", text)
    for p in parts:
        n = normalize(p)
        if len(n) >= 3 and n not in GENERIC and not n.isdigit():
            out.add(n)
    whole = normalize(text)
    if len(whole) >= 4:
        out.add(whole)
    return out


# --------------------------------------------------------------------------
# Leftover roots: the folders where apps keep data that uninstalling leaves behind
# --------------------------------------------------------------------------

def leftover_roots():
    """[(label, Path)] of folders whose direct children are per-app leftovers."""
    if SYSTEM == "Darwin":
        lib = HOME / "Library"
        return [
            ("Application Support", lib / "Application Support"),
            ("Caches", lib / "Caches"),
            ("Preferences", lib / "Preferences"),
            ("Logs", lib / "Logs"),
            ("Containers", lib / "Containers"),
            ("Group Containers", lib / "Group Containers"),
            ("Saved Application State", lib / "Saved Application State"),
            ("HTTPStorages", lib / "HTTPStorages"),
            ("WebKit", lib / "WebKit"),
        ]
    if SYSTEM == "Windows":
        appdata = Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming"))
        local = Path(os.environ.get("LOCALAPPDATA", HOME / "AppData" / "Local"))
        return [
            ("AppData\\Roaming", appdata),
            ("AppData\\Local", local),
            ("AppData\\LocalLow", local.parent / "LocalLow"),
            ("ProgramData", Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))),
        ]
    # Linux and everything else
    return [
        ("~/.config", HOME / ".config"),
        ("~/.cache", HOME / ".cache"),
        ("~/.local/share", HOME / ".local" / "share"),
        ("~/.local/state", HOME / ".local" / "state"),
    ]


# --------------------------------------------------------------------------
# Protected: belongs to the OS or to this tool. Never a ghost, never buried.
# --------------------------------------------------------------------------

PROTECTED_PREFIXES = {
    "Darwin": ("com.apple", "apple", "icloud", "cloud", "mobile", "addressbook",
               "callhistory", "crashreporter", "fileprovider", "knowledge",
               "syncservices", "accounts", "loginwindow", "group.com.apple",
               "dock", "finder", "safari", "siri", "siriremote", "diagnostic",
               "keychain", "corespotlight", "spotlight", "sharedfilelist",
               "systempreferences", "textinput", "wifi", "bluetooth"),
    "Windows": ("microsoft", "windows", "packages", "comms", "connecteddevices",
                "d3dscache", "peerdist", "placeholder", "publishers",
                "virtualstore", "iconcache", "temp", "programs", "ntuser",
                "packagecache", "usoshared", "ssh", "pip"),
    "Linux": ("dconf", "pulse", "systemd", "gnome", "kde", "fontconfig", "mesa",
              "ibus", "gvfs", "ibus", "xdg", "dbus", "nautilus", "gtk", "qt",
              "evolution", "gstreamer", "flatpak", "snap", "pip", "user-dirs",
              "mimeapps", "trash", "recently-used", "fish", "nvim", "vim"),
}

PROTECTED_EXACT = {
    "Darwin": {"ByHost", "Google", "Microsoft", "Adobe", "JetBrains", "Mozilla",
               "Residue", ".DS_Store", "com.residue",
               # macOS components that do not carry a com.apple prefix
               "PassKit", "GeoServices", "GameKit", "Animoji", "networkserviceproxy", "icdd",
               "homeenergyd", "locationaccessstored", "familycircled", "FamilyCircle", "familycircled.plist",
               "DifferentialPrivacy", "PrivacyPreservingMeasurement", "Baseband", "TemporaryItems",
               "TokenBucketRateLimiter.plist", "ContextStoreAgent.plist", "FeatureToggle.plist", "pbs.plist",
               "PhotosSearch.aapbz", "PhotosUpgrade.aapbz", "Avatar Cache Index.plist", "executorchcoreml",
               "default.store", "default.store-shm", "default.store-wal", "group.is.workflow.my.app",
               "group.tvappservices.container", "com.android.Emulator.plist", "Assistant", "SyncServices",
               "ScreenRecording", "StatusKit", "UBF8T346G9.ms", "Dropbox"},
    "Windows": {"Microsoft", "Google", "Adobe", "Mozilla", "Residue"},
    "Linux": {"Residue"},
}


def is_protected(name):
    n = name.lower().lstrip(".")
    sysname = SYSTEM if SYSTEM in PROTECTED_PREFIXES else "Linux"
    if name in PROTECTED_EXACT.get(sysname, set()):
        return True
    if name.startswith("."):
        return True
    if SYSTEM == "Darwin" and ("com.apple" in n or n.startswith("74j34u3r6x.") or n.startswith("group.com.apple")):
        return True
    return any(n.startswith(p) for p in PROTECTED_PREFIXES[sysname])


# --------------------------------------------------------------------------
# Installed apps
# --------------------------------------------------------------------------

def _run(cmd, timeout=15):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return out.stdout
    except Exception:
        return ""


def _mac_apps():
    apps = []
    patterns = [
        "/Applications/*.app", "/Applications/*/*.app", "/Applications/Utilities/*.app",
        str(HOME / "Applications" / "*.app"), "/System/Applications/*.app",
        "/System/Applications/Utilities/*.app", "/System/Library/CoreServices/*.app",
        "/Library/Application Support/*/*.app", "/Library/Application Support/*/*/*.app",
        "/Library/Application Support/*/*/*/*.app",
    ]
    seen = set()
    for pat in patterns:
        for path in glob.glob(pat):
            if path in seen:
                continue
            seen.add(path)
            name = Path(path).stem
            ids = set()
            try:
                with open(Path(path) / "Contents" / "Info.plist", "rb") as f:
                    info = plistlib.load(f)
                for key in ("CFBundleIdentifier", "CFBundleName", "CFBundleExecutable", "CFBundleDisplayName"):
                    if info.get(key):
                        ids.add(str(info[key]))
            except Exception:
                pass
            apps.append({"name": name, "ids": sorted(ids), "source": "app bundle"})
    for kind in ("--formula", "--cask"):
        for line in _run(["brew", "list", kind]).split():
            apps.append({"name": line, "ids": [], "source": "homebrew"})
    return apps


def _windows_apps():
    apps = []
    try:
        import winreg  # type: ignore
        roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, sub in roots:
            try:
                key = winreg.OpenKey(hive, sub)
            except OSError:
                continue
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    sk = winreg.OpenKey(key, winreg.EnumKey(key, i))
                    name = winreg.QueryValueEx(sk, "DisplayName")[0]
                    ids = []
                    for val in ("Publisher", "InstallLocation"):
                        try:
                            v = winreg.QueryValueEx(sk, val)[0]
                            if v:
                                ids.append(str(Path(v).name) if val == "InstallLocation" else str(v))
                        except OSError:
                            pass
                    apps.append({"name": str(name), "ids": ids, "source": "registry"})
                except OSError:
                    continue
    except ImportError:
        pass
    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        if root and os.path.isdir(root):
            for child in os.listdir(root):
                apps.append({"name": child, "ids": [], "source": "program folder"})
    # Microsoft Store apps (optional, slow)
    out = _run(["powershell", "-NoProfile", "-Command",
                "Get-AppxPackage | Select-Object -ExpandProperty Name"], timeout=20)
    for line in out.splitlines():
        if line.strip():
            apps.append({"name": line.strip(), "ids": [], "source": "store"})
    return apps


def _linux_apps():
    apps = []
    for pat in ("/usr/share/applications/*.desktop", str(HOME / ".local/share/applications/*.desktop"),
                "/var/lib/flatpak/exports/share/applications/*.desktop"):
        for path in glob.glob(pat):
            name = Path(path).stem
            ids = [name]
            try:
                for line in open(path, errors="ignore"):
                    if line.startswith("Name=") or line.startswith("Exec="):
                        ids.append(line.split("=", 1)[1].strip().split()[0])
            except Exception:
                pass
            apps.append({"name": name, "ids": ids, "source": "desktop entry"})
    for cmd in (["dpkg-query", "-W", "-f=${Package}\n"], ["pacman", "-Qq"], ["rpm", "-qa", "--qf", "%{NAME}\n"],
                ["flatpak", "list", "--app", "--columns=application"], ["snap", "list"]):
        for line in _run(cmd).splitlines():
            line = line.strip()
            if line and not line.startswith("Name"):
                apps.append({"name": line.split()[0], "ids": [], "source": cmd[0]})
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if os.path.isdir(d):
            for exe in os.listdir(d):
                apps.append({"name": exe, "ids": [], "source": "PATH"})
    return apps


def installed_apps():
    """List of {name, ids, source, tokens:set, norms:set}."""
    if SYSTEM == "Darwin":
        apps = _mac_apps()
    elif SYSTEM == "Windows":
        apps = _windows_apps()
    else:
        apps = _linux_apps()
    for app in apps:
        toks = set(tokens(app["name"]))
        norms = {normalize(app["name"])}
        for i in app["ids"]:
            toks |= tokens(i)
            norms.add(normalize(i))
        app["tokens"] = {t for t in toks if t}
        app["norms"] = {n for n in norms if len(n) >= 4}
    return apps
