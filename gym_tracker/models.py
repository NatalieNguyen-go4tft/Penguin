"""Domain models for GymHabitTracker.

All measurements are held in metric units (cm, kg, liters). Conversion to
and from imperial units happens at the edges, in ``units.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

WORKOUT_TYPES = (
    "Push",
    "Pull",
    "Legs",
    "Cardio",
    "Upper Body",
    "Lower Body",
    "Full Body",
    "Other",
)


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    """Return the Body Mass Index, rounded to one decimal place.

    Args:
        height_cm: Height in centimeters (must be positive).
        weight_kg: Weight in kilograms (must be positive).

    Raises:
        ValueError: If either value is not positive.
    """
    if height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Height and weight must be positive numbers.")
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def bmi_category(bmi: float) -> str:
    """Return the standard adult WHO category for a BMI value."""
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal weight"
    if bmi < 30:
        return "Overweight"
    return "Obese"


@dataclass
class User:
    """A snapshot of the user's body metrics.

    Attributes:
        height_cm: Height in centimeters.
        weight_kg: Weight in kilograms.
        age: Age in years.
        unit_system: Preferred display units, ``"metric"`` or ``"imperial"``.
        recorded_at: ISO timestamp set by the database when saved.
    """

    height_cm: float
    weight_kg: float
    age: int
    unit_system: str = "metric"
    recorded_at: Optional[str] = None

    def __post_init__(self) -> None:
        if self.height_cm <= 0 or self.weight_kg <= 0 or self.age <= 0:
            raise ValueError("Height, weight and age must be positive.")

    @property
    def bmi(self) -> float:
        """Body Mass Index for this snapshot."""
        return calculate_bmi(self.height_cm, self.weight_kg)

    @property
    def bmi_category(self) -> str:
        """Adult BMI category for this snapshot."""
        return bmi_category(self.bmi)


@dataclass
class Exercise:
    """A single exercise performed during a workout.

    ``weight_kg`` may be 0 for bodyweight movements.
    """

    name: str
    sets: int
    reps: int
    weight_kg: float = 0.0
    id: Optional[int] = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Exercise name cannot be empty.")
        if self.sets <= 0 or self.reps <= 0:
            raise ValueError("Sets and reps must be positive.")
        if self.weight_kg < 0:
            raise ValueError("Weight cannot be negative.")

    @property
    def volume_kg(self) -> float:
        """Total weight moved: sets x reps x weight."""
        return self.sets * self.reps * self.weight_kg


@dataclass
class Workout:
    """A logged workout session with optional exercises."""

    workout_date: date
    workout_type: str
    duration_min: int
    calories: int = 0
    water_l: float = 0.0
    exercises: List[Exercise] = field(default_factory=list)
    id: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.workout_type.strip():
            raise ValueError("Workout type cannot be empty.")
        if self.duration_min <= 0:
            raise ValueError("Duration must be positive.")
        if self.calories < 0 or self.water_l < 0:
            raise ValueError("Calories and water cannot be negative.")
