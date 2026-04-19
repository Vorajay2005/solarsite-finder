"""
Configuration settings for Solar Site Finder
"""
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(_file_).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Analysis parameters
SUITABILITY_PARAMS = {
    'min_solar_radiation': 4.5,  # kWh/m²/day
    'max_slope': 5.0,  # degrees
    'max_distance_to_grid': 10000,  # meters
    'min_distance_to_existing': 5000,  # meters
}

# Coordinate Reference System
CRS = "EPSG:4326"  # WGS84 (lat/lon)