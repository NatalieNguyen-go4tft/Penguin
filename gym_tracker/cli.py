"""Interactive text menu for GymHabitTracker."""

from __future__ import annotations

from datetime import date
from typing import Callable, Dict, List, Optional

from .database import DatabaseManager
from .inputs import (
    prompt_choice,
    prompt_date,
    prompt_float,
    prompt_int,
    prompt_text,
    prompt_yes_no,
)
from .models import WORKOUT_TYPES, Exercise, User, Workout
from .stats import compute_stats
from .units import (
    CM_PER_INCH,
    METRIC,
    UNIT_SYSTEMS,
    UnitSystem,
    get_unit_system,
)

HISTORY_PAGE_SIZE = 20
BANNER = "=" * 40 + "\n        GYM HABIT TRACKER\n" + "=" * 40
MENU = """
Main Menu
  1. Log Workout
  2. View History
  3. View Stats
  4. Update Profile
  5. Exit"""


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


class CLIApp:
    """Text-based interface wired to a :class:`DatabaseManager`."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @property
    def units(self) -> UnitSystem:
        """Unit system from the saved profile (metric if none yet)."""
        profile = self.db.get_profile()
        return get_unit_system(profile.unit_system) if profile else METRIC

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Run the menu loop until the user exits.

        Ctrl+C inside an action cancels that action; Ctrl+C or Ctrl+D at the
        menu exits the app.
        """
        actions: Dict[str, Callable[[], None]] = {
            "1": self._log_workout,
            "2": self._view_history,
            "3": self._view_stats,
            "4": self._update_profile,
        }
        print(BANNER)
        try:
            if self.db.get_profile() is None:
                self._first_run_setup()
            while True:
                print(MENU)
                choice = input("Select an option: ").strip()
                if choice == "5":
                    break
                action = actions.get(choice)
                if action is None:
                    print("Invalid choice. Please enter a number from 1 to 5.")
                    continue
                try:
                    action()
                except KeyboardInterrupt:
                    print("\nCancelled.")
        except (KeyboardInterrupt, EOFError):
            print()
        print("Goodbye! Keep showing up.")

    def _first_run_setup(self) -> None:
        print("\nWelcome! No profile found yet.")
        if prompt_yes_no("Set up your profile now?", default=True):
            self._update_profile()

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------
    def _update_profile(self) -> None:
        current = self.db.get_profile()
        print("\n--- Update Profile ---")
        if current:
            print("Press Enter to keep a current value.")

        systems = list(UNIT_SYSTEMS.values())
        default_index = (
            [s.name for s in systems].index(current.unit_system) + 1
            if current
            else 1
        )
        chosen = prompt_choice(
            "Unit system",
            [s.description for s in systems],
            default_index=default_index,
        )
        units = next(s for s in systems if s.description == chosen)

        height_cm = self._prompt_height(
            units, current.height_cm if current else None
        )
        weight_kg = prompt_float(
            "Weight",
            20,
            500,
            unit=units.weight_label,
            factor=units.weight_factor,
            default=current.weight_kg if current else None,
        )
        age = prompt_int("Age", 10, 120, default=current.age if current else None)

        user = User(height_cm, weight_kg, age, unit_system=units.name)
        self.db.save_profile(user)
        print(f"\nProfile saved. BMI: {user.bmi:.1f} ({user.bmi_category})")

    @staticmethod
    def _prompt_height(units: UnitSystem, default_cm: Optional[float]) -> float:
        """Prompt for height in the user's units and return centimeters."""
        min_cm, max_cm = 50.0, 272.0
        if units.name == "metric":
            return prompt_float(
                "Height", min_cm, max_cm, unit="cm", default=default_cm
            )
        default_ft: Optional[int] = None
        default_in: Optional[int] = None
        if default_cm is not None:
            default_ft, default_in = divmod(round(default_cm / CM_PER_INCH), 12)
        while True:
            feet = prompt_int("Height, feet", 1, 8, default=default_ft)
            inches = prompt_float(
                "Height, inches", 0, 11.99, default=default_in
            )
            height_cm = (feet * 12 + inches) * CM_PER_INCH
            if min_cm <= height_cm <= max_cm:
                return height_cm
            print("  That height is outside the supported range. Try again.")

    # ------------------------------------------------------------------
    # Logging a workout
    # ------------------------------------------------------------------
    def _log_workout(self) -> None:
        print("\n--- Log Workout ---")
        units = self.units
        workout_date = prompt_date("Date (YYYY-MM-DD)", default=date.today())
        workout_type = prompt_choice("Workout type", WORKOUT_TYPES)
        duration = prompt_int("Duration (minutes)", 1, 1440)
        calories = prompt_int("Estimated calories burned", 0, 20000, default=0)
        water_l = prompt_float(
            "Water consumed",
            0,
            20,
            unit=units.water_label,
            factor=units.water_factor,
            default=0.0,
        )
        workout = Workout(
            workout_date=workout_date,
            workout_type=workout_type,
            duration_min=duration,
            calories=calories,
            water_l=water_l,
            exercises=self._prompt_exercises(units),
        )

        print("\nSummary")
        self._print_workout_detail(workout, units)
        if prompt_yes_no("\nSave this workout?", default=True):
            workout_id = self.db.add_workout(workout)
            print(f"Workout #{workout_id} saved.")
        else:
            print("Workout discarded.")

    @staticmethod
    def _prompt_exercises(units: UnitSystem) -> List[Exercise]:
        exercises: List[Exercise] = []
        label, default = "Add an exercise?", True
        while prompt_yes_no(label, default):
            name = prompt_text("  Exercise name")
            sets = prompt_int("  Sets", 1, 100)
            reps = prompt_int("  Reps per set", 1, 1000)
            weight_kg = prompt_float(
                "  Weight, 0 for bodyweight",
                0,
                1000,
                unit=units.weight_label,
                factor=units.weight_factor,
            )
            exercises.append(Exercise(name, sets, reps, weight_kg))
            label, default = "Add another exercise?", False
        return exercises

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    def _view_history(self) -> None:
        print("\n--- Workout History ---")
        units = self.units
        limit: Optional[int] = HISTORY_PAGE_SIZE
        while True:
            workouts = self.db.list_workouts(limit)
            if not workouts:
                print("No workouts logged yet.")
                return
            self._print_workout_table(workouts, units)
            total = self.db.count_workouts()
            if limit is not None and total > limit:
                print(f"Showing the {limit} most recent of {total}.")

            raw = (
                input("\nWorkout ID for details, 'all', or Enter to go back: ")
                .strip()
                .lower()
            )
            if not raw:
                return
            if raw == "all":
                limit = None
            elif raw.isdigit():
                workout = self.db.get_workout(int(raw))
                if workout is None:
                    print(f"No workout found with ID {raw}.")
                else:
                    print()
                    self._print_workout_detail(workout, units)
            else:
                print("Please enter a workout ID, 'all', or press Enter.")

    @staticmethod
    def _print_workout_table(workouts: List[Workout], units: UnitSystem) -> None:
        print(
            f"{'ID':>4}  {'Date':<10}  {'Type':<11}  {'Min':>4}  "
            f"{'Calories':>8}  {'Water':>10}"
        )
        print("-" * 56)
        for w in workouts:
            print(
                f"{w.id:>4}  {w.workout_date.isoformat():<10}  "
                f"{w.workout_type:<11}  {w.duration_min:>4}  "
                f"{w.calories:>8}  {units.format_water(w.water_l):>10}"
            )

    @staticmethod
    def _print_workout_detail(workout: Workout, units: UnitSystem) -> None:
        heading = f"{workout.workout_type} on {workout.workout_date.isoformat()}"
        if workout.id is not None:
            heading = f"#{workout.id}  {heading}"
        print(heading)
        print(
            f"  Duration: {workout.duration_min} min | "
            f"Calories: {workout.calories} | "
            f"Water: {units.format_water(workout.water_l)}"
        )
        if not workout.exercises:
            print("  No exercises logged.")
            return
        print(f"  {'Exercise':<24}{'Sets':>5}{'Reps':>6}  Weight")
        for e in workout.exercises:
            weight = (
                units.format_weight(e.weight_kg) if e.weight_kg > 0 else "bodyweight"
            )
            print(f"  {e.name:<24}{e.sets:>5}{e.reps:>6}  {weight}")

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def _view_stats(self) -> None:
        units = self.units
        stats = compute_stats(self.db)
        print("\n--- Consistency Stats ---")
        if stats.total_workouts == 0:
            print("No workouts logged yet. Log your first one from the menu.")
        else:
            print(f"Total workouts:    {stats.total_workouts}")
            print(f"Current streak:    {_plural(stats.current_streak, 'day')}")
            print(f"Longest streak:    {_plural(stats.longest_streak, 'day')}")
            print(f"Average duration:  {stats.avg_duration_min:.1f} min")
            week = _plural(stats.workouts_last_7_days, "workout")
            print(f"Last 7 days:       {week}")
            print(f"Total calories:    {stats.total_calories:,}")
            print(f"Total water:       {units.format_water(stats.total_water_l)}")
            if stats.current_streak == 0:
                print("\nNo active streak. Log a workout today to start one.")

        profile = self.db.get_profile()
        print("\n--- Body Metrics ---")
        if profile is None:
            print("No profile yet. Use 'Update Profile' to add one.")
            return
        print(f"Height:  {units.format_height(profile.height_cm)}")
        print(f"Weight:  {units.format_weight(profile.weight_kg)}")
        print(f"Age:     {profile.age}")
        print(f"BMI:     {profile.bmi:.1f} ({profile.bmi_category})")

        history = self.db.get_profile_history(limit=5)
        if len(history) > 1:
            print("\nRecent BMI history (newest first)")
            for snapshot in history:
                stamp = (snapshot.recorded_at or "")[:10]
                print(
                    f"  {stamp}  {units.format_weight(snapshot.weight_kg):>9}"
                    f"  BMI {snapshot.bmi:.1f}"
                )
