import os
import sys
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.preprocessing import LabelEncoder

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA     = os.path.join(PROJECT_ROOT, "data", "raw", "uspvdb.csv")
MODELS_DIR   = os.path.join(PROJECT_ROOT, "models")
MODEL_PATH   = os.path.join(MODELS_DIR, "solar_capacity_model.pkl")



AXIS_MAP = {
    "fixed-tilt":             0,
    "fixed-tilt,single-axis": 1,
    "single-axis":            1,
    "dual-axis":              2,
}

LAND_MAP = {
    "greenfield":    0,
    "brownfield":    1,
    "landfill":      2,
    "landfill named":2,
    "superfund":     3,
    "AML":           3,
    "RCRA":          3,
    "PCSC":          4,
}


def load_and_prepare(path: str) -> pd.DataFrame:
    """Load USPVDB CSV and engineer features for training."""
    df = pd.read_csv(path, low_memory=False)

    df = df.rename(columns={
        "ylat":    "latitude",
        "xlong":   "longitude",
        "p_cap_ac":"capacity_mw",
        "p_area":  "area_m2",
        "p_year":  "install_year",
        "p_type":  "land_cover_type",
        "p_axis":  "axis_type",
        "p_azimuth":"azimuth",
        "p_tilt":  "tilt",
    })

    df["area_acres"] = df["area_m2"] * 0.000247105

    required = ["capacity_mw", "area_acres", "latitude", "longitude", "install_year"]
    df = df.dropna(subset=required)

    log_cap = np.log1p(df["capacity_mw"])
    mu, sigma = log_cap.mean(), log_cap.std()
    df = df[(log_cap >= mu - 3 * sigma) & (log_cap <= mu + 3 * sigma)]

    df = df[(df["capacity_mw"] > 0) & (df["area_acres"] > 0)]
    df = df[(df["latitude"].between(-90, 90)) & (df["longitude"].between(-180, 180))]

    df["axis_encoded"] = df["axis_type"].str.strip().str.lower().map(
        {k.lower(): v for k, v in AXIS_MAP.items()}
    ).fillna(0).astype(int)

    df["land_encoded"] = df["land_cover_type"].str.strip().str.lower().map(
        {k.lower(): v for k, v in LAND_MAP.items()}
    ).fillna(0).astype(int)

    df["tilt"]    = pd.to_numeric(df["tilt"],    errors="coerce").fillna(df["tilt"].median() if "tilt" in df else 20)
    df["azimuth"] = pd.to_numeric(df["azimuth"], errors="coerce").fillna(180.0)

    df["tilt"]         = df["tilt"].clip(0, 90)
    df["azimuth"]      = df["azimuth"].clip(0, 360)
    df["install_year"] = df["install_year"].clip(1980, 2025)

    return df


FEATURE_COLS = [
    "area_acres",
    "latitude",
    "longitude",
    "azimuth",
    "tilt",
    "axis_encoded",
    "land_encoded",
    "install_year",
]


def train(df: pd.DataFrame):
    """Train Random Forest; return model and metrics dict."""
    X = df[FEATURE_COLS].values
    y = df["capacity_mw"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=None,
        min_samples_leaf=3,
        max_features="sqrt",
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred  = model.predict(X_test)
    r2      = r2_score(y_test, y_pred)
    rmse    = np.sqrt(mean_squared_error(y_test, y_pred))
    mae     = mean_absolute_error(y_test, y_pred)

    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="r2", n_jobs=-1)

    metrics = {
        "r2":        round(float(r2),      4),
        "rmse_mw":   round(float(rmse),    3),
        "mae_mw":    round(float(mae),     3),
        "cv_r2_mean":round(float(cv_scores.mean()), 4),
        "cv_r2_std": round(float(cv_scores.std()),  4),
        "train_rows":len(X_train),
        "test_rows": len(X_test),
    }

    importances = dict(zip(FEATURE_COLS, model.feature_importances_.round(4).tolist()))

    return model, metrics, importances


def save_model(model, metrics: dict, importances: dict):
    os.makedirs(MODELS_DIR, exist_ok=True)
    payload = {
        "model":        model,
        "feature_cols": FEATURE_COLS,
        "axis_map":     AXIS_MAP,
        "land_map":     LAND_MAP,
        "metrics":      metrics,
        "importances":  importances,
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(payload, f)
    print(f"  Model saved → {MODEL_PATH}")


def predict_capacity(
    area_acres: float,
    latitude: float,
    longitude: float,
    azimuth: float = 180.0,
    tilt: float = 20.0,
    axis_type: str = "fixed-tilt",
    land_cover_type: str = "greenfield",
    install_year: int = 2024,
    model_payload: dict = None,
) -> float:
    if model_payload is None:
        with open(MODEL_PATH, "rb") as f:
            model_payload = pickle.load(f)

    axis_enc = model_payload["axis_map"].get(axis_type.lower().strip(), 0)
    land_enc = model_payload["land_map"].get(land_cover_type.lower().strip(), 0)

    X = np.array([[
        area_acres, latitude, longitude,
        azimuth, tilt, axis_enc, land_enc, install_year
    ]])
    pred = model_payload["model"].predict(X)[0]
    return round(max(0.0, float(pred)), 3)


if __name__ == "__main__":
    print("=" * 60)
    print("Solar Capacity Predictor — Model Training")
    print("=" * 60)

    if not os.path.exists(RAW_DATA):
        print(f"ERROR: Training data not found at {RAW_DATA}")
        sys.exit(1)

    print(f"\n1. Loading data from {RAW_DATA} ...")
    df = load_and_prepare(RAW_DATA)
    print(f"   Clean training rows: {len(df):,}")
    print(f"   Capacity range:      {df['capacity_mw'].min():.1f} – {df['capacity_mw'].max():.1f} MW")
    print(f"   Median capacity:     {df['capacity_mw'].median():.1f} MW")

    print("\n2. Training Random Forest Regressor ...")
    model, metrics, importances = train(df)

    print("\n3. Model performance:")
    print(f"   Test R²:             {metrics['r2']:.4f}  (target ≥ 0.80)")
    print(f"   Test RMSE:           {metrics['rmse_mw']:.2f} MW")
    print(f"   Test MAE:            {metrics['mae_mw']:.2f} MW")
    print(f"   CV R² (5-fold):      {metrics['cv_r2_mean']:.4f} ± {metrics['cv_r2_std']:.4f}")
    print(f"   Train / test split:  {metrics['train_rows']:,} / {metrics['test_rows']:,}")

    if metrics["r2"] < 0.80:
        print("\n   WARNING: R² below target. Check training data quality.")

    print("\n4. Feature importances:")
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        bar = "█" * int(imp * 40)
        print(f"   {feat:<20} {imp:.4f}  {bar}")

    print("\n5. Saving model ...")
    save_model(model, metrics, importances)

    print("\nTraining complete.")
    print(f"Run `python scripts/score_sites.py` to attach ML predictions to all candidate sites.")
