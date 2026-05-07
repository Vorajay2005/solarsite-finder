import sqlite3
import pandas as pd
import numpy as np
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH      = os.path.join(PROJECT_ROOT, "database", "solar_site_finder.db")
RAW_DIR      = os.path.join(PROJECT_ROOT, "data", "raw")
SAMPLE_DIR   = os.path.join(PROJECT_ROOT, "sample_data")

def get_conn():
    if not os.path.exists(DB_PATH):
        print("Database not found. Run scripts/create_database.py first.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def find_file(filename):
    """Prefer data/raw/ over sample_data/."""
    for d in [RAW_DIR, SAMPLE_DIR]:
        p = os.path.join(d, filename)
        if os.path.exists(p):
            label = "real data" if d == RAW_DIR else "sample data"
            print(f"  Using {label}: {p}")
            return p
    print(f"  WARNING: {filename} not found — skipping.")
    return None

def clean_coordinates(df, lat_col="latitude", lon_col="longitude"):
    """
    Ensure lat/lon are numeric and within valid Earth bounds.
    US bounds: lat 18–72, lon -180 to -60.
    Rows failing this check are logged and dropped.
    """
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")

    before = len(df)
    df = df.dropna(subset=[lat_col, lon_col])

    df = df[df[lat_col].between(17.0, 72.0)]
    df = df[df[lon_col].between(-180.0, -60.0)]

    dropped = before - len(df)
    if dropped:
        print(f"    [clean] Dropped {dropped} rows with invalid/out-of-bounds coordinates.")
    return df


def report_nulls(df, name):
    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    if nulls.empty:
        print(f"    [clean] {name}: no missing values.")
    else:
        print(f"    [clean] {name} missing values:")
        for col, n in nulls.items():
            pct = 100 * n / len(df)
            print(f"           {col}: {n} ({pct:.1f}%)")

USPVDB_RENAME = {
    "p_name":    "name",
    "p_state":   "state",
    "p_county":  "county",
    "ylat":      "latitude",
    "xlong":     "longitude",
    "p_cap_ac":  "capacity_mw",
    "p_area":    "area_acres",
    "p_type":    "land_cover_type",
    "p_year":    "install_year",
}

def load_existing_solar_sites(conn):
    """
    Load USPVDB solar installations.

    Data cleaning steps:
      1. Rename columns from USPVDB convention to our schema names.
      2. Drop rows with missing lat/lon (0 in this dataset, but verified).
      3. Validate US coordinate bounds.
      4. Cast capacity and area to float; install_year to integer.
      5. Standardize land_cover_type to title case.
      6. Report null counts for transparency.
    """
    print("\n[1] Loading: existing_solar_sites  (USPVDB)")
    path = find_file("uspvdb.csv")
    if not path:
        return

    df = pd.read_csv(path, low_memory=False)
    print(f"    Raw rows: {len(df)}")

    df = df.rename(columns=USPVDB_RENAME)

    df = clean_coordinates(df)

    df["capacity_mw"]  = pd.to_numeric(df["capacity_mw"],  errors="coerce")
    df["area_acres"]   = pd.to_numeric(df["area_acres"],   errors="coerce")
    df["install_year"] = pd.to_numeric(df["install_year"], errors="coerce").astype("Int64")
    before = len(df)
    df = df.dropna(subset=["capacity_mw"])
    if len(df) < before:
        print(f"    [clean] Dropped {before - len(df)} rows with null capacity_mw.")


    df["land_cover_type"] = df["land_cover_type"].str.strip().str.title()
    df["source"] = "USPVDB"

    report_nulls(df[["name","state","county","capacity_mw","area_acres","install_year"]], "USPVDB")

    schema_cols = ["name","state","county","latitude","longitude",
                   "capacity_mw","area_acres","land_cover_type","install_year","source"]
    df = df[schema_cols]

    conn.execute("DELETE FROM existing_solar_sites;")
    df.to_sql("existing_solar_sites", conn, if_exists="append", index=False)
    conn.commit()
    print(f"    Loaded {len(df)} rows — {len(df[df['state']=='NJ'])} are NJ sites.")


def _process_nsrdb_file(path):
    """
    Parse one NSRDB CSV file and return (lat, lon, ghi_kwh_m2_day, year).
    Returns None if the file cannot be parsed.

    NSRDB format:
      Row 1: metadata — Source, Location ID, Latitude, Longitude, Elevation, …
      Row 2: units row
      Row 3: column headers (Year, Month, Day, Hour, Minute, GHI, …)
      Row 4+: hourly readings
    """
    try:
        meta = pd.read_csv(path, nrows=1)
        lat  = float(meta["Latitude"].iloc[0])
        lon  = float(meta["Longitude"].iloc[0])

        df = pd.read_csv(path, skiprows=2)
        df["GHI"] = pd.to_numeric(df["GHI"], errors="coerce")
        df = df[df["GHI"] >= 0]           

        df["date"]  = pd.to_datetime(df[["Year", "Month", "Day"]])
        daily_sum   = df.groupby("date")["GHI"].sum()
        annual_avg  = round((daily_sum / 1000.0).mean(), 4)  

        year = int(df["Year"].iloc[0]) if len(df) else 2024
        return (lat, lon, annual_avg, year)
    except Exception:
        return None


def load_solar_radiation(conn):
    print("\n[2] Loading: solar_radiation  (NSRDB)")

    folder_path = os.path.join(RAW_DIR, "solar_radiation_nj")
    single_path = os.path.join(RAW_DIR, "solar_radiation_nj.csv")

    if os.path.isdir(folder_path):
        csv_files = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.endswith(".csv")
        ]
        print(f"    Found {len(csv_files)} NSRDB files in {folder_path}")
        if not csv_files:
            print("    WARNING: folder exists but contains no CSV files.")
            return

        rows = []
        errors = 0
        for i, fpath in enumerate(csv_files):
            result = _process_nsrdb_file(fpath)
            if result:
                rows.append(result)
            else:
                errors += 1
            if (i + 1) % 500 == 0:
                print(f"    Processed {i + 1}/{len(csv_files)} files …")

        if not rows:
            print("    ERROR: no files could be parsed.")
            return

        print(f"    Parsed {len(rows)} locations ({errors} files skipped due to errors).")

        ghi_values = [r[2] for r in rows]
        print(f"    GHI range: {min(ghi_values):.4f} – {max(ghi_values):.4f} kWh/m²/day")
        print(f"    GHI mean:  {sum(ghi_values)/len(ghi_values):.4f} kWh/m²/day")

        conn.execute("DELETE FROM solar_radiation;")
        conn.executemany("""
            INSERT INTO solar_radiation
                (latitude, longitude, ghi_kwh_m2_day, year, source)
            VALUES (?, ?, ?, ?, 'NSRDB');
        """, [(lat, lon, ghi, yr) for lat, lon, ghi, yr in rows])
        conn.commit()
        print(f"    Loaded {len(rows)} location rows into solar_radiation.")
        return

    if os.path.exists(single_path):
        print(f"    Using single-file fallback: {single_path}")
        result = _process_nsrdb_file(single_path)
        if not result:
            print("    ERROR: could not parse single radiation file.")
            return
        lat, lon, annual_avg_ghi, year = result
        print(f"    Location: lat={lat}, lon={lon}")
        print(f"    Annual average GHI: {annual_avg_ghi} kWh/m²/day")
        conn.execute("DELETE FROM solar_radiation;")
        conn.execute("""
            INSERT INTO solar_radiation
                (latitude, longitude, ghi_kwh_m2_day, year, source)
            VALUES (?, ?, ?, ?, 'NSRDB');
        """, (lat, lon, annual_avg_ghi, year))
        conn.commit()
        print("    Loaded 1 location row.")
        return

    path = find_file("solar_radiation_nj.csv")
    if path:
        result = _process_nsrdb_file(path)
        if result:
            lat, lon, annual_avg_ghi, year = result
            conn.execute("DELETE FROM solar_radiation;")
            conn.execute("""
                INSERT INTO solar_radiation
                    (latitude, longitude, ghi_kwh_m2_day, year, source)
                VALUES (?, ?, ?, ?, 'NSRDB');
            """, (lat, lon, annual_avg_ghi, year))
            conn.commit()
            print(f"    Loaded 1 location row (GHI={annual_avg_ghi}).")
    else:
        print("    WARNING: no solar radiation data found — skipping.")


NJ_TYPE_SUITABILITY = {
    "AGRICULTURE": "High",
    "BARREN LAND": "High",
    "FOREST":      "Low",
    "WETLANDS":    "Unsuitable",
    "WATER":       "Unsuitable",
    "URBAN":       "Low",
}

NJ_TYPE_CLASS_NAME = {
    "AGRICULTURE": "Cultivated Crops",
    "BARREN LAND": "Barren Land",
    "FOREST":      "Deciduous Forest",
    "WETLANDS":    "Woody Wetlands",
    "WATER":       "Open Water",
    "URBAN":       "Developed Low Intensity",
}


def load_land_cover(conn):
    """
    Load NJ Land Cover from the NJDEP 2020 shapefile and convert to a grid CSV.

    The shapefile uses NJ State Plane (EPSG:3424, feet) — not lat/lon.
    We must reproject to WGS84 before storing coordinates.

    Data cleaning steps:
      1. Load shapefile with geopandas.
      2. Drop rows with null geometry or null LU20/TYPE20 codes.
      3. Reproject from EPSG:3424 → EPSG:4326 (WGS84 lat/lon).
      4. Compute centroid of each polygon for our point-based schema.
      5. Filter out water bodies (Unsuitable for solar).
      6. Map NJ-specific land use codes to standardized class names and
         suitability ratings.
      7. Dissolve / aggregate by TYPE20 to reduce row count — we keep one
         representative centroid per 0.05° grid cell to match our candidate grid.
      8. Extract county from LABEL20 where possible; fall back to None.
      9. Report type distribution before and after filtering.
    """
    print("\n[3] Loading: land_cover  (NJ DEP Land Use 2020 Shapefile)")
    shp_path = os.path.join(RAW_DIR, "nj_land_cover", "Land_Use_2020.shp")
    if not os.path.exists(shp_path):
   
        path = find_file("land_cover.csv")
        if not path:
            return
        df = pd.read_csv(path)
        df = clean_coordinates(df)
        conn.execute("DELETE FROM land_cover;")
        df.to_sql("land_cover", conn, if_exists="append", index=False)
        conn.commit()
        print(f"    Loaded {len(df)} rows from sample CSV.")
        return

    print(f"  Using real data: {shp_path}")

    try:
        import geopandas as gpd
    except ImportError:
        print("    ERROR: geopandas not installed. Run: pip install geopandas")
        return

    def _read_shapefile(path):
        try:
            return gpd.read_file(path)
        except Exception as e:
            print(f"    ERROR: Failed to read shapefile with default engine: {e}")
            try:
                import fiona
                print("    Retrying with Fiona engine...")
                return gpd.read_file(path, engine="fiona")
            except ModuleNotFoundError:
                print("    ERROR: Fiona is not installed. Install it with `pip install fiona`.")
            except Exception as e2:
                print(f"    ERROR: Fiona fallback also failed: {e2}")
            raise

    try:
        gdf = _read_shapefile(shp_path)
    except Exception:
        print("    Aborting land cover load due to shapefile read failure.")
        return
    print(f"    Raw polygon rows: {len(gdf):,}  |  CRS: {gdf.crs}")

    before = len(gdf)
    gdf = gdf[gdf.geometry.notna()]
    gdf = gdf[gdf["TYPE20"].notna()]
    gdf = gdf[gdf["LU20"].notna()]
    print(f"    [clean] Dropped {before - len(gdf):,} rows with null geometry/code.")

    print("    Land type distribution (before filter):")
    for t, n in gdf["TYPE20"].value_counts().items():
        print(f"      {t:15s} {n:7,} polygons")

    gdf = gdf[gdf["TYPE20"] != "WATER"]
    print(f"    [clean] Dropped WATER polygons. Remaining: {len(gdf):,}")

    centroids_proj = gdf.geometry.centroid

    import geopandas as _gpd
    centroid_gdf = _gpd.GeoDataFrame(geometry=centroids_proj, crs=gdf.crs).to_crs(epsg=4326)
    gdf["latitude"]  = centroid_gdf.geometry.y.values
    gdf["longitude"] = centroid_gdf.geometry.x.values
    print("    Reprojected centroids to WGS84.")

    gdf["class_name"]  = gdf["TYPE20"].map(NJ_TYPE_CLASS_NAME)
    gdf["suitability"] = gdf["TYPE20"].map(NJ_TYPE_SUITABILITY)
    gdf["state"]       = "NJ"

    GRID_RES = 0.05
    gdf["lat_bin"] = (gdf["latitude"]  / GRID_RES).round(0) * GRID_RES
    gdf["lon_bin"] = (gdf["longitude"] / GRID_RES).round(0) * GRID_RES
    gdf["ACRES"]   = pd.to_numeric(gdf["ACRES"], errors="coerce").fillna(0)

    agg = (gdf.groupby(["lat_bin", "lon_bin", "class_name", "suitability", "state"])["ACRES"]
              .sum()
              .reset_index(name="total_acres"))

    idx      = agg.groupby(["lat_bin","lon_bin"])["total_acres"].idxmax()
    dominant = agg.loc[idx].reset_index(drop=True)
    dominant = dominant.rename(columns={"lat_bin": "latitude", "lon_bin": "longitude"})

    dominant["county"]          = None
    dominant["nlcd_class_code"] = None
    dominant = dominant.drop(columns=["total_acres"])
    dominant = clean_coordinates(dominant)

    print(f"    [clean] Grid-aggregated to {len(dominant):,} 0.05° cells.")
    print("    Suitability breakdown after aggregation:")
    print(dominant["suitability"].value_counts().to_string())

    conn.execute("DELETE FROM land_cover;")
    dominant.to_sql("land_cover", conn, if_exists="append", index=False)
    conn.commit()
    print(f"    Loaded {len(dominant)} rows into land_cover.")

def load_transmission(conn):
    """Load optional substation data from sample_data (no real file provided)."""
    print("\n[4] Loading: transmission_infrastructure")
    path = find_file("transmission_infrastructure.csv")
    if not path:
        return
    df = pd.read_csv(path)
    df = clean_coordinates(df)
    schema_cols = ["name","type","latitude","longitude","voltage_kv","state","source"]
    for col in schema_cols:
        if col not in df.columns:
            df[col] = None
    df = df[schema_cols]
    conn.execute("DELETE FROM transmission_infrastructure;")
    df.to_sql("transmission_infrastructure", conn, if_exists="append", index=False)
    conn.commit()
    print(f"    Loaded {len(df)} transmission rows.")


def print_summary(conn):
    print("\n══ Load Summary ══════════════════════════════")
    tables = ["existing_solar_sites","solar_radiation","land_cover","transmission_infrastructure"]
    for t in tables:
        try:
            (n,) = conn.execute(f"SELECT COUNT(*) FROM {t};").fetchone()
            print(f"  {t:<35} {n:>6} rows")
        except sqlite3.OperationalError:
            print(f"  {t}: table not found")
    print("══════════════════════════════════════════════")


if __name__ == "__main__":
    conn = get_conn()
    load_existing_solar_sites(conn)
    load_solar_radiation(conn)
    load_land_cover(conn)
    load_transmission(conn)
    print_summary(conn)
    conn.close()
    print("\nDone. Next step: python scripts/generate_candidate_sites.py")
