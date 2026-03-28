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
)


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

    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_setting_values.automatic_downloads": 1,
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)

    # extra force download behavior
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": download_dir},
        )
    except Exception:
        pass

    print("OK: Forced download dir:", download_dir)
    return driver


def accept_alert_if_present(driver) -> str | None:
    """Accept alert if present; return its text, else None."""
    try:
        alert = driver.switch_to.alert
        text = alert.text
        alert.accept()
        return text
    except Exception:
        return None


def wait_for_download(download_dir: str, start_ts: float, timeout: int = 180) -> str | None:
    """
    Wait 10 seconds then find newest XLS/XLSX/CSV file created in last 2 minutes.
    Returns absolute path or None if no valid file found.
    """
    d = Path(download_dir).resolve()
    exts = {".xls", ".xlsx", ".csv"}
    
    print("Waiting 15 seconds for download to complete...")
    time.sleep(10)
    
    print(f"Looking for XLS/CSV files created in last 2 minutes in: {d}")
    
    now = time.time()
    two_minutes_ago = now - 120  # 2 minutes = 120 seconds
    
    candidates = []
    for p in d.iterdir():
        if not p.is_file():
            continue
        
        # Skip .crdownload and other incomplete files
        if p.suffix.lower() == ".crdownload" or ".crdownload" in p.name:
            print(f"Skipping incomplete: {p.name}")
            continue
            
        try:
            file_mtime = p.stat().st_mtime
            file_size = p.stat().st_size
            
            # Must be right extension, recent, and have content
            if p.suffix.lower() in exts and file_mtime >= two_minutes_ago and file_size > 0:
                candidates.append(p)
                print(f"Found: {p.name} (size: {file_size} bytes, modified: {time.ctime(file_mtime)})")
        except Exception as e:
            print(f"Warning: Error checking file {p}: {e}")
    
    if not candidates:
        print("Error: No valid .xls/.xlsx/.csv file found in last 2 minutes")
        return None
    
    # Return the newest one
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    newest = candidates[0]
    print(f"OK: Using newest file: {newest.name}")
    return str(newest.resolve())


def select_by_visible_text(wait: WebDriverWait, by, locator: str, text: str):
    """
    Select option reliably from a <select>.
    """
    el = wait.until(EC.presence_of_element_located((by, locator)))
    Select(el).select_by_visible_text(text)


def safe_js_click(driver, wait: WebDriverWait, by, locator: str):
    el = wait.until(EC.element_to_be_clickable((by, locator)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(2.5)
    driver.execute_script("arguments[0].click();", el)
    return el


# ----------------------------
# Main flow
# ----------------------------
def go_to_tracking_page_and_download(driver: webdriver.Chrome, wait: WebDriverWait, download_dir: str) -> str:
    # Clean up old XLS/CSV files before starting
    d = Path(download_dir)
    print("Cleaning old XLS/CSV files from downloads directory...")
    
    cleaned_count = 0
    # Use glob to find XLS, XLSX, CSV files
    for pattern in ["*.xls", "*.xlsx", "*.csv", "*.XLS", "*.XLSX", "*.CSV"]:
        for old_file in d.glob(pattern):
            try:
                print(f"Removing: {old_file.name}")
                old_file.unlink()
                cleaned_count += 1
            except Exception as e:
                print(f"Warning: Could not remove {old_file.name}: {e}")
    
    print(f"✓ Cleaned {cleaned_count} file(s)")
    
    driver.get("https://dashboard-tracking.punjab.gov.pk/user_wise_larva_report")

    # District -> Chakwal (use Select)
    select_by_visible_text(wait, By.ID, "district_id", "Chakwal")

    # Date range -> Today (use Select)
    # NOTE: if exact visible text differs ("Today " / "Today(…)" etc),
    # then change this to match dropdown exactly.
    select_by_visible_text(wait, By.ID, "date_range", "Today")

    # Click dormant
    safe_js_click(driver, wait, By.ID, "link-dormant")

    # Now export
    # If export triggers alert, handle it and retry after selecting date again
    for attempt in range(1, 4):
        try:
            t0 = time.time()
            safe_js_click(driver, wait, By.ID, "btn-export-csv")  # same button even if it exports xls
            print(f"Export clicked (attempt {attempt})... waiting download")

            downloaded_path = wait_for_download(download_dir, start_ts=t0, timeout=180)
            if downloaded_path:
                return downloaded_path
            else:
                print(f"Warning: No valid file detected on attempt {attempt}")

        except UnexpectedAlertPresentException:
            msg = accept_alert_if_present(driver)
            print("Warning: Alert accepted:", msg)

            # Re-apply date range and retry
            try:
                select_by_visible_text(wait, By.ID, "date_range", "Today")
            except Exception as e:
                print("Warning: Failed to re-select date range:", e)

        except TimeoutException as e:
            # Something didn't appear; retry
            print("Warning: Timeout while clicking/exporting, retrying:", e)

    raise RuntimeError("Failed to export after multiple attempts.")


def login_to_dashboard_and_download(headless: bool = False) -> str:
    download_dir = os.path.join(os.getcwd(), "downloads")
    driver = setup_driver(download_dir, headless=headless)
    wait = WebDriverWait(driver, 25)

    try:
        driver.get("https://dashboard-tracking.punjab.gov.pk/")

        # Username / password
        wait.until(EC.presence_of_element_located((By.ID, "user_username"))).send_keys("sed.chk")
        wait.until(EC.presence_of_element_located((By.ID, "user_password"))).send_keys("chakwal@951")

        # Captcha
        captcha_text_el = wait.until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div/div/div/div/div/div/form/div[3]/div/div/span"))
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

        # Submit
        safe_js_click(driver, wait, By.XPATH, "/html/body/div/div/div/div/div/div/form/button")

        # Wait a little until dashboard loads
        time.sleep(1)
        print("OK: Login completed.")
        print("Current URL:", driver.current_url)
        print("Title:", driver.title)

        # Download report
        downloaded_path = go_to_tracking_page_and_download(driver, wait, download_dir)
        print("OK: Downloaded file:", downloaded_path)
        return downloaded_path

    finally:
        driver.quit()


if __name__ == "__main__":
    path = login_to_dashboard_and_download(headless=False)
    print("RETURNED PATH:", path)
