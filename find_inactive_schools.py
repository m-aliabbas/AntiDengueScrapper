#!/usr/bin/env python3
"""
Script to find EMIS codes in a file and create text message with school names
for schools that haven't done activity.
"""

import json
import re
import sys
import os
import pandas as pd

def load_emis_mapping():
    """Load EMIS to school name mapping from JSON file."""
    try:
        with open('emis_to_school_mapping.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print("Error: emis_to_school_mapping.json not found!")
        print("Please run create_emis_json.py first to create the mapping file.")
        return None
    except Exception as e:
        print(f"Error loading JSON mapping: {e}")
        return None

def extract_emis_codes_with_pandas(file_path):
    """Extract EMIS codes from Excel/CSV file using pandas with tehsil filtering."""
    try:
        # Read the file based on extension
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            # Handle Excel files (.xls, .xlsx)
            df = pd.read_excel(file_path)
        
        print(f"Loaded data with {len(df)} rows and {len(df.columns)} columns")
        print(f"Columns: {list(df.columns)}")
        
        # Target tehsils
        target_tehsils = ['Talagang', 'Lawa']
        
        # Try to find tehsil column (case-insensitive)
        tehsil_col = None
        for col in df.columns:
            if 'Tehsil' in col.lower():
                tehsil_col = col
                break
        
        if tehsil_col:
            print(f"Found tehsil column: '{tehsil_col}'")
            
            # Filter by target tehsils
            df_filtered = df[df[tehsil_col].str.upper().isin(target_tehsils)]
            print(f"Filtered to {len(df_filtered)} rows for Talagang and Lawa")
            
            # Print unique tehsils for verification
            unique_tehsils = df[tehsil_col].dropna().unique()
            print(f"Available tehsils: {sorted(unique_tehsils)}")
            
        else:
            print("No 'tehsil' column found. Using all data.")
            df_filtered = df
        
        # Try to find EMIS code column
        emis_col = None
        for col in df.columns:
            if 'emis' in col.lower() or 'code' in col.lower():
                emis_col = col
                break
        
        if emis_col:
            print(f"Found EMIS column: '{emis_col}'")
            emis_codes = df_filtered[emis_col].dropna().astype(str).tolist()
        else:
            print("No EMIS column found. Extracting from all text content.")
            # Fallback: extract from all content
            content = df_filtered.to_string()
            pattern = r'\b374\d{5}\b'
            emis_codes = re.findall(pattern, content)
        
        # Clean and validate EMIS codes
        valid_emis = []
        for code in emis_codes:
            code_str = str(code).strip()
            if re.match(r'^374\d{5}$', code_str):
                valid_emis.append(code_str)
        
        return list(set(valid_emis))  # Remove duplicates
        
    except Exception as e:
        print(f"Error reading file with pandas: {e}")
        print("Falling back to text extraction method...")
        return extract_emis_codes_fallback(file_path)

def extract_emis_codes_fallback(file_path):
    """Fallback method: Extract EMIS codes from the given file using text search."""
    emis_codes = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Find EMIS codes (8-digit numbers starting with 374)
            # Pattern matches CHAKWAL district EMIS codes
            pattern = r'\b374\d{5}\b'
            matches = re.findall(pattern, content)
            
            emis_codes.update(matches)
            
        return list(emis_codes)
    
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return []

def create_activity_message(file_path):
    """Create text message for schools that haven't done Dengue activity from Tehsil Talagang and Lawa only."""
    
    # Load EMIS to school mapping
    emis_mapping = load_emis_mapping()
    if not emis_mapping:
        return
    
    # Extract EMIS codes from file using pandas
    emis_codes = extract_emis_codes_with_pandas(file_path)
    
    if not emis_codes:
        print("No EMIS codes found in the file.")
        return
    
    print(f"Found {len(emis_codes)} EMIS codes from Talagang and Lawa tehsils.")
    
    # Create message (no need for additional filtering since pandas already filtered by tehsil)
    message_lines = []
    found_schools = 0
    
    for emis in sorted(emis_codes):
        if emis in emis_mapping:
            school_name = emis_mapping[emis]
            message_lines.append(f"{school_name} {emis}")
            found_schools += 1
        # Skip EMIS codes not in mapping
    
    # Generate final message
    output_file = "schools_no_activity_message.txt"
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write("SCHOOLS THAT HAVE NOT DONE Dengue ACTIVITY (TALAGANG & LAWA TEHSIL)\n")
        file.write("=" * 60 + "\n\n")
        
        if message_lines:
            for line in message_lines:
                file.write(line + "\n")
        else:
            file.write("No schools from Talagang and Lawa tehsils found without Dengue activity.\n")
        
        # file.write(f"\n📊 SUMMARY:\n")
        # file.write(f"EMIS codes from Talagang/Lawa: {len(emis_codes)}\n")
        # file.write(f"Schools found in mapping: {found_schools}\n")
        # file.write(f"Schools not in mapping: {len(emis_codes) - found_schools}\n")
    
    not_in_mapping = len(emis_codes) - found_schools
    print(f"Message created: {output_file}")
    print(f"Talagang/Lawa EMIS codes: {len(emis_codes)} | Found in mapping: {found_schools} | Not in mapping: {not_in_mapping}")
    
    # Show preview
    print("\nPreview of Talagang/Lawa schools:")
    print("-" * 40)
    for i, line in enumerate(message_lines[:5]):
        print(line)
    if len(message_lines) > 5:
        print("...")
    
    if not_in_mapping > 0:
        print(f"\nNote: {not_in_mapping} EMIS codes from target tehsils were not found in school mapping.")

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) != 2:
        print("Usage: python find_inactive_schools.py <file_path>")
        print("Example: python find_inactive_schools.py downloads/user_wise_dormancy_report.xls")
        return
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"Error: File does not exist: {file_path}")
        return
    
    print(f"Analyzing file: {file_path}")
    create_activity_message(file_path)

if __name__ == "__main__":
    main()