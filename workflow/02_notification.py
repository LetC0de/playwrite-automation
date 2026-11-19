"""Step: login ke baad aane wala 'Important Notification' popup band karna."""
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

NOTIFICATION_MODAL = "#notificationModal"
CLOSE_BUTTON = "#closeCrossBtn"


def run(page: Page) -> None:
    """Agar 'Important Notification' popup dikhe to use band kar do (na dikhe to skip)."""
    try:
        page.locator(CLOSE_BUTTON).wait_for(state="visible", timeout=10_000)
    except PlaywrightTimeout:
        print(">> Koi notification popup nahi aaya, skip.")
        return

    page.click(CLOSE_BUTTON)
    try:
        page.locator(NOTIFICATION_MODAL).wait_for(state="hidden", timeout=5_000)
    except PlaywrightTimeout:
        pass
    print(">> Notification popup band kar diya.")
