"""
Data loading and preprocessing functions
"""
import pandas as pd
import geopandas as gpd
from pathlib import Path
from src.config import RAW_DATA_DIR, CRS


def load_solar_data(filename):
    """Load solar installation data from CSV"""
    filepath = RAW_DATA_DIR / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    df = pd.read_csv(filepath)
    print(f"✓ Loaded {len(df)} records from {filename}")
    return df


def csv_to_geodataframe(df, lat_col='latitude', lon_col='longitude'):
    """Convert pandas DataFrame to GeoDataFrame"""
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs=CRS
    )
    print(f"✓ Converted to GeoDataFrame with {len(gdf)} points")
    return gdf


def get_data_summary(df):
    """Print summary statistics of the dataset"""
    print("\n" + "="*50)
    print("DATA SUMMARY")
    print("="*50)
    print(f"Total records: {len(df)}")
    print(f"\nColumns: {df.columns.tolist()}")
    print(f"\nData types:\n{df.dtypes}")
    print(f"\nMissing values:\n{df.isnull().sum()}")
    print(f"\nFirst few rows:\n{df.head()}")
    print("="*50)