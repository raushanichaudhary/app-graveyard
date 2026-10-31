#!/bin/sh
# Linux: run ./app-graveyard.sh or double-click it in a file manager that runs scripts.
cd "$(dirname "$0")"
echo "  App Graveyard: keep this window open while you use the page."
exec python3 -m appgraveyard open
