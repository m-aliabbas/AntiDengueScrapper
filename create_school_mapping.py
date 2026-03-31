#!/usr/bin/env python3
"""
Create a JSON mapping from XLSX file with EMIS codes and school names.
"""

import pandas as pd
import json
import sys
import os


def create_school_mapping(xlsx_file_path, output_json="school_emis_json_mapping.json"):
    """
    Read XLSX file with 'EMIS Code' and 'School Name' columns.
    Create a JSON file with EMIS code as key and school name as value.
    """
    print(f"📖 Reading file: {xlsx_file_path}")
    
    try:
        # Read the XLSX file
        df = pd.read_excel(xlsx_file_path)
        
        print(f"File loaded successfully. Found {len(df)} rows")
        print(f"Columns: {df.columns.tolist()}")
        
        # Check if required columns exist
        if "EMIS Code" not in df.columns or "School Name" not in df.columns:
            print("Error: Required columns 'EMIS Code' and 'School Name' not found")
            print(f"Available columns: {df.columns.tolist()}")
            return False
        
        # Create the mapping dictionary
        mapping = {}
        skipped = 0
        
        for idx, row in df.iterrows():
            emis_code = row["EMIS Code"]
            school_name = row["School Name"]
            
            # Skip if either value is NaN or empty
            if pd.isna(emis_code) or pd.isna(school_name):
                skipped += 1
                continue
            
            # Convert EMIS code to string and clean it
            emis_str = str(emis_code).strip()
            
            # Remove decimal point if it's a float representation (e.g., "123456.0" -> "123456")
            if '.' in emis_str:
                emis_str = emis_str.split('.')[0]
            
            school_name_str = str(school_name).strip()
            
            # Only add if EMIS code is 6-9 digits
            if emis_str.isdigit() and 6 <= len(emis_str) <= 9:
                mapping[emis_str] = school_name_str
            else:
                skipped += 1
        
        print(f"Created mapping with {len(mapping)} entries")
        if skipped > 0:
            print(f"Skipped {skipped} rows (invalid or empty data)")
        
        # Save to JSON file
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        
        print(f"JSON file created: {output_json}")
        
        # Show sample entries
        if mapping:
            print("\n Sample entries:")
            for i, (emis, school) in enumerate(list(mapping.items())[:5]):
                print(f"  {emis}: {school}")
            if len(mapping) > 5:
                print(f"  ... and {len(mapping) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_school_mapping.py <xlsx_file_path> [output_json]")
        print("\nExample:")
        print("  python create_school_mapping.py downloads/user_wise_dormancy_report.xls")
        sys.exit(1)
    
    xlsx_file = sys.argv[1]
    output_json = sys.argv[2] if len(sys.argv) > 2 else "school_emis_json_mapping.json"
    
    if not os.path.exists(xlsx_file):
        print(f"File not found: {xlsx_file}")
        sys.exit(1)
    
    success = create_school_mapping(xlsx_file, output_json)
    sys.exit(0 if success else 1)
