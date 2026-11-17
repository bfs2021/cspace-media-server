"""The refresh pages added from October 26 to 30, 2026: checks T134 to T148 of the test inventory
(serena-test-inventory.xlsx; docs/testing-checklist.md sections 35, 36, 40 to 46 and 51).

They all act on the Botanical Garden, a reserved museum with no refresh in the dataset (dataset.py), and make its
refreshes themselves as the checklist does, with the fake ETL (`./serena etl`) and the failed-update tool
(`./serena failed-update`), through stack.py. Each builds on the one before:

- T134: Overview, Past refreshes and Manual refresh before any refresh.
- T135 to T137: two updated refreshes and one of 18 rows, which fails on the delta threshold alone; then the ETL job
  again with 3 rows, far past it.
- T138 to T140: the override, with why the change is expected; its alert and audit entry; the Overridden filter. The
  Garden then publishes 3 rows.
- T141 to T143: a failed ETL list update, an admin's retry, and a retry that comes second.
- T144 to T147: Manual refresh: an older ETL list, Apply with override (the Garden publishes 20 rows again), a file
  that isn't an ETL list, and an ETL list made from the simulator.
- T148: the words, on every page.

What stays by hand is in each section of the checklist: how the pills look, VoiceOver and Reduce motion, the requests
a page makes by itself (sections 36 and 38), and Serena's own retry after 10 minutes (section 45, step 5)."""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from serenade.dataset import BOTGARDEN, BOTGARDEN_NAME, media_csid
from serenade.pages.alerts_page import AlertsPage
from serenade.pages.audit_log_page import AuditLogPage
from serenade.pages.lookup_page import LookUpPage
from serenade.pages.overview_page import OverviewPage
from serenade.pages.refreshes_page import RefreshesPage
from serenade.pages.settings_page import SettingsPage
from serenade.pages.sign_in_page import SignInPage
from serenade.stack import etl_list, failed_update, fake_etl, simulator

pytestmark = pytest.mark.usefixtures("built_dataset")

ADMIN = ("admin", "admin")  # the simulator's synthetic account: its password is its username
GIVE_A_REASON = "Give a reason first."
CHOOSE_A_KIND = "Choose why the change is expected."
SAY_MORE = "Say a little more: at least 20 characters (9 so far)."
KINDS = ["First load", "Known bulk change in CollectionSpace", "Testing", "Something else"]
OVERRIDE_REASON = "serenade T138: the Garden republished many images"
RETRY_REASON = "serenade T142: a test retry"
OLDER_REASON = "serenade T144: an older ETL list"
APPLY_REASON = "serenade T145: twenty rows again"
SIMULATOR_REASON = "serenade T147: made from the simulator"
FAILED_ON_THRESHOLD = ("It failed only on the delta threshold: override it {where} if the change is expected, or apply "
                       "another ETL list.")
FAR_PAST = ("Far past the delta threshold. 85% is 17.0 times the threshold: the last ETL list update had 20 rows, "
            "this list has 3. A change this large is usually a first load or the wrong file. Check that the file is "
            "the right one before you override.")

# The refreshes the tests make, by what they are: each test after T135 reads the IDs the earlier ones left here.
made: dict[str, str] = {}


def signed_in(driver: WebDriver, base_url: str) -> RefreshesPage:
    SignInPage(driver, base_url).sign_in(BOTGARDEN_NAME, *ADMIN)
    SignInPage(driver, base_url).wait_for_url(f"/admin/{BOTGARDEN}")
    return RefreshesPage(driver, base_url)


def words(text: str) -> str:
    """A page's text with each run of spaces and line breaks as one space, as it reads."""
    return " ".join(text.split())


def showing(page: RefreshesPage) -> str:
    """Which of All and Overridden is chosen on Past refreshes."""
    return page.text_of((By.XPATH, "//*[@id='refreshes-show']//button[contains(@class, 'v-btn--active')]"))


def retried_until(page: RefreshesPage, refresh_id: str) -> str:
    """Until when Serena retries a failed update by itself, as the pages say it (HH:MM, UTC): 6 hours from its
    failure."""
    until = datetime.fromisoformat(page.refresh(BOTGARDEN, refresh_id)["retry_until"])
    assert timedelta(hours=5, minutes=50) < until - datetime.now(UTC) <= timedelta(hours=6), until
    return until.astimezone(UTC).strftime("%H:%M")


def test_t134_before_any_refresh(driver: WebDriver, base_url: str) -> None:
    """Checklist section 44, step 1; section 46, step 1. The Botanical Garden has had no refresh yet."""
    page = signed_in(driver, base_url)
    overview = OverviewPage(driver, base_url)
    overview.open_page(BOTGARDEN)
    assert overview.text_of(overview.CURRENT_NONE) == "None yet: Serena hasn't had an ETL list update."
    assert overview.text_of(overview.PENDING_NONE) == "None"
    assert "Nothing under way." in overview.text_of(overview.PENDING_CARD)
    page.open(f"{BOTGARDEN}/refreshes")
    page.wait_for_text(page.TABLE, "No refreshes in the last 30 days.")
    page.open(f"{BOTGARDEN}/manual-refresh")
    assert "Current refresh: none yet" in words(page.wait_for_text(page.CURRENT, "none yet").text)
    assert words(page.text_of(page.PENDING)) == "Pending refresh: none."
    assert page.text_of(page.CARD_HEAD) == "Replace with:"
    assert not page.count(page.CHECK), "a check button before an ETL list is chosen"


@pytest.mark.after("test_t134_before_any_refresh")
def test_t135_a_refreshs_state_as_a_pill_and_a_pending_refreshs_steps(driver: WebDriver, base_url: str) -> None:
    """Checklist section 35, steps 1 to 3 (and step 4's rule: a pill's icon is hidden from screen readers, so only
    its words are read out); section 43, steps 1 and 2; section 44, steps 4 and 5. Two ETL refreshes of 20 rows (the
    first is the Garden's first load), then one of 18, which fails on the delta threshold alone."""
    first, within, failed = fake_etl(BOTGARDEN), fake_etl(BOTGARDEN), fake_etl(BOTGARDEN, rows=18)
    assert [r["state"] for r in (first, within, failed)] == ["updated", "updated", "check_failed"]
    made.update(first=first["refresh_id"], within=within["refresh_id"], failed=failed["refresh_id"])
    page = signed_in(driver, base_url)
    # Past refreshes: a red pill with a failure icon, and a green one with none.
    page.open_list(BOTGARDEN)
    label, classes, icons = page.pill(page.pill_of(made["failed"]))
    assert label == "ETL list check failed" and icons == 1, (label, icons)
    assert "refresh-state-failed" in classes and "text-error" in classes, classes
    label, classes, icons = page.pill(page.pill_of(made["within"]))
    assert (label, icons) == ("Updated", 0) and "text-success" in classes, (label, icons, classes)
    # The failed refresh's page: the same pill, the four steps with the third in red, and what an admin can do.
    page.open_refresh(BOTGARDEN, made["failed"])
    label, classes, icons = page.pill(page.STATE)
    assert label == "ETL list check failed" and icons == 1 and "text-error" in classes, (label, icons, classes)
    assert page.steps() == [("Started", "done"), ("ETL list received", "done"), ("ETL list check failed", "bad"),
                            ("Apply the ETL list", "")]
    assert page.text_of(page.FIX) == FAILED_ON_THRESHOLD.format(where="below")
    assert page.text_of(page.WENT_WRONG) == "1 problem in the ETL list"
    assert page.text_of(page.ADMINS_DID_NONE) == "None."
    # An updated refresh's page: no steps, and nothing in either list.
    page.open_refresh(BOTGARDEN, made["within"])
    assert not page.count(page.STEPS), "an updated refresh shows steps"
    assert (page.text_of(page.WENT_WRONG_NONE), page.text_of(page.ADMINS_DID_NONE)) == ("None.", "None.")
    # Overview: the current refresh Serena serves from, and the pending one, which needs an admin.
    overview = OverviewPage(driver, base_url)
    overview.open_page(BOTGARDEN)
    current = words(overview.text_of(overview.CURRENT_CARD))
    assert made["within"] in current and "20 rows" in current, current
    assert page.pill(overview.CURRENT_STATE)[0] == "Updated"
    pending = overview.wait_for(overview.PENDING_CARD)
    assert "needs-admin" in str(pending.get_attribute("class")), "the pending card isn't outlined in red"
    # (The card's label is shown in capitals.)
    assert "pending refresh: needs an admin" in words(pending.text).lower() and made["failed"] in pending.text, \
        pending.text
    label, _, icons = page.pill(overview.PENDING_STATE)
    assert (label, icons) == ("ETL list check failed", 1)
    assert overview.text_of(overview.PENDING_FIX) == FAILED_ON_THRESHOLD.format(where="on its page")


@pytest.mark.after("test_t135_a_refreshs_state_as_a_pill_and_a_pending_refreshs_steps")
def test_t136_how_far_past_the_delta_threshold(driver: WebDriver, base_url: str) -> None:
    """Checklist section 40, steps 1 to 3 and 6. The 18-row list is 2 times past the 5% threshold; then the ETL job
    runs again with 3 rows, 17 times past it: far past, from 10 times."""
    over = (By.CSS_SELECTOR, "#check-counts .delta-over")
    page = signed_in(driver, base_url)
    page.open_refresh(BOTGARDEN, made["failed"])
    assert words(page.text_of(page.CHECK_COUNTS)) == (
        "18 rows; 0 added, 2 removed, 0 changed (10% of the 20 rows of the last ETL list update; 2.0 times the 5% "
        "threshold).")
    assert page.text_of(over) == "10%", "the percent past the threshold isn't marked"
    assert not page.count(page.FAR_PAST), "2 times the threshold isn't far past it"
    page.click(page.OVERRIDE)
    explanation = words(page.text_of(page.OVERRIDE_EXPLANATION))
    assert "this list changes 10% of the rows, 2.0 times the 5% threshold." in explanation, explanation
    assert not page.count(page.DIALOG_FAR_PAST)
    page.click(page.CANCEL)
    page.wait_until_gone(page.CONFIRM)
    # Far past it. The ETL job's next run takes up its pending refresh, or starts another: either way, its refresh.
    far = fake_etl(BOTGARDEN, rows=3)
    assert far["state"] == "check_failed", far["state"]
    made["failed"] = far["refresh_id"]
    page.open_refresh(BOTGARDEN, made["failed"])
    assert words(page.text_of(page.FAR_PAST)) == FAR_PAST
    page.click(page.OVERRIDE)
    assert words(page.text_of(page.DIALOG_FAR_PAST)) == FAR_PAST
    explanation = words(page.text_of(page.OVERRIDE_EXPLANATION))
    assert "85% of the rows, 17.0 times the 5% threshold: far past it." in explanation, explanation
    page.click(page.CANCEL)
    page.wait_until_gone(page.CONFIRM)
    # Within it: the threshold in plain words, nothing marked.
    page.open_refresh(BOTGARDEN, made["within"])
    assert words(page.text_of(page.CHECK_COUNTS)).endswith(
        "(0% of the 20 rows of the last ETL list update; the threshold is 5%).")
    assert not page.count(over) and not page.count(page.FAR_PAST)


@pytest.mark.after("test_t135_a_refreshs_state_as_a_pill_and_a_pending_refreshs_steps")
def test_t137_no_overridden_refreshes_yet(driver: WebDriver, base_url: str) -> None:
    """Checklist section 41, step 1."""
    page = signed_in(driver, base_url)
    page.click(page.MENU_ITEM)
    page.wait_for(page.ROWS)
    assert showing(page) == "All"
    assert page.text_of(page.SHOW_OVERRIDDEN) == "Overridden (0)"
    page.click(page.SHOW_OVERRIDDEN)
    page.wait_for_text(page.TABLE, "No overridden refreshes in the last 30 days.")


@pytest.mark.after("test_t136_how_far_past_the_delta_threshold")
def test_t138_why_the_change_is_expected(driver: WebDriver, base_url: str) -> None:
    """Checklist section 42, steps 1 to 3; section 40, step 4; section 36, steps 1 and 3; section 43, step 3. The
    override's dialog asks why the change is expected and for a reason of 20 characters or more; overridden, the
    page says how far past the threshold the list went, and updates by itself."""
    failed = made["failed"]
    page = signed_in(driver, base_url)
    page.open_refresh(BOTGARDEN, failed)
    page.click(page.OVERRIDE)
    page.wait_for(page.CONFIRM)
    assert "Why is the change expected? (required)" in page.text_of(page.DIALOG_TEXT)
    assert [label.text for label in driver.find_elements(*page.KIND_LABELS)] == KINDS
    assert not any(radio.is_selected() for radio in driver.find_elements(*page.KIND_RADIOS)), "a kind chosen already"
    hint = page.text_of(page.REASON_MESSAGES)
    assert "Required, at least 20 characters: what changed, and how you know it's expected." in hint, hint
    # Nothing chosen, and too short a reason: each says so, focus goes to the first kind, and nothing is sent.
    page.type(page.REASON, "too short")
    page.click(page.CONFIRM)
    page.wait_for_text(page.KIND_MESSAGES, CHOOSE_A_KIND)
    page.wait_for_text(page.REASON_MESSAGES, SAY_MORE)
    assert page.focused_id() == "override-kind-first_load"
    assert page.refresh(BOTGARDEN, failed)["state"] == "check_failed", "overridden without a kind or a reason"
    page.click(page.KIND_BULK_CHANGE)
    WebDriverWait(driver, 10).until(lambda d: CHOOSE_A_KIND not in page.text_of(page.KIND_MESSAGES))
    page.type(page.REASON, OVERRIDE_REASON)
    page.click(page.CONFIRM)
    # The banner: the kind before the reason, and how far past the threshold; the red note under the check goes.
    banner = words(page.wait_for_text(
        page.OVERRIDE_BANNER, f"Reason: Known bulk change in CollectionSpace: {OVERRIDE_REASON}").text)
    assert "The ETL list changes 85% of the rows, 17.0 times the 5% threshold: far past it." in banner, banner
    # It finishes by itself, without a reload: never a green "Updated", never "passed" on its own.
    page.wait_for_text(page.STATE, "Updated by override", timeout=60)
    label, classes, icons = page.pill(page.STATE)
    assert icons == 1 and "refresh-state-overridden" in classes and "text-warning" in classes, (label, classes)
    assert "failed, overridden by admin" in page.text_of(page.CHECK_HEADING)
    assert page.text_of(page.PASSED_WITHOUT_THRESHOLD).startswith(
        "It passed when Serena checked it again without the delta threshold")
    assert not page.count(page.FAR_PAST), "the banner says it: no note under the check"
    assert words(page.text_of(page.OVERRIDE_BANNER)).endswith("and updated from it. The team was emailed.")
    # The reason only in the banner; the problem still under What went wrong.
    assert "1 problem in the ETL list" in page.text_of(page.WENT_WRONG)
    assert OVERRIDE_REASON not in page.text_of(page.WENT_WRONG)
    admins_did = page.text_of(page.ADMINS_DID)
    assert "its reason is in the banner above" in admins_did and OVERRIDE_REASON not in admins_did, admins_did


@pytest.mark.after("test_t138_why_the_change_is_expected")
def test_t139_the_overrides_alert_and_audit_entry(driver: WebDriver, base_url: str) -> None:
    """Checklist section 42, step 4 (the email carries the alert's message; the email itself stays by hand)."""
    reason = f"Reason: Known bulk change in CollectionSpace: {OVERRIDE_REASON}"
    signed_in(driver, base_url)
    alerts = AlertsPage(driver, base_url)
    alerts.open_page(BOTGARDEN)
    alert = words(alerts.wait_for(alerts.row_with("An admin overrode the delta threshold")).text)
    assert made["failed"] in alert and reason in alert, alert
    audit = AuditLogPage(driver, base_url)
    audit.open_page(BOTGARDEN)
    entry = audit.cells(audit.entry("threshold override", OVERRIDE_REASON))
    assert (entry["By"], entry["Target"]) == (ADMIN[0], made["failed"]), entry
    assert reason in words(entry["Details"]) and "Delta percent: 85" in words(entry["Details"]), entry


@pytest.mark.after("test_t138_why_the_change_is_expected")
def test_t140_the_overridden_filter(driver: WebDriver, base_url: str) -> None:
    """Checklist section 41, steps 2 to 4; section 36, step 4 (once it's updated)."""
    overridden = made["failed"]
    page = signed_in(driver, base_url)
    # Overview's current refresh: the orange pill, never a green "Updated".
    overview = OverviewPage(driver, base_url)
    overview.open_page(BOTGARDEN)
    label, classes, _ = page.pill(overview.CURRENT_STATE)
    assert label == "Updated by override" and "text-warning" in classes, (label, classes)
    # From the menu: All, every refresh, the overridden one with its orange bar.
    page.click(page.MENU_ITEM)
    page.wait_for(page.ROWS)
    assert showing(page) == "All" and page.text_of(page.SHOW_OVERRIDDEN) == "Overridden (1)"
    every = page.first_column()
    assert sorted(every) == sorted([made["first"], made["within"], overridden]), every
    assert [row.find_element(By.XPATH, "./td[1]").text for row in driver.find_elements(*page.OVERRIDE_ROWS)] == [
        overridden]
    assert page.pill(page.pill_of(overridden))[0] == "Updated by override"
    # Overridden: only that one, in the address, through a reload.
    page.click(page.SHOW_OVERRIDDEN)
    page.wait_for_count(page.ROWS, 1)
    page.wait_for_address("show=overridden")
    assert page.first_column() == [overridden]
    driver.refresh()
    page.wait_for(page.ROWS)
    assert showing(page) == "Overridden (1)" and page.first_column() == [overridden]
    # Through the refresh's page and the browser's Back; the menu opens All again.
    page.click((By.XPATH, f"{page.row_of(overridden)[1]}//a"))
    page.wait_for(page.STATE)
    driver.back()
    page.wait_for_address("show=overridden")
    page.wait_for_count(page.ROWS, 1)
    assert showing(page) == "Overridden (1)"
    page.click(page.MENU_ITEM)
    page.wait_for_count(page.ROWS, len(every))
    assert showing(page) == "All" and "show=overridden" not in driver.current_url


@pytest.mark.after("test_t138_why_the_change_is_expected")
def test_t141_a_failed_etl_list_update(driver: WebDriver, base_url: str) -> None:
    """Checklist section 45, steps 1 and 2; section 42, step 6 (a retry's reason is a plain one). An update can't be
    made to fail on the local stack, so the failed-update tool records one, repeating the last updated ETL list."""
    made["update_failed"] = failed = failed_update(BOTGARDEN)
    page = signed_in(driver, base_url)
    until = retried_until(page, failed)
    retries = f"Serena tries the update again every 10 minutes, until {until} UTC."
    fix = f"Serena serves some of each ETL list. {retries} Retry the ETL list update {{where}} to try now, or apply " \
          "another ETL list."
    # Overview: the current refresh partly replaced, and the pending one, which needs an admin.
    overview = OverviewPage(driver, base_url)
    overview.open_page(BOTGARDEN)
    partly = overview.wait_for(overview.PARTLY_REPLACED)
    assert partly.text == "partly replaced" and "text-warning" in str(partly.get_attribute("class"))
    assert made["failed"] in overview.text_of(overview.CURRENT_CARD), "the current refresh isn't the last updated one"
    assert words(overview.text_of(overview.PARTLY_REPLACED_DETAIL)) == (
        f"{failed}'s update stopped partway, so Serena serves some of each ETL list, never a file either one "
        f"restricts or drops. {retries}")
    pending = overview.wait_for(overview.PENDING_CARD)
    assert "needs-admin" in str(pending.get_attribute("class")) and failed in pending.text
    label, _, icons = page.pill(overview.PENDING_STATE)
    assert (label, icons) == ("ETL list update failed", 1)
    assert overview.text_of(overview.PENDING_FIX) == fix.format(where="on its page")
    # Its page: the four steps, the last in red, and the same words with "below".
    page.open_refresh(BOTGARDEN, failed)
    assert page.steps() == [("Started", "done"), ("ETL list received", "done"), ("ETL list checked", "done"),
                            ("ETL list update failed", "bad")]
    assert page.text_of(page.FIX) == fix.format(where="below")
    # The dialog: what a retry does, and that Serena also retries by itself; a plain reason, with no kinds.
    page.click(page.RETRY)
    page.wait_for(page.CONFIRM)
    dialog = words(page.text_of(page.DIALOG_TEXT))
    assert "Serena runs the ETL list update again now, doing only what's left." in dialog, dialog
    assert f"Serena also tries again by itself every 10 minutes until {until} UTC." in dialog, dialog
    assert not page.count(page.KIND_LABELS), "a retry asks why the change is expected"
    assert "at least" not in page.text_of(page.REASON_MESSAGES), "a retry's reason has a minimum"
    page.click(page.CANCEL)
    page.wait_until_gone(page.CONFIRM)


@pytest.mark.after("test_t141_a_failed_etl_list_update")
def test_t142_retrying_a_failed_update(driver: WebDriver, base_url: str) -> None:
    """Checklist section 45, step 3."""
    failed = made["update_failed"]
    page = signed_in(driver, base_url)
    page.open_refresh(BOTGARDEN, failed)
    page.click(page.RETRY)
    page.click(page.CONFIRM)
    page.wait_for_text(page.REASON_MESSAGES, GIVE_A_REASON)
    assert page.refresh(BOTGARDEN, failed)["state"] == "update_failed", "retried without a reason"
    page.type(page.REASON, RETRY_REASON)
    page.click(page.CONFIRM)
    page.wait_for_text(page.STATE, "Updated", timeout=60)  # by itself, without a reload
    assert page.text_of(page.ADMINS_DID) == f"ETL list update retried by {ADMIN[0]}: {RETRY_REASON}"
    assert not page.count(page.RETRY) and not page.count(page.STEPS)
    # Overview: the retried refresh is the current one, whole; nothing pending.
    overview = OverviewPage(driver, base_url)
    overview.open_page(BOTGARDEN)
    assert failed in overview.text_of(overview.CURRENT_CARD)
    assert not overview.count(overview.PARTLY_REPLACED), "still partly replaced"
    assert overview.text_of(overview.PENDING_NONE) == "None"
    audit = AuditLogPage(driver, base_url)
    audit.open_page(BOTGARDEN)
    entry = audit.cells(audit.entry("update retry", RETRY_REASON))
    assert (entry["By"], entry["Target"]) == (ADMIN[0], failed), entry


@pytest.mark.after("test_t142_retrying_a_failed_update")
def test_t143_a_retry_that_comes_second(driver: WebDriver, second_driver: WebDriver, base_url: str) -> None:
    """Checklist section 45, step 4. Two browsers with the failed refresh open: the second's retry is refused, saying
    who retried it first, and its page shows the refresh as it is, with no Retry button."""
    failed = failed_update(BOTGARDEN)
    first, second = signed_in(driver, base_url), signed_in(second_driver, base_url)
    for page in (first, second):
        page.open_refresh(BOTGARDEN, failed)
        page.wait_for(page.RETRY)
    first.click(first.RETRY)
    first.type(first.REASON, "serenade T143: the first retry")
    first.click(first.CONFIRM)
    first.wait_for_text(first.STATE, "Updated", timeout=60)
    second.click(second.RETRY)
    second.type(second.REASON, "serenade T143: the second retry")
    second.click(second.CONFIRM)
    refused = second.wait_for(second.ERROR).text
    assert re.fullmatch(rf"Not retried: {ADMIN[0]} retried it first, and (Serena is applying the ETL list now|it is "
                        r"updated now)\. This page shows the refresh as it is\.", words(refused)), refused
    second.wait_for_text(second.STATE, "Updated", timeout=60)
    assert not second.count(second.RETRY), "the page still offers a retry"
    retries = [e for e in AuditLogPage(driver, base_url).entries(BOTGARDEN)
               if e["action"] == "update_retry" and e["target"] == failed]
    assert len(retries) == 1, f"{len(retries)} retries in the audit log, not one"


@pytest.mark.after("test_t142_retrying_a_failed_update")
def test_t144_an_older_etl_list_is_checked_then_confirmed(driver: WebDriver, base_url: str) -> None:
    """Checklist section 46, steps 1 to 4. The Garden publishes 3 rows; an older 3-row list is chosen from the
    previous ETL lists: a dry run changes nothing, and Apply warns, asks for a reason and asks again."""
    page = signed_in(driver, base_url)
    audit = AuditLogPage(driver, base_url)
    page.open(f"{BOTGARDEN}/manual-refresh")
    current = words(page.wait_for_text(page.CURRENT, "Serena serves from it").text)
    assert current.startswith("Current refresh:") and "3 rows" in current, current
    assert words(page.text_of(page.PENDING)) == "Pending refresh: none."
    assert not page.count(page.CHECK) and not page.count(page.PICKS), "a list or a check before a choice"
    before = len(page.refreshes(BOTGARDEN)), len(audit.entries(BOTGARDEN))
    # Choose from previous: the check shows only once a list is picked, and the top card says which.
    page.click(page.SOURCE_ETL)
    page.wait_for(page.LISTS)
    assert "none yet" in page.text_of(page.CHOSEN) and not page.count(page.CHECK)
    older = next(n for n, rows in enumerate(page.list_rows(), start=1) if n > 1 and rows == "3")
    page.pick_list(older)
    assert "3 rows, from" in words(page.wait_for_text(page.CHOSEN, "the one for").text)
    # The dry run: passed, nothing changed, nothing new on Past refreshes or in the Audit log.
    page.click(page.CHECK)
    page.wait_for_text(page.DRY_HEAD, "The dry run passed", timeout=30)
    assert "Nothing has changed." in page.text_of(page.DRY)
    assert (len(page.refreshes(BOTGARDEN)), len(audit.entries(BOTGARDEN))) == before, "the dry run was recorded"
    page.wait_until_gone(page.pick(older))  # the bottom card folds away
    # Another list: the result goes, and the check shows again.
    page.pick_list(1)
    page.wait_until_gone(page.DRY)
    page.wait_for(page.CHECK)
    page.pick_list(older)
    page.click(page.CHECK)
    page.wait_for_text(page.DRY_HEAD, "The dry run passed", timeout=30)
    # Apply: the older-list warning, a reason, then a confirmation.
    assert page.text_of(page.OLDER).startswith("This isn't the newest ETL list.")
    page.click(page.APPLY)
    page.wait_for_text(page.REASON_MESSAGES, GIVE_A_REASON)
    page.type(page.REASON, OLDER_REASON)
    page.click(page.APPLY)
    assert "Apply an older ETL list?" in page.wait_for(page.CONFIRM_DIALOG).text
    assert len(page.refreshes(BOTGARDEN)) == before[0], "applied before the confirmation"
    page.click(page.MANUAL_CONFIRM)
    applied = words(page.wait_for_text(page.APPLIED, "started", timeout=60).text)
    assert f"Reason: {OLDER_REASON}." in applied and "Past refreshes" in applied, applied
    started = page.text_of(page.APPLIED_LINK)
    assert driver.current_url.endswith(f"/{BOTGARDEN}/manual-refresh"), "the summary is on the page"
    # "Replace with another ETL list" starts over.
    page.click(page.AGAIN)
    page.wait_for(page.CARD_HEAD)
    assert not page.count(page.APPLIED)
    # It checks and updates by itself; Past refreshes says where its list came from.
    page.wait_for_state(BOTGARDEN, started, "Updated")
    assert not page.count(page.RETRY) and not page.count(page.OVERRIDE)
    page.open_list(BOTGARDEN)
    assert "manual refresh · ETL list" in page.cells(page.row_of(started))["Refresh date"]


@pytest.mark.after("test_t142_retrying_a_failed_update")
def test_t145_apply_with_override(driver: WebDriver, base_url: str, tmp_path: Path) -> None:
    """Checklist section 46, step 6; section 42, step 5; section 40, step 5. A 20-row list uploaded while the Garden
    publishes 3: the dry run fails only on the delta threshold, far past it, and Apply with override asks why the
    change is expected, as the override on a refresh's page does. The Garden then publishes 20 rows again."""
    twenty = tmp_path / "botgarden-20.tsv"
    twenty.write_text(etl_list(BOTGARDEN))
    page = signed_in(driver, base_url)
    before = len(page.refreshes(BOTGARDEN))
    page.open(f"{BOTGARDEN}/manual-refresh")
    page.click(page.SOURCE_UPLOAD)
    page.choose_file(page.FILE, str(twenty))
    page.click(page.CHECK)
    page.wait_for_text(page.DRY_HEAD, "The dry run failed only on the delta threshold", timeout=30)
    assert words(page.text_of(page.MANUAL_FAR_PAST)).startswith("Far past the delta threshold.")
    apply = page.wait_for(page.APPLY)
    assert apply.text == "Apply with override" and "bg-error" in str(apply.get_attribute("class")), apply.text
    assert [label.text for label in driver.find_elements(*page.KIND_LABELS)] == KINDS
    # Without a kind, a reason or the live public core's confirmation: each says so.
    page.click(page.APPLY)
    page.wait_for_text(page.KIND_MESSAGES, CHOOSE_A_KIND)
    page.wait_for_text(page.MANUAL_REASON_MESSAGES, GIVE_A_REASON)
    page.wait_for_text(page.CONFIRM_MESSAGES, "Confirm the ETL list was made from the live public core.")
    page.click(page.KIND_TESTING)
    page.click(page.CONFIRM_LIVE_CORE)
    page.type(page.MANUAL_REASON, "too short")
    page.click(page.APPLY)
    page.wait_for_text(page.MANUAL_REASON_MESSAGES, SAY_MORE)
    assert len(page.refreshes(BOTGARDEN)) == before, "applied with too short a reason"
    page.type(page.MANUAL_REASON, APPLY_REASON)
    page.click(page.APPLY)
    applied = words(page.wait_for_text(page.APPLIED, "started", timeout=60).text)
    assert f"Reason: Testing: {APPLY_REASON} (the delta threshold is overridden for it, and the team was emailed)." \
        in applied, applied
    started = page.text_of(page.APPLIED_LINK)
    page.wait_for_state(BOTGARDEN, started, "Updated by override")
    assert f"Reason: Testing: {APPLY_REASON}" in words(page.text_of(page.OVERRIDE_BANNER))
    page.open_list(BOTGARDEN)
    assert "manual refresh · uploaded list" in page.cells(page.row_of(started))["Refresh date"]
    alerts = AlertsPage(driver, base_url)
    alerts.open_page(BOTGARDEN)
    assert "An admin overrode the delta threshold" in alerts.wait_for(alerts.row_with(started)).text


@pytest.mark.after("test_t135_a_refreshs_state_as_a_pill_and_a_pending_refreshs_steps")
def test_t146_a_file_that_isnt_an_etl_list(driver: WebDriver, base_url: str, tmp_path: Path) -> None:
    """Checklist section 46, step 7. Its problems can't be overridden: a table of them, no Apply, and Cancel goes
    back to "Replace with:"."""
    other = tmp_path / "not-an-etl-list.tsv"
    other.write_text("serenade T146\nthis file isn't an ETL list\n")
    page = signed_in(driver, base_url)
    before = len(page.refreshes(BOTGARDEN))
    page.open(f"{BOTGARDEN}/manual-refresh")
    page.click(page.SOURCE_UPLOAD)
    page.choose_file(page.FILE, str(other))
    page.click(page.CHECK)
    head = page.wait_for_text(page.DRY_HEAD, "The dry run found", timeout=30).text
    assert re.fullmatch(r"The dry run found \d+ problems?", head), head
    assert page.wait_for(page.PROBLEMS).find_elements(By.CSS_SELECTOR, "tbody tr"), "no problem listed"
    assert "These problems can't be overridden." in page.text_of(page.DRY)
    assert not page.count(page.APPLY), "a file with problems can be applied"
    page.click(page.MANUAL_CANCEL)
    page.wait_until_gone(page.DRY)
    assert page.text_of(page.CARD_HEAD) == "Replace with:" and not page.count(page.CHOSEN)
    assert len(page.refreshes(BOTGARDEN)) == before


@pytest.mark.after("test_t145_apply_with_override")
def test_t147_an_etl_list_made_from_the_simulator(driver: WebDriver, base_url: str) -> None:
    """Checklist section 51, steps 1 to 4. The Garden's 20 records in the simulator, listed as the ETL would; one
    soft-deleted meanwhile is counted but not listed, and put back."""
    def made_list() -> tuple[int, int, str]:
        text = page.text_of(page.SIMULATOR_MADE)
        found = re.fullmatch(r"(\d+) rows from (\d+) records(?:; not listed: (.+))?\.", words(text))
        assert found, text
        return int(found[1]), int(found[2]), found[3] or ""

    page = signed_in(driver, base_url)
    page.open(f"{BOTGARDEN}/manual-refresh")
    page.click(page.SOURCE_SIMULATOR)
    assert page.text_of(page.SIMULATOR_MAKE) == "Make the ETL list"
    assert not page.count(page.CHECK), "a check button before the ETL list is made"
    page.click(page.SIMULATOR_MAKE)
    assert made_list() == (20, 20, "")
    chosen = words(page.text_of(page.CHOSEN))
    assert "made from the simulator" in chosen and f"simulator-{BOTGARDEN}-" in chosen, chosen
    # What's left out: a soft-deleted record, one row fewer.
    record = media_csid(BOTGARDEN, 0)
    simulator("POST", f"/{BOTGARDEN}/_fake/delete/{record}")
    try:
        assert page.text_of(page.SIMULATOR_MAKE) == "Make it again"
        page.click(page.SIMULATOR_MAKE)
        page.wait_for_text(page.SIMULATOR_MADE, "not listed")
        assert made_list() == (19, 20, "1 soft-deleted")
    finally:
        simulator("POST", f"/{BOTGARDEN}/_fake/undelete/{record}")
    page.click(page.SIMULATOR_MAKE)
    page.wait_for_text(page.SIMULATOR_MADE, "20 rows")
    # Check and apply, with no live public core to confirm.
    page.click(page.CHECK)
    page.wait_for_text(page.DRY_HEAD, "The dry run passed", timeout=30)
    assert not driver.find_elements(By.ID, "confirm-live-core"), "it asks to confirm the live public core"
    page.type(page.REASON, SIMULATOR_REASON)
    page.click(page.APPLY)
    applied = words(page.wait_for_text(page.APPLIED, "started", timeout=60).text)
    assert "made from the simulator" in applied, applied
    started = page.text_of(page.APPLIED_LINK)
    page.wait_for_state(BOTGARDEN, started, "Updated")
    assert f"made from the simulator: {SIMULATOR_REASON}" in page.text_of(page.ADMINS_DID)


@pytest.mark.after("test_t138_why_the_change_is_expected")
def test_t148_the_words_etl_list_on_every_page(driver: WebDriver, base_url: str) -> None:
    """Checklist section 44, step 6. No page says "servable list" or "servability update" (October 28, 2026): on
    Alerts, neither the failed check's alert nor the override's."""
    page = signed_in(driver, base_url)
    look_up, settings, alerts = (LookUpPage(driver, base_url), SettingsPage(driver, base_url),
                                 AlertsPage(driver, base_url))

    def looked_up() -> None:
        look_up.look_up(BOTGARDEN, media_csid(BOTGARDEN, 0))
        look_up.wait_for_answer(media_csid(BOTGARDEN, 0))

    def manual_refresh() -> None:
        page.open(f"{BOTGARDEN}/manual-refresh")
        page.wait_for_text(page.CURRENT, "Serena serves from it")

    pages = {
        "Overview": (lambda: OverviewPage(driver, base_url).open_page(BOTGARDEN), ""),
        "Past refreshes": (lambda: page.open_list(BOTGARDEN), "ETL list"),
        "a refresh's page": (lambda: page.open_refresh(BOTGARDEN, made["failed"]), "ETL list check"),
        "Settings": (lambda: settings.open_page(BOTGARDEN), "ETL list check"),
        "Media look up": (looked_up, "ETL list"),
        "Alerts": (lambda: alerts.open_page(BOTGARDEN), "An ETL list check failed"),
        "Manual refresh": (manual_refresh, "ETL list"),
    }
    for name, (open_it, expected) in pages.items():
        open_it()
        text = words(page.text_of((By.TAG_NAME, "main")))
        assert expected in text, f"{name} doesn't say {expected!r}"
        for old in ("servable list", "servability"):
            assert old not in text.lower(), f"{name} says {old!r}"
