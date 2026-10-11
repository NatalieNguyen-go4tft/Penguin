"""Validated, re-prompting input helpers for the CLI.

Numeric prompts take their bounds in base (metric) units and an optional
``factor`` that converts the units the user types into base units. This lets
imperial users type pounds or ounces while validation and storage stay metric.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Sequence


def _ask(label: str, default_text: Optional[str] = None) -> str:
    suffix = f" [{default_text}]" if default_text is not None else ""
    return input(f"{label}{suffix}: ").strip()


def prompt_text(label: str, max_length: int = 60) -> str:
    """Prompt for a non-empty string of at most ``max_length`` characters."""
    while True:
        value = _ask(label)
        if not value:
            print("  This field cannot be empty.")
        elif len(value) > max_length:
            print(f"  Please keep it under {max_length} characters.")
        else:
            return value


def prompt_int(
    label: str,
    minimum: int,
    maximum: int,
    *,
    default: Optional[int] = None,
) -> int:
    """Prompt for a whole number within [minimum, maximum]."""
    default_text = str(default) if default is not None else None
    while True:
        raw = _ask(label, default_text)
        if not raw and default is not None:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("  Please enter a whole number.")
            continue
        if not minimum <= value <= maximum:
            print(f"  Please enter a value between {minimum} and {maximum}.")
            continue
        return value


def prompt_float(
    label: str,
    minimum: float,
    maximum: float,
    *,
    unit: str = "",
    factor: float = 1.0,
    default: Optional[float] = None,
) -> float:
    """Prompt for a number and return it in base units.

    Args:
        label: Prompt text.
        minimum: Smallest allowed value, in base units.
        maximum: Largest allowed value, in base units.
        unit: Display unit shown in the prompt (e.g. ``"lb"``).
        factor: Multiplier converting the entered value to base units.
        default: Value in base units returned when the user presses Enter.
    """
    shown = f"{label} ({unit})" if unit else label
    default_text = (
        f"{round(default / factor, 2):g}" if default is not None else None
    )
    low, high = round(minimum / factor, 1), round(maximum / factor, 1)
    while True:
        raw = _ask(shown, default_text)
        if not raw and default is not None:
            return float(default)
        try:
            value = float(raw)
        except ValueError:
            print("  Please enter a number.")
            continue
        base_value = value * factor
        # Written this way so NaN is rejected too.
        if not minimum <= base_value <= maximum:
            print(f"  Please enter a value between {low:g} and {high:g}.")
            continue
        return base_value


def prompt_date(label: str, default: date) -> date:
    """Prompt for a YYYY-MM-DD date that is not in the future."""
    while True:
        raw = _ask(label, default.isoformat())
        if not raw:
            return default
        try:
            value = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            print("  Invalid date. Use the format YYYY-MM-DD (e.g. 2026-03-14).")
            continue
        if value > date.today():
            print("  The date cannot be in the future.")
            continue
        return value


def prompt_choice(
    label: str, options: Sequence[str], *, default_index: Optional[int] = None
) -> str:
    """Show a numbered list and return the chosen option.

    ``default_index`` is 1-based and is used when the user presses Enter.
    """
    for number, option in enumerate(options, start=1):
        print(f"  {number}. {option}")
    default_text = str(default_index) if default_index is not None else None
    while True:
        raw = _ask(f"{label} (1-{len(options)})", default_text)
        if not raw and default_index is not None:
            return options[default_index - 1]
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print(f"  Please enter a number from 1 to {len(options)}.")


def prompt_yes_no(label: str, default: bool = True) -> bool:
    """Prompt for a yes/no answer."""
    hint = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{label} [{hint}]: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please answer y or n.")
