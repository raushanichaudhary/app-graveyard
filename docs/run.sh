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
PY="$(command -v python3)"
LOG="$HOME/.app-graveyard/helper.log"

# Register the helper as a background service that starts at login, so the page
# only ever needs a Scan button from now on. Falls back to running in the foreground.
if [ "$(uname)" = "Darwin" ]; then
  PLIST="$HOME/Library/LaunchAgents/io.github.raushanichaudhary.app-graveyard.plist"
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>io.github.raushanichaudhary.app-graveyard</string>
  <key>ProgramArguments</key><array><string>$PY</string><string>-m</string><string>appgraveyard</string><string>open</string><string>--no-browser</string></array>
  <key>WorkingDirectory</key><string>$DIR/app-graveyard-main</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>ThrottleInterval</key><integer>15</integer>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
PL
  launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
  if launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null; then
    echo
    echo "  Done. App Graveyard now runs in the background and starts with your Mac."
    echo "  You can close this window. Go back to the page in your browser; it connects by itself."
    echo "  To remove it later:  launchctl bootout gui/\$(id -u) '$PLIST'; rm -rf ~/.app-graveyard"
    echo
    exit 0
  fi
elif command -v systemctl >/dev/null 2>&1 && systemctl --user status >/dev/null 2>&1; then
  UNIT="$HOME/.config/systemd/user/app-graveyard.service"
  mkdir -p "$HOME/.config/systemd/user"
  cat > "$UNIT" <<SV
[Unit]
Description=App Graveyard helper (local only, 127.0.0.1:7777)
[Service]
WorkingDirectory=$DIR/app-graveyard-main
ExecStart=$PY -m appgraveyard open --no-browser
Restart=on-failure
RestartSec=15
[Install]
WantedBy=default.target
SV
  if systemctl --user daemon-reload && systemctl --user enable --now app-graveyard.service >/dev/null 2>&1; then
    systemctl --user restart app-graveyard.service >/dev/null 2>&1 || true
    echo
    echo "  Done. App Graveyard now runs in the background and starts when you log in."
    echo "  You can close this window. Go back to the page in your browser; it connects by itself."
    echo "  To remove it later:  systemctl --user disable --now app-graveyard; rm -rf ~/.app-graveyard"
    echo
    exit 0
  fi
fi

echo
echo "  App Graveyard is running. Keep this window open."
echo "  Go back to the page in your browser; it connects by itself."
echo "  No page open? Visit http://127.0.0.1:7777/"
echo
exec "$PY" -m appgraveyard open --no-browser
