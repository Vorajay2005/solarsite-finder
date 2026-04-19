"""
Query the solar installations database
"""
from src.database import SolarDatabase


def main():
    db = SolarDatabase()
    db.connect()
    
    print("="*50)
    print("SOLAR INSTALLATIONS DATABASE QUERY")
    print("="*50)
    
    while True:
        print("\nOptions:")
        print("1. View all installations")
        print("2. Search by state")
        print("3. Search by year")
        print("4. View summary statistics")
        print("5. View top states")
        print("6. Search near location")
        print("7. Exit")
        
        choice = input("\nEnter choice (1-7): ")
        
        if choice == "1":
            df = db.get_all_installations()
            print(f"\nTotal installations: {len(df)}")
            print(df.head(10))
            
        elif choice == "2":
            state = input("Enter state code (e.g., CA, TX): ").upper()
            df = db.get_by_state(state)
            print(f"\nInstallations in {state}: {len(df)}")
            print(df.head())
            
        elif choice == "3":
            year = int(input("Enter year: "))
            df = db.get_by_year(year)
            print(f"\nInstallations in {year}: {len(df)}")
            print(df.head())
            
        elif choice == "4":
            stats = db.get_summary_stats()
            print("\nSummary Statistics:")
            print(stats.to_string(index=False))
            
        elif choice == "5":
            limit = int(input("How many states? (default 10): ") or 10)
            df = db.get_top_states(limit)
            print(f"\nTop {limit} States:")
            print(df.to_string(index=False))
            
        elif choice == "6":
            lat = float(input("Enter latitude: "))
            lon = float(input("Enter longitude: "))
            radius = float(input("Enter radius (km, default 50): ") or 50)
            df = db.search_by_location(lat, lon, radius)
            print(f"\nFound {len(df)} installations within {radius}km")
            print(df.head())
            
        elif choice == "7":
            break
        else:
            print("Invalid choice!")
    
    db.close()
    print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()