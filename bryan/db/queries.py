"""Async database helpers for Bryan's health-metric store."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

from .models import (
    BodyCompEntry,
    DailyNutrition,
    NutritionEntry,
    PlateauStatus,
    SleepEntry,
    SupplementEntry,
    SymptomEntry,
    WeightEntry,
    WorkoutEntry,
)

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


# ------------------------------------------------------------------
# Initialisation
# ------------------------------------------------------------------

async def init_db(db_path: Path) -> None:
    """Create empty tables, indexes, and views (idempotent)."""
    schema_sql = _SCHEMA_PATH.read_text()
    async with aiosqlite.connect(str(db_path)) as db:
        await db.executescript(schema_sql)
        await db.commit()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _row_to_dict(cursor: aiosqlite.Cursor, row: tuple) -> dict:
    """Convert a raw row tuple to a dict keyed by column name."""
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


async def _connect(db_path: Path) -> aiosqlite.Connection:
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    return db


# ------------------------------------------------------------------
# Append helpers
# ------------------------------------------------------------------

async def append_weight(
    db_path: Path,
    date: str,
    weight: float,
    notes: str | None = None,
) -> WeightEntry:
    """Insert or replace a weight entry."""
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "INSERT OR REPLACE INTO weight_log (date, weight_lbs, notes) VALUES (?, ?, ?)",
            (date, weight, notes),
        )
        await db.commit()
    return WeightEntry(date=date, weight_lbs=weight, notes=notes)


async def append_nutrition(
    db_path: Path,
    date: str,
    meal: str,
    description: str | None = None,
    calories: float | None = None,
    protein: float | None = None,
    carbs: float | None = None,
    fat: float | None = None,
    notes: str | None = None,
) -> NutritionEntry:
    """Insert a nutrition log entry."""
    async with aiosqlite.connect(str(db_path)) as db:
        cursor = await db.execute(
            """INSERT INTO nutrition_log
               (date, meal, description, calories_est, protein_g, carbs_g, fat_g, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (date, meal, description, calories, protein, carbs, fat, notes),
        )
        await db.commit()
        row_id = cursor.lastrowid
    return NutritionEntry(
        id=row_id, date=date, meal=meal, description=description,
        calories_est=calories, protein_g=protein, carbs_g=carbs,
        fat_g=fat, notes=notes,
    )


async def append_body_comp(
    db_path: Path,
    date: str,
    weight_lbs: float | None = None,
    smm_lbs: float | None = None,
    body_fat_pct: float | None = None,
    fat_mass_lbs: float | None = None,
    ffm_lbs: float | None = None,
    bmi: float | None = None,
    bmr_kcal: float | None = None,
    visceral_fat: str | None = None,
    score: int | None = None,
    notes: str | None = None,
) -> BodyCompEntry:
    """Insert or replace a body-composition entry."""
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            """INSERT OR REPLACE INTO body_comp_log
               (date, weight_lbs, smm_lbs, body_fat_pct, fat_mass_lbs,
                ffm_lbs, bmi, bmr_kcal, visceral_fat, score, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (date, weight_lbs, smm_lbs, body_fat_pct, fat_mass_lbs,
             ffm_lbs, bmi, bmr_kcal, visceral_fat, score, notes),
        )
        await db.commit()
    return BodyCompEntry(
        date=date, weight_lbs=weight_lbs, smm_lbs=smm_lbs,
        body_fat_pct=body_fat_pct, fat_mass_lbs=fat_mass_lbs,
        ffm_lbs=ffm_lbs, bmi=bmi, bmr_kcal=bmr_kcal,
        visceral_fat=visceral_fat, score=score, notes=notes,
    )


async def append_workout(
    db_path: Path,
    date: str,
    type: str | None = None,
    duration_min: int | None = None,
    exercises: str | None = None,
    notes: str | None = None,
) -> WorkoutEntry:
    """Insert a workout entry."""
    async with aiosqlite.connect(str(db_path)) as db:
        cursor = await db.execute(
            """INSERT INTO workout_log (date, type, duration_min, exercises, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (date, type, duration_min, exercises, notes),
        )
        await db.commit()
        row_id = cursor.lastrowid
    return WorkoutEntry(
        id=row_id, date=date, type=type, duration_min=duration_min,
        exercises=exercises, notes=notes,
    )


async def append_symptom(
    db_path: Path,
    date: str,
    area: str | None = None,
    severity: int | None = None,
    description: str | None = None,
    trigger: str | None = None,
    notes: str | None = None,
) -> SymptomEntry:
    """Insert a symptom entry."""
    async with aiosqlite.connect(str(db_path)) as db:
        cursor = await db.execute(
            """INSERT INTO symptom_log (date, area, severity, description, trigger, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (date, area, severity, description, trigger, notes),
        )
        await db.commit()
        row_id = cursor.lastrowid
    return SymptomEntry(
        id=row_id, date=date, area=area, severity=severity,
        description=description, trigger=trigger, notes=notes,
    )


async def append_supplement(
    db_path: Path,
    date: str,
    supplement: str,
    dose: str | None = None,
    notes: str | None = None,
) -> SupplementEntry:
    """Insert a supplement entry."""
    async with aiosqlite.connect(str(db_path)) as db:
        cursor = await db.execute(
            """INSERT INTO supplement_log (date, supplement, dose, notes)
               VALUES (?, ?, ?, ?)""",
            (date, supplement, dose, notes),
        )
        await db.commit()
        row_id = cursor.lastrowid
    return SupplementEntry(
        id=row_id, date=date, supplement=supplement, dose=dose, notes=notes,
    )


async def append_sleep(
    db_path: Path,
    date: str,
    hours: float | None = None,
    quality: int | None = None,
    notes: str | None = None,
) -> SleepEntry:
    """Insert or replace a sleep entry."""
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "INSERT OR REPLACE INTO sleep_log (date, hours, quality, notes) VALUES (?, ?, ?, ?)",
            (date, hours, quality, notes),
        )
        await db.commit()
    return SleepEntry(date=date, hours=hours, quality=quality, notes=notes)


# ------------------------------------------------------------------
# Query helpers
# ------------------------------------------------------------------

async def get_weight_trend(db_path: Path, days: int = 14) -> list[WeightEntry]:
    """Return recent weight entries with 14-day rolling average."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                w.date,
                w.weight_lbs,
                w.notes,
                ROUND(AVG(w2.weight_lbs), 2) AS rolling_avg
            FROM weight_log w
            JOIN weight_log w2
                ON w2.date BETWEEN DATE(w.date, '-13 days') AND w.date
            WHERE w.date >= DATE('now', ? || ' days')
            GROUP BY w.date
            ORDER BY w.date
            """,
            (str(-days),),
        )
        rows = await cursor.fetchall()
    return [
        WeightEntry(
            date=r["date"],
            weight_lbs=r["weight_lbs"],
            notes=r["notes"],
            rolling_avg=r["rolling_avg"],
        )
        for r in rows
    ]


async def get_daily_nutrition(db_path: Path, date: str) -> DailyNutrition:
    """Return aggregated macros for a single day."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM v_daily_nutrition WHERE date = ?", (date,)
        )
        row = await cursor.fetchone()
    if row is None:
        return DailyNutrition(date=date)
    return DailyNutrition(
        date=row["date"],
        meal_count=row["meal_count"],
        total_calories=row["total_calories"],
        total_protein_g=row["total_protein_g"],
        total_carbs_g=row["total_carbs_g"],
        total_fat_g=row["total_fat_g"],
    )


async def get_nutrition_entries(db_path: Path, date: str) -> list[NutritionEntry]:
    """Return individual meal entries for a day."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM nutrition_log WHERE date = ? ORDER BY id", (date,)
        )
        rows = await cursor.fetchall()
    return [NutritionEntry(**dict(r)) for r in rows]


async def get_adherence(
    db_path: Path,
    start_date: str,
    end_date: str,
) -> dict:
    """Return weight-logging adherence between two dates.

    Returns a dict with keys: start_date, end_date, days_logged, total_days, pct.
    """
    async with aiosqlite.connect(str(db_path)) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM weight_log WHERE date BETWEEN ? AND ?",
            (start_date, end_date),
        )
        (days_logged,) = await cursor.fetchone()

        cursor = await db.execute(
            "SELECT CAST(JULIANDAY(?) - JULIANDAY(?) + 1 AS INTEGER)",
            (end_date, start_date),
        )
        (total_days,) = await cursor.fetchone()

    total_days = max(total_days or 0, 1)
    return {
        "start_date": start_date,
        "end_date": end_date,
        "days_logged": days_logged,
        "total_days": total_days,
        "pct": round(days_logged * 100 / total_days, 1),
    }


async def get_body_comp_trend(db_path: Path) -> list[BodyCompEntry]:
    """Return all InBody scans ordered by date."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM v_body_comp_trend")
        rows = await cursor.fetchall()
    return [BodyCompEntry(**dict(r)) for r in rows]


async def detect_plateau(db_path: Path, days: int = 14) -> PlateauStatus:
    """Check if weight trend is plateauing over the given window.

    Uses a simple linear-regression slope. Returns a PlateauStatus model.
    """
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        # We compute on the fly rather than using the view so the caller
        # can control the window size.
        cursor = await db.execute(
            """
            WITH numbered AS (
                SELECT
                    date,
                    weight_lbs,
                    JULIANDAY(date) AS jd
                FROM weight_log
                WHERE date >= DATE('now', ? || ' days')
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
            FROM slope_calc
            """,
            (str(-days),),
        )
        row = await cursor.fetchone()
    if row is None:
        return PlateauStatus()
    return PlateauStatus(**dict(row))


async def query_metric(
    db_path: Path,
    metric_name: str,
    days: int = 30,
) -> list[dict]:
    """Generic trend query across supported metrics.

    Supported metric_name values:
      weight, nutrition, body_comp, workouts, symptoms, supplements, sleep

    Returns a list of dicts (raw rows).
    """
    table_map: dict[str, tuple[str, str]] = {
        "weight":      ("weight_log",     "date, weight_lbs, notes"),
        "nutrition":   ("nutrition_log",   "date, meal, description, calories_est, protein_g, carbs_g, fat_g, notes"),
        "body_comp":   ("body_comp_log",   "date, weight_lbs, smm_lbs, body_fat_pct, score, notes"),
        "workouts":    ("workout_log",     "date, type, duration_min, exercises, notes"),
        "symptoms":    ("symptom_log",     "date, area, severity, description, trigger, notes"),
        "supplements": ("supplement_log",  "date, supplement, dose, notes"),
        "sleep":       ("sleep_log",       "date, hours, quality, notes"),
    }

    if metric_name not in table_map:
        raise ValueError(
            f"Unknown metric '{metric_name}'. Choose from: {', '.join(table_map)}"
        )

    table, cols = table_map[metric_name]
    query = f"SELECT {cols} FROM {table} WHERE date >= DATE('now', ? || ' days') ORDER BY date"  # noqa: S608

    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, (str(-days),))
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]
