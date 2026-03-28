import requests
import time
from datetime import datetime
import os

def fetch_and_save_webpage(url, wait_time_minutes=2):
    """
    Fetch a webpage, wait for specified time, and save the HTML content to a file.
    
    Args:
        url (str): The URL to fetch
        wait_time_minutes (int): Time to wait in minutes before saving
    """
    
    print(f"Starting to fetch webpage: {url}")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Set headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Make the request
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        print(f"Successfully fetched webpage. Status code: {response.status_code}")
        print(f"Content length: {len(response.text)} characters")
        
        # Wait for the specified time
        print(f"Waiting for {wait_time_minutes} minutes...")
        time.sleep(wait_time_minutes * 60)  # Convert minutes to seconds
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"webpage_content_{timestamp}.html"
        filepath = os.path.join(os.getcwd(), filename)
        
        # Save the HTML content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"HTML content saved to: {filepath}")
        print(f"Completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return filepath
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching webpage: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

if __name__ == "__main__":
    url = "https://sis.pesrp.edu.pk/dashboard/sanctioned_post_detail?std_id=3&std_name=PST&stg_id=&stg_name=&district_id=&tehsil_id=&markaz_id=&school_id="
    
    print("=" * 80)
    print("WEBPAGE FETCHER")
    print("=" * 80)
    
    result = fetch_and_save_webpage(url, wait_time_minutes=2)
    
    if result:
        print(f"\n✅ Success! HTML content saved to: {result}")
    else:
        print("\n❌ Failed to fetch and save webpage")
    
    print("=" * 80)