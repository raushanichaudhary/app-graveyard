# App Graveyard 👻

**The apps you uninstalled left ghosts behind.**

Every app you ever installed and removed left folders in your application-data directories: caches, preferences, logs, containers. Uninstalling almost never cleans them up. App Graveyard finds those leftovers, works out which installed app each one belongs to, and asks an open-weight model running **on your own machine** to identify the rest: what the app was, who made it, and whether it is safe to put to rest.

Nothing is deleted. Ever. "Burying" a ghost moves its folder to a quarantine directory with a manifest, and one click restores it.

No cloud, no API key, no telemetry. The only network call is to `127.0.0.1:11434`, your local [Ollama](https://ollama.com).

**Site with install steps:** https://raushanichaudhary77-create.github.io/app-graveyard/

![App Graveyard](docs/screenshot.png)

## Run it

Two things need to be on the machine: Python 3.9+ (Windows: [python.org](https://www.python.org/downloads/), tick "Add python to PATH"; macOS and most Linux already have it) and [Ollama](https://ollama.com), opened once.

**The no-terminal way.** Download this repo (green Code button, Download ZIP, unzip) and double-click the launcher for your OS:

| OS | Double-click |
| --- | --- |
| macOS | `App Graveyard.command` (if macOS refuses the first time, right-click it and choose Open) |
| Windows | `App Graveyard.bat` |
| Linux | `app-graveyard.sh` |

A terminal window opens and stays open, and the graveyard page opens in your browser. The page tells you whether the Gemma model is ready, offers a one-time **Download model** button if it is not (about 3 GB through Ollama), and then one **Scan this machine** button does the rest with a progress bar. After the model is downloaded, nothing needs the internet. If Ollama is not running at all, **Scan without the model** still sorts every folder; it just declares nothing dead.

**The terminal way.**

```bash
ollama pull gemma3:4b          # one time, ~3.3 GB (gemma3:1b is faster on small machines)
git clone https://github.com/raushanichaudhary77-create/app-graveyard
cd app-graveyard
python -m appgraveyard              # scan, consult the model, open the graveyard at http://127.0.0.1:7777
```

Or install it as a command: `pip install .` then `appgraveyard`.

Other commands:

```bash
python -m appgraveyard open             # open the page and scan from there (what the launchers do)
python -m appgraveyard scan             # scan only, print a summary, write ~/.app-graveyard/report.json
python -m appgraveyard serve            # reopen the graveyard from the last report
python -m appgraveyard buried           # list everything in quarantine
python -m appgraveyard restore <id>     # put a buried folder back
python -m appgraveyard --no-model       # skip the model, judge by idle time only
GRAVEYARD_MODEL=gemma3:1b python -m appgraveyard   # pick a different local model
```

A full scan with `gemma3:4b` takes about 2.5 minutes on an 8 GB laptop; the model, not the file walk, is the slow part.

Works on macOS, Windows and Linux. Only the folders differ:

| OS | Leftovers scanned | "Installed" comes from |
| --- | --- | --- |
| macOS | `~/Library/{Application Support, Caches, Preferences, Logs, Containers, Group Containers, Saved Application State, HTTPStorages, WebKit}` | `.app` bundles in `/Applications`, `~/Applications`, `/System/Applications` (bundle id, name, executable) + Homebrew |
| Windows | `%APPDATA%`, `%LOCALAPPDATA%`, `LocalLow`, `%PROGRAMDATA%` | Registry uninstall keys, Program Files, `%LOCALAPPDATA%\Programs`, Microsoft Store packages |
| Linux | `~/.config`, `~/.cache`, `~/.local/share`, `~/.local/state` | `.desktop` entries, dpkg/pacman/rpm, flatpak, snap, `$PATH` |

## How it works

1. **Scan** (`scan.py`): walks every direct child of the leftover roots and measures size, file count, first and last modification dates and a few sample children. Read-only.
2. **Match** (`match.py`): no AI here. Folder names and bundle ids are tokenised and compared against the installed-app list. A word shared by three or more installed apps (`microsoft`, `google`) is treated as a vendor word and never proves an app is installed on its own, which is what stops a leftover Edge profile from hiding behind VS Code.
3. **Protect** (`platforms.py`): anything that belongs to the OS is marked protected and can never be buried.
4. **Consult** (`oracle.py`): the orphans, in batches of four, go to Gemma through Ollama's `/api/chat` with JSON output forced. For each folder the model returns product, vendor, category, a verdict (`ghost`, `keep`, `unsure`), a confidence, a one-line reason and an epitaph. A "ghost" verdict under 60% confidence is downgraded to "unsure", so the model never gets to bury on a coin flip.
5. **Graveyard** (`report.py`, `job.py`, `ui/index.html`): a local page with one tombstone per dead app. The page can also start a scan or a model download itself (`/api/scan`, `/api/pull`, `/api/status`), so the launchers never need a typed command. Bury moves the folder to `~/.app-graveyard/quarantine/<timestamp>/`; Restore moves it back.

If Ollama is not running, the scan still completes using an idle-time heuristic and the page says so. Nothing is promoted to "ghost" without the model.

## Why open-source AI

The input to this tool is a list of every application you have ever used, with paths, dates and file names. That is a profile of you. It should not leave your laptop to be classified, and with an open-weight model it does not have to. A 4B-parameter Gemma, quantised, identifies "com.clipy-app.Clipy" as a clipboard manager that is no longer installed just as well as a hosted model would, on a machine with 8 GB of RAM, for free, offline.

## Safety

- Read-only scan.
- Bury is a move, never a delete. The manifest at `~/.app-graveyard/quarantine/manifest.json` records every original path.
- Protected (OS) items and living (installed) items cannot be buried from the UI or the API.
- Credentials, licences, SSH keys and package caches are prompted to be marked "keep" or "unsure"; and you are the one who clicks.

## License

MIT
