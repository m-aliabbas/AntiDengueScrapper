#!/usr/bin/env python3
"""
Script to create JSON mapping of EMIS codes to school names from CHAKWAL CSV data.
"""

import csv
import json
import re

def create_emis_to_school_json():
    """Create JSON mapping from EMIS codes to school names."""
    
    emis_to_school = {}
    
    # Read the CSV file
    try:
        with open('chakwal_pst_data.csv', 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                school_column = row['School']  # Column name is 'School'
                
                # Parse EMIS and school name from format: "37410173 - GGES BIKHARI KALAN"
                match = re.match(r'^(\d+)\s*-\s*(.+)$', school_column.strip())
                
                if match:
                    emis_code = match.group(1)
                    school_name = match.group(2).strip()
                    
                    # Add to dictionary
                    emis_to_school[emis_code] = school_name
                else:
                    print(f"Warning: Could not parse school entry: {school_column}")
    
    except FileNotFoundError:
        print("Error: chakwal_pst_data.csv not found!")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Write to JSON file
    json_filename = 'emis_to_school_mapping.json'
    try:
        with open(json_filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(emis_to_school, jsonfile, ensure_ascii=False, indent=2)
        
        print(f"JSON mapping created successfully: {json_filename}")
        print(f"Total unique schools: {len(emis_to_school)}")
        
        # Show first few entries as preview
        print("\n🔍 Sample entries:")
        print("-" * 50)
        count = 0
        for emis, school in emis_to_school.items():
            if count < 5:
                print(f"EMIS: {emis} -> School: {school}")
                count += 1
            else:
                break
        
        if len(emis_to_school) > 5:
            print("...")
            
    except Exception as e:
        print(f"Error writing JSON file: {e}")

if __name__ == "__main__":
    create_emis_to_school_json()