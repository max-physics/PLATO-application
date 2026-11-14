"""Small, explicit models that use the currently available planet catalog data.

The rocky interior approximation follows Zeng et al. (2016),
https://doi.org/10.3847/0004-637X/819/2/127. It is not suitable for volatile-rich
planets or planets outside the paper's stated rocky-planet mass/composition range.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

EARTH_MEAN_DENSITY_G_CM3 = 5.514
EARTH_SURFACE_GRAVITY_M_S2 = 9.80665
ROCKY_MODEL_MIN_MASS_EARTH = 1.0
ROCKY_MODEL_MAX_MASS_EARTH = 8.0
ROCKY_MODEL_MAX_CMF = 0.4


@dataclass(frozen=True)
class Estimate:
    """Central derived value and optional asymmetric 68% interval."""

    value: float | None
    uncertainty_plus: float | None = None
    uncertainty_minus: float | None = None


@dataclass(frozen=True)
class DerivedPlanetProperties:
    bulk_density: Estimate
    surface_gravity: Estimate


@dataclass(frozen=True)
class CoreMassFractionEstimate:
    estimate: Estimate | None
    applicable: bool
    reason: str | None = None
    valid_sample_fraction: float | None = None


def derive_bulk_properties(
    mass_earth: float | None,
    radius_earth: float | None,
    mass_uncertainty_plus: float | None = None,
    mass_uncertainty_minus: float | None = None,
    radius_uncertainty_plus: float | None = None,
    radius_uncertainty_minus: float | None = None,
    *,
    samples: int = 20_000,
    random_seed: int = 2026,
) -> DerivedPlanetProperties:
    """Calculate mean density and surface gravity, propagating complete errors.

    If any of the four asymmetric input uncertainties is missing, the central
    physical values are returned but uncertainty estimates remain unavailable.
    """
    if mass_earth is None or radius_earth is None or mass_earth <= 0 or radius_earth <= 0:
        unknown = Estimate(None)
        return DerivedPlanetProperties(unknown, unknown)

    density = EARTH_MEAN_DENSITY_G_CM3 * mass_earth / radius_earth**3
    gravity = EARTH_SURFACE_GRAVITY_M_S2 * mass_earth / radius_earth**2
    errors = (mass_uncertainty_plus, mass_uncertainty_minus,
              radius_uncertainty_plus, radius_uncertainty_minus)
    if any(error is None or error < 0 for error in errors):
        return DerivedPlanetProperties(Estimate(density), Estimate(gravity))

    rng = np.random.default_rng(random_seed)
    mass_samples = _sample_two_piece_normal(
        mass_earth, float(mass_uncertainty_plus), float(mass_uncertainty_minus), samples, rng
    )
    radius_samples = _sample_two_piece_normal(
        radius_earth, float(radius_uncertainty_plus), float(radius_uncertainty_minus), samples, rng
    )
    mass_samples = np.clip(mass_samples, np.finfo(float).tiny, None)
    radius_samples = np.clip(radius_samples, np.finfo(float).tiny, None)
    density_samples = EARTH_MEAN_DENSITY_G_CM3 * mass_samples / radius_samples**3
    gravity_samples = EARTH_SURFACE_GRAVITY_M_S2 * mass_samples / radius_samples**2
    return DerivedPlanetProperties(
        _estimate_interval(density, density_samples),
        _estimate_interval(gravity, gravity_samples),
    )


def infer_rocky_core_mass_fraction(
    mass_earth: float | None,
    radius_earth: float | None,
    mass_uncertainty_plus: float | None = None,
    mass_uncertainty_minus: float | None = None,
    radius_uncertainty_plus: float | None = None,
    radius_uncertainty_minus: float | None = None,
    *,
    samples: int = 20_000,
    random_seed: int = 2026,
) -> CoreMassFractionEstimate:
    """Invert Zeng et al.'s rocky two-layer PREM-based mass-radius relation.

    The approximation is restricted here to 1--8 Earth masses and core mass
    fractions (CMF) of 0--0.4. It assumes an iron core and silicate mantle.
    """
    if mass_earth is None or radius_earth is None or mass_earth <= 0 or radius_earth <= 0:
        return CoreMassFractionEstimate(None, False, "Masse und Radius werden benötigt.")
    if not ROCKY_MODEL_MIN_MASS_EARTH <= mass_earth <= ROCKY_MODEL_MAX_MASS_EARTH:
        return CoreMassFractionEstimate(
            None, False, "Das Modell gilt hier nur für 1 bis 8 Erdmassen."
        )

    cmf = _invert_rocky_mass_radius(mass_earth, radius_earth)
    if not 0 <= cmf <= ROCKY_MODEL_MAX_CMF:
        return CoreMassFractionEstimate(
            None,
            False,
            "Die Messwerte liegen außerhalb der modellierten felsigen Zusammensetzungen (CMF 0–0,4).",
        )

    errors = (mass_uncertainty_plus, mass_uncertainty_minus,
              radius_uncertainty_plus, radius_uncertainty_minus)
    if any(error is None or error < 0 for error in errors):
        return CoreMassFractionEstimate(Estimate(cmf), True, valid_sample_fraction=None)

    rng = np.random.default_rng(random_seed)
    sampled_mass = np.clip(
        _sample_two_piece_normal(
            mass_earth, float(mass_uncertainty_plus), float(mass_uncertainty_minus), samples, rng
        ),
        np.finfo(float).tiny,
        None,
    )
    sampled_radius = np.clip(
        _sample_two_piece_normal(
            radius_earth, float(radius_uncertainty_plus), float(radius_uncertainty_minus), samples, rng
        ),
        np.finfo(float).tiny,
        None,
    )
    sampled_cmf = _invert_rocky_mass_radius(sampled_mass, sampled_radius)
    valid = (
        (sampled_mass >= ROCKY_MODEL_MIN_MASS_EARTH)
        & (sampled_mass <= ROCKY_MODEL_MAX_MASS_EARTH)
        & (sampled_cmf >= 0)
        & (sampled_cmf <= ROCKY_MODEL_MAX_CMF)
    )
    valid_fraction = float(np.mean(valid))
    if valid.sum() < max(50, samples * 0.01):
        return CoreMassFractionEstimate(
            Estimate(cmf), True,
            "Zu wenige Unsicherheitsziehungen liegen im gültigen Modellbereich.",
            valid_sample_fraction=valid_fraction,
        )
    return CoreMassFractionEstimate(
        _estimate_interval(cmf, sampled_cmf[valid]),
        True,
        valid_sample_fraction=valid_fraction,
    )


def rocky_reference_curves(
    masses_earth: NDArray[np.float64] | None = None,
) -> dict[float, tuple[NDArray[np.float64], NDArray[np.float64]]]:
    """Return PREM-based rocky radius curves for selected core mass fractions."""
    masses = masses_earth if masses_earth is not None else np.linspace(1.0, 8.0, 200)
    curves: dict[float, tuple[NDArray[np.float64], NDArray[np.float64]]] = {}
    for cmf in (0.0, 0.3, 0.4):
        radii = (1.07 - 0.21 * cmf) * masses ** (1.0 / 3.7)
        curves[cmf] = (masses, radii)
    return curves


def _invert_rocky_mass_radius(mass_earth: float | NDArray[np.float64], radius_earth: float | NDArray[np.float64]):
    return (1.07 - radius_earth / np.power(mass_earth, 1.0 / 3.7)) / 0.21


def _sample_two_piece_normal(
    value: float, plus: float, minus: float, size: int, rng: np.random.Generator
) -> NDArray[np.float64]:
    if plus == 0 and minus == 0:
        return np.full(size, value, dtype=float)
    if plus == 0:
        choose_plus = np.zeros(size, dtype=bool)
    elif minus == 0:
        choose_plus = np.ones(size, dtype=bool)
    else:
        choose_plus = rng.random(size) < plus / (plus + minus)
    scales = np.where(choose_plus, plus, minus)
    offsets = np.abs(rng.standard_normal(size)) * scales
    return value + np.where(choose_plus, offsets, -offsets)


def _estimate_interval(value: float, samples: NDArray[np.float64]) -> Estimate:
    lower, upper = np.quantile(samples, (0.16, 0.84))
    return Estimate(float(value), float(max(0.0, upper - value)), float(max(0.0, value - lower)))
