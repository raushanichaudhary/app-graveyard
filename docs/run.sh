#!/bin/sh
# App Graveyard: download the helper and start it. macOS and Linux.
#   curl -fsSL https://raushanichaudhary.github.io/app-graveyard/run.sh | sh
# Nothing is installed system-wide: everything lives in ~/.app-graveyard/app.
set -e
ZIP="https://github.com/raushanichaudhary/app-graveyard/archive/refs/heads/main.zip"
DIR="$HOME/.app-graveyard/app"

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
  echo
  echo "  Python 3.9 or newer is needed."
  echo "  macOS: if a window just offered to install the Command Line Tools, click Install, wait, then run this line again."
  echo "  Otherwise get Python from https://www.python.org/downloads/ and run this line again."
  exit 1
fi

mkdir -p "$DIR" && cd "$DIR"
echo "  downloading App Graveyard..."
curl -fsSL "$ZIP" -o app.zip
rm -rf app-graveyard-main
if command -v unzip >/dev/null 2>&1; then unzip -qo app.zip; else python3 -c "import zipfile; zipfile.ZipFile('app.zip').extractall('.')"; fi
rm -f app.zip
cd app-graveyard-main
echo
echo "  App Graveyard is running. Keep this window open."
echo "  Go back to the page in your browser; it connects by itself."
echo "  No page open? Visit http://127.0.0.1:7777/"
echo
exec python3 -m appgraveyard open --no-browser
