from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys

print("Script started!", flush=True)
sys.stdout.flush()

# Set up Chrome options
chrome_options = Options()
# Remove the headless option if you want to see the browser
# chrome_options.add_argument('--headless')

print("Initializing Chrome driver...", flush=True)
sys.stdout.flush()

# Initialize the Chrome driver
driver = webdriver.Chrome(options=chrome_options)

print("Chrome driver initialized!", flush=True)
sys.stdout.flush()

try:
    # Open time.gov
    driver.get("https://www.time.gov/")
    
    print("Successfully opened time.gov", flush=True)
    sys.stdout.flush()
    
    # Initial load wait
    print("Waiting 5 seconds for initial page load...", flush=True)
    sys.stdout.flush()
    time.sleep(5)
    
    # Continuously refresh every 5 seconds
    while True:
        # Wait for element to be present and find it using xpath
        print("Waiting for element...", flush=True)
        sys.stdout.flush()
        
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[2]/div[2]/div/div/div/div[3]/div[2]'))
        )
        print("Element found!", flush=True)
        sys.stdout.flush()
        
        print(f"Element text: {element.text}", flush=True)
        sys.stdout.flush()
        
        print(f"Element tag: {element.tag_name}", flush=True)
        sys.stdout.flush()
        
        # Wait for 5 seconds
        time.sleep(5)
        
        # Refresh the page
        driver.refresh()
        print("Page refreshed", flush=True)
        sys.stdout.flush()
    
except KeyboardInterrupt:
    print("\nStopping script...", flush=True)
    sys.stdout.flush()
except Exception as e:
    print(f"Error occurred: {e}", flush=True)
    sys.stdout.flush()
finally:
    # Close the browser
    driver.quit()
    print("Browser closed", flush=True)
    sys.stdout.flush()
