import os
import subprocess
import sys

# CAPTCHA reader (ddddocr) + playwright ek venv me hain. Local .venv na ho to ECHS-automation ka venv use karo.
_HERE = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [
    os.path.join(_HERE, ".venv", "Scripts", "python.exe"),
    os.path.join(_HERE, "ECHS-automation", ".venv", "Scripts", "python.exe"),
]
_VENV_PYTHON = next((p for p in _CANDIDATES if os.path.exists(p)), None)
if _VENV_PYTHON and os.path.normcase(sys.executable) != os.path.normcase(_VENV_PYTHON):
    sys.exit(subprocess.call([_VENV_PYTHON, os.path.abspath(__file__), *sys.argv[1:]]))

from playwright.sync_api import sync_playwright

import config
import login

# Flow ke steps yahan order me add hote jaayenge (login me hi captcha solve ho jaata hai).
STEPS = [
    login.run,
    # aage ke steps yahan add karo, jaise reference (ECHS-automation) me pop_up.run, claim_status_query.run
]


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS, slow_mo=config.SLOW_MO_MS)
        context = browser.new_context(ignore_https_errors=True, no_viewport=True)
        page = context.new_page()
        try:
            for step in STEPS:
                step(page)
        finally:
            try:
                input("\nPress Enter to close the browser...")
            except EOFError:
                pass
            browser.close()


if __name__ == "__main__":
    main()
