"""Entry point for the packaged (PyInstaller) builds. Double-click = `appgraveyard open`."""
import sys

from appgraveyard.__main__ import main

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:] or ["open"]))
    except Exception as exc:  # keep the window readable when something goes wrong
        print("\n  App Graveyard could not start: %s: %s" % (type(exc).__name__, exc))
        try:
            input("  press Enter to close")
        except EOFError:
            pass
        sys.exit(1)
