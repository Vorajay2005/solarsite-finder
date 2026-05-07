# Solar Site Finder — New Jersey

A full-stack data science application that identifies and scores optimal locations for utility-scale solar installations across New Jersey. Combines solar irradiance, land use, and existing installation data with a trained Random Forest model to rank 671 candidate sites.

---

## Demo

<!-- Replace the URL below with your actual demo video link (YouTube, Loom, Google Drive, etc.) -->

[![Demo Video](https://img.shields.io/badge/Watch%20Demo-Click%20Here-blue)](https://youtu.be/A6LnCbixREw)

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- ~3 GB free disk space

---

## Data Setup (Required Before Running)

Two large datasets are not included in this repo due to file size. Download and place them manually before running.

> [!WARNING]
> The pipeline looks for these datasets in specific subfolders inside `data/raw/`.
> Placing files directly in `data/raw/` instead of the subfolders will cause the pipeline to fail.

---

### 1. NJ Land Cover Shapefile

**Download:** https://drive.google.com/drive/folders/1Hfkh73Ry9hC0ePL5hhAaE_8oSaunD7qQ?usp=sharing

**Steps:**

**Step 1** — Open the Google Drive link. You will see a folder called `nj_land_cover` containing these files:

```
nj_land_cover/
├── Land_Use_2020.cpg
├── Land_Use_2020.dbf
├── Land_Use_2020.prj
├── Land_Use_2020.shp
├── Land_Use_2020.shp.xml
└── Land_Use_2020.shx
```

**Step 2** — Download the **entire folder** (right-click → Download). Do not download files one by one.

**Step 3** — Extract the zip and place the folder so your project looks like this:

```
data/
└── raw/
    └── nj_land_cover/          ← the folder goes HERE
        ├── Land_Use_2020.cpg
        ├── Land_Use_2020.dbf
        ├── Land_Use_2020.prj
        ├── Land_Use_2020.shp
        ├── Land_Use_2020.shp.xml
        └── Land_Use_2020.shx
```

> [!IMPORTANT]
> The folder must be named `nj_land_cover` and must sit directly inside `data/raw/`.
> The pipeline specifically looks for `data/raw/nj_land_cover/Land_Use_2020.shp`.

---

### 2. Solar Radiation Data (NSRDB)

**Download:** https://drive.google.com/drive/folders/12w_R22HhN09R_mgZdBEBRvGh6h4m3_cE

**Steps:**

**Step 1** — Open the Google Drive link. You will see a folder called `solar_radiation_nj` containing thousands of CSV files like:

```
solar_radiation_nj/
├── 1194517_41.33_-75.54_2024.csv
├── 1194518_41.29_-75.54_2024.csv
├── 1194519_41.25_-75.54_2024.csv
└── ... (2,500+ files)
```

**Step 2** — Download the **entire folder** (right-click → Download). Do not download files one by one.

**Step 3** — Extract the zip and place the folder so your project looks like this:

```
data/
└── raw/
    └── solar_radiation_nj/     ← the folder goes HERE
        ├── 1194517_41.33_-75.54_2024.csv
        ├── 1194518_41.29_-75.54_2024.csv
        └── ... (2,500+ files)
```

> [!IMPORTANT]
> The folder must be named `solar_radiation_nj` and must sit directly inside `data/raw/`.
> The pipeline scans every `.csv` inside this folder — if the folder is missing or empty, solar radiation data will not load.

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

| Factor                      | Weight |
| --------------------------- | ------ |
| Solar Irradiance (GHI)      | 35%    |
| Land Cover Suitability      | 35%    |
| Slope (flatness)            | 20%    |
| Proximity to Existing Sites | 10%    |

Each site also includes an ML-predicted installed capacity (MW) from a Random Forest model trained on 6,611 real USPVDB installations.

---

## Folder structure

```text
solarsite-finder/
├── backend/
│   ├── app.py
│   └── requirements.txt
├── data/
│   ├── cleaned/
│   ├── processed/
│   └── raw/
│       ├── nj_land_cover/
│       │   ├── Land_Use_2020.{cpg,dbf,prj,shp,shp.xml,shx}
│       ├── solar_radiation_nj/
│       │   ├── *.csv  (thousands of per-lat/lon files)
│       ├── solar_radiation_nj.csv
│       └── uspvdb.csv
├── database/
│   ├── schema.sql
│   └── solar_site_finder.db
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FilterPanel.jsx
│   │   │   ├── MapView.jsx
│   │   │   ├── SiteDetailModal.jsx
│   │   │   ├── StatsCharts.jsx
│   │   │   └── TopSitesList.jsx
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── vite.config.js
├── models/
├── notebooks/
│   └── solar_analysis.ipynb
├── scripts/
│   ├── create_database.py
│   ├── export_cleaned_data.py
│   ├── export_results.py
│   ├── generate_candidate_sites.py
│   ├── load_datasets.py
│   ├── score_sites.py
│   └── train_model.py
├── .gitignore
├── README.md
└── run.sh
```
