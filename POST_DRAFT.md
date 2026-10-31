---
title: "App Graveyard: find and bury the leftovers of uninstalled apps, judged by Gemma 3 on your own machine"
published: false
tags: devchallenge, hf26challenge, ai, opensource
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26)*

## What I Built

A few weeks ago I set up a new MacBook and did what everyone does with a new laptop: tried a pile of apps. iTerm2, Arc, a couple of Edge betas, Vivaldi, a clipboard manager called Clipy. Most of them went to the Trash within days. The icons disappeared, so I assumed the apps had too.

They hadn't. Each one had left a little pile of itself in `~/Library`: preferences, caches, a log or two, sometimes a whole container. Nothing big. But it was sitting on a laptop that was four weeks old, and nothing was ever going to look at it again. That felt like the theme, so I ran with it.

**App Graveyard** looks through your application-data folders, works out which leftovers still belong to an app you actually have, and hands the rest to a small open-weight model running on your own machine. The model's job is to say what the app was, who made it, and whether it's safe to put to rest. Every dead app gets a tombstone, a one-line reason, and an epitaph. (The model writes the epitaphs. Some of them are better than I expected. "A fleeting glimpse of a vanished client" was for Arc.)

"Bury" moves an app's folders into a quarantine with a manifest. "Restore" puts them back exactly where they were. There is no delete button anywhere, and that's deliberate.

It runs on macOS, Windows and Linux, offline, with no API key. The only network call in the whole codebase goes to `127.0.0.1:11434`, which is Ollama.

## Demo

{% embed https://youtu.be/HYClrIPK-YQ %}

**Open https://raushanichaudhary.github.io/app-graveyard/** and follow the three one-time steps on the page. The page talks to a 1 MB helper on your own machine and runs the scan from there, so the site is the app, not a landing page for it. On macOS and Linux the install line registers the helper as a login service, and after that the page is just a Scan button. On Windows it's a single .exe.

If you'd rather stay in a terminal, this is what a run looks like:

```
$ python -m appgraveyard
  summoning installed apps...
  216 installed apps found
  1307 leftovers scanned, folded into 1273 apps, 18 belong to nothing installed
  consulting gemma3:4b  18/18
  12 ghosts haunting 355.3 KB, 0 unsure (0 B), 59 still living, 1182 protected
  graveyard open at http://127.0.0.1:7777/
```

## Code

{% embed https://github.com/raushanichaudhary/app-graveyard %}

MIT. Python standard library only. The one thing you need besides Python is Ollama.

## How I Built It

There are four stages, and only the last one is AI. That ratio ended up being the real lesson of the week.

**Scan.** Walk the direct children of the usual leftover roots. On a Mac that's `~/Library/Application Support`, `Caches`, `Preferences`, `Logs`, `Containers`, `Group Containers`, `Saved Application State`, `HTTPStorages` and `WebKit`. On Windows it's `%APPDATA%`, `%LOCALAPPDATA%`, `LocalLow` and `ProgramData`; on Linux `~/.config`, `~/.cache` and `~/.local/share`. For each entry, note the size, the file count, the first and last modification dates, and a handful of child names. Everything here is read-only.

**Match, with no AI at all.** Build the list of installed apps: bundle ids and names from `.app` bundles plus Homebrew on the Mac, registry uninstall keys and Program Files and Store packages on Windows, desktop entries, dpkg, flatpak and `$PATH` on Linux. Tokenise both sides and compare. The one rule that mattered more than anything else: a word shared by three or more installed apps (`microsoft`, `google`, `zoom`) is a vendor word, and on its own it never proves an app is installed. Before I added that rule, a leftover Edge profile was hiding behind VS Code because both of them say "microsoft".

**Group and protect.** Fold the folders of one app together, so `com.clipy-app.Clipy` in Application Support, Caches, HTTPStorages and Preferences becomes one Clipy with four parts. Anything that belongs to the OS gets marked protected and can never be buried, whatever the model says.

**Consult the ghost.** Whatever is still unexplained goes to Gemma 3 4B through Ollama, four apps per call, with JSON output forced. For each app the model gets the folder names, where they live, sizes, dates, a few sample children, and the list of installed apps from the same vendor. It sends back a product, a vendor, a category, a verdict (`ghost`, `keep` or `unsure`), a confidence, a one-line reason and an epitaph. Any ghost verdict under 60% confidence gets downgraded to unsure, so the model can't bury something on a coin flip. Anything it skips in a batch gets asked again on its own.

### Things that went wrong

I expected the model to be the hard part. It wasn't. The hard part was making sure I wasn't asking it the wrong question.

- **Vendor words.** My first matcher saw "microsoft" in `Microsoft Edge Beta`, found "microsoft" in VS Code's bundle id, and declared Edge alive and well. Hence the three-apps rule above.
- **Zoom was dead, apparently.** `ZoomChat.plist`, `ZoomPhone` and `zoomusinstall.log` never produced the token "zoom", so the model was told Zoom wasn't installed and, quite reasonably, called all three ghosts. The fix was to split CamelCase and match on prefixes, so `zoomus` finds `zoom.us`. The lesson stuck with me: if the context you hand the model is wrong, a confident answer is worse than no answer.
- **The model wanted to bury things it shouldn't.** It called the pip cache and the Office group container ghosts, because no `.app` is named "pip". So two kinds of thing never reach the model at all now: caches of command-line developer tools, and shared containers of a developer team that still has apps installed. Rules first, model last.
- **Where Gemma still gets it wrong.** It kept `com.clipy-app.Clipy` at 85% ("preferences may be reused"). Clipy is gone. It also kept the main `Microsoft Edge` folder because other Microsoft apps are installed, while correctly burying Edge Beta, Dev and Canary one call earlier. Both are in the video, unedited. A 4B model is a good intern, not an auditor, which is exactly why every verdict is a move and never a delete.
- **Batches.** Six apps per call and the model would skip or reorder items. Four per call, matched by name instead of position, with a single-item retry pass, and that dropped to zero on this machine.

### The numbers

For the record, from a four-week-old MacBook with 8 GB of RAM:

| | |
| --- | --- |
| Leftover folders and files scanned | 1,307 |
| Folded into apps | 1,273 |
| Protected (operating system) | 1,182 |
| Living (matched to an installed app) | 59 |
| Kept by rule (dev caches, shared vendor containers) | 14 |
| Sent to Gemma 3 4B | 18 |
| Declared ghosts | 12 (355 KB) |
| Wrong verdicts, by my own count | 2 |
| Scan time, model included | about 2.5 minutes |

I'll be honest that these are small numbers. A new laptop has small ghosts. The real test is an older Windows machine that has seen years of installs, and the Windows paths are in the code waiting for one.

## Why Does Open Innovation Matter?

I thought about this more than I expected to while building it. The input to this tool is a list of every application you have ever used, with paths, dates and file names. That is a pretty complete profile of a person. Sending it to a hosted model to ask "which of these are dead?" would be a strange trade: hand over the most detailed inventory of your digital life to free up a few hundred kilobytes.

With an open-weight model it never leaves the laptop. A quantised 4B Gemma on a machine with 8 GB of RAM figured out that `com.clipy-app.Clipy` was a clipboard manager, knew that OneAuth is a Microsoft auth broker still used by Office, and wrote a little tombstone for each dead browser channel. It did all of that offline, for free, and you can swap the model with one environment variable. The same tool built on a cloud API would need a key, a bill, and a privacy policy, and I don't think I'd have shipped it.

## The Spirit of It

Día de los Muertos is about remembering, not erasing. App Graveyard doesn't delete anything. It gives each dead app a marigold, a candle and a line of remembrance, and moves it to a quarantine you can reopen whenever you like. The ghost in your machine is just data nobody came back for.

## Prize Categories

**Best Use of Gemma**
