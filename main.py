"""
Solar Site Finder - Main Script
Authors: Jay Vora & Shashank Vemparala
"""
from src.data_loader import load_solar_data
from src.database import SolarDatabase
from src.config import RAW_DATA_DIR


def main():
    print("="*50)
    print("SOLAR SITE FINDER - DATABASE SETUP")
    print("="*50)
    
    # Initialize database
    db = SolarDatabase()
    db.connect()
    db.create_tables()
    
    # Load CSV data
    csv_files = list(RAW_DATA_DIR.glob("*.csv"))
    
    if csv_files:
        print(f"\n📊 Loading {csv_files[0].name}...")
        df = load_solar_data(csv_files[0].name)
        
        # Insert into database
        print("\n💾 Inserting data into database...")
        db.insert_solar_data(df)
        
        # Get summary statistics
        print("\n📈 Database Summary:")
        print("="*50)
        stats = db.get_summary_stats()
        print(stats.to_string(index=False))
        
        # Show top states
        print("\n🏆 Top 10 States by Installation Count:")
        print("="*50)
        top_states = db.get_top_states(10)
        print(top_states.to_string(index=False))
        
    else:
        print("\n⚠️  No CSV files found in data/raw/")
    
    # Close database
    db.close()
    
    print("\n" + "="*50)
    print("✅ Database setup complete!")
    print(f"Database location: {db.db_path}")
    print("="*50)


if __name__ == "__main__":
    main()