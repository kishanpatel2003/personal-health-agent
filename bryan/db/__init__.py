"""Bryan database layer — schema, models, and async query helpers."""

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
from .queries import (
    append_body_comp,
    append_nutrition,
    append_sleep,
    append_supplement,
    append_symptom,
    append_weight,
    append_workout,
    detect_plateau,
    get_adherence,
    get_body_comp_trend,
    get_daily_nutrition,
    get_nutrition_entries,
    get_weight_trend,
    init_db,
    query_metric,
)

__all__ = [
    # Models
    "BodyCompEntry",
    "DailyNutrition",
    "NutritionEntry",
    "PlateauStatus",
    "SleepEntry",
    "SupplementEntry",
    "SymptomEntry",
    "WeightEntry",
    "WorkoutEntry",
    # Init
    "init_db",
    # Append
    "append_body_comp",
    "append_nutrition",
    "append_sleep",
    "append_supplement",
    "append_symptom",
    "append_weight",
    "append_workout",
    # Query
    "detect_plateau",
    "get_adherence",
    "get_body_comp_trend",
    "get_daily_nutrition",
    "get_nutrition_entries",
    "get_weight_trend",
    "query_metric",
]
