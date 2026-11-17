"""Past refreshes, a refresh's page and Manual refresh (design: Admin web app; Refreshes)."""
from __future__ import annotations

import json
import time
from typing import Any

from selenium.webdriver.common.by import By

from .page import DIALOG, Locator, Page, by_id, dialog_button, messages_of

API = "/admin/v1/museums"


class RefreshesPage(Page):
    TITLE = by_id("page-title")
    # Past refreshes.
    TABLE = by_id("refreshes-table")
    ROWS = (By.XPATH, "//*[@id='refreshes-table']//tbody/tr[contains(@class, 'v-data-table__tr')]")  # not "Loading"
    PER_PAGE = (By.XPATH, "//*[@id='refreshes-table']//div[contains(@class, 'v-data-table-footer__items-per-page')]"
                          "//div[contains(concat(' ', normalize-space(@class), ' '), ' v-field ')]")
    # All or only the overridden refreshes (issue #120), and an overridden refresh's row, with its orange bar.
    SHOW_ALL = by_id("refreshes-show-all")
    SHOW_OVERRIDDEN = by_id("refreshes-show-overridden")
    OVERRIDE_ROWS = (By.XPATH, "//*[@id='refreshes-table']//tbody/tr[contains(concat(' ', @class, ' '), "
                               "' override-row ')]")
    MENU_ITEM = by_id("nav-refreshes")  # "Past refreshes" in the menu
    # A refresh's page.
    STATE = by_id("refresh-state")
    STEPS = (By.XPATH, "//*[@id='refresh-steps']/li")  # a pending refresh's four steps (mockup version 55)
    FIX = by_id("refresh-fix")  # what an admin can do about a pending refresh that needs one
    # Issue #120: a refresh's reasons in two lists.
    WENT_WRONG = by_id("refresh-problems")
    ADMINS_DID = by_id("refresh-admin-actions")
    CHECK_PROBLEMS = by_id("check-problems")
    WENT_WRONG_NONE = by_id("refresh-problems-none")
    ADMINS_DID_NONE = by_id("refresh-admin-actions-none")
    CHECK_COUNTS = by_id("check-counts")
    FAR_PAST = by_id("check-far-past")  # issue #120: from 10 times the delta threshold, a red note under the check
    PASSED_WITHOUT_THRESHOLD = by_id("check-passed-without-threshold")
    ERROR = (By.XPATH, "//div[contains(@class, 'v-alert') and contains(@class, 'bg-error')]")  # an action refused
    RETRY = by_id("retry-update")
    # The dialog of Override the delta threshold, or of Retry the ETL list update.
    DIALOG_TEXT = (By.XPATH, f"{DIALOG}//div[contains(@class, 'v-card-text')]")
    OVERRIDE_EXPLANATION = by_id("override-explanation")
    DIALOG_FAR_PAST = by_id("override-far-past")
    KIND_LABELS = (By.XPATH, "//label[starts-with(@for, 'override-kind-')]")  # why the change is expected
    KIND_RADIOS = (By.XPATH, "//input[starts-with(@id, 'override-kind-') and @type='radio']")
    OVERRIDE_BANNER = by_id("override-banner")  # issue #108: who overrode the delta threshold, when and why
    CHECK_OVERRIDDEN = by_id("check-overridden")  # only when a re-check fails on something else (issue #110)
    CHECK_HEADING = by_id("check-heading")  # issue #110: "failed, overridden by admin" after an override
    OVERRIDE = by_id("override-threshold")
    CONFIRM = by_id("confirm-action")
    REASON = by_id("reason")  # the action's reason (ReasonField's own id)
    REASON_MESSAGES = messages_of("reason")
    # Issue #120: an override says why the change is expected (a kind) before its reason.
    KIND_TESTING = (By.XPATH, "//input[@id='override-kind-testing']"
                              "/ancestor::div[contains(@class, 'v-selection-control')][1]")
    KIND_MESSAGES = messages_of("override-kind-first_load")
    KIND_BULK_CHANGE = (By.XPATH, "//input[@id='override-kind-bulk_change']"
                                  "/ancestor::div[contains(@class, 'v-selection-control')][1]")
    CANCEL = dialog_button("Cancel")
    # Manual refresh (issue #118; mockup version 55): "Replace with:", a dry run, then Apply and its summary.
    SOURCE_ETL = (By.XPATH, "//input[@id='source-etl']/ancestor::div[contains(@class, 'v-selection-control')][1]")
    SOURCE_UPLOAD = (By.XPATH, "//input[@id='source-upload']/ancestor::div[contains(@class, 'v-selection-control')][1]")
    CHECK = by_id("manual-check")  # the dry run: shown once an ETL list is chosen
    DRY_HEAD = by_id("manual-dry-head")
    APPLY = by_id("manual-apply")
    MANUAL_CONFIRM = by_id("manual-confirm")  # stopping the pending refresh, or applying an older list
    APPLIED = by_id("manual-applied")
    FILE = by_id("file")
    CONFIRM_LIVE_CORE = (By.XPATH, "//input[@id='confirm-live-core']/ancestor::div[contains(@class, "
                                   "'v-selection-control')][1]")
    CONFIRM_MESSAGES = messages_of("confirm-live-core")
    CURRENT = by_id("manual-current")  # the top card's current and pending refreshes
    PENDING = by_id("manual-pending")
    CARD_HEAD = by_id("manual-card-head")  # "Replace with:"
    CHOSEN = by_id("manual-chosen")  # "The ETL list: …", once a source is chosen
    LISTS = by_id("manual-lists")  # the previous ETL lists, newest first
    PICKS = (By.CSS_SELECTOR, "input[name='manual-pick']")
    PICKER_TITLE = (By.CSS_SELECTOR, "#manual-picker .v-expansion-panel-title")  # opens the bottom card again
    APPLIED_LINK = (By.XPATH, "//*[@id='manual-applied-head']//a")  # the refresh Apply started
    DRY = by_id("manual-dry")
    OLDER = by_id("manual-older")  # the warning that the ETL list chosen isn't the newest
    CONFIRM_DIALOG = by_id("manual-confirm-dialog")
    AGAIN = by_id("manual-again")  # "Replace with another ETL list"
    MANUAL_FAR_PAST = by_id("manual-far-past")
    MANUAL_REASON = by_id("manual-override-reason")  # Apply with override's reason, under its kinds
    MANUAL_REASON_MESSAGES = messages_of("manual-override-reason")
    PROBLEMS = by_id("manual-problems")  # a dry run's problems that can't be overridden
    MANUAL_CANCEL = by_id("manual-cancel")
    # "Make one from the simulator" (mockup version 57), only where every museum's CollectionSpace is the simulator.
    SOURCE_SIMULATOR = (By.XPATH, "//input[@id='source-simulator']/ancestor::div[contains(@class, "
                                  "'v-selection-control')][1]")
    SIMULATOR_MAKE = by_id("simulator-make")
    SIMULATOR_MADE = by_id("simulator-made")

    COLUMNS = ("Refresh", "Refresh date", "State", "Rows", "Last change")

    @staticmethod
    def row_of(refresh_id: str) -> Locator:
        return (By.XPATH, f"//*[@id='refreshes-table']//tbody/tr[td[1][normalize-space()='{refresh_id}']]")

    @staticmethod
    def header(title: str) -> Locator:
        return (By.XPATH, f"//*[@id='refreshes-table']//thead//th[.//span[normalize-space()='{title}']]")

    @staticmethod
    def pill_of(refresh_id: str) -> Locator:
        """A refresh's state pill in its row on Past refreshes."""
        return (By.XPATH, f"//*[@id='refreshes-table']//tbody/tr[td[1][normalize-space()='{refresh_id}']]"
                          "//*[contains(concat(' ', @class, ' '), ' refresh-state ')]")

    @staticmethod
    def pick(n: int) -> Locator:
        """The nth of Manual refresh's previous ETL lists, from 1, the newest."""
        return (By.CSS_SELECTOR, f"#manual-lists tbody tr:nth-child({n}) input[name='manual-pick']")

    def pick_list(self, n: int) -> None:
        """Picks the nth previous ETL list, opening the bottom card again first if it's folded away (after a dry
        run)."""
        picks = self.driver.find_elements(*self.pick(n))
        if not picks or not picks[0].is_displayed():
            self.click(self.PICKER_TITLE)
        self.click(self.pick(n))

    def list_rows(self) -> list[str]:
        """The Rows column of Manual refresh's previous ETL lists, in their order."""
        return [td.text for td in self.driver.find_elements(By.CSS_SELECTOR, "#manual-lists tbody tr td:nth-child(4)")]

    def pill(self, locator: Locator) -> tuple[str, str, int]:
        """A state pill (issue #107): its words, its classes (its colour, and whether it failed or was overridden)
        and how many icons it has. An icon only repeats the words, so it must be hidden from screen readers."""
        element = self.wait_for(locator)
        icons = element.find_elements(By.CSS_SELECTOR, ".refresh-state-icon")
        if not all(icon.get_attribute("aria-hidden") == "true" for icon in icons):
            raise AssertionError(f"The pill {element.text!r} has an icon a screen reader would read out")
        return element.text, str(element.get_attribute("class")), len(icons)

    def steps(self) -> list[tuple[str, str]]:
        """A pending refresh's four steps: each one's words and its class ("done", "now", "bad" or "")."""
        return [(li.text, str(li.get_attribute("class"))) for li in self.driver.find_elements(*self.STEPS)]

    def cells(self, row: Locator) -> dict[str, str]:
        tds = self.wait_for(row).find_elements(By.TAG_NAME, "td")
        return {name: td.text for name, td in zip(self.COLUMNS, tds, strict=False)}

    def first_column(self) -> list[str]:
        return [td.text for td in self.driver.find_elements(By.XPATH, "//*[@id='refreshes-table']//tbody/tr/td[1]")]

    def open_list(self, museum: str) -> None:
        self.open(f"{museum}/refreshes")
        self.wait_for(self.TABLE)
        self.wait_for(self.ROWS)

    def open_refresh(self, museum: str, refresh_id: str) -> None:
        self.open(f"{museum}/refreshes/{refresh_id}")
        self.wait_for(self.STATE)

    def wait_for_state(self, museum: str, refresh_id: str, state: str, seconds: float = 60) -> None:
        """Opens the refresh's page again until it shows the state: the worker checks and updates on its own, and the
        page shows a refresh as it was when it opened."""
        deadline = time.monotonic() + seconds
        while True:
            self.open_refresh(museum, refresh_id)
            if self.text_of(self.STATE) == state or time.monotonic() > deadline:
                if self.text_of(self.STATE) != state:
                    raise AssertionError(f"{refresh_id} is {self.text_of(self.STATE)!r}, not {state!r}")
                return
            time.sleep(1)

    # The admin API, with the browser's session: for setting up refreshes a test needs before it looks.

    def refreshes(self, museum: str) -> list[dict[str, Any]]:
        status, text = self.call_api("GET", f"{API}/{museum}/refreshes")
        _expect(status, 200, text)
        found: list[dict[str, Any]] = json.loads(text)["refreshes"]
        return found

    def refresh(self, museum: str, refresh_id: str) -> dict[str, Any]:
        status, text = self.call_api("GET", f"{API}/{museum}/refreshes/{refresh_id}")
        _expect(status, 200, text)
        found: dict[str, Any] = json.loads(text)
        return found

    def admin_refresh(self, museum: str, servable_list: str, reason: str, seconds: float = 60) -> dict[str, Any]:
        """Applies an uploaded ETL list, as Manual refresh's Apply does, replacing the museum's pending refresh if
        there is one, and waits until the worker has checked it and, on a pass, updated. Returns the refresh."""
        status, text = self.call_api("GET", f"{API}/{museum}/status")
        _expect(status, 200, text)
        pending = json.loads(text)["pending"]
        open_refresh = pending["refresh_id"] if pending else ""
        status, text = self.call_api("POST", f"{API}/{museum}/refreshes", servable_list, {
            "X-Live-Core-Confirmed": "yes", "X-File-Name": "serenade.tsv", "X-Reason": reason,
            "X-Open-Refresh": open_refresh})
        _expect(status, 201, text)
        refresh_id = json.loads(text)["refresh_id"]
        return self._settled(museum, refresh_id, seconds)

    def _settled(self, museum: str, refresh_id: str, seconds: float) -> dict[str, Any]:
        deadline = time.monotonic() + seconds
        while (found := self.refresh(museum, refresh_id))["state"] in ("started", "received", "checking", "updating"):
            if time.monotonic() > deadline:
                raise AssertionError(f"{refresh_id} is still {found['state']}")
            time.sleep(0.5)
        return found


def _expect(status: int, expected: int, text: str) -> None:
    if status != expected:
        raise AssertionError(f"The admin API answered {status}, not {expected}: {text[:300]}")
