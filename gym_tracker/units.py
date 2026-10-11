"""Unit systems and formatting helpers.

Data is always stored in metric units. The chosen unit system only changes
what the user types and what is displayed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

CM_PER_INCH = 2.54
KG_PER_LB = 0.45359237
LITERS_PER_FL_OZ = 0.0295735296


@dataclass(frozen=True)
class UnitSystem:
    """Display units and the factors that convert them to metric."""

    name: str
    description: str
    weight_label: str
    weight_factor: float  # displayed weight * factor = kilograms
    water_label: str
    water_factor: float  # displayed water * factor = liters

    def format_weight(self, kg: float) -> str:
        """Format a weight given in kilograms."""
        return f"{kg / self.weight_factor:.1f} {self.weight_label}"

    def format_water(self, liters: float) -> str:
        """Format a water volume given in liters."""
        decimals = 2 if self.name == "metric" else 1
        return f"{liters / self.water_factor:.{decimals}f} {self.water_label}"

    def format_height(self, cm: float) -> str:
        """Format a height given in centimeters."""
        if self.name == "metric":
            return f"{cm:.1f} cm"
        feet, inches = divmod(round(cm / CM_PER_INCH), 12)
        return f"{feet}'{inches}\""


METRIC = UnitSystem("metric", "Metric (cm, kg, L)", "kg", 1.0, "L", 1.0)
IMPERIAL = UnitSystem(
    "imperial", "Imperial (ft/in, lb, oz)", "lb", KG_PER_LB, "oz", LITERS_PER_FL_OZ
)

UNIT_SYSTEMS: Dict[str, UnitSystem] = {u.name: u for u in (METRIC, IMPERIAL)}


def get_unit_system(name: str) -> UnitSystem:
    """Look up a unit system by name, falling back to metric."""
    return UNIT_SYSTEMS.get(name, METRIC)
