"""SQLite persistence layer for GymHabitTracker."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from types import TracebackType
from typing import Dict, List, Optional, Type, Union

from .models import Exercise, User, Workout

DEFAULT_DB_PATH = "gym_tracker.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS user_profile (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    height_cm   REAL    NOT NULL CHECK (height_cm > 0),
    weight_kg   REAL    NOT NULL CHECK (weight_kg > 0),
    age         INTEGER NOT NULL CHECK (age > 0),
    bmi         REAL    NOT NULL,
    unit_system TEXT    NOT NULL DEFAULT 'metric',
    recorded_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS workouts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_date TEXT    NOT NULL,
    workout_type TEXT    NOT NULL,
    duration_min INTEGER NOT NULL CHECK (duration_min > 0),
    calories     INTEGER NOT NULL DEFAULT 0 CHECK (calories >= 0),
    water_l      REAL    NOT NULL DEFAULT 0 CHECK (water_l >= 0)
);
CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts (workout_date);

CREATE TABLE IF NOT EXISTS exercises (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL REFERENCES workouts (id) ON DELETE CASCADE,
    name       TEXT    NOT NULL,
    sets       INTEGER NOT NULL CHECK (sets > 0),
    reps       INTEGER NOT NULL CHECK (reps > 0),
    weight_kg  REAL    NOT NULL DEFAULT 0 CHECK (weight_kg >= 0)
);
CREATE INDEX IF NOT EXISTS idx_exercises_workout ON exercises (workout_id);
"""


class DatabaseManager:
    """Thin wrapper around a SQLite connection.

    Usable as a context manager::

        with DatabaseManager("gym_tracker.db") as db:
            db.save_profile(User(175, 70, 25))

    Pass ``":memory:"`` for a throwaway in-memory database (used in tests).
    """

    def __init__(self, db_path: Union[str, Path] = DEFAULT_DB_PATH) -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()

    def __enter__(self) -> "DatabaseManager":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()

    # ------------------------------------------------------------------
    # User profile
    # ------------------------------------------------------------------
    def save_profile(self, user: User) -> None:
        """Store a new profile snapshot.

        Profiles are append-only so BMI can be tracked over time. The most
        recent row is the current profile.
        """
        recorded_at = datetime.now().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                "INSERT INTO user_profile "
                "(height_cm, weight_kg, age, bmi, unit_system, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    user.height_cm,
                    user.weight_kg,
                    user.age,
                    user.bmi,
                    user.unit_system,
                    recorded_at,
                ),
            )

    def get_profile(self) -> Optional[User]:
        """Return the current profile, or None if none has been saved."""
        history = self.get_profile_history(limit=1)
        return history[0] if history else None

    def get_profile_history(self, limit: int = 10) -> List[User]:
        """Return profile snapshots, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM user_profile ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            User(
                height_cm=r["height_cm"],
                weight_kg=r["weight_kg"],
                age=r["age"],
                unit_system=r["unit_system"],
                recorded_at=r["recorded_at"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Workouts
    # ------------------------------------------------------------------
    def add_workout(self, workout: Workout) -> int:
        """Insert a workout and its exercises in a single transaction.

        Returns:
            The new workout's id (also set on ``workout.id``).
        """
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO workouts "
                "(workout_date, workout_type, duration_min, calories, water_l) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    workout.workout_date.isoformat(),
                    workout.workout_type,
                    workout.duration_min,
                    workout.calories,
                    workout.water_l,
                ),
            )
            workout_id = cursor.lastrowid
            assert workout_id is not None
            self._conn.executemany(
                "INSERT INTO exercises (workout_id, name, sets, reps, weight_kg) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (workout_id, e.name, e.sets, e.reps, e.weight_kg)
                    for e in workout.exercises
                ],
            )
        workout.id = workout_id
        return workout_id

    def list_workouts(self, limit: Optional[int] = None) -> List[Workout]:
        """Return workouts (without exercises), newest first."""
        query = "SELECT * FROM workouts ORDER BY workout_date DESC, id DESC"
        params: tuple = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_workout(r) for r in rows]

    def get_workout(self, workout_id: int) -> Optional[Workout]:
        """Return one workout including its exercises, or None."""
        row = self._conn.execute(
            "SELECT * FROM workouts WHERE id = ?", (workout_id,)
        ).fetchone()
        if row is None:
            return None
        workout = self._row_to_workout(row)
        exercise_rows = self._conn.execute(
            "SELECT * FROM exercises WHERE workout_id = ? ORDER BY id",
            (workout_id,),
        ).fetchall()
        workout.exercises = [
            Exercise(
                id=r["id"],
                name=r["name"],
                sets=r["sets"],
                reps=r["reps"],
                weight_kg=r["weight_kg"],
            )
            for r in exercise_rows
        ]
        return workout

    def count_workouts(self, since: Optional[date] = None) -> int:
        """Count workouts, optionally only those on or after ``since``."""
        if since is None:
            row = self._conn.execute("SELECT COUNT(*) FROM workouts").fetchone()
        else:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM workouts WHERE workout_date >= ?",
                (since.isoformat(),),
            ).fetchone()
        return int(row[0])

    def get_workout_dates(self) -> List[date]:
        """Return each distinct date that has at least one workout."""
        rows = self._conn.execute(
            "SELECT DISTINCT workout_date FROM workouts"
        ).fetchall()
        return [date.fromisoformat(r["workout_date"]) for r in rows]

    def get_totals(self) -> Dict[str, float]:
        """Return aggregate totals: total, avg_duration, calories, water."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS total, "
            "COALESCE(AVG(duration_min), 0) AS avg_duration, "
            "COALESCE(SUM(calories), 0) AS calories, "
            "COALESCE(SUM(water_l), 0) AS water "
            "FROM workouts"
        ).fetchone()
        return {key: row[key] for key in row.keys()}

    @staticmethod
    def _row_to_workout(row: sqlite3.Row) -> Workout:
        return Workout(
            id=row["id"],
            workout_date=date.fromisoformat(row["workout_date"]),
            workout_type=row["workout_type"],
            duration_min=row["duration_min"],
            calories=row["calories"],
            water_l=row["water_l"],
        )
