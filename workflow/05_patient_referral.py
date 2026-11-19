"""Step: Patient Referral.

CONDITION: ye step tabhi chalta hai jab Claim Status List me Process Stage = "Patient Referral" dikhe.
           (warna skip - kyunki Scrutinizer Verified / aur stages bhi aa sakte hain.)

ACTIONS:  Intimation -> Patient Referral -> Claim ID paste (claim_id.txt se) -> Submit.

NOTE: Intimation / Patient Referral / Claim-ID-field / Submit ke selectors abhi GUESS hain
      (live page inspect nahi kar paya). Test me koi click na lage to batao - theek kar dunga.
"""
import os

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout, Error as PlaywrightError

CLAIM_ID_FILE = os.path.join(os.path.dirname(__file__), "..", "claim_id.txt")


def _read_claim_id() -> str:
    try:
        with open(CLAIM_ID_FILE, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#"):
                    return s
    except FileNotFoundError:
        pass
    return ""


def _stage_is_patient_referral(page: Page) -> bool:
    """Claim Status List me VISIBLE 'Patient Referral' text ho to True.
    (collapsed menu ka 'Patient Referral' hidden hota hai, isliye visible-check se process-stage pakda jaata hai)."""
    loc = page.get_by_text("Patient Referral", exact=False)
    for i in range(loc.count()):
        try:
            if loc.nth(i).is_visible():
                return True
        except PlaywrightError:
            pass
    return False


def _click_first(page: Page, label: str, *selectors, navigate: bool = False) -> bool:
    """Diye gaye selectors me se jo pehle mile+visible ho use click karo."""
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible():
                if navigate:
                    with page.expect_navigation(wait_until="domcontentloaded"):
                        loc.click()
                else:
                    loc.click()
                print(f">> '{label}' click kiya.")
                return True
        except PlaywrightError:
            continue
    print(f">> '{label}' nahi mila/click nahi hua (selector adjust karna padega).")
    return False


def run(page: Page) -> None:
    page.wait_for_timeout(1500)  # claim status list load hone do

    # ---- CONDITION: sirf Patient Referral stage par chalo
    if not _stage_is_patient_referral(page):
        print(">> Process Stage 'Patient Referral' nahi hai -> Patient Referral step SKIP.")
        return
    print(">> Process Stage = Patient Referral -> aage badh rahe hain.")

    # ---- 1. Intimation par click
    _click_first(
        page, "Intimation",
        "a:has-text('Intimation')", "button:has-text('Intimation')", "li:has-text('Intimation')",
    )
    page.wait_for_timeout(800)

    # ---- 2. Patient Referral par click (Intimation ke andar)
    _click_first(
        page, "Patient Referral",
        "a:has-text('Patient Referral')", "li:has-text('Patient Referral')", "button:has-text('Patient Referral')",
    )
    page.wait_for_timeout(1500)

    # ---- 3. Claim ID field me claim number (claim_id.txt se)
    claim_id = _read_claim_id()
    if not claim_id:
        print(">> claim_id.txt khali hai! claim number paste karo.")
        return
    field = page.locator(
        "#claimId, #claimID, #claim_id, input[id*='claim' i][type='text'], input[name*='claim' i][type='text']"
    ).first
    try:
        field.wait_for(state="visible", timeout=8000)
        field.fill(claim_id)
        print(f">> Claim ID bhara: {claim_id}")
    except PlaywrightTimeout:
        print(">> Claim ID field nahi mila (selector adjust karna padega).")
        return

    # ---- 4. Submit par click
    _click_first(
        page, "Submit",
        "#submit", "button:has-text('Submit')",
        "input[type='submit'][value*='Submit' i]", "input[type='button'][value*='Submit' i]",
    )
