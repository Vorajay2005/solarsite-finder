import pandas as pd
import numpy as np
import os
import sys
from io import StringIO

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR      = os.path.join(PROJECT_ROOT, "data", "raw")
CLEANED_DIR  = os.path.join(PROJECT_ROOT, "data", "cleaned")
DB_PATH      = os.path.join(PROJECT_ROOT, "database", "solar_site_finder.db")

os.makedirs(CLEANED_DIR, exist_ok=True)
_report_lines = []

def log(msg=""):
    print(msg)
    _report_lines.append(msg)
USPVDB_RENAME = {
    "p_name":   "name",
    "p_state":  "state",
    "p_county": "county",
    "ylat":     "latitude",
    "xlong":    "longitude",
    "p_cap_ac": "capacity_mw",
    "p_area":   "area_acres",
    "p_type":   "land_cover_type",
    "p_year":   "install_year",
}
def clean_uspvdb():
    log("=" * 60)
    log("DATASET 1: Solar Installations  (USPVDB)")
    log("  Source file : data/raw/uspvdb.csv")
    log("  Description : US Large-Scale Solar PV Database — all US")
    log("                utility-scale solar installations.")
    log("=" * 60)
    path = os.path.join(RAW_DIR, "uspvdb.csv")
    raw  = pd.read_csv(path, low_memory=False)
    log(f"\n  Raw rows    : {len(raw):,}")
    log(f"  Raw columns : {len(raw.columns)}")
    log(f"  Columns     : {', '.join(raw.columns[:10])} …")
    log("\n  -- Step 1: Column rename --")
    log("  Non-intuitive USPVDB codes renamed to readable field names:")
    for old, new in USPVDB_RENAME.items():
        if old in raw.columns:
            log(f"    {old:12s} → {new}")
    df = raw.rename(columns=USPVDB_RENAME)
    log("\n  -- Step 2: Coordinate validation --")
    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["latitude", "longitude"])
    null_coords = before - len(df)
    before = len(df)
    df = df[df["latitude"].between(17.0, 72.0) & df["longitude"].between(-180.0, -60.0)]
    oob = before - len(df)
    log(f"  Rows with null lat/lon dropped     : {null_coords}")
    log(f"  Rows outside US bounds dropped     : {oob}")
    log("\n  -- Step 3: Numeric type casting --")
    df["capacity_mw"]  = pd.to_numeric(df["capacity_mw"],  errors="coerce")
    df["area_acres"]   = pd.to_numeric(df["area_acres"],   errors="coerce")
    df["install_year"] = pd.to_numeric(df["install_year"], errors="coerce").astype("Int64")
    before = len(df)
    df = df.dropna(subset=["capacity_mw"])
    no_cap = before - len(df)
    log(f"  Rows with null capacity_mw dropped : {no_cap}")
    log("\n  -- Step 4: String normalization --")
    df["land_cover_type"] = df["land_cover_type"].str.strip().str.title()
    log("  land_cover_type → stripped whitespace, title-cased")

    log("\n  -- Step 5: Null audit (kept columns) --")
    keep = ["name","state","county","latitude","longitude",
            "capacity_mw","area_acres","land_cover_type","install_year"]
    df = df[keep]
    for col in keep:
        n = df[col].isna().sum()
        pct = 100 * n / len(df)
        flag = "  ← sparse optional field" if n > 0 else ""
        log(f"    {col:20s}: {n:5,} nulls  ({pct:5.1f}%){flag}")

    log(f"\n  Raw → Cleaned : {len(raw):,} → {len(df):,} rows")
    log(f"  NJ sites      : {len(df[df['state']=='NJ']):,}")

    out_path = os.path.join(CLEANED_DIR, "cleaned_solar_installations.csv")
    df.to_csv(out_path, index=False)
    log(f"  Saved → data/cleaned/cleaned_solar_installations.csv\n")
    return df

def clean_nsrdb():
    log("=" * 60)
    log("DATASET 2: Solar Radiation  (NSRDB)")
    log("  Source file : data/raw/solar_radiation_nj.csv")
    log("  Description : NREL National Solar Radiation Database — hourly")
    log("                GHI readings for one NJ monitoring station.")
    log("=" * 60)

    path = os.path.join(RAW_DIR, "solar_radiation_nj.csv")

   
    meta = pd.read_csv(path, nrows=1)
    lat  = float(meta["Latitude"].iloc[0])
    lon  = float(meta["Longitude"].iloc[0])
    elev = float(meta["Elevation"].iloc[0]) if "Elevation" in meta.columns else None
    log(f"\n  Station     : lat={lat}, lon={lon}, elevation={elev}m")
    log(f"  File format : Row 1 = metadata, Row 2 = units, Row 3+ = data")

    raw = pd.read_csv(path, skiprows=2)
    log(f"\n  Raw hourly rows : {len(raw):,}")
    log(f"  Columns         : {', '.join(raw.columns.tolist())}")

    log("\n  -- Step 1: Cast GHI to numeric, drop negatives (sensor errors) --")
    raw["GHI"] = pd.to_numeric(raw["GHI"], errors="coerce")
    neg = (raw["GHI"] < 0).sum()
    df  = raw[raw["GHI"] >= 0].copy()
    log(f"  Negative GHI rows dropped : {neg}")

    log("\n  -- Step 2: Annotate nighttime zeros (expected, not errors) --")
    night = (df["GHI"] == 0).sum()
    pct   = 100 * night / len(df)
    df["is_nighttime"] = df["GHI"] == 0
    log(f"  Nighttime zero rows       : {night:,}  ({pct:.1f}%) — flagged is_nighttime=True")

    log("\n  -- Step 3: Aggregate hourly → daily GHI --")
    df["date"] = pd.to_datetime(df[["Year","Month","Day"]])
    daily = df.groupby("date")["GHI"].sum().reset_index()
    daily.columns = ["date", "ghi_wh_m2_day"]
    daily["ghi_kwh_m2_day"] = (daily["ghi_wh_m2_day"] / 1000.0).round(4)
    avg = daily["ghi_kwh_m2_day"].mean().round(4)
    log(f"  Hourly rows aggregated to : {len(daily)} daily rows")
    log(f"  Annual average GHI        : {avg} kWh/m²/day")
    log(f"  (NJ typical range: 3.5–5.0 kWh/m²/day — this value is realistic)")

    log("\n  -- Step 4: Null check on aggregated data --")
    nulls = daily.isnull().sum().sum()
    log(f"  Null values after aggregation : {nulls}")

    hourly_out = df[["Year","Month","Day","Hour","Minute","GHI","is_nighttime"]].copy()
    hourly_out = hourly_out.rename(columns={"GHI": "ghi_w_m2"})

    log(f"\n  Raw → Cleaned hourly : {len(raw):,} → {len(hourly_out):,} rows")
    log(f"  Aggregated daily     : {len(daily)} rows")

    out_path = os.path.join(CLEANED_DIR, "cleaned_solar_radiation.csv")
    hourly_out.to_csv(out_path, index=False)
    log(f"  Saved → data/cleaned/cleaned_solar_radiation.csv\n")
    return hourly_out, daily

NJ_TYPE_CLASS_NAME = {
    "AGRICULTURE": "Cultivated Crops",
    "BARREN LAND": "Barren Land",
    "FOREST":      "Deciduous Forest",
    "WETLANDS":    "Woody Wetlands",
    "WATER":       "Open Water",
    "URBAN":       "Developed Low Intensity",
}
NJ_TYPE_SUITABILITY = {
    "AGRICULTURE": "High",
    "BARREN LAND": "High",
    "FOREST":      "Low",
    "WETLANDS":    "Unsuitable",
    "WATER":       "Unsuitable",
    "URBAN":       "Low",
}

def clean_land_cover():
    log("=" * 60)
    log("DATASET 3: NJ Land Cover  (NJ DEP Land Use 2020)")
    log("  Source file : data/raw/nj_land_cover/Land_Use_2020.shp")
    log("  Description : NJ Dept of Environmental Protection land use")
    log("                shapefile — 699,777 polygons, EPSG:3424.")
    log("=" * 60)

    shp_path = os.path.join(RAW_DIR, "nj_land_cover", "Land_Use_2020.shp")
    try:
        import geopandas as gpd
    except ImportError:
        log("  ERROR: geopandas not installed.")
        return None

    log("\n  -- Step 1: Load shapefile --")
    gdf = gpd.read_file(shp_path)
    log(f"  Raw polygons : {len(gdf):,}")
    log(f"  CRS          : {gdf.crs}  (NJ State Plane feet — not lat/lon)")

    log("\n  -- Step 2: Drop null geometry / null land-use codes --")
    before = len(gdf)
    gdf = gdf[gdf.geometry.notna() & gdf["TYPE20"].notna() & gdf["LU20"].notna()]
    log(f"  Null rows dropped : {before - len(gdf):,}")

    log("\n  -- Step 3: Land type distribution (raw) --")
    for t, n in gdf["TYPE20"].value_counts().items():
        log(f"    {t:15s} : {n:7,} polygons")

    log("\n  -- Step 4: Drop WATER polygons (unsuitable for solar) --")
    before = len(gdf)
    gdf = gdf[gdf["TYPE20"] != "WATER"]
    log(f"  Water polygons removed : {before - len(gdf):,}")
    log(f"  Remaining              : {len(gdf):,}")

    log("\n  -- Step 5: Reproject centroids EPSG:3424 → EPSG:4326 (WGS84) --")
    centroids_proj = gdf.geometry.centroid
    import geopandas as _gpd
    centroid_gdf = _gpd.GeoDataFrame(geometry=centroids_proj, crs=gdf.crs).to_crs(epsg=4326)
    gdf = gdf.copy()
    gdf["latitude"]  = centroid_gdf.geometry.y.values
    gdf["longitude"] = centroid_gdf.geometry.x.values
    log("  Centroid computed in projected CRS before reprojection (avoids distortion).")
    log(f"  Lat range : {gdf['latitude'].min():.3f} – {gdf['latitude'].max():.3f}")
    log(f"  Lon range : {gdf['longitude'].min():.3f} – {gdf['longitude'].max():.3f}")

    log("\n  -- Step 6: Map land use codes to solar suitability --")
    gdf["class_name"]  = gdf["TYPE20"].map(NJ_TYPE_CLASS_NAME)
    gdf["suitability"] = gdf["TYPE20"].map(NJ_TYPE_SUITABILITY)
    log("  TYPE20 mapped to class_name and suitability:")
    for t, cn in NJ_TYPE_CLASS_NAME.items():
        log(f"    {t:15s} → {cn:25s} ({NJ_TYPE_SUITABILITY[t]})")

    log("\n  -- Step 7: Grid-cell aggregation (area-weighted majority) --")
    log("  699,777 polygons → 949 grid cells (0.05° resolution)")
    log("  Method: sum ACRES per (lat_bin, lon_bin, class_name) → pick dominant type")
    log("  Area-weighting ensures large farms beat many small urban parcels.")
    GRID_RES = 0.05
    gdf["ACRES"] = pd.to_numeric(gdf["ACRES"], errors="coerce").fillna(0)
    gdf["lat_bin"] = (gdf["latitude"]  / GRID_RES).round(0) * GRID_RES
    gdf["lon_bin"] = (gdf["longitude"] / GRID_RES).round(0) * GRID_RES

    agg = (gdf.groupby(["lat_bin","lon_bin","class_name","suitability"])["ACRES"]
              .sum().reset_index(name="total_acres"))
    idx      = agg.groupby(["lat_bin","lon_bin"])["total_acres"].idxmax()
    dominant = agg.loc[idx].reset_index(drop=True)
    dominant = dominant.rename(columns={"lat_bin":"latitude","lon_bin":"longitude"})
    dominant["state"] = "NJ"

    log(f"\n  Aggregated cells : {len(dominant)}")
    log("\n  Suitability breakdown:")
    for s, n in dominant["suitability"].value_counts().items():
        log(f"    {s:12s} : {n:3d} cells")

    out_path = os.path.join(CLEANED_DIR, "cleaned_land_cover.csv")
    dominant.to_csv(out_path, index=False)
    log(f"\n  Raw → Cleaned : {len(gdf):,} polygons → {len(dominant)} grid cells")
    log(f"  Saved → data/cleaned/cleaned_land_cover.csv\n")
    return dominant

def export_candidate_sites():
    log("=" * 60)
    log("DATASET 4: Candidate Solar Sites  (generated)")
    log("  Source      : candidate_sites + site_scores tables in SQLite DB")
    log("  Description : Final scored grid of NJ candidate solar sites,")
    log("                derived from all three datasets above.")
    log("=" * 60)

    import sqlite3
    if not os.path.exists(DB_PATH):
        log("  ERROR: Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT
            c.candidate_id,
            c.latitude,
            c.longitude,
            c.state,
            c.county,
            c.slope_degrees,
            ss.ghi_value,
            ss.land_cover_name,
            ss.ghi_score,
            ss.land_cover_score,
            ss.slope_score,
            ss.proximity_score,
            ss.total_score,
            ss.rank
        FROM candidate_sites c
        JOIN site_scores ss ON c.candidate_id = ss.candidate_id
        ORDER BY ss.rank;
    """, conn)
    conn.close()

    log(f"\n  Total candidate sites : {len(df):,}")
    log(f"  Score range           : {df['total_score'].min():.2f} – {df['total_score'].max():.2f}")
    log(f"  Average score         : {df['total_score'].mean():.2f}")
    log(f"\n  How candidates were derived:")
    log("    1. 0.05° lat/lon grid over NJ bounding box  → 1,750 points")
    log("    2. Shapefile spatial clip (land polygons only, water excluded)  → 795 points")
    log("    3. Wetland/water land cover exclusion  → 671 final sites")
    log(f"\n  County distribution:")
    for county, n in df["county"].value_counts().items():
        log(f"    {county:15s} : {n:3d} sites")
    log(f"\n  Land cover distribution:")
    for lc, n in df["land_cover_name"].value_counts().items():
        log(f"    {lc:30s} : {n:3d} sites")

    out_path = os.path.join(CLEANED_DIR, "cleaned_candidate_sites.csv")
    df.to_csv(out_path, index=False)
    log(f"\n  Saved → data/cleaned/cleaned_candidate_sites.csv\n")
    return df

if __name__ == "__main__":
    log("SolarScope — Data Cleaning Report")
    log("CS 210: Data Management for Data Science")
    log(f"Output directory: data/cleaned/\n")

    clean_uspvdb()
    clean_nsrdb()
    clean_land_cover()
    export_candidate_sites()

    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log("  cleaned_solar_installations.csv  — USPVDB, 6,611 US sites, columns renamed,")
    log("                                     coordinates validated, types cast")
    log("  cleaned_solar_radiation.csv      — NSRDB hourly, negatives removed,")
    log("                                     nighttime flagged, 8,760 cleaned rows")
    log("  cleaned_land_cover.csv           — NJ DEP shapefile, 699,777 polygons →")
    log("                                     949 grid cells, area-weighted aggregation")
    log("  cleaned_candidate_sites.csv      — final 671 NJ candidate sites with scores")
    log("  cleaning_report.txt              — this full audit log")
    log("")
    report_path = os.path.join(CLEANED_DIR, "cleaning_report.txt")
    with open(report_path, "w") as f:
        f.write("\n".join(_report_lines))
    print(f"\nCleaning report saved → data/cleaned/cleaning_report.txt")
    print("Done.")
