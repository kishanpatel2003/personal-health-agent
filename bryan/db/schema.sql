-- Bryan health-performance agent: SQLite schema

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ============================================================
-- Tables
-- ============================================================

CREATE TABLE IF NOT EXISTS weight_log (
    date        TEXT PRIMARY KEY,   -- ISO-8601 date (YYYY-MM-DD)
    weight_lbs  REAL NOT NULL,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS nutrition_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,      -- YYYY-MM-DD
    meal        TEXT NOT NULL,      -- breakfast / lunch / dinner / snack
    description TEXT,
    calories_est REAL,
    protein_g   REAL,
    carbs_g     REAL,
    fat_g       REAL,
    notes       TEXT
);
CREATE INDEX IF NOT EXISTS idx_nutrition_date ON nutrition_log(date);

CREATE TABLE IF NOT EXISTS body_comp_log (
    date            TEXT PRIMARY KEY,   -- YYYY-MM-DD
    weight_lbs      REAL,
    smm_lbs         REAL,              -- skeletal muscle mass
    body_fat_pct    REAL,
    fat_mass_lbs    REAL,
    ffm_lbs         REAL,              -- fat-free mass
    bmi             REAL,
    bmr_kcal        REAL,
    visceral_fat    TEXT,
    score           INTEGER,           -- InBody score
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS workout_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    type         TEXT,                  -- push / pull / legs / cardio / etc.
    duration_min INTEGER,
    exercises    TEXT,                  -- JSON array or freeform
    notes        TEXT
);
CREATE INDEX IF NOT EXISTS idx_workout_date ON workout_log(date);

CREATE TABLE IF NOT EXISTS symptom_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    area        TEXT,
    severity    INTEGER CHECK(severity BETWEEN 1 AND 10),
    description TEXT,
    trigger     TEXT,
    notes       TEXT
);
CREATE INDEX IF NOT EXISTS idx_symptom_date ON symptom_log(date);

CREATE TABLE IF NOT EXISTS supplement_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    supplement  TEXT NOT NULL,
    dose        TEXT,
    notes       TEXT
);
CREATE INDEX IF NOT EXISTS idx_supplement_date ON supplement_log(date);

CREATE TABLE IF NOT EXISTS sleep_log (
    date    TEXT PRIMARY KEY,
    hours   REAL,
    quality INTEGER CHECK(quality BETWEEN 1 AND 10),
    notes   TEXT
);

-- ============================================================
-- Views
-- ============================================================

-- 14-day rolling average weight
CREATE VIEW IF NOT EXISTS v_weight_trend_14d AS
SELECT
    w.date,
    w.weight_lbs,
    ROUND(AVG(w2.weight_lbs), 2) AS rolling_avg_14d,
    COUNT(w2.weight_lbs)         AS data_points
FROM weight_log w
JOIN weight_log w2
    ON w2.date BETWEEN DATE(w.date, '-13 days') AND w.date
GROUP BY w.date
ORDER BY w.date;

-- Weekly adherence: days with a weight entry per ISO week
CREATE VIEW IF NOT EXISTS v_weekly_adherence AS
SELECT
    STRFTIME('%Y-W%W', date) AS week,
    MIN(date)                AS week_start,
    MAX(date)                AS week_end,
    COUNT(*)                 AS days_logged,
    ROUND(COUNT(*) * 100.0 / 7, 1) AS pct_adherence
FROM weight_log
GROUP BY STRFTIME('%Y-W%W', date)
ORDER BY week;

-- All InBody scans ordered chronologically
CREATE VIEW IF NOT EXISTS v_body_comp_trend AS
SELECT
    date,
    weight_lbs,
    smm_lbs,
    body_fat_pct,
    fat_mass_lbs,
    ffm_lbs,
    bmi,
    bmr_kcal,
    visceral_fat,
    score,
    notes
FROM body_comp_log
ORDER BY date;

-- Daily macro totals
CREATE VIEW IF NOT EXISTS v_daily_nutrition AS
SELECT
    date,
    COUNT(*)                     AS meal_count,
    ROUND(SUM(calories_est), 0)  AS total_calories,
    ROUND(SUM(protein_g), 1)     AS total_protein_g,
    ROUND(SUM(carbs_g), 1)       AS total_carbs_g,
    ROUND(SUM(fat_g), 1)         AS total_fat_g
FROM nutrition_log
GROUP BY date
ORDER BY date;

-- Plateau detection: flag when the 14-day weight trend slope is near-zero
-- Uses a simple linear regression (slope) over the most recent N entries.
-- A plateau is flagged when |slope| < 0.03 lbs/day (~0.2 lbs/week)
-- and there are at least 7 data points in the window.
CREATE VIEW IF NOT EXISTS v_plateau_detection AS
WITH numbered AS (
    SELECT
        date,
        weight_lbs,
        JULIANDAY(date) AS jd
    FROM weight_log
    WHERE date >= DATE('now', '-14 days')
),
stats AS (
    SELECT
        COUNT(*)        AS n,
        AVG(jd)         AS mean_x,
        AVG(weight_lbs) AS mean_y,
        MIN(date)       AS window_start,
        MAX(date)       AS window_end
    FROM numbered
),
slope_calc AS (
    SELECT
        s.n,
        s.window_start,
        s.window_end,
        s.mean_y AS avg_weight,
        CASE
            WHEN s.n < 2 THEN NULL
            ELSE ROUND(
                SUM((n.jd - s.mean_x) * (n.weight_lbs - s.mean_y))
                / NULLIF(SUM((n.jd - s.mean_x) * (n.jd - s.mean_x)), 0),
            4)
        END AS slope_lbs_per_day
    FROM numbered n, stats s
    GROUP BY s.n, s.window_start, s.window_end, s.mean_y
)
SELECT
    window_start,
    window_end,
    n           AS data_points,
    avg_weight,
    slope_lbs_per_day,
    CASE
        WHEN n < 7                          THEN 'insufficient_data'
        WHEN ABS(slope_lbs_per_day) < 0.03  THEN 'plateau'
        WHEN slope_lbs_per_day < 0           THEN 'losing'
        ELSE                                      'gaining'
    END AS trend_status
FROM slope_calc;
