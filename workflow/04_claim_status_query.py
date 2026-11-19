"""Step: Claim Status Query.

Other -> Claim Status Query -> Search Criteria = Claim ID -> Search Value = claim number -> Search.
Claim number project root ki `claim_id.txt` se padha jaata hai (usme tum paste karoge).
"""
import os

from playwright.sync_api import Page

OTHER_MENU = "#li_7"           # left menu me "Other"
OTHER_SUBMENU = "ul[id='7']"   # uske neeche khulne wali list
SEARCH_CRITERIA = "#searchCriteria"
SEARCH_VALUE = "#searchValue"
CLAIM_ID_OPTION = "i"          # Search Criteria me "Claim ID" option ki value
# Search button - alag-alag possible selectors (jo pehle mile use karega)
SEARCH_BUTTON = "#searchBtn, button:has-text('Search'), input[type='submit'][value*='Search' i], input[type='button'][value*='Search' i]"

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


def run(page: Page) -> None:
    # 1. "Other" menu kholo
    menu = page.locator(OTHER_MENU)
    menu.wait_for(state="visible")
    if not page.locator(OTHER_SUBMENU).is_visible():
        menu.click()
        page.locator(OTHER_SUBMENU).wait_for(state="visible")
    print(">> 'Other' menu khola.")

    # 2. "Claim Status Query" par click
    with page.expect_navigation(wait_until="domcontentloaded"):
        page.locator(OTHER_SUBMENU).get_by_role("link", name="Claim Status Query").click()
    page.locator(SEARCH_CRITERIA).wait_for(state="visible")
    print(">> 'Claim Status Query' khola.")

    # 3. Search Criteria = Claim ID
    page.select_option(SEARCH_CRITERIA, CLAIM_ID_OPTION)
    print(">> Search Criteria = 'Claim ID'.")

    # 4. Search Value me claim number (claim_id.txt se)
    claim_id = _read_claim_id()
    if not claim_id:
        print(">> claim_id.txt khali hai! usme claim number paste karo, phir dobara chalao.")
        return
    page.fill(SEARCH_VALUE, claim_id)
    print(f">> Claim number bhara: {claim_id}")

    # 5. Search par click
    page.locator(SEARCH_BUTTON).first.click()
    print(">> Search dabaya.")
