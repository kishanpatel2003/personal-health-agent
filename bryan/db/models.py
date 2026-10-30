"""Pydantic models for Bryan's health-metric tables."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WeightEntry(BaseModel):
    date: str
    weight_lbs: float
    notes: str | None = None
    rolling_avg: float | None = Field(default=None, description="14-day rolling average")


class NutritionEntry(BaseModel):
    id: int | None = None
    date: str
    meal: str
    description: str | None = None
    calories_est: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    notes: str | None = None


class DailyNutrition(BaseModel):
    """Aggregated macros for a single day."""

    date: str
    meal_count: int = 0
    total_calories: float | None = None
    total_protein_g: float | None = None
    total_carbs_g: float | None = None
    total_fat_g: float | None = None


class BodyCompEntry(BaseModel):
    date: str
    weight_lbs: float | None = None
    smm_lbs: float | None = None
    body_fat_pct: float | None = None
    fat_mass_lbs: float | None = None
    ffm_lbs: float | None = None
    bmi: float | None = None
    bmr_kcal: float | None = None
    visceral_fat: str | None = None
    score: int | None = None
    notes: str | None = None


class WorkoutEntry(BaseModel):
    id: int | None = None
    date: str
    type: str | None = None
    duration_min: int | None = None
    exercises: str | None = None
    notes: str | None = None


class SymptomEntry(BaseModel):
    id: int | None = None
    date: str
    area: str | None = None
    severity: int | None = Field(default=None, ge=1, le=10)
    description: str | None = None
    trigger: str | None = None
    notes: str | None = None


class SupplementEntry(BaseModel):
    id: int | None = None
    date: str
    supplement: str
    dose: str | None = None
    notes: str | None = None


class SleepEntry(BaseModel):
    date: str
    hours: float | None = None
    quality: int | None = Field(default=None, ge=1, le=10)
    notes: str | None = None


class PlateauStatus(BaseModel):
    """Result of the plateau-detection query."""

    window_start: str | None = None
    window_end: str | None = None
    data_points: int = 0
    avg_weight: float | None = None
    slope_lbs_per_day: float | None = None
    trend_status: str = "insufficient_data"

    @property
    def is_plateau(self) -> bool:
        return self.trend_status == "plateau"
