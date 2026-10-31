---
title: "App Graveyard: find and bury the leftovers of uninstalled apps, judged by Gemma 3 on your own machine"
published: false
tags: devchallenge, hf26challenge, ai, opensource
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26)*

## What I Built

A few weeks ago I set up a new Mac and did what everyone does with a new laptop: tried a pile of apps. A couple of browsers, a fancier terminal, a clipboard manager, two beta builds of things I already had. Most of them went to the Trash within days. The icons disappeared, so I assumed the apps had too.

They hadn't. Each one had left a little pile of itself in `~/Library`: preferences, caches, a log or two, sometimes a whole container. Nothing big. But it was sitting on a laptop that was four weeks old, and nothing was ever going to look at it again. That felt like the theme, so I ran with it.

**App Graveyard** looks through your application-data folders, works out which leftovers still belong to an app you actually have, and hands the rest to a small open-weight model running on your own machine. The model's job is to say what the app was, who made it, and whether it's safe to put to rest. Every dead app gets a tombstone, a one-line reason, and an epitaph. The model writes the epitaphs, and some of them are better than I expected.

"Bury" moves an app's folders into a quarantine with a manifest. "Restore" puts them back exactly where they were. There is no delete button anywhere, and that's deliberate.

It runs on macOS, Windows and Linux, offline, with no API key. The only network call in the whole codebase goes to `127.0.0.1:11434`, which is Ollama.

## Demo

{% embed https://youtu.be/HYClrIPK-YQ %}

**Open https://raushanichaudhary.github.io/app-graveyard/** and follow the three one-time steps on the page. The page talks to a 1 MB helper on your own machine and runs the scan from there, so the site is the app, not a landing page for it. On macOS and Linux the install line registers the helper as a login service, and after that the page is just a Scan button. On Windows it's a single .exe.

If you'd rather stay in a terminal, `python -m appgraveyard` runs the same scan and opens the graveyard at `http://127.0.0.1:7777/`.

## Code

{% embed https://github.com/raushanichaudhary/app-graveyard %}

MIT. Python standard library only. The one thing you need besides Python is Ollama.

## How I Built It

There are four stages, and only the last one is AI. Keeping it that way turned out to be the real lesson of the week: the model gives much better answers when the code has already done the boring, certain parts.

**Scan.** Look inside the folders where apps keep their data. On a Mac that is mostly `~/Library` (Application Support, Caches, Preferences, Logs, Containers and a few more); on Windows it is `%APPDATA%`, `%LOCALAPPDATA%` and `ProgramData`; on Linux `~/.config`, `~/.cache` and `~/.local/share`. For every folder found there, note how big it is, how many files it has, when it was first and last touched, and a few of the file names inside. Nothing is modified at this stage.

**Match, with no AI at all.** Make a list of the apps that are actually installed (on a Mac, the `.app` bundles and Homebrew; on Windows, the registry's uninstall list, Program Files and Store apps; on Linux, desktop entries, dpkg, flatpak and whatever is on `$PATH`). Then compare names: does this leftover folder look like it belongs to one of those apps? The one rule that mattered more than anything else: a word that three or more installed apps share is almost always a company name, and on its own it proves nothing. Without that rule, the leftover profile of an uninstalled browser can hide behind an unrelated app from the same company, just because both carry the company's name.

**Group and protect.** One app usually leaves folders in several places. A clipboard manager might leave one in Application Support, one in Caches and one in Preferences; those get folded into a single entry with three parts, rather than three separate tombstones. Anything that belongs to the operating system itself is marked protected: it never goes to the model and can never be buried.

**Consult the ghost.** Whatever is still unexplained goes to Gemma 3 4B through Ollama, four apps at a time, with the answer forced into JSON. For each app the model is told the folder names, where they are, how big and how old they are, a few file names inside, and which apps from the same company are still installed. It answers with the product name, the company, what kind of app it was, a verdict (`ghost`, `keep` or `unsure`), how confident it is, a one-line reason and an epitaph. If it says ghost with less than 60% confidence, that becomes unsure, so the model can't bury something on a coin flip. If it skips an app in a batch, that app gets asked about again on its own.

## Why Does Open Innovation Matter?

I thought about this more than I expected to while building it. The input to this tool is a list of every application you have ever used, with paths, dates and file names. That is a pretty complete profile of a person. Sending it to a hosted model to ask "which of these are dead?" would be a strange trade: hand over the most detailed inventory of your digital life to free up a few hundred kilobytes.

With an open-weight model it never leaves the laptop. A quantised 4B Gemma on a machine with 8 GB of RAM can recognise a clipboard manager from nothing but its bundle id, knows which vendor helpers are still needed by the apps that remain, and writes a little tombstone for each dead browser build. It does all of that offline, for free, and you can swap the model with one environment variable. The same tool built on a cloud API would need a key, a bill, and a privacy policy, and I don't think I'd have shipped it.

## The Spirit of It

Día de los Muertos is about remembering, not erasing. App Graveyard doesn't delete anything. It gives each dead app a marigold, a candle and a line of remembrance, and moves it to a quarantine you can reopen whenever you like. The ghost in your machine is just data nobody came back for.

## Prize Categories

**Best Use of Gemma**
