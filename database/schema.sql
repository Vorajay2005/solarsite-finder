
DROP TABLE IF EXISTS site_scores;
DROP TABLE IF EXISTS candidate_sites;
DROP TABLE IF EXISTS transmission_infrastructure;
DROP TABLE IF EXISTS land_cover;
DROP TABLE IF EXISTS solar_radiation;
DROP TABLE IF EXISTS existing_solar_sites;


CREATE TABLE existing_solar_sites (
    site_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT,                   -- facility name
    state           TEXT NOT NULL,          -- 2-letter state code (e.g. NJ)
    county          TEXT,
    latitude        REAL NOT NULL,          -- decimal degrees
    longitude       REAL NOT NULL,          -- decimal degrees
    capacity_mw     REAL,                   -- installed capacity in megawatts
    area_acres      REAL,                   -- site footprint
    land_cover_type TEXT,                   -- primary land cover at installation
    install_year    INTEGER,                -- year commissioned
    source          TEXT DEFAULT 'USPVDB'
);


CREATE TABLE solar_radiation (
    radiation_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    ghi_kwh_m2_day  REAL NOT NULL,          -- avg daily solar energy (key metric)
    dni_kwh_m2_day  REAL,                   -- direct normal irradiance
    dhi_kwh_m2_day  REAL,                   -- diffuse horizontal irradiance
    year            INTEGER DEFAULT 2022,
    source          TEXT DEFAULT 'NSRDB'
);


CREATE TABLE land_cover (
    cover_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    nlcd_class_code INTEGER,                -- NLCD numeric code (e.g. 81=Pasture)
    class_name      TEXT NOT NULL,          -- human-readable name
    suitability     TEXT,                   -- 'High', 'Medium', 'Low', 'Unsuitable'
    state           TEXT,
    county          TEXT
);


CREATE TABLE candidate_sites (
    candidate_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    state           TEXT NOT NULL,
    county          TEXT,
    grid_resolution REAL DEFAULT 0.1,       -- grid spacing in degrees
    slope_degrees   REAL,                   -- terrain slope (lower = better)
    created_at      TEXT DEFAULT (datetime('now'))
);


CREATE TABLE site_scores (
    score_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id        INTEGER NOT NULL,
    ghi_score           REAL,               -- 0-100, based on GHI value
    land_cover_score    REAL,               -- 0-100, based on land type
    slope_score         REAL,               -- 0-100, flatter = higher score
    proximity_score     REAL,               -- 0-100, distance from existing sites
    total_score         REAL NOT NULL,      -- weighted final score (0-100)
    ghi_value           REAL,              -- raw GHI used in scoring
    land_cover_name     TEXT,               -- land cover class at this site
    slope_value         REAL,               -- raw slope used
    rank                    INTEGER,            -- rank among all candidates
    predicted_capacity_mw   REAL,               -- ML model: predicted capacity in MW
    scored_at               TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (candidate_id) REFERENCES candidate_sites(candidate_id)
);


CREATE TABLE transmission_infrastructure (
    infra_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT,
    type            TEXT,                   -- 'substation' or 'transmission_line'
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    voltage_kv      REAL,
    state           TEXT,
    source          TEXT DEFAULT 'OpenStreetMap'
);

CREATE INDEX idx_candidate_state   ON candidate_sites(state);
CREATE INDEX idx_scores_total      ON site_scores(total_score DESC);
CREATE INDEX idx_scores_candidate  ON site_scores(candidate_id);
CREATE INDEX idx_radiation_coords  ON solar_radiation(latitude, longitude);
CREATE INDEX idx_landcover_coords  ON land_cover(latitude, longitude);
