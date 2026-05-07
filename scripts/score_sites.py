import sqlite3
import pandas as pd
import numpy as np
import os
import sys
import math
import pickle
import geopandas as gpd
from shapely.geometry import Point

PROJECT_ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH       = os.path.join(PROJECT_ROOT, "database", "solar_site_finder.db")
MODEL_PATH    = os.path.join(PROJECT_ROOT, "models", "solar_capacity_model.pkl")
SHAPEFILE_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "nj_land_cover", "Land_Use_2020.shp")

WEIGHTS = {
    "ghi":        0.35,
    "land_cover": 0.35,
    "slope":      0.20,
    "proximity":  0.10,
}

LAND_COVER = {
    #  name                           score  acres  land_type
    "Barren Land":                   (95,    18.0,  "brownfield"),
    "Cultivated Crops":              (88,    16.0,  "greenfield"),
    "Pasture/Hay":                   (88,    15.0,  "greenfield"),
    "Grassland/Herbaceous":          (85,    13.0,  "greenfield"),
    "Shrub/Scrub":                   (65,    10.0,  "greenfield"),
    "Developed Open Space":          (50,    10.0,  "brownfield"),
    "Developed Low Intensity":       (25,     9.0,  "brownfield"),
    "Developed Medium Intensity":    (10,     6.0,  "brownfield"),
    "Developed High Intensity":      ( 5,     4.0,  "brownfield"),
    "Deciduous Forest":              (20,     7.0,  "greenfield"),
    "Evergreen Forest":              (20,     6.0,  "greenfield"),
    "Mixed Forest":                  (20,     6.0,  "greenfield"),
    "Woody Wetlands":                ( 5,     0.0,  "greenfield"),
    "Emergent Herbaceous Wetlands":  ( 5,     0.0,  "greenfield"),
    "Open Water":                    ( 0,     0.0,  "greenfield"),
}

LAND_COVER_SCORES = {k: v[0] for k, v in LAND_COVER.items()}
GHI_MIN = 3.0   
GHI_MAX = 5.5   
def get_conn():
    if not os.path.exists(DB_PATH):
        print("Database not found. Run scripts/create_database.py first.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def score_ghi(ghi_value):
    """Normalize GHI to 0–100. Returns 50 if GHI is missing."""
    if ghi_value is None or pd.isna(ghi_value):
        return 50.0
    score = (ghi_value - GHI_MIN) / (GHI_MAX - GHI_MIN) * 100
    return round(max(0.0, min(100.0, score)), 2)


def score_land_cover(class_name):
    """Look up land cover class in the scoring table. Returns 50 if unknown."""
    if class_name is None or pd.isna(class_name):
        return 50.0
    return float(LAND_COVER_SCORES.get(class_name, 50))

def score_slope(slope_degrees):
    """
    Slope score: 0° = 100, 5° = 75, 10° = 50, 20° = 0.
    Steep terrain is difficult to build on.
    """
    if slope_degrees is None or pd.isna(slope_degrees):
        return 60.0   
   
    score = max(0.0, (1.0 - slope_degrees / 20.0)) * 100
    return round(score, 2)

def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def score_proximity(lat, lon, existing_coords):
    """
    Proximity to existing NJ solar installations.
    NJ has 330 installations spread across a small state (~230 km tall),
    so we use tighter distance bands than the national default.

    < 3 km  → 100  (immediate vicinity — grid infrastructure very likely)
    3–30 km → linear decay 100 → 20
    > 30 km → 10   (far from any existing solar, more grid buildout needed)
    """
    if not existing_coords:
        return 50.0

    min_dist = min(haversine_km(lat, lon, elat, elon)
                   for elat, elon in existing_coords)

    if min_dist < 3:
        return 100.0
    elif min_dist <= 30:
        return round(100.0 - (min_dist - 3) / 27.0 * 80.0, 2)
    else:
        return 10.0

def load_existing_coords(conn):
    """
    Load lat/lon of existing NJ solar installations for proximity scoring.
    Filtering to NJ keeps distances meaningful — a CA site shouldn't
    affect a NJ candidate's proximity score.
    """
    rows = conn.execute(
        "SELECT latitude, longitude FROM existing_solar_sites WHERE state = 'NJ';"
    ).fetchall()
    print(f"  Found {len(rows)} existing NJ installations for proximity scoring.")
    return [(r[0], r[1]) for r in rows]

def build_score_dataframe(conn):
    """
    Combine candidates with radiation and land_cover using nearest-neighbour
    matching in Python (no exact-coordinate JOIN needed).

    Why not a SQL JOIN?
      - The NSRDB file gives one point; the land cover grid is 0.05° cells;
        the candidate grid is 0.1°. Rounding-based JOINs miss most rows.
      - Instead we load each reference table into a NumPy array and find the
        closest point by Manhattan distance (fast for lat/lon grids).
    """
    cands = pd.read_sql(
        "SELECT candidate_id, latitude, longitude, state, slope_degrees FROM candidate_sites;",
        conn
    )
    print(f"  Scoring {len(cands)} candidate sites ...")

    rad = pd.read_sql(
        "SELECT latitude, longitude, ghi_kwh_m2_day FROM solar_radiation;", conn
    )
    if rad.empty:
        cands["ghi_kwh_m2_day"] = None
    else:
        rad_lats = rad["latitude"].values
        rad_lons = rad["longitude"].values
        rad_ghi  = rad["ghi_kwh_m2_day"].values

        def nearest_ghi(lat, lon):
         
            dists = np.abs(rad_lats - lat) + np.abs(rad_lons - lon)
            idx   = np.argmin(dists)
            return float(rad_ghi[idx]) if dists[idx] <= 5.0 else None

        cands["ghi_kwh_m2_day"] = [nearest_ghi(r.latitude, r.longitude)
                                   for r in cands.itertuples(index=False)]

    lc = pd.read_sql(
        "SELECT latitude, longitude, class_name, suitability FROM land_cover;", conn
    )
    if lc.empty:
        cands["land_cover_name"] = None
    else:
        lc_lats  = lc["latitude"].values
        lc_lons  = lc["longitude"].values
        lc_names = lc["class_name"].values

        def nearest_land_cover(lat, lon):
            dists = np.abs(lc_lats - lat) + np.abs(lc_lons - lon)
            idx   = np.argmin(dists)
            return str(lc_names[idx]) if dists[idx] <= 2.0 else None

        cands["land_cover_name"] = [nearest_land_cover(r.latitude, r.longitude)
                                    for r in cands.itertuples(index=False)]

    print(f"  GHI assigned:        {cands['ghi_kwh_m2_day'].notna().sum():,} / {len(cands)}")
    print(f"  Land cover assigned: {cands['land_cover_name'].notna().sum():,} / {len(cands)}")
    return cands

def compute_scores(df, existing_coords):
    """Apply all scoring functions and calculate the weighted total score."""
    df["ghi_score"]        = df["ghi_kwh_m2_day"].apply(score_ghi)
    df["land_cover_score"] = df["land_cover_name"].apply(score_land_cover)
    df["slope_score"]      = df["slope_degrees"].apply(score_slope)

    print("  Calculating proximity scores (may take a moment) ...")
    df["proximity_score"]  = df.apply(
        lambda row: score_proximity(row["latitude"], row["longitude"], existing_coords),
        axis=1
    )

    df["total_score"] = (
        df["ghi_score"]        * WEIGHTS["ghi"] +
        df["land_cover_score"] * WEIGHTS["land_cover"] +
        df["slope_score"]      * WEIGHTS["slope"] +
        df["proximity_score"]  * WEIGHTS["proximity"]
    ).round(2)

    df["rank"] = df["total_score"].rank(ascending=False, method="min").astype(int)
    return df

def get_real_acres_from_shapefile(df: pd.DataFrame) -> pd.Series:
    """
    Spatial join: for each candidate site, find the NJ land cover polygon
    it falls inside and return its real measured ACRES value.
    Falls back to LAND_COVER table estimates if shapefile is missing or a
    point doesn't intersect any polygon (e.g. on a boundary).
    """
    if not os.path.exists(SHAPEFILE_PATH):
        print("  Shapefile not found — using estimated areas.")
        return df["land_cover_name"].apply(
            lambda c: LAND_COVER.get(c, (0, 9.0, "greenfield"))[1]
        )

    print("  Loading NJ land cover shapefile for real area lookup ...")
    shp = gpd.read_file(SHAPEFILE_PATH)

   
    candidates_gdf = gpd.GeoDataFrame(
        df[["candidate_id"]].copy(),
        geometry=[Point(lon, lat) for lat, lon in zip(df["latitude"], df["longitude"])],
        crs="EPSG:4326",
    ).to_crs(shp.crs)

    joined = gpd.sjoin(candidates_gdf, shp[["ACRES", "geometry"]], how="left", predicate="within")

    fallback = df["land_cover_name"].apply(
        lambda c: LAND_COVER.get(c, (0, 9.0, "greenfield"))[1]
    )
    acres = joined["ACRES"].fillna(fallback).clip(lower=0.5)

    joined_count = joined["ACRES"].notna().sum()
    print(f"  Real area from shapefile: {joined_count}/{len(df)} sites "
          f"({len(df)-joined_count} used fallback estimates)")

    return acres.values


def attach_ml_predictions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Load the trained capacity model and predict expected MW for every candidate.
    Uses real polygon ACRES from the NJ land cover shapefile via spatial join.
    Falls back to per-cover estimates if shapefile unavailable.
    """
    if not os.path.exists(MODEL_PATH):
        print("  ML model not found — skipping capacity predictions.")
        print("  Run `python scripts/train_model.py` to build it.")
        df["predicted_capacity_mw"] = None
        return df

    with open(MODEL_PATH, "rb") as f:
        payload = pickle.load(f)

    model    = payload["model"]
    axis_map = payload["axis_map"]
    land_map = payload["land_map"]

    acres_series = get_real_acres_from_shapefile(df)

    rows = []
    for i, (_, row) in enumerate(df.iterrows()):
        cover      = row.get("land_cover_name", "")
        _, _, land_type = LAND_COVER.get(cover, (0, 9.0, "greenfield"))
        axis_enc   = axis_map.get("fixed-tilt", 0)
        land_enc   = land_map.get(land_type, 0)
        rows.append([
            float(acres_series[i]),
            row["latitude"],
            row["longitude"],
            180.0,
            20.0,
            axis_enc,
            land_enc,
            2024,
        ])

    X     = np.array(rows, dtype=float)
    preds = model.predict(X)
    df["predicted_capacity_mw"] = np.round(np.clip(preds, 0, None), 2)

    print(f"  ML predictions attached: median {np.median(preds):.1f} MW, "
          f"range {preds.min():.1f}–{preds.max():.1f} MW")
    return df


def save_scores(conn, df):
    """Write scores (including ML capacity prediction) to the site_scores table."""
    score_cols = [
        "candidate_id", "ghi_score", "land_cover_score", "slope_score",
        "proximity_score", "total_score", "ghi_kwh_m2_day",
        "land_cover_name", "slope_degrees", "rank", "predicted_capacity_mw"
    ]

    for col in score_cols:
        if col not in df.columns:
            df[col] = None

    out = df[score_cols].rename(columns={
        "ghi_kwh_m2_day": "ghi_value",
        "slope_degrees":  "slope_value"
    })

    conn.execute("DELETE FROM site_scores;")
    out.to_sql("site_scores", conn, if_exists="append", index=False)
    conn.commit()
    print(f"  Saved {len(out)} score rows.")

def print_top_sites(conn, n=10):
    """Print the top N sites using a SQL JOIN across three tables."""
    query = f"""
        SELECT
            ss.rank,
            ss.total_score,
            c.latitude,
            c.longitude,
            c.state,
            c.county,
            ss.ghi_value,
            ss.land_cover_name,
            ROUND(ss.slope_value, 1) AS slope_deg
        FROM site_scores ss
        JOIN candidate_sites c ON ss.candidate_id = c.candidate_id
        ORDER BY ss.total_score DESC
        LIMIT {n};
    """
    top = pd.read_sql(query, conn)
    print(f"\nTop {n} Solar Sites:")
    print(top.to_string(index=False))


if __name__ == "__main__":
    conn = get_conn()

    print("Loading existing solar site locations for proximity scoring ...")
    existing_coords = load_existing_coords(conn)
    print(f"  Found {len(existing_coords)} existing installations.")

    df = build_score_dataframe(conn)
    df = compute_scores(df, existing_coords)

    print("\nAttaching ML capacity predictions ...")
    df = attach_ml_predictions(df)

    save_scores(conn, df)
    print_top_sites(conn)

    conn.close()
    print("\nScoring complete. Next step: run scripts/export_results.py")
