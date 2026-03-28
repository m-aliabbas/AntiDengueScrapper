#!/usr/bin/env python3
"""
Script to extract table data from HTML file and filter for CHAKWAL district.
Creates a CSV file with all CHAKWAL entries.
"""

import csv
from bs4 import BeautifulSoup
import re

def extract_chakwal_data():
    """Extract table data for CHAKWAL district and save to CSV."""
    
    # Read the HTML file
    with open('webpage_content_20260201_114543.html', 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the table with specific classes
    table = soup.find('table', class_='table table-striped table-bordered table-hover table-highlight table-checkable')
    
    if not table:
        print("Table not found!")
        return
    
    # Get header row
    header_row = table.find('thead').find('tr')
    headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
    
    print(f"Headers found: {headers}")
    
    # Get all data rows
    tbody = table.find('tbody')
    rows = tbody.find_all('tr')
    
    chakwal_data = []
    chakwal_count = 0
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 9:  # Ensure we have enough cells
            row_data = []
            for cell in cells:
                # Extract text and clean it
                text = cell.get_text(strip=True)
                # Remove any extra whitespace
                text = re.sub(r'\s+', ' ', text)
                row_data.append(text)
            
            # Check if District (2nd column, index 1) is CHAKWAL
            if len(row_data) >= 2 and row_data[1] == 'CHAKWAL':
                chakwal_data.append(row_data)
                chakwal_count += 1
    
    print(f"Found {chakwal_count} rows with District = CHAKWAL")
    
    # Write to CSV file
    csv_filename = 'chakwal_pst_data.csv'
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write headers
        writer.writerow(headers)
        
        # Write CHAKWAL data
        for row_data in chakwal_data:
            writer.writerow(row_data)
    
    print(f"Data saved to {csv_filename}")
    
    # Print first few rows as preview
    if chakwal_data:
        print("\nFirst few rows of CHAKWAL data:")
        print("-" * 80)
        for i, row in enumerate(chakwal_data[:5]):
            print(f"Row {i+1}: {row}")

if __name__ == "__main__":
    extract_chakwal_data()