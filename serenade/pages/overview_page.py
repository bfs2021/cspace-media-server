from __future__ import annotations

from selenium.webdriver.common.by import By

from .page import Locator, Page, by_id


class OverviewPage(Page):
    TITLE = by_id("overview-title")
    MUSEUM_MENU = by_id("museum-menu")
    SIGN_OUT = by_id("sign-out")
    AUDIT = by_id("nav-audit")
    LOOKUP = by_id("nav-lookup")
    AUDIT_TABLE = by_id("audit-table")
    # The audit log's rows arrive after the page opens: wait for one, by its action.
    SIGN_IN_ROW = (By.XPATH, "//*[@id='audit-table']//td[normalize-space()='sign in']")

    # The current refresh, which Serena serves from, and the pending one (mockup version 55).
    CURRENT_CARD = by_id("current-card")
    CURRENT_NONE = by_id("current-none")
    CURRENT_STATE = by_id("current-refresh-state")
    PARTLY_REPLACED = by_id("partly-replaced")  # a failed update stopped partway
    PARTLY_REPLACED_DETAIL = by_id("partly-replaced-detail")
    PENDING_CARD = by_id("pending-card")
    PENDING_NONE = by_id("pending-none")
    PENDING_STATE = by_id("pending-refresh-state")
    PENDING_FIX = by_id("pending-fix")

    SIGN_IN_ANOTHER = by_id("sign-in-another")  # in the museum menu
    SIGN_OUT_ALL = by_id("sign-out-all")
    CONFIRM_SIGN_OUT_ALL = by_id("confirm-sign-out-all")
    SIGN_OUT_ALL_ERROR = by_id("sign-out-all-error")  # in the dialog, when signing everyone out failed
    # The museum menu's museums, each "<museum> (<user>)".
    MUSEUMS = (By.XPATH, "//div[contains(@class, 'v-overlay--active')]//a[contains(@class, 'v-list-item')]"
                         "[not(@id='sign-in-another')]//div[contains(@class, 'v-list-item-title')]")

    @staticmethod
    def museum_item(title: str) -> Locator:
        return (By.XPATH, "//div[contains(@class, 'v-overlay--active')]//div[contains(@class, 'v-list-item-title') "
                          f"and normalize-space()='{title}']")

    def open_page(self, museum: str) -> None:
        self.open(museum)
        self.wait_for(self.PENDING_CARD)

    def museums_in_menu(self) -> list[str]:
        """The museums the museum menu lists (it's opened, read and closed again)."""
        self.click(self.MUSEUM_MENU)
        self.wait_for(self.SIGN_IN_ANOTHER)
        shown = [item.text for item in self.driver.find_elements(*self.MUSEUMS)]
        self.click(self.MUSEUM_MENU)
        self.wait_until_gone(self.SIGN_IN_ANOTHER)
        return shown

    def sign_out(self) -> None:
        self.click(self.SIGN_OUT)
