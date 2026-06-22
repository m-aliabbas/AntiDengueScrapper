import os
import time
import re
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    UnexpectedAlertPresentException,
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)


# ----------------------------
# Config
# ----------------------------
BASE_URL = "https://dashboard-tracking.punjab.gov.pk/"
REPORT_URL = "https://dashboard-tracking.punjab.gov.pk/user_wise_larva_report"

USERNAME = "sed.chk"
PASSWORD = "chakwal@951"

DISTRICT_TEXT = "Chakwal"
DATE_RANGE_TEXT_CONTAINS = "today"

DORMANT_TILE_ID = "tile-dormant-users"


# ----------------------------
# Helpers
# ----------------------------
def extract_numbers_and_calculate(text: str):
    nums = re.findall(r"\d+", text)
    if len(nums) >= 2:
        return int(nums[0]) + int(nums[1])
    return None


def setup_driver(download_dir: str, headless: bool = False) -> webdriver.Chrome:
    download_dir = os.path.abspath(download_dir)
    os.makedirs(download_dir, exist_ok=True)

    options = webdriver.ChromeOptions()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--window-size=1400,900")

    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_setting_values.automatic_downloads": 1,
    }

    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)

    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": download_dir,
            },
        )
    except Exception:
        pass

    print("OK: Forced download dir:", download_dir)
    return driver


def wait_page_ready(driver, timeout: int = 30):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def accept_alert_if_present(driver) -> str | None:
    try:
        alert = driver.switch_to.alert
        text = alert.text
        alert.accept()
        return text
    except Exception:
        return None


def safe_js_click(driver, wait: WebDriverWait, by, locator: str, timeout: int = 30):
    el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, locator))
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.7)
    driver.execute_script("arguments[0].click();", el)
    return el


def normal_click(driver, wait: WebDriverWait, by, locator: str, timeout: int = 30):
    el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, locator))
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.5)
    el.click()
    return el


def print_select_options(select_el, label: str):
    try:
        sel = Select(select_el)
        print(f"Available options for {label}:")

        for opt in sel.options:
            txt = opt.text.strip()
            val = opt.get_attribute("value")
            print(f" - text='{txt}', value='{val}'")

    except Exception as e:
        print(f"Warning: Could not print options for {label}: {e}")


def select_by_exact_or_contains(wait: WebDriverWait, by, locator: str, wanted_text: str):
    el = wait.until(EC.presence_of_element_located((by, locator)))
    sel = Select(el)

    wanted_clean = wanted_text.strip().lower()

    print_select_options(el, locator)

    for opt in sel.options:
        option_text = opt.text.strip()
        if option_text.lower() == wanted_clean:
            sel.select_by_visible_text(option_text)
            print(f"OK: Selected exact option: {option_text}")
            return

    for opt in sel.options:
        option_text = opt.text.strip()
        if wanted_clean in option_text.lower():
            sel.select_by_visible_text(option_text)
            print(f"OK: Selected contains option: {option_text}")
            return

    for opt in sel.options:
        option_value = str(opt.get_attribute("value") or "").strip()
        if wanted_clean in option_value.lower():
            sel.select_by_value(option_value)
            print(
                f"OK: Selected by value: text='{opt.text.strip()}', value='{option_value}'"
            )
            return

    raise NoSuchElementException(
        f"Could not find option containing text/value: {wanted_text}"
    )


def clean_old_downloads(download_dir: str):
    d = Path(download_dir)
    d.mkdir(parents=True, exist_ok=True)

    print("Cleaning old XLS/CSV files from downloads directory...")

    cleaned_count = 0

    patterns = [
        "*.xls",
        "*.xlsx",
        "*.csv",
        "*.XLS",
        "*.XLSX",
        "*.CSV",
        "*.crdownload",
    ]

    for pattern in patterns:
        for old_file in d.glob(pattern):
            try:
                print(f"Removing: {old_file.name}")
                old_file.unlink()
                cleaned_count += 1
            except Exception as e:
                print(f"Warning: Could not remove {old_file.name}: {e}")

    print(f"Cleaned {cleaned_count} file(s)")


def wait_for_download(download_dir: str, start_ts: float, timeout: int = 180) -> str | None:
    d = Path(download_dir).resolve()
    exts = {".xls", ".xlsx", ".csv"}

    print("Waiting for download to complete...")

    end_time = time.time() + timeout

    while time.time() < end_time:
        candidates = []

        for p in d.iterdir():
            if not p.is_file():
                continue

            name_lower = p.name.lower()

            if name_lower.endswith(".crdownload"):
                continue

            if p.suffix.lower() not in exts:
                continue

            try:
                file_mtime = p.stat().st_mtime
                file_size = p.stat().st_size

                if file_mtime >= start_ts and file_size > 0:
                    candidates.append(p)

            except Exception as e:
                print(f"Warning: Error checking file {p.name}: {e}")

        if candidates:
            candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            newest = candidates[0]
            print(f"OK: Download found: {newest.name}")
            return str(newest.resolve())

        time.sleep(1)

    print("Error: No valid .xls/.xlsx/.csv file downloaded within timeout")
    return None


def ensure_login_success(driver, timeout: int = 30):
    print("Checking login success...")

    end_time = time.time() + timeout

    while time.time() < end_time:
        current_url = driver.current_url

        if "/users/sign_in" not in current_url:
            print("OK: Login redirect detected:", current_url)
            return True

        time.sleep(1)

    print("ERROR: Login did not succeed.")
    print("Current URL:", driver.current_url)
    print("Title:", driver.title)

    try:
        driver.save_screenshot("login_failed.png")
        print("Saved screenshot: login_failed.png")
    except Exception:
        pass

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        print("Page text:")
        print(body_text[:2000])
    except Exception:
        pass

    raise RuntimeError(
        "Login failed. Check username, password, captcha, or website validation message."
    )


# ----------------------------
# Main flow
# ----------------------------
def go_to_tracking_page_and_download(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    download_dir: str,
) -> str:
    clean_old_downloads(download_dir)

    print("Opening report page...")
    driver.get(REPORT_URL)
    wait_page_ready(driver)

    if "/users/sign_in" in driver.current_url:
        raise RuntimeError(
            "Session expired or login failed. Website sent back to sign in page."
        )

    print("Selecting district...")
    select_by_exact_or_contains(wait, By.ID, "district_id", DISTRICT_TEXT)

    time.sleep(1)

    print("Selecting date range...")
    select_by_exact_or_contains(wait, By.ID, "date_range", DATE_RANGE_TEXT_CONTAINS)

    time.sleep(1)

    print("Clicking Apply button...")
    safe_js_click(driver, wait, By.ID, "btn-filter")

    time.sleep(4)
    accept_alert_if_present(driver)

    print("Clicking dormant users tile...")
    safe_js_click(driver, wait, By.ID, DORMANT_TILE_ID)

    time.sleep(3)
    accept_alert_if_present(driver)

    for attempt in range(1, 4):
        try:
            print(f"Clicking export button, attempt {attempt}...")

            t0 = time.time()

            safe_js_click(driver, wait, By.ID, "btn-export-csv")

            print("Export clicked. Waiting for file...")

            downloaded_path = wait_for_download(
                download_dir,
                start_ts=t0,
                timeout=180,
            )

            if downloaded_path:
                return downloaded_path

            print(f"Warning: No file detected on attempt {attempt}")

        except UnexpectedAlertPresentException:
            msg = accept_alert_if_present(driver)
            print("Warning: Alert accepted:", msg)

        except TimeoutException as e:
            print("Warning: Timeout while exporting:", e)

        except StaleElementReferenceException:
            print("Warning: Stale element. Retrying...")

        time.sleep(3)

    raise RuntimeError("Failed to export after multiple attempts.")


def login_to_dashboard_and_download(headless: bool = False) -> str:
    if not PASSWORD or PASSWORD == "YOUR_REAL_PASSWORD_HERE":
        raise RuntimeError("Please set your real password in PASSWORD variable first.")

    download_dir = os.path.join(os.getcwd(), "downloads")
    driver = setup_driver(download_dir, headless=headless)
    wait = WebDriverWait(driver, 30)

    try:
        print("Opening login page...")
        driver.get(BASE_URL)
        wait_page_ready(driver)

        print("Entering username/password...")

        username_input = wait.until(
            EC.presence_of_element_located((By.ID, "user_username"))
        )
        password_input = wait.until(
            EC.presence_of_element_located((By.ID, "user_password"))
        )

        username_input.clear()
        username_input.send_keys(USERNAME)

        password_input.clear()
        password_input.send_keys(PASSWORD)

        captcha_text_el = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/div/div/div/div/div/div/form/div[3]/div/div/span",
                )
            )
        )

        captcha_text = captcha_text_el.text.strip()
        print("Captcha:", captcha_text)

        ans = extract_numbers_and_calculate(captcha_text)

        if ans is None:
            raise RuntimeError(f"Could not parse captcha: {captcha_text}")

        print("OK: Captcha answer:", ans)

        cap_inp = wait.until(EC.presence_of_element_located((By.ID, "captcha")))
        cap_inp.clear()
        cap_inp.send_keys(str(ans))

        print("Submitting login...")

        normal_click(
            driver,
            wait,
            By.XPATH,
            "/html/body/div/div/div/div/div/div/form/button",
        )

        time.sleep(2)

        ensure_login_success(driver, timeout=30)

        wait_page_ready(driver)

        print("OK: Login completed.")
        print("Current URL:", driver.current_url)
        print("Title:", driver.title)

        downloaded_path = go_to_tracking_page_and_download(
            driver,
            wait,
            download_dir,
        )

        print("OK: Downloaded file:", downloaded_path)
        return downloaded_path

    finally:
        driver.quit()


if __name__ == "__main__":
    path = login_to_dashboard_and_download(headless=False)
    print("RETURNED PATH:", path)