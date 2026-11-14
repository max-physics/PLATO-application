"""Reusable Plotly visualizations for planet catalog data."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import plotly.graph_objects as go

from analysis.planet_models import rocky_reference_curves


def mass_radius_figure(
    planets: Sequence[Mapping[str, Any]], *, include_rocky_references: bool = False
) -> go.Figure:
    """Build a logarithmic mass-radius chart with selectable planet points.

    Each input mapping uses ``id``, ``name``, ``mass``, ``radius`` and optional
    asymmetric ``mass_plus/minus`` and ``radius_plus/minus`` uncertainty fields.
    """
    figure = go.Figure()
    if include_rocky_references:
        for cmf, (curve_mass, curve_radius) in rocky_reference_curves().items():
            figure.add_trace(
                go.Scatter(
                    x=curve_mass,
                    y=curve_radius,
                    mode="lines",
                    name=f"Gesteinsreferenz, CMF {cmf:.1f}",
                    hovertemplate="Masse: %{x:.2f} M⊕<br>Radius: %{y:.2f} R⊕<extra>%{fullData.name}</extra>",
                )
            )

    plotted = [
        planet for planet in planets
        if planet.get("mass") is not None
        and planet.get("radius") is not None
        and planet["mass"] > 0
        and planet["radius"] > 0
    ]
    has_errors = lambda planet: all(
        planet.get(key) is not None
        for key in ("mass_plus", "mass_minus", "radius_plus", "radius_minus")
    ) and planet["mass_minus"] < planet["mass"] and planet["radius_minus"] < planet["radius"]
    with_errors = [planet for planet in plotted if has_errors(planet)]
    without_errors = [planet for planet in plotted if planet not in with_errors]

    def add_planet_trace(rows: list[Mapping[str, Any]], *, errors: bool) -> None:
        if not rows:
            return
        trace_options: dict[str, Any] = {}
        if errors:
            trace_options["error_x"] = {
                "type": "data", "symmetric": False,
                "array": [planet["mass_plus"] for planet in rows],
                "arrayminus": [planet["mass_minus"] for planet in rows],
            }
            trace_options["error_y"] = {
                "type": "data", "symmetric": False,
                "array": [planet["radius_plus"] for planet in rows],
                "arrayminus": [planet["radius_minus"] for planet in rows],
            }
        else:
            trace_options["marker"] = {"symbol": "x", "color": "gray"}
        figure.add_trace(
            go.Scatter(
                x=[planet["mass"] for planet in rows],
                y=[planet["radius"] for planet in rows],
                text=[planet["name"] for planet in rows],
                customdata=[[planet.get("id")] for planet in rows],
                mode="markers",
                name="Planeten mit Unsicherheiten" if errors else "Unsicherheiten unbekannt",
                hovertemplate=(
                    "%{text}<br>Masse: %{x:.3g} M⊕<br>Radius: %{y:.3g} R⊕"
                    + ("<extra></extra>" if errors else "<br>Unsicherheiten unbekannt<extra></extra>")
                ),
                **trace_options,
            )
        )

    add_planet_trace(with_errors, errors=True)
    add_planet_trace(without_errors, errors=False)
    figure.update_layout(
        xaxis={"title": "Masse (Erdenmassen)", "type": "log"},
        yaxis={"title": "Radius (Erdradien)", "type": "log"},
        legend_title="Daten / Modellkurve",
        height=560,
        margin={"t": 20},
        clickmode="event+select",
    )
    return figure


def selected_planet_id(chart_event: Any) -> int | None:
    """Extract a planet ID from Streamlit's Plotly point-selection event."""
    selection = getattr(chart_event, "selection", None)
    points = getattr(selection, "points", None)
    if not points:
        return None
    customdata = points[0].get("customdata")
    if isinstance(customdata, (tuple, list)):
        customdata = customdata[0] if customdata else None
    try:
        return int(customdata) if customdata is not None else None
    except (TypeError, ValueError):
        return None
