#!/bin/bash
# macOS: double-click this file. It opens the graveyard in your browser.
# If macOS says it cannot be opened, right-click it and choose Open once.
cd "$(dirname "$0")"
echo "  App Graveyard: keep this window open while you use the page."
python3 -m appgraveyard open || { echo; echo "  Python 3 is needed: https://www.python.org/downloads/"; read -r -p "  press Enter to close"; }
