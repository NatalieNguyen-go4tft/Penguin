"""Entry point for GymHabitTracker.

Usage:
    python main.py [--db PATH]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from typing import List, Optional

from gym_tracker.cli import CLIApp
from gym_tracker.database import DEFAULT_DB_PATH, DatabaseManager


def main(argv: Optional[List[str]] = None) -> int:
    """Parse arguments, open the database and start the CLI."""
    parser = argparse.ArgumentParser(
        description="Track gym attendance, workouts and health metrics."
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help=f"path to the SQLite database file (default: {DEFAULT_DB_PATH})",
    )
    args = parser.parse_args(argv)

    try:
        with DatabaseManager(args.db) as db:
            CLIApp(db).run()
    except sqlite3.Error as error:
        print(f"Database error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
