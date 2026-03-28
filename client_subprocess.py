#!/usr/bin/env python3
"""
Alternative client script using subprocess calls.
This version runs the scripts as separate processes for better isolation.
"""

import os
import sys
import subprocess
import time
import glob
import requests
import json
from pathlib import Path


def run_gpt_dashboard_subprocess():
    """
    Run gpt_dashboard.py as a subprocess.
    Returns the path of the most recent download.
    """
    print("🚀 Starting GPT Dashboard script...")
    print("-" * 50)
    
    try:
        # Get current downloads before running
        downloads_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        
        before_files = set(glob.glob(os.path.join(downloads_dir, "*")))
        
        # Run the dashboard script
        result = subprocess.run([
            sys.executable, "gpt_dashboar.py"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Dashboard script completed successfully!")
            
            # Look for newly downloaded XLS/XLSX/CSV files only
            xls_patterns = ["*.xls", "*.xlsx", "*.csv", "*.XLS", "*.XLSX", "*.CSV"]
            new_xls_files = []
            
            for pattern in xls_patterns:
                after_xls = set(glob.glob(os.path.join(downloads_dir, pattern)))
                before_xls = {f for f in before_files if f in after_xls or Path(f).suffix.lower() in ['.xls', '.xlsx', '.csv']}
                new_found = after_xls - before_xls
                new_xls_files.extend(new_found)
            
            if new_xls_files:
                # Get the most recent XLS file
                newest_file = max(new_xls_files, key=os.path.getmtime)
                print(f"📁 Downloaded file: {newest_file}")
                
                # Verify the file exists and is valid
                if os.path.exists(newest_file) and os.path.getsize(newest_file) > 0:
                    print(f"✅ Verified downloaded file exists: {newest_file}")
                    return newest_file
                else:
                    print(f"⚠️  File exists but may be invalid: {newest_file}")
            else:
                print("⚠️  No new XLS/XLSX/CSV files detected in downloads directory")
                # Look for most recent XLS file in downloads
                all_xls = []
                for pattern in xls_patterns:
                    all_xls.extend(glob.glob(os.path.join(downloads_dir, pattern)))
                
                if all_xls:
                    newest_file = max(all_xls, key=os.path.getmtime)
                    print(f"📁 Using most recent XLS file: {newest_file}")
                    return newest_file
                
        else:
            print(f"❌ Dashboard script failed with return code: {result.returncode}")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            
        return None
        
    except subprocess.TimeoutExpired:
        print("❌ Dashboard script timed out after 5 minutes")
        return None
    except Exception as e:
        print(f"❌ Error running GPT dashboard: {e}")
        return None


def run_find_inactive_schools_subprocess(file_path):
    """
    Run find_inactive_schools.py as a subprocess.
    Returns the path of the generated text file.
    """
    print(f"\n🔍 Analyzing file for inactive schools...")
    print("-" * 50)
    
    try:
        # Run the inactive schools script
        result = subprocess.run([
            sys.executable, "find_inactive_schools.py", file_path
        ], capture_output=True, text=True, timeout=60)
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("✅ Analysis completed successfully!")
            
            # Check if output file was created
            output_file = "schools_no_activity_message.txt"
            if os.path.exists(output_file):
                output_path = os.path.abspath(output_file)
                print(f"📄 Text output created: {output_path}")
                return output_path
            else:
                print("❌ Expected output file not found")
                return None
        else:
            print(f"❌ Analysis script failed with return code: {result.returncode}")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ Analysis script timed out after 1 minute")
        return None
    except Exception as e:
        print(f"❌ Error analyzing inactive schools: {e}")
        return None


def send_text_to_api(text_file_path, phone_number="923171585452"):
    """
    Send the text content to the specified API endpoint.
    """
    if not text_file_path or not os.path.exists(text_file_path):
        print("❌ No text file to send")
        return False
    
    print(f"\n📤 Sending text content to API...")
    print("-" * 50)
    
    try:
        # Read the file content
        with open(text_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Prepare the API payload
        payload = {
            "phone_number": phone_number,
            "message": content
        }
        
        # Send POST request to API
        api_url = "http://localhost:8000/send"
        headers = {"Content-Type": "application/json"}
        
        print(f"🌐 Sending to: {api_url}")
        print(f"📱 Phone number: {phone_number}")
        print(f"📄 Message length: {len(content)} characters")

        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("✅ Message sent successfully!")
            print(f"📋 API Response: {response.text}")
            return True
        else:
            print(f"❌ API request failed with status code: {response.status_code}")
            print(f"📋 Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server. Is it running on localhost:8000?")
        return False
    except requests.exceptions.Timeout:
        print("❌ API request timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Error sending to API: {e}")
        return False


def display_results(text_file_path):
    """
    Display the contents of the generated text file.
    """
    if not text_file_path or not os.path.exists(text_file_path):
        print("❌ No results file to display")
        return
    
    print(f"\n📄 RESULTS FROM: {text_file_path}")
    print("=" * 60)
    
    try:
        with open(text_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            print(content)
            
        # Also show file size and modification time
        file_stat = os.stat(text_file_path)
        file_size = file_stat.st_size
        mod_time = time.ctime(file_stat.st_mtime)
        print(f"\n📊 File info: {file_size} bytes, modified {mod_time}")
        
    except Exception as e:
        print(f"❌ Error reading results file: {e}")


def check_prerequisites():
    """
    Check if required files exist.
    """
    required_files = [
        "gpt_dashboar.py",
        "find_inactive_schools.py",
        "emis_to_school_mapping.json"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True


def main():
    """
    Main function to orchestrate the complete workflow.
    """
    print("🤖 DengueBot Client - Automated Workflow (Subprocess Version)")
    print("=" * 70)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Cannot proceed without required files.")
        sys.exit(1)
    
    print("✅ All required files found")
    
    # Step 1: Run GPT Dashboard to download data
    downloaded_file = run_gpt_dashboard_subprocess()
    
    if not downloaded_file:
        print("❌ Failed to download data from dashboard. Exiting.")
        sys.exit(1)
    
    # Step 2: Verify the downloaded file exists
    if not os.path.exists(downloaded_file):
        print(f"❌ Downloaded file not found: {downloaded_file}")
        sys.exit(1)
    
    print(f"✅ Verified downloaded file exists: {downloaded_file}")
    
    # Step 3: Analyze the downloaded file for inactive schools
    text_output = run_find_inactive_schools_subprocess(downloaded_file)
    
    if not text_output:
        print("❌ Failed to analyze inactive schools. Exiting.")
        sys.exit(1)
    
    # Step 4: Display results
    display_results(text_output)
    
    # Step 5: Send results to API
    api_success = send_text_to_api(text_output)
    
    print("\n" + "=" * 70)
    if api_success:
        print("✅ WORKFLOW COMPLETED SUCCESSFULLY!")
        print("📤 Text content sent to API successfully!")
    else:
        print("⚠️  WORKFLOW COMPLETED WITH API ERROR!")
        print("📋 Data analysis completed but API sending failed")
    print(f"📁 Downloaded data: {downloaded_file}")
    print(f"📄 Text output: {text_output}")
    print("=" * 70)
    
    


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)