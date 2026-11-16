"""Keplerian separation and velocity estimates for catalogued exoplanets."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, pi, sqrt

GRAVITATIONAL_CONSTANT_M3_KG_S2 = 6.67430e-11
SOLAR_MASS_KG = 1.98847e30
EARTH_MASS_KG = 5.9722e24
ASTRONOMICAL_UNIT_M = 149_597_870_700.0
DAY_S = 86_400.0


@dataclass(frozen=True)
class OrbitalKinematics:
    """Central-value orbital estimates and the source of the semimajor axis."""

    semimajor_axis_au: float | None
    semimajor_axis_source: str | None
    circular_speed_km_s: float | None
    periastron_distance_au: float | None
    apastron_distance_au: float | None
    periastron_speed_km_s: float | None
    apastron_speed_km_s: float | None


def calculate_orbital_kinematics(
    *,
    orbital_period_days: float | None,
    stellar_mass_solar: float | None,
    planet_mass_earth: float | None,
    semimajor_axis_au: float | None,
    eccentricity: float | None,
) -> OrbitalKinematics:
    """Calculate orbit-scale and speed estimates from public catalog values.

    Prefer the catalogue semimajor axis. If it is missing, derive it from the
    period and total system mass using Kepler's third law. Velocities use the
    two-body gravitational parameter when stellar mass is known, otherwise
    the circular relation 2*pi*a/P. Uncertainties are not propagated here.
    """
    period_s = _positive_finite(orbital_period_days)
    if period_s is not None:
        period_s *= DAY_S

    star_mass_kg = _positive_finite(stellar_mass_solar)
    if star_mass_kg is not None:
        star_mass_kg *= SOLAR_MASS_KG
    planet_mass_kg = _positive_finite(planet_mass_earth)
    if planet_mass_kg is not None:
        planet_mass_kg *= EARTH_MASS_KG

    axis = _positive_finite(semimajor_axis_au)
    axis_source: str | None = "NASA catalogue value" if axis is not None else None
    total_mass_kg = (
        star_mass_kg + (planet_mass_kg or 0.0)
        if star_mass_kg is not None
        else None
    )

    if axis is None and period_s is not None and total_mass_kg is not None:
        axis_m = (
            GRAVITATIONAL_CONSTANT_M3_KG_S2
            * total_mass_kg
            * period_s**2
            / (4.0 * pi**2)
        ) ** (1.0 / 3.0)
        axis = axis_m / ASTRONOMICAL_UNIT_M
        axis_source = "derived from orbital period and stellar mass using Kepler's third law"

    if axis is None:
        return OrbitalKinematics(None, None, None, None, None, None, None)

    axis_m = axis * ASTRONOMICAL_UNIT_M
    if total_mass_kg is not None:
        mu = GRAVITATIONAL_CONSTANT_M3_KG_S2 * total_mass_kg
        circular_speed = sqrt(mu / axis_m)
    elif period_s is not None:
        mu = 4.0 * pi**2 * axis_m**3 / period_s**2
        circular_speed = 2.0 * pi * axis_m / period_s
    else:
        mu = None
        circular_speed = None

    e = eccentricity if _finite(eccentricity) and 0.0 <= eccentricity < 1.0 else None
    if e is None:
        return OrbitalKinematics(
            axis, axis_source,
            circular_speed / 1000.0 if circular_speed is not None else None,
            None, None, None, None,
        )

    r_peri_m = axis_m * (1.0 - e)
    r_apo_m = axis_m * (1.0 + e)
    v_peri = sqrt(mu * (2.0 / r_peri_m - 1.0 / axis_m)) if mu else None
    v_apo = sqrt(mu * (2.0 / r_apo_m - 1.0 / axis_m)) if mu else None
    return OrbitalKinematics(
        semimajor_axis_au=axis,
        semimajor_axis_source=axis_source,
        circular_speed_km_s=circular_speed / 1000.0 if circular_speed is not None else None,
        periastron_distance_au=axis * (1.0 - e),
        apastron_distance_au=axis * (1.0 + e),
        periastron_speed_km_s=v_peri / 1000.0 if v_peri is not None else None,
        apastron_speed_km_s=v_apo / 1000.0 if v_apo is not None else None,
    )


def _finite(value: float | None) -> bool:
    return value is not None and isfinite(value)


def _positive_finite(value: float | None) -> float | None:
    return float(value) if _finite(value) and value > 0 else None
