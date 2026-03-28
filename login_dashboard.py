import os
import time
import re
import secrets
from datetime import datetime
from pathlib import Path

import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    UnexpectedAlertPresentException,
    TimeoutException,
)


# ----------------------------
# Selenium + Download helpers
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

    print("✅ Forced download dir:", download_dir)
    return driver


def accept_alert_if_present(driver) -> str | None:
    try:
        alert = driver.switch_to.alert
        text = alert.text
        alert.accept()
        return text
    except Exception:
        return None


def wait_for_download(download_dir: str, start_ts: float, timeout: int = 180) -> str:
    """
    Wait for a NEW downloaded file after start_ts in download_dir.
    Supports: .xls, .xlsx, .csv
    Ignores .crdownload until complete.
    """
    d = Path(download_dir).resolve()
    end = time.time() + timeout
    exts = {".xls", ".xlsx", ".csv"}

    while time.time() < end:
        if list(d.glob("*.crdownload")):
            time.sleep(0.5)
            continue

        candidates = []
        for p in d.iterdir():
            if not p.is_file():
                continue
            try:
                if p.suffix.lower() in exts and p.stat().st_mtime >= start_ts:
                    candidates.append(p)
            except Exception:
                pass

        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            newest = candidates[0]

            s1 = newest.stat().st_size
            time.sleep(0.8)
            s2 = newest.stat().st_size
            if s1 == s2 and s2 > 0:
                return str(newest.resolve())

        time.sleep(0.5)

    raise TimeoutError(f"No new .xls/.xlsx/.csv download detected in {timeout}s inside {d}")


def select_by_visible_text(wait: WebDriverWait, by, locator: str, text: str):
    el = wait.until(EC.presence_of_element_located((by, locator)))
    Select(el).select_by_visible_text(text)


def safe_js_click(driver, wait: WebDriverWait, by, locator: str):
    el = wait.until(EC.element_to_be_clickable((by, locator)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.2)
    driver.execute_script("arguments[0].click();", el)
    return el


# ----------------------------
# XLS -> Extract numbers -> CSV
# ----------------------------
def extract_8digit_from_username(username: str) -> str | None:
    """
    Username example: '37440175.se'
    Extract: '37440175'
    """
    if username is None:
        return None
    s = str(username).strip()
    m = re.match(r"^(\d{8})\.", s)  # starts with 8 digits then a dot
    return m.group(1) if m else None


def convert_xls_to_numbers_csv(xls_path: str, out_dir: str) -> str:
    """
    Open downloaded XLS/XLSX, extract 8-digit from Username column,
    save to a NEW CSV with random name + datetime, return output path.

    Requirements:
      - .xls: pip install xlrd==2.0.1
      - .xlsx: pip install openpyxl
    """
    xls_path = os.path.abspath(xls_path)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    ext = os.path.splitext(xls_path)[1].lower()
    if ext == ".xls":
        # For .xls you need: pip install xlrd==2.0.1
        df = pd.read_excel(xls_path, engine="xlrd")
    else:
        # For .xlsx: pip install openpyxl
        df = pd.read_excel(xls_path, engine="openpyxl")

    # Find Username column (case-insensitive)
    cols_norm = {}
    for c in df.columns:
        if isinstance(c, str):
            cols_norm[c.strip().lower()] = c

    if "username" not in cols_norm:
        raise ValueError(f"'Username' column not found. Available columns: {list(df.columns)}")

    username_col = cols_norm["username"]

    extracted = (
        df[username_col]
        .apply(extract_8digit_from_username)
        .dropna()
        .astype(str)
        .drop_duplicates()
        .reset_index(drop=True)
    )

    out_df = pd.DataFrame({"number": extracted})

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand = secrets.token_hex(3)  # 6 hex chars
    out_name = f"extracted_numbers_{stamp}_{rand}.csv"
    out_path = os.path.join(out_dir, out_name)

    out_df.to_csv(out_path, index=False)
    return os.path.abspath(out_path)


# ----------------------------
# Main flow
# ----------------------------
def go_to_tracking_page_and_download(driver: webdriver.Chrome, wait: WebDriverWait, download_dir: str) -> str:
    driver.get("https://dashboard-tracking.punjab.gov.pk/user_wise_larva_report")

    # District -> Chakwal
    select_by_visible_text(wait, By.ID, "district_id", "Chakwal")

    # Date range -> Today
    select_by_visible_text(wait, By.ID, "date_range", "Today")

    # Dormant
    safe_js_click(driver, wait, By.ID, "link-dormant")

    # Export (may show alert, retry)
    for attempt in range(1, 4):
        try:
            t0 = time.time()
            safe_js_click(driver, wait, By.ID, "btn-export-csv")
            print(f"📥 Export clicked (attempt {attempt})... waiting download")

            downloaded_path = wait_for_download(download_dir, start_ts=t0, timeout=180)
            return downloaded_path

        except UnexpectedAlertPresentException:
            msg = accept_alert_if_present(driver)
            print("⚠️ Alert accepted:", msg)

            # Re-apply date range then retry
            try:
                select_by_visible_text(wait, By.ID, "date_range", "Today")
            except Exception as e:
                print("⚠️ Failed to re-select date range:", e)

        except TimeoutException as e:
            print("⚠️ Timeout while exporting, retrying:", e)

    raise RuntimeError("Failed to export after multiple attempts.")


def login_to_dashboard_download_and_extract(headless: bool = False) -> tuple[str, str]:
    """
    1) Login
    2) Download XLS from dormant report
    3) Open downloaded file, extract 8-digit numbers from Username column
    4) Save extracted numbers to NEW CSV (random name + datetime)
    Returns: (downloaded_xls_path, extracted_csv_path)
    """
    download_dir = os.path.join(os.getcwd(), "downloads")
    extracted_out_dir = os.path.join(os.getcwd(), "extracted")  # separate folder for output CSVs

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
        print("🧩 Captcha:", captcha_text)

        ans = extract_numbers_and_calculate(captcha_text)
        if ans is None:
            raise RuntimeError(f"Could not parse captcha: {captcha_text}")
        print("✅ Captcha answer:", ans)

        cap_inp = wait.until(EC.presence_of_element_located((By.ID, "captcha")))
        cap_inp.clear()
        cap_inp.send_keys(str(ans))

        # Submit
        safe_js_click(driver, wait, By.XPATH, "/html/body/div/div/div/div/div/div/form/button")

        time.sleep(2)
        print("✅ Login completed.")
        print("🔎 Current URL:", driver.current_url)
        print("🔎 Title:", driver.title)

        # Download report file (xls/xlsx/csv)
        downloaded_path = go_to_tracking_page_and_download(driver, wait, download_dir)
        print("✅ Downloaded file:", downloaded_path)

        # Convert downloaded XLS/XLSX -> extracted CSV
        extracted_csv_path = convert_xls_to_numbers_csv(downloaded_path, extracted_out_dir)
        print("✅ Extracted numbers CSV:", extracted_csv_path)

        return downloaded_path, extracted_csv_path

    finally:
        driver.quit()


if __name__ == "__main__":
    downloaded_file, extracted_csv = login_to_dashboard_download_and_extract(headless=False)
    print("\nRETURNED DOWNLOADED FILE:", downloaded_file)
    print("RETURNED EXTRACTED CSV:", extracted_csv)
