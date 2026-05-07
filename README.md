# Solar Site Finder — New Jersey

A full-stack data science application that identifies and scores optimal locations for utility-scale solar installations across New Jersey. Combines solar irradiance, land use, and existing installation data with a trained Random Forest model to rank 671 candidate sites.

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- ~3 GB free disk space

---

## Data Setup (Required Before Running)

Two large datasets are not included in this repo due to file size. Download and place them manually before running.

### 1. NJ Land Cover Shapefile

1. Download it from https://drive.google.com/drive/folders/1Hfkh73Ry9hC0ePL5hhAaE_8oSaunD7qQ?usp=sharing
2. Follow the below folder structure

```
data/raw/nj_land_cover/
├── LULC2020_ver1.shp
├── LULC2020_ver1.dbf
├── LULC2020_ver1.shx
├── LULC2020_ver1.prj
└── ...
```

### 2. Solar Radiation Data (NSRDB)

1. Download it from https://drive.google.com/drive/folders/1Hfkh73Ry9hC0ePL5hhAaE_8oSaunD7qQ?usp=sharing
2. Follow the below folder structure

```
data/raw/solar_radiation_nj/
├── 40.0_-74.5_psm3.csv
├── 39.5_-74.0_psm3.csv
└── ... (2,500+ files)
```

---

## Running the Project

From the project root:

```bash
./run.sh
```

This will run the full data pipeline (create DB, load datasets, generate candidate sites, train model, score sites), then start:
- Flask backend at `http://localhost:5001`
- React frontend at `http://localhost:5173`

> If the database already has scored sites, the pipeline is skipped and only the servers start.

---

## Scoring Methodology

Each site scores 0–100 across four weighted factors:

| Factor | Weight |
|---|---|
| Solar Irradiance (GHI) | 35% |
| Land Cover Suitability | 35% |
| Slope (flatness) | 20% |
| Proximity to Existing Sites | 10% |

Each site also includes an ML-predicted installed capacity (MW) from a Random Forest model trained on 6,611 real USPVDB installations.
