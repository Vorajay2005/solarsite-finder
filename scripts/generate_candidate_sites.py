import sqlite3
import math
import pandas as pd
import numpy as np
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH      = os.path.join(PROJECT_ROOT, "database", "solar_site_finder.db")
RAW_DIR      = os.path.join(PROJECT_ROOT, "data", "raw")
SAMPLE_DIR   = os.path.join(PROJECT_ROOT, "sample_data")

NJ_BOUNDS       = (38.92, 41.36, -75.56, -73.89)
GRID_RESOLUTION = 0.05  

UNSUITABLE_CLASSES = {"Woody Wetlands", "Open Water", "Emergent Herbaceous Wetlands"}

NJ_COUNTY_CENTROIDS = {
    "Atlantic":   (39.37, -74.63),
    "Bergen":     (40.96, -74.07),
    "Burlington": (39.87, -74.67),
    "Camden":     (39.80, -75.00),
    "Cape May":   (39.08, -74.83),
    "Cumberland": (39.38, -75.11),
    "Essex":      (40.78, -74.22),
    "Gloucester": (39.71, -75.14),
    "Hudson":     (40.72, -74.07),
    "Hunterdon":  (40.56, -74.92),
    "Mercer":     (40.28, -74.70),
    "Middlesex":  (40.44, -74.41),
    "Monmouth":   (40.27, -74.17),
    "Morris":     (40.86, -74.54),
    "Ocean":      (39.89, -74.27),
    "Passaic":    (41.03, -74.30),
    "Salem":      (39.57, -75.36),
    "Somerset":   (40.56, -74.61),
    "Sussex":     (41.13, -74.69),
    "Union":      (40.66, -74.27),
    "Warren":     (40.86, -74.97),
}
_county_names  = list(NJ_COUNTY_CENTROIDS.keys())
_county_lats   = np.array([v[0] for v in NJ_COUNTY_CENTROIDS.values()])
_county_lons   = np.array([v[1] for v in NJ_COUNTY_CENTROIDS.values()])

def county_for(lat, lon):
    """Return the NJ county whose centroid is closest to (lat, lon)."""
    dists = np.sqrt((_county_lats - lat) ** 2 + (_county_lons - lon) ** 2)
    return _county_names[int(np.argmin(dists))]

def get_conn():
    if not os.path.exists(DB_PATH):
        print("Database not found. Run scripts/create_database.py first.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def load_slope_lookup():
    for d in [RAW_DIR, SAMPLE_DIR]:
        p = os.path.join(d, "slope.csv")
        if os.path.exists(p):
            df = pd.read_csv(p)
            df["latitude"]      = pd.to_numeric(df["latitude"],      errors="coerce").round(2)
            df["longitude"]     = pd.to_numeric(df["longitude"],     errors="coerce").round(2)
            df["slope_degrees"] = pd.to_numeric(df["slope_degrees"], errors="coerce")
            df = df.dropna()
            lookup = {(r.latitude, r.longitude): r.slope_degrees
                      for r in df.itertuples(index=False)}
            print(f"  Loaded slope lookup: {len(lookup)} entries")
            return lookup
    return None

def simulate_slope(lat, lon):
    """
    Reproducible NJ slope estimate.
    Pine Barrens (south, lat < 39.8): very flat.
    Highlands (north, lat > 40.5): hillier.
    """
    rng = np.random.default_rng(seed=int(abs(lat * 10000) + abs(lon * 10000)))
    if lat < 39.8:
        return round(float(rng.uniform(0.3, 3.0)), 2)
    elif lat < 40.5:
        return round(float(rng.uniform(1.0, 5.0)), 2)
    else:
        return round(float(rng.uniform(3.0, 10.0)), 2)

def build_land_cover_lookup(conn):
    """
    Load the land_cover table into NumPy arrays for fast nearest-neighbour
    lookup. Returns (lats, lons, class_names) arrays.
    """
    rows = conn.execute(
        "SELECT latitude, longitude, class_name FROM land_cover;"
    ).fetchall()
    lats  = np.array([r[0] for r in rows])
    lons  = np.array([r[1] for r in rows])
    names = [r[2] for r in rows]
    return lats, lons, names


def nearest_land_cover(lat, lon, lc_lats, lc_lons, lc_names, max_dist=1.0):
    """Return the class_name of the nearest land cover cell within max_dist degrees."""
    dists = np.abs(lc_lats - lat) + np.abs(lc_lons - lon)
    idx   = int(np.argmin(dists))
    if dists[idx] <= max_dist:
        return lc_names[idx]
    return None

def generate_clipped_grid():
   
    lat_min, lat_max, lon_min, lon_max = NJ_BOUNDS
    lats = np.round(np.arange(lat_min, lat_max + GRID_RESOLUTION, GRID_RESOLUTION), 2)
    lons = np.round(np.arange(lon_min, lon_max + GRID_RESOLUTION, GRID_RESOLUTION), 2)
    grid_lats, grid_lons = np.meshgrid(lats, lons)
    grid_lats = grid_lats.ravel()
    grid_lons = grid_lons.ravel()
    print(f"  Bounding-box grid: {len(grid_lats)} points")

    shp_path = os.path.join(RAW_DIR, "nj_land_cover", "Land_Use_2020.shp")
    if os.path.exists(shp_path):
        try:
            import geopandas as gpd
            from shapely.geometry import Point
            from shapely.ops import unary_union

            print("  Building NJ LAND-ONLY boundary from shapefile…")
            gdf = gpd.read_file(shp_path)

            land_gdf = gdf[gdf["TYPE20"] != "WATER"].copy()
            print(f"  Land polygons: {len(land_gdf):,}  (removed {len(gdf)-len(land_gdf):,} water polygons)")

            land_gdf = land_gdf.to_crs(epsg=4326)

            land_gdf["geometry"] = land_gdf.geometry.buffer(0)

            print("  Dissolving land polygons into NJ land boundary…")
            nj_land = unary_union(land_gdf.geometry)

            print("  Clipping grid points to NJ land boundary…")
            inside = []
            for lat, lon in zip(grid_lats, grid_lons):
                if nj_land.contains(Point(lon, lat)):
                    inside.append((round(float(lat), 2), round(float(lon), 2)))

            removed = len(grid_lats) - len(inside)
            print(f"  Clipped: {len(inside)} inside NJ land  ({removed} water/ocean/out-of-state removed)")
            return inside

        except Exception as e:
            print(f"  Shapefile clip failed ({e}), using bounding box.")
    return [(round(float(la), 2), round(float(lo), 2))
            for la, lo in zip(grid_lats, grid_lons)]


if __name__ == "__main__":
    conn         = get_conn()
    slope_lookup = load_slope_lookup()

    print("\nStep 1: Building land cover lookup from database…")
    lc_lats, lc_lons, lc_names = build_land_cover_lookup(conn)
    print(f"  {len(lc_lats)} land cover cells loaded.")

    print("\nStep 2: Generating NJ candidate grid…")
    points = generate_clipped_grid()

    print("\nStep 3: Assigning county, land cover, and slope…")
    rows     = []
    excluded = 0

    for lat, lon in points:
        lc_name = nearest_land_cover(lat, lon, lc_lats, lc_lons, lc_names, max_dist=0.5)

        if lc_name in UNSUITABLE_CLASSES:
            excluded += 1
            continue

        slope = (slope_lookup.get((round(lat, 2), round(lon, 2)))
                 if slope_lookup else simulate_slope(lat, lon))

        rows.append({
            "latitude":        lat,
            "longitude":       lon,
            "state":           "NJ",
            "county":          county_for(lat, lon),
            "grid_resolution": GRID_RESOLUTION,
            "slope_degrees":   slope,
        })

    print(f"  Excluded {excluded} unsuitable (wetland/water) points.")
    print(f"  Remaining: {len(rows)} valid candidate sites.")

    print("\nStep 4: Writing to database…")
    conn.execute("DELETE FROM candidate_sites;")
    conn.execute("DELETE FROM site_scores;")
    df = pd.DataFrame(rows)
    df.to_sql("candidate_sites", conn, if_exists="append", index=False)
    conn.commit()

    county_counts = df["county"].value_counts().head(10)
    print("\nCandidate sites by county (top 10):")
    for county, n in county_counts.items():
        print(f"  {county:15s}: {n}")

    print(f"\nLat range : {df['latitude'].min()} – {df['latitude'].max()}")
    print(f"Lon range : {df['longitude'].min()} – {df['longitude'].max()}")
    print(f"\nTotal inserted: {len(df)} NJ candidate sites.")

    conn.close()
    print("\nDone. Next step: python scripts/score_sites.py")
