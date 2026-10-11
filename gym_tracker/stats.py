"""Consistency statistics and streak calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Optional

from .database import DatabaseManager


def current_streak(dates: Iterable[date], today: Optional[date] = None) -> int:
    """Return the current run of consecutive workout days.

    The streak stays alive if the latest workout was today or yesterday, so
    the user is not penalised before they have had a chance to train today.
    """
    today = today or date.today()
    unique = set(dates)
    cursor = today if today in unique else today - timedelta(days=1)
    streak = 0
    while cursor in unique:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def longest_streak(dates: Iterable[date]) -> int:
    """Return the longest run of consecutive workout days ever logged."""
    longest = run = 0
    previous: Optional[date] = None
    for day in sorted(set(dates)):
        if previous is not None and (day - previous).days == 1:
            run += 1
        else:
            run = 1
        longest = max(longest, run)
        previous = day
    return longest


@dataclass(frozen=True)
class ConsistencyStats:
    """Summary of workout consistency."""

    total_workouts: int
    current_streak: int
    longest_streak: int
    avg_duration_min: float
    total_calories: int
    total_water_l: float
    workouts_last_7_days: int


def compute_stats(
    db: DatabaseManager, today: Optional[date] = None
) -> ConsistencyStats:
    """Build a :class:`ConsistencyStats` from the database."""
    today = today or date.today()
    dates = db.get_workout_dates()
    totals = db.get_totals()
    return ConsistencyStats(
        total_workouts=int(totals["total"]),
        current_streak=current_streak(dates, today),
        longest_streak=longest_streak(dates),
        avg_duration_min=float(totals["avg_duration"]),
        total_calories=int(totals["calories"]),
        total_water_l=float(totals["water"]),
        workouts_last_7_days=db.count_workouts(since=today - timedelta(days=6)),
    )
