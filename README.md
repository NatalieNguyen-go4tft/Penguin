# GymHabitTracker

A command-line app for tracking gym attendance, workouts and body metrics over time. Data is stored locally in a SQLite database using only the Python standard library, so there is nothing to install.

## Requirements

- Python 3.9 or newer
- No third-party packages

## Setup and Run

```bash
cd GymHabitTracker
python main.py
```

On first launch the app offers to set up your profile (height, weight, age). The database file `gym_tracker.db` is created in the current directory. To use a different file:

```bash
python main.py --db /path/to/my_tracker.db
```

Run the tests:

```bash
python -m unittest discover -s tests -v
```

## Features

**Main menu**

| Option | What it does |
|--------|--------------|
| 1. Log Workout | Record date, type, duration, calories, water and any number of exercises |
| 2. View History | Table of past workouts (duration, calories, water); enter an ID to see its exercises |
| 3. View Stats | Consistency stats, current body metrics and recent BMI history |
| 4. Update Profile | Change height, weight, age and unit system |
| 5. Exit | Quit the app |

**Logging a workout**
- Date defaults to today. Press Enter to accept it or type `YYYY-MM-DD` to backdate. Future and invalid dates are rejected.
- Workout types: Push, Pull, Legs, Cardio, Upper Body, Lower Body, Full Body, Other.
- Exercises record name, sets, reps and weight. Use weight 0 for bodyweight movements.
- A summary is shown before saving, and you can discard it.

**Stats**
- Total workouts, average duration, total calories and total water
- Current streak and longest streak (in days)
- Workouts in the last 7 days
- BMI with its adult WHO category, plus the last few profile snapshots so you can see BMI change over time

**Units**
Choose metric (cm, kg, L) or imperial (ft/in, lb, oz) in the profile. Everything is stored in metric, so you can switch units at any time without losing data.

## Project Structure

```
GymHabitTracker/
├── main.py                  # Entry point and argument parsing
├── README.md
├── gym_tracker/
│   ├── models.py            # User, Workout, Exercise dataclasses, BMI helpers
│   ├── database.py          # DatabaseManager: schema and all SQL
│   ├── stats.py             # Streak logic and ConsistencyStats
│   ├── units.py             # Metric/imperial conversion and formatting
│   ├── inputs.py            # Validated, re-prompting input helpers
│   └── cli.py               # CLIApp: menus and screens
└── tests/
    └── test_gym_tracker.py
```

## Database Schema

- `user_profile`: id, height_cm, weight_kg, age, bmi, unit_system, recorded_at
- `workouts`: id, workout_date, workout_type, duration_min, calories, water_l
- `exercises`: id, workout_id (foreign key, cascades on delete), name, sets, reps, weight_kg

The profile table is append-only. Each update adds a row, and the newest row is the current profile. This is what makes BMI history possible.

## Design Notes

- **Streaks** count consecutive calendar days with at least one workout. The streak stays alive if your last workout was yesterday, so you are not shown a zero before you have had the chance to train today.
- **Validation** happens in three layers: the input prompts re-ask until the value is valid, the dataclasses reject invalid values, and the SQL schema has `CHECK` constraints.
- **Cancelling**: press Ctrl+C during any action to return to the menu. Ctrl+C or Ctrl+D at the menu exits.
- **BMI** uses adult WHO categories and is a rough screening number, not medical advice.

## Ideas for Extending

- Edit or delete workouts
- Per-exercise progress charts and personal records
- Weekly attendance goals
- CSV export
