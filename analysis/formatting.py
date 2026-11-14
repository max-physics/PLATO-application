"""Formatting helpers for displaying missing scientific values consistently."""

from __future__ import annotations

from math import isnan
from typing import Any


def display_value(value: Any) -> Any:
    """Return a readable placeholder for null or NaN values."""
    if value is None or value == "":
        return "unbekannt"
    if isinstance(value, float) and isnan(value):
        return "unbekannt"
    return value


def display_uncertainty(plus: Any, minus: Any) -> str:
    """Format asymmetric uncertainties, preserving a missing side explicitly."""
    plus_text = display_value(plus)
    minus_text = display_value(minus)
    if plus_text == "unbekannt" and minus_text == "unbekannt":
        return "unbekannt"
    return f"+ {plus_text} / − {minus_text}"


def display_estimate(value: Any, plus: Any, minus: Any, unit: str) -> str:
    """Format a computed quantity and its optional asymmetric interval."""
    value_text = display_value(value)
    if value_text == "unbekannt":
        return value_text
    plus_text = display_value(plus)
    minus_text = display_value(minus)
    if plus_text == "unbekannt" and minus_text == "unbekannt":
        return f"{value_text:.4g} {unit} (Unsicherheit unbekannt)"
    return f"{value_text:.4g} +{plus_text}/−{minus_text} {unit}"
