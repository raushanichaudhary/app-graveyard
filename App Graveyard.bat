@echo off
rem Windows: double-click this file. It opens the graveyard in your browser.
cd /d "%~dp0"
echo   App Graveyard: keep this window open while you use the page.
where py >nul 2>nul
if %errorlevel%==0 (py -3 -m appgraveyard open) else (python -m appgraveyard open)
if %errorlevel% neq 0 (
  echo.
  echo   Python 3 is needed: https://www.python.org/downloads/  ^(tick "Add python to PATH"^)
  pause
)
