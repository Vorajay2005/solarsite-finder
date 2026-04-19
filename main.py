"""
Solar Site Finder - Main Script
Authors: Jay Vora & Shashank Vemparala
"""
import sys
from pathlib import Path
from src.data_loader import load_solar_data, csv_to_geodataframe, get_data_summary
from src.config import RAW_DATA_DIR


def main():
    print("="*50)
    print("SOLAR SITE FINDER")
    print("="*50)
    
    # Check if data directory has files
    csv_files = list(RAW_DATA_DIR.glob("*.csv"))
    
    if not csv_files:
        print(f"\n⚠️  No CSV files found in {RAW_DATA_DIR}")
        print("Please add your data files to data/raw/")
        return
    
    print(f"\n📁 Found {len(csv_files)} CSV file(s):")
    for i, f in enumerate(csv_files, 1):
        print(f"   {i}. {f.name}")
    
    # Load first CSV file
    print(f"\n📊 Loading {csv_files[0].name}...")
    df = load_solar_data(csv_files[0].name)
    
    # Show summary
    get_data_summary(df)
    
    print("\n✅ Data loaded successfully!")
    print("\nNext steps:")
    print("1. Add more data files to data/raw/")
    print("2. Run analysis on the data")
    print("3. Create visualizations")


if _name_ == "_main_":
    main()