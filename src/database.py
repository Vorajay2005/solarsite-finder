"""
Database management for Solar Site Finder
"""
import sqlite3
import pandas as pd
from pathlib import Path
from src.config import DATA_DIR


class SolarDatabase:
    """SQLite database handler for solar site data"""
    
    def __init__(self, db_name='solar_sites.db'):
        """Initialize database connection"""
        self.db_path = DATA_DIR / db_name
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"✓ Connected to database: {self.db_path}")
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")
    
    def create_tables(self):
        """Create necessary tables"""
        # Solar installations table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS solar_installations (
                case_id INTEGER PRIMARY KEY,
                eia_id INTEGER,
                state TEXT,
                county TEXT,
                latitude REAL,
                longitude REAL,
                area INTEGER,
                year INTEGER,
                capacity_ac REAL,
                capacity_dc REAL,
                tech_primary TEXT,
                type TEXT,
                agrivoltaic TEXT,
                UNIQUE(case_id)
            )
        ''')
        
        self.conn.commit()
        print("✓ Tables created successfully")
    
    def insert_solar_data(self, df):
        """Insert solar installation data from DataFrame"""
        # Prepare data - rename columns to match database schema
        data = df[[
            'case_id', 'eia_id', 'p_state', 'p_county', 
            'ylat', 'xlong', 'p_area', 'p_year',
            'p_cap_ac', 'p_cap_dc', 'p_tech_pri', 
            'p_type', 'p_agrivolt'
        ]].copy()
        
        data.columns = [
            'case_id', 'eia_id', 'state', 'county',
            'latitude', 'longitude', 'area', 'year',
            'capacity_ac', 'capacity_dc', 'tech_primary',
            'type', 'agrivoltaic'
        ]
        
        # Insert into database
        data.to_sql('solar_installations', self.conn, 
                    if_exists='replace', index=False)
        
        print(f"✓ Inserted {len(data)} records into database")
    
    def get_all_installations(self):
        """Get all solar installations"""
        query = "SELECT * FROM solar_installations"
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def get_by_state(self, state):
        """Get installations by state"""
        query = "SELECT * FROM solar_installations WHERE state = ?"
        df = pd.read_sql_query(query, self.conn, params=(state,))
        return df
    
    def get_summary_stats(self):
        """Get summary statistics"""
        query = '''
            SELECT 
                COUNT(*) as total_installations,
                COUNT(DISTINCT state) as num_states,
                SUM(capacity_ac) as total_capacity_ac,
                AVG(capacity_ac) as avg_capacity_ac,
                MIN(year) as earliest_year,
                MAX(year) as latest_year
            FROM solar_installations
        '''
        return pd.read_sql_query(query, self.conn)
    
    def get_by_year(self, year):
        """Get installations by year"""
        query = "SELECT * FROM solar_installations WHERE year = ?"
        df = pd.read_sql_query(query, self.conn, params=(year,))
        return df
    
    def get_top_states(self, limit=10):
        """Get top states by number of installations"""
        query = '''
            SELECT 
                state,
                COUNT(*) as count,
                SUM(capacity_ac) as total_capacity,
                AVG(capacity_ac) as avg_capacity
            FROM solar_installations
            GROUP BY state
            ORDER BY count DESC
            LIMIT ?
        '''
        return pd.read_sql_query(query, self.conn, params=(limit,))
    
    def search_by_location(self, lat, lon, radius_km=50):
        """Find installations near a location (simplified)"""
        # Simple bounding box search
        # For proper distance calculation, use PostGIS or GeoPandas
        lat_delta = radius_km / 111  # rough conversion
        lon_delta = radius_km / 111
        
        query = '''
            SELECT * FROM solar_installations
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
        '''
        params = (lat - lat_delta, lat + lat_delta,
                  lon - lon_delta, lon + lon_delta)
        
        return pd.read_sql_query(query, self.conn, params=params)