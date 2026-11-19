"""Step: 'We have checked all the "Need More Info" claims pertaining to our hospital' checkbox tick karna."""
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

NMI_CHECKBOX = "#ihaveseennmi"


def run(page: Page) -> None:
    checkbox = page.locator(NMI_CHECKBOX)
    try:
        checkbox.wait_for(state="visible", timeout=10_000)
    except PlaywrightTimeout:
        print(">> 'Need More Info' checkbox nahi mila, skip.")
        return

    if checkbox.is_checked():
        print(">> 'Need More Info' checkbox pehle se ticked hai.")
        return

    checkbox.check()
    print(">> 'We have checked all the Need More Info claims' tick kar diya.")
