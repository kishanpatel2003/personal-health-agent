"""SQLite metric tools for the Bryan MCP server.

Each function is a plain ``async`` callable registered as an MCP tool by
``server.py``.  Actual database operations are delegated to
``bryan.db.queries`` so this layer stays thin.
"""

from __future__ import annotations

import json

from bryan.config import DB_PATH
from bryan.db import queries


VALID_KINDS = frozenset(
    ["weight", "nutrition", "workout", "symptom", "supplement", "sleep", "body_comp"]
)

# Maps MCP kind → queries.append_* function + expected JSON keys
_APPEND_DISPATCH = {
    "weight": (queries.append_weight, ["weight", "notes"]),
    "nutrition": (queries.append_nutrition, ["meal", "description", "calories", "protein", "carbs", "fat", "notes"]),
    "body_comp": (queries.append_body_comp, ["weight_lbs", "smm_lbs", "body_fat_pct", "fat_mass_lbs", "ffm_lbs", "bmi", "bmr_kcal", "visceral_fat", "score", "notes"]),
    "workout": (queries.append_workout, ["type", "duration_min", "exercises", "notes"]),
    "symptom": (queries.append_symptom, ["area", "severity", "description", "trigger", "notes"]),
    "supplement": (queries.append_supplement, ["supplement", "dose", "notes"]),
    "sleep": (queries.append_sleep, ["hours", "quality", "notes"]),
}


async def append_metric(kind: str, date: str, data: str) -> str:
    """Append a health metric data point.

    Parameters
    ----------
    kind:
        One of: weight, nutrition, workout, symptom, supplement, sleep,
        body_comp.
    date:
        ISO-8601 date string (YYYY-MM-DD).
    data:
        JSON string with metric-specific fields (e.g.
        ``{"weight": 185.4, "notes": "rest day"}`` for weight).

    Returns a confirmation message.
    """
    if kind not in VALID_KINDS:
        raise ValueError(f"Unknown metric kind '{kind}'. Must be one of: {sorted(VALID_KINDS)}")

    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ValueError(f"data is not valid JSON: {exc}") from exc

    fn, allowed_keys = _APPEND_DISPATCH[kind]
    kwargs = {k: payload[k] for k in allowed_keys if k in payload}
    await fn(DB_PATH, date, **kwargs)
    return f"Appended {kind} metric for {date}"


async def query_trend(metric: str, days: int = 14) -> str:
    """Query recent trend data for a given metric.

    Parameters
    ----------
    metric:
        Metric name (weight, nutrition, workout, symptom, supplement, sleep,
        body_comp).
    days:
        Number of days to look back (default 14).

    Returns formatted trend rows.
    """
    if metric not in VALID_KINDS:
        raise ValueError(f"Unknown metric '{metric}'. Must be one of: {sorted(VALID_KINDS)}")

    rows = await queries.query_metric(DB_PATH, metric, days)
    if not rows:
        return f"No {metric} data in the last {days} days."

    lines: list[str] = []
    for row in rows:
        parts = [f"{k}={v}" for k, v in row.items()]
        lines.append(" | ".join(parts))
    return "\n".join(lines)


async def get_adherence(start_date: str, end_date: str) -> str:
    """Return adherence rate for a date range.

    Parameters
    ----------
    start_date:
        Start of range (YYYY-MM-DD), inclusive.
    end_date:
        End of range (YYYY-MM-DD), inclusive.

    Returns a human-readable adherence summary.
    """
    result = await queries.get_adherence(DB_PATH, start_date, end_date)
    return (
        f"Adherence from {start_date} to {end_date}: "
        f"{result['pct']:.0f}% "
        f"({result['days_logged']}/{result['total_days']} days logged)"
    )
