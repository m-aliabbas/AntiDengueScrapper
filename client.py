#!/usr/bin/env python3
"""
Client script to automate the complete workflow:
1. Run gpt_dashboard.py to download data from the dashboard
2. Parse the downloaded file using find_inactive_schools.py
3. Generate text file output with inactive schools information
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def run_gpt_dashboard():
    """
    Run the gpt_dashboard.py script to download data.
    Returns the path of the downloaded file.
    """
    print("🚀 Starting GPT Dashboard script...")
    print("-" * 50)
    
    try:
        # Import and run the dashboard script
        import gpt_dashboar as dashboard
        
        # Run the download process
        downloaded_file = dashboard.login_to_dashboard_and_download(headless=False)
        
        print(f"✅ Dashboard script completed successfully!")
        print(f"📁 Downloaded file: {downloaded_file}")
        return downloaded_file
        
    except Exception as e:
        print(f"❌ Error running GPT dashboard: {e}")
        return None


def run_find_inactive_schools(file_path):
    """
    Run the find_inactive_schools.py script on the downloaded file.
    Returns the path of the generated text file.
    """
    print(f"\n🔍 Analyzing file for inactive schools...")
    print("-" * 50)
    
    try:
        # Import and run the inactive schools finder
        import find_inactive_schools as finder
        
        # Change working directory to script location to ensure relative paths work
        original_cwd = os.getcwd()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        try:
            # Run the analysis
            finder.create_activity_message(file_path)
            
            # Check if the output file was created
            output_file = "schools_no_activity_message.txt"
            if os.path.exists(output_file):
                output_path = os.path.abspath(output_file)
                print(f"✅ Analysis completed successfully!")
                print(f"📄 Text output created: {output_path}")
                return output_path
            else:
                print("❌ Output file was not created")
                return None
                
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
            
    except Exception as e:
        print(f"❌ Error analyzing inactive schools: {e}")
        return None


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
    except Exception as e:
        print(f"❌ Error reading results file: {e}")


def main():
    """
    Main function to orchestrate the complete workflow.
    """
    print("🤖 DengueBot Client - Automated Workflow")
    print("=" * 60)
    
    # Step 1: Run GPT Dashboard to download data
    downloaded_file = run_gpt_dashboard()
    
    if not downloaded_file:
        print("❌ Failed to download data from dashboard. Exiting.")
        sys.exit(1)
    
    # Step 2: Check if the downloaded file exists
    if not os.path.exists(downloaded_file):
        print(f"❌ Downloaded file not found: {downloaded_file}")
        sys.exit(1)
    
    # Step 3: Analyze the downloaded file for inactive schools
    text_output = run_find_inactive_schools(downloaded_file)
    
    if not text_output:
        print("❌ Failed to analyze inactive schools. Exiting.")
        sys.exit(1)
    
    # Step 4: Display results
    display_results(text_output)
    
    print("\n✅ Workflow completed successfully!")
    print(f"📁 Downloaded data: {downloaded_file}")
    print(f"📄 Text output: {text_output}")
    
    # Optional: Ask user if they want to open the text file
    try:
        response = input("\n📖 Would you like to open the text file? (y/n): ").lower()
        if response in ['y', 'yes']:
            if sys.platform.startswith('darwin'):  # macOS
                os.system(f'open "{text_output}"')
            elif sys.platform.startswith('linux'):  # Linux
                os.system(f'xdg-open "{text_output}"')
            elif sys.platform.startswith('win'):  # Windows
                os.system(f'start "" "{text_output}"')
    except KeyboardInterrupt:
        print("\nBye! 👋")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)