import glob
import importlib.util
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

# ---- workflow/ folder ke saare steps, FILENAME ke order me (01_, 02_, ...) khud load hote hain.
# Naya step add karna ho to bas workflow/ me ek numbered file daalo jisme run(page) ho.
WORKFLOW_DIR = os.path.join(_HERE, "workflow")


def load_steps():
    steps = []
    for path in sorted(glob.glob(os.path.join(WORKFLOW_DIR, "*.py"))):
        name = os.path.basename(path)
        if name.startswith("__"):
            continue
        spec = importlib.util.spec_from_file_location(name[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "run"):
            steps.append((name[:-3], mod.run))
    return steps


def main() -> None:
    steps = load_steps()
    print(">> Workflow steps (order):", ", ".join(n for n, _ in steps))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS, slow_mo=config.SLOW_MO_MS)
        context = browser.new_context(ignore_https_errors=True, no_viewport=True)
        page = context.new_page()
        try:
            for name, step in steps:
                print(f"\n=== STEP: {name} ===")
                step(page)
        finally:
            try:
                input("\nPress Enter to close the browser...")
            except EOFError:
                pass
            browser.close()


if __name__ == "__main__":
    main()
