import re
import time

from playwright.sync_api import Page, Error as PlaywrightError

import config
import credentials
import captcha

USERNAME_INPUT = "#username"
PASSWORD_INPUT = "#password"
CAPTCHA_INPUT = "#txtCaptcha"
LOGIN_BUTTON = "#submitBtn"
CAPTCHA_ERROR_TEXT = "Capatcha text does not match"  # site's own spelling


def _fill_credentials(page: Page) -> None:
    page.fill(USERNAME_INPUT, credentials.USERNAME)
    page.fill(PASSWORD_INPUT, credentials.PASSWORD)


def _login_form_visible(page: Page) -> bool:
    try:
        return page.locator(USERNAME_INPUT).is_visible()
    except PlaywrightError:
        # Page is mid-navigation; treat as "still on login page" and check again.
        return True


def _dismiss_error(page: Page) -> None:
    """Galat captcha ka error popup (#opaquepopup) hide kar do taaki agla fill/click block na ho."""
    try:
        page.evaluate("var e=document.getElementById('opaquepopup'); if(e){e.style.display='none';}")
    except PlaywrightError:
        pass


def _error_dialog_message(html: str) -> str:
    """Server ne is response me jo error-dialog inject kiya uska message (lowercase) - warna ''.

    Galti se poora page match na ho isliye SIRF openDialogBox("....") ka asli message dekhte hain
    (login page ke JS me error-words waise bhi pade rehte hain - unko ignore karo)."""
    m = re.search(r'opendialogbox\(\s*"(.*?)"', html, re.S)
    return m.group(1) if m else ""


def _submit_outcome(page: Page) -> str:
    """Login dabane ke baad jaldi se nateeja: 'ok' | 'captcha' | 'password'."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=8000)
    except PlaywrightError:
        pass
    page.wait_for_timeout(300)                         # inline error-script ko DOM me aane do
    try:
        html = page.content().lower()
    except PlaywrightError:
        page.wait_for_timeout(300)
        try:
            html = page.content().lower()
        except PlaywrightError:
            html = ""

    if page.locator(USERNAME_INPUT).count() == 0:      # login form gayab = andar aa gaye
        return "ok"
    msg = _error_dialog_message(html)                  # is submit par dikhaya gaya asli error
    if "match" in msg or "captcha" in msg or "does not match" in html:
        return "captcha"                               # captcha galat -> retry
    if msg:                                             # koi aur explicit error (password/account) -> ruk jao
        return "password"
    return "captcha"                                   # login page par hi + koi error-dialog nahi -> captcha maano


def _auto_login(page: Page) -> bool:
    """OCR se captcha padh ke login. Logged-in hone par True.

    Sirf captcha galat hone par retry (turant, naye captcha ke saath). Password/account error par
    seedha raise - taaki baar-baar galat password se account lock na ho.
    """
    for attempt in range(1, config.CAPTCHA_MAX_ATTEMPTS + 1):
        page.wait_for_selector(USERNAME_INPUT)
        _dismiss_error(page)
        _fill_credentials(page)
        text = captcha.solve(page)
        page.fill(CAPTCHA_INPUT, text)
        print(f">> Attempt {attempt}: CAPTCHA '{text}', logging in...")

        page.click(LOGIN_BUTTON)
        outcome = _submit_outcome(page)

        if outcome == "ok":
            return True
        if outcome == "password":
            raise RuntimeError(
                "Login fail hua aur captcha sahi tha -> USERNAME/PASSWORD galat lag raha hai "
                "(credentials.txt check karo). Account lock na ho isliye retry nahi kar rahe."
            )
        # captcha galat -> TURANT naya captcha, poora page reload kiye bina (fast)
        print(">> captcha galat, turant naya try...")
        _dismiss_error(page)
        try:
            captcha.refresh(page)
        except PlaywrightError:
            page.goto(config.BASE_URL, wait_until="domcontentloaded")
    return False


def _manual_login(page: Page) -> None:
    """Fill the credentials and wait for the user to type the CAPTCHA."""
    page.wait_for_selector(USERNAME_INPUT)
    _fill_credentials(page)
    page.focus(CAPTCHA_INPUT)
    print(">> Type the CAPTCHA in the browser and click Login.")

    deadline = time.time() + config.LOGIN_WAIT_SECONDS
    while time.time() < deadline:
        time.sleep(1)
        if not _login_form_visible(page):
            # Confirm it stays gone (not just a reload after a wrong CAPTCHA).
            time.sleep(2)
            if not _login_form_visible(page):
                return
        # If a wrong CAPTCHA reloaded the form, fill the credentials again.
        try:
            if page.locator(USERNAME_INPUT).input_value() == "":
                _fill_credentials(page)
                print(">> Login page reloaded (wrong CAPTCHA?). Credentials refilled, try again.")
        except PlaywrightError:
            pass

    raise TimeoutError(f"Login not completed within {config.LOGIN_WAIT_SECONDS} seconds.")


def run(page: Page) -> None:
    """Open the ECHS portal and log in using credentials.py."""
    if not credentials.USERNAME or not credentials.PASSWORD:
        raise ValueError("Fill USERNAME and PASSWORD in credentials.py first.")

    page.goto(config.BASE_URL, wait_until="domcontentloaded")

    logged_in = False
    if config.AUTO_CAPTCHA:
        logged_in = _auto_login(page)
        if not logged_in:
            print(f">> Could not read the CAPTCHA in {config.CAPTCHA_MAX_ATTEMPTS} tries.")
            page.goto(config.BASE_URL, wait_until="domcontentloaded")

    if not logged_in:
        _manual_login(page)

    page.wait_for_load_state("domcontentloaded")
    print(f">> Logged in. Current page: {page.url}")
