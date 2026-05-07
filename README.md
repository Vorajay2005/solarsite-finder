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

1. Download the shapefile from the [NJ DEP Open Data portal](https://www.nj.gov/dep/gis/digidownload/zips/OpenData/LULC2020_ver1.zip) (~300–600 MB zip).
2. Extract the zip — you'll get files like `LULC2020_ver1.shp`, `.dbf`, `.shx`, `.prj`, etc.
3. Place **all extracted files** into `data/raw/nj_land_cover/`.

```
data/raw/nj_land_cover/
├── LULC2020_ver1.shp
├── LULC2020_ver1.dbf
├── LULC2020_ver1.shx
├── LULC2020_ver1.prj
└── ...
```

### 2. Solar Radiation Data (NSRDB)

1. Create a free account at [https://nsrdb.nrel.gov/data-viewer](https://nsrdb.nrel.gov/data-viewer).
2. Draw a bounding box over New Jersey (lat 38.9–41.4, lon -75.6 to -73.9).
3. Select **PSM v3**, year **2020**, **hourly** resolution, then request the download.
4. NREL will email you a link — download and extract the zip (2,500+ CSV files).
5. Place **all CSV files** into `data/raw/solar_radiation_nj/`.

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
