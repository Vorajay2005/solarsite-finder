import sqlite3
import pandas as pd
import os
import sys

PROJECT_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH        = os.path.join(PROJECT_ROOT, "database", "solar_site_finder.db")
PROCESSED_DIR  = os.path.join(PROJECT_ROOT, "data", "processed")
OUTPUT_CSV     = os.path.join(PROCESSED_DIR, "top_sites.csv")

TOP_N = 50   

def get_conn():
    if not os.path.exists(DB_PATH):
        print("Database not found. Run scripts/create_database.py first.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def export_top_sites(conn):
    """Write the top N ranked sites to a CSV file."""
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    query = f"""
        SELECT
            ss.rank,
            ss.total_score,
            c.latitude,
            c.longitude,
            c.state,
            c.county,
            ss.ghi_value          AS ghi_kwh_m2_day,
            ss.ghi_score,
            ss.land_cover_name,
            ss.land_cover_score,
            ss.slope_value        AS slope_degrees,
            ss.slope_score,
            ss.proximity_score
        FROM site_scores ss
        JOIN candidate_sites c ON ss.candidate_id = c.candidate_id
        ORDER BY ss.total_score DESC
        LIMIT {TOP_N};
    """
    df = pd.read_sql(query, conn)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Exported top {len(df)} sites to: {OUTPUT_CSV}")
    return df


def print_statistics(conn):
    """
    Print summary statistics that are useful in a final report.
    Demonstrates SQL aggregate queries (COUNT, AVG, MAX, MIN, GROUP BY).
    """
    print("\n========== Summary Statistics ==========\n")

    total_candidates = conn.execute("SELECT COUNT(*) FROM candidate_sites;").fetchone()[0]
    total_scored     = conn.execute("SELECT COUNT(*) FROM site_scores;").fetchone()[0]
    print(f"Total candidate sites:    {total_candidates}")
    print(f"Scored sites:             {total_scored}")

    stats = pd.read_sql("""
        SELECT
            ROUND(MIN(total_score), 2)  AS min_score,
            ROUND(AVG(total_score), 2)  AS avg_score,
            ROUND(MAX(total_score), 2)  AS max_score
        FROM site_scores;
    """, conn)
    print("\nScore distribution:")
    print(stats.to_string(index=False))

    by_state = pd.read_sql("""
        SELECT
            c.state,
            COUNT(*)                       AS site_count,
            ROUND(AVG(ss.total_score), 2)  AS avg_score,
            ROUND(MAX(ss.total_score), 2)  AS best_score,
            ROUND(AVG(ss.ghi_value),   2)  AS avg_ghi
        FROM site_scores ss
        JOIN candidate_sites c ON ss.candidate_id = c.candidate_id
        GROUP BY c.state
        ORDER BY best_score DESC;
    """, conn)
    print("\nResults by state:")
    print(by_state.to_string(index=False))
    land_summary = pd.read_sql("""
        SELECT
            land_cover_name,
            COUNT(*)                       AS site_count,
            ROUND(AVG(total_score), 2)     AS avg_score
        FROM (
            SELECT land_cover_name, total_score
            FROM site_scores
            WHERE land_cover_name IS NOT NULL
            ORDER BY total_score DESC
            LIMIT 100
        ) top100
        GROUP BY land_cover_name
        ORDER BY site_count DESC;
    """, conn)
    print("\nLand cover breakdown (top 100 sites):")
    print(land_summary.to_string(index=False))
    existing = pd.read_sql("""
        SELECT
            state,
            COUNT(*)                    AS installations,
            ROUND(SUM(capacity_mw), 1)  AS total_mw,
            ROUND(AVG(capacity_mw), 1)  AS avg_mw
        FROM existing_solar_sites
        GROUP BY state
        ORDER BY total_mw DESC;
    """, conn)
    print("\nExisting solar installations by state:")
    print(existing.to_string(index=False))

    print("\n=========================================")

if __name__ == "__main__":
    conn = get_conn()
    df = export_top_sites(conn)
    print_statistics(conn)
    conn.close()
    print("\nExport complete. Results are in data/processed/top_sites.csv")
