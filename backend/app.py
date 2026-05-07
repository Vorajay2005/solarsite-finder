import sqlite3
import subprocess
import pickle
import os
import sys
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH      = os.path.join(PROJECT_ROOT, "database", "solar_site_finder.db")
SCRIPTS_DIR  = os.path.join(PROJECT_ROOT, "scripts")
MODEL_PATH   = os.path.join(PROJECT_ROOT, "models", "solar_capacity_model.pkl")

_model_cache = None

def load_model():
    """Load and cache the ML model payload from disk."""
    global _model_cache
    if _model_cache is None and os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            _model_cache = pickle.load(f)
    return _model_cache


def get_conn():
    """Return a SQLite connection with row_factory so rows act like dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def db_ready():
    """Return True if the database file exists and has site_scores rows."""
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        (n,) = conn.execute("SELECT COUNT(*) FROM site_scores;").fetchone()
        conn.close()
        return n > 0
    except Exception:
        return False



@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":    "ok",
        "db_ready":  db_ready(),
        "db_path":   DB_PATH,
        "version":   "2.0"
    })


@app.route("/api/sites", methods=["GET"])
def get_sites():
    """
    Return all scored candidate sites. Supports optional filters:
      ?state=NJ
      ?min_score=60
      ?land_cover=Pasture%2FHay
      ?max_slope=5
    """
    state      = request.args.get("state")
    county     = request.args.get("county")
    min_score  = request.args.get("min_score",  type=float, default=0)
    land_cover = request.args.get("land_cover")
    max_slope  = request.args.get("max_slope",  type=float)

    query = """
        SELECT
            c.candidate_id,
            c.latitude,
            c.longitude,
            c.state,
            c.county,
            ss.total_score,
            ss.ghi_score,
            ss.land_cover_score,
            ss.slope_score,
            ss.proximity_score,
            ss.ghi_value,
            ss.land_cover_name,
            ss.slope_value  AS slope_degrees,
            ss.rank,
            ss.predicted_capacity_mw
        FROM site_scores ss
        JOIN candidate_sites c ON ss.candidate_id = c.candidate_id
        WHERE ss.total_score >= ?
    """
    params = [min_score]

    if state:
        query += " AND c.state = ?"
        params.append(state.upper())
    if county:
        query += " AND c.county = ?"
        params.append(county)
    if land_cover:
        query += " AND ss.land_cover_name = ?"
        params.append(land_cover)
    if max_slope is not None:
        query += " AND (c.slope_degrees IS NULL OR c.slope_degrees <= ?)"
        params.append(max_slope)

    query += " ORDER BY ss.total_score DESC LIMIT 2000;"

    conn = get_conn()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows])


@app.route("/api/sites/top", methods=["GET"])
def get_top_sites():
    """Return the top N sites. Default N=20."""
    n     = request.args.get("n", type=int, default=20)
    state = request.args.get("state")

    query = """
        SELECT
            ss.rank,
            ss.total_score,
            c.candidate_id,
            c.latitude,
            c.longitude,
            c.state,
            c.county,
            ss.ghi_value,
            ss.ghi_score,
            ss.land_cover_name,
            ss.land_cover_score,
            ss.slope_value  AS slope_degrees,
            ss.slope_score,
            ss.proximity_score,
            ss.predicted_capacity_mw
        FROM site_scores ss
        JOIN candidate_sites c ON ss.candidate_id = c.candidate_id
    """
    params = []
    if state:
        query += " WHERE c.state = ?"
        params.append(state.upper())

    query += " ORDER BY ss.total_score DESC LIMIT ?;"
    params.append(n)

    conn = get_conn()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows])


@app.route("/api/site/<int:candidate_id>", methods=["GET"])
def get_site(candidate_id):
    """Return full detail for one candidate site."""
    conn = get_conn()

    site = conn.execute("""
        SELECT
            c.*,
            ss.total_score,
            ss.ghi_score,
            ss.land_cover_score,
            ss.slope_score,
            ss.proximity_score,
            ss.ghi_value,
            ss.land_cover_name,
            ss.slope_value  AS slope_degrees,
            ss.rank,
            ss.predicted_capacity_mw
        FROM candidate_sites c
        JOIN site_scores ss ON c.candidate_id = ss.candidate_id
        WHERE c.candidate_id = ?;
    """, [candidate_id]).fetchone()

    if site is None:
        conn.close()
        return jsonify({"error": "Site not found"}), 404

    nearby = conn.execute("""
        SELECT name, state, county, capacity_mw, install_year,
               latitude, longitude
        FROM existing_solar_sites
        WHERE ABS(latitude  - ?) < 0.5
          AND ABS(longitude - ?) < 0.5
        LIMIT 5;
    """, [site["latitude"], site["longitude"]]).fetchall()

    conn.close()
    return jsonify({
        "site":   dict(site),
        "nearby": [dict(r) for r in nearby]
    })


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """
    Aggregate statistics for the dashboard charts.
    Uses SQL GROUP BY, AVG, COUNT queries.
    """
    conn = get_conn()

    dist = conn.execute("""
        SELECT
            CASE
                WHEN total_score >= 70 THEN '70-100'
                WHEN total_score >= 60 THEN '60-69'
                WHEN total_score >= 50 THEN '50-59'
                WHEN total_score >= 40 THEN '40-49'
                ELSE '<40'
            END AS bucket,
            COUNT(*) AS count
        FROM site_scores
        GROUP BY bucket
        ORDER BY bucket DESC;
    """).fetchall()

    ghi_by_state = conn.execute("""
        SELECT
            c.county                       AS state,
            ROUND(AVG(ss.ghi_value), 2)   AS avg_ghi,
            ROUND(AVG(ss.total_score), 2) AS best_score,
            COUNT(*)                       AS site_count
        FROM site_scores ss
        JOIN candidate_sites c ON ss.candidate_id = c.candidate_id
        WHERE ss.ghi_value IS NOT NULL
          AND c.state = 'NJ'
        GROUP BY c.county
        ORDER BY best_score DESC
        LIMIT 10;
    """).fetchall()

    land_cover = conn.execute("""
        SELECT
            land_cover_name,
            COUNT(*) AS count,
            ROUND(AVG(total_score), 2) AS avg_score
        FROM site_scores
        WHERE land_cover_name IS NOT NULL
        GROUP BY land_cover_name
        ORDER BY count DESC;
    """).fetchall()

    existing = conn.execute("""
        SELECT
            county                      AS state,
            COUNT(*)                    AS count,
            ROUND(SUM(capacity_mw), 1)  AS total_mw
        FROM existing_solar_sites
        WHERE state = 'NJ'
          AND county IS NOT NULL
        GROUP BY county
        ORDER BY total_mw DESC
        LIMIT 12;
    """).fetchall()

    total_candidates = conn.execute("SELECT COUNT(*) FROM candidate_sites WHERE state = 'NJ';").fetchone()[0]
    total_scored     = conn.execute("SELECT COUNT(*) FROM site_scores;").fetchone()[0]
    total_existing   = conn.execute("SELECT COUNT(*) FROM existing_solar_sites WHERE state = 'NJ';").fetchone()[0]

    conn.close()

    return jsonify({
        "score_distribution": [dict(r) for r in dist],
        "ghi_by_state":       [dict(r) for r in ghi_by_state],
        "land_cover_counts":  [dict(r) for r in land_cover],
        "existing_by_state":  [dict(r) for r in existing],
        "totals": {
            "candidates": total_candidates,
            "scored":     total_scored,
            "existing":   total_existing
        }
    })


@app.route("/api/existing", methods=["GET"])
def get_existing():
    """Return existing solar installations, optionally filtered by state and/or county."""
    state  = request.args.get("state")
    county = request.args.get("county")
    conn   = get_conn()

    query  = "SELECT * FROM existing_solar_sites"
    where  = []
    params = []

    if state:
        where.append("state = ?")
        params.append(state.upper())
    if county:
        where.append("county = ?")
        params.append(county)

    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY capacity_mw DESC"
    if not state and not county:
        query += " LIMIT 200"

    rows = conn.execute(query + ";", params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/counties", methods=["GET"])
def get_counties():
    """Return distinct counties for a given state (default: NJ)."""
    state = request.args.get("state", "NJ")
    conn  = get_conn()
    rows  = conn.execute(
        """
        SELECT county, COUNT(*) AS site_count
        FROM candidate_sites
        WHERE state = ? AND county IS NOT NULL
        GROUP BY county
        ORDER BY county;
        """,
        [state.upper()]
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/ml/model-info", methods=["GET"])
def ml_model_info():
    """Return ML model performance metrics and feature importances."""
    payload = load_model()
    if payload is None:
        return jsonify({"error": "Model not trained yet. Run scripts/train_model.py."}), 404

    return jsonify({
        "metrics":      payload["metrics"],
        "importances":  payload["importances"],
        "feature_cols": payload["feature_cols"],
    })


@app.route("/api/ml/predict", methods=["POST"])
def ml_predict():
    """
    Predict expected AC capacity (MW) for a candidate site.

    Request body (JSON):
      area_acres       float   required  — estimated buildable area
      latitude         float   required
      longitude        float   required
      azimuth          float   optional  default 180.0 (south-facing)
      tilt             float   optional  default 20.0
      axis_type        string  optional  "fixed-tilt" | "single-axis" | "dual-axis"
      land_cover_type  string  optional  "greenfield" | "brownfield" | "landfill" | ...
      install_year     int     optional  default 2024

    Response:
      { "predicted_capacity_mw": 3.7, "model_r2": 0.9012 }
    """
    payload = load_model()
    if payload is None:
        return jsonify({"error": "Model not trained yet. Run scripts/train_model.py."}), 404

    data = request.get_json(force=True, silent=True) or {}

    missing = [f for f in ("area_acres", "latitude", "longitude") if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    try:
        axis_enc = payload["axis_map"].get(
            str(data.get("axis_type", "fixed-tilt")).lower().strip(), 0
        )
        land_enc = payload["land_map"].get(
            str(data.get("land_cover_type", "greenfield")).lower().strip(), 0
        )

        X = np.array([[
            float(data["area_acres"]),
            float(data["latitude"]),
            float(data["longitude"]),
            float(data.get("azimuth", 180.0)),
            float(data.get("tilt", 20.0)),
            axis_enc,
            land_enc,
            int(data.get("install_year", 2024)),
        ]])

        pred = float(payload["model"].predict(X)[0])
        pred = max(0.0, round(pred, 3))

    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400

    return jsonify({
        "predicted_capacity_mw": pred,
        "model_r2": payload["metrics"]["r2"],
    })


@app.route("/api/score/recalculate", methods=["POST"])
def recalculate():
    """
    Re-run the full pipeline: generate candidates -> score -> export.
    Useful after adding new dataset files to data/raw/.
    """
    python = sys.executable
    try:
        for script in ["generate_candidate_sites.py", "score_sites.py", "export_results.py"]:
            path = os.path.join(SCRIPTS_DIR, script)
            result = subprocess.run(
                [python, path],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                return jsonify({
                    "status": "error",
                    "script": script,
                    "stderr": result.stderr[-500:]
                }), 500

        return jsonify({"status": "ok", "message": "Recalculation complete."})

    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "Script timed out."}), 500


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print("WARNING: Database not found. Run the setup scripts first:")
        print("  python scripts/create_database.py")
        print("  python scripts/load_datasets.py")
        print("  python scripts/generate_candidate_sites.py")
        print("  python scripts/score_sites.py")

    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=True)
