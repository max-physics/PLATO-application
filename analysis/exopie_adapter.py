"""Optional adapter for ExoPie rocky-planet composition inference."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

import numpy as np

from analysis.planet_models import Estimate

EXOPIE_ROCKY_MIN_MASS_EARTH = 0.01
EXOPIE_ROCKY_MAX_MASS_EARTH = 19.95


@dataclass(frozen=True)
class ExoPieRockyResult:
    """Summaries of ExoPie's accepted rocky-interior posterior samples."""

    core_mass_fraction: Estimate
    iron_mass_fraction: Estimate
    accepted_samples: int
    requested_samples: int

    @property
    def acceptance_fraction(self) -> float:
        return self.accepted_samples / self.requested_samples


def run_exopie_rocky_inference(
    mass_earth: float,
    radius_earth: float,
    mass_uncertainty_plus: float,
    mass_uncertainty_minus: float,
    radius_uncertainty_plus: float,
    radius_uncertainty_minus: float,
    *,
    samples: int = 5_000,
    random_seed: int = 2026,
) -> ExoPieRockyResult:
    """Run ExoPie using fixed-size, independent asymmetric-error posterior draws.

    The explicit xSi/xFe ranges constrain silicon in the core and iron in the
    mantle. The returned intervals summarize accepted model samples. A fixed
    random seed makes the calculation reproducible.
    """
    values = (
        mass_earth,
        radius_earth,
        mass_uncertainty_plus,
        mass_uncertainty_minus,
        radius_uncertainty_plus,
        radius_uncertainty_minus,
    )
    if any(not np.isfinite(value) for value in values):
        raise ValueError("Masse, Radius und ihre Unsicherheiten müssen endlich sein.")
    if mass_earth <= 0 or radius_earth <= 0:
        raise ValueError("Masse und Radius müssen positiv sein.")
    if not EXOPIE_ROCKY_MIN_MASS_EARTH <= mass_earth <= EXOPIE_ROCKY_MAX_MASS_EARTH:
        raise ValueError(
            "Die Zentralmasse liegt außerhalb des ExoPie-rocky-Modellbereichs "
            f"({EXOPIE_ROCKY_MIN_MASS_EARTH:g}–{EXOPIE_ROCKY_MAX_MASS_EARTH:g} Erdmassen)."
        )
    if any(error < 0 for error in values[2:]):
        raise ValueError("Unsicherheiten dürfen nicht negativ sein.")
    if samples < 50:
        raise ValueError("Für eine ExoPie-Vorschau werden mindestens 50 Ziehungen benötigt.")

    try:
        exopie = import_module("exopie")
    except ImportError as exc:
        raise ImportError(
            "ExoPie ist nicht installiert. Installiere die optionale Abhängigkeit "
            "mit `python -m pip install -r requirements-exopie.txt`."
        ) from exc

    rng = np.random.default_rng(random_seed)
    mass_samples = _sample_asymmetric_normal(
        mass_earth, mass_uncertainty_plus, mass_uncertainty_minus, samples, rng
    )
    radius_samples = _sample_asymmetric_normal(
        radius_earth, radius_uncertainty_plus, radius_uncertainty_minus, samples, rng
    )
    # ExoPie 2.1.0's rocky-grid validation uses the original N to build model
    # arrays, then masks masses outside the grid. Those arrays become
    # incompatible if even one mass draw is outside the grid. Filter such
    # input pairs here while preserving their original requested denominator.
    mass_in_grid = (
        (mass_samples > EXOPIE_ROCKY_MIN_MASS_EARTH)
        & (mass_samples < EXOPIE_ROCKY_MAX_MASS_EARTH)
        & (radius_samples > 0)
    )
    mass_samples = mass_samples[mass_in_grid]
    radius_samples = radius_samples[mass_in_grid]
    if mass_samples.size == 0:
        raise RuntimeError(
            "Keine der gezogenen Massen liegt im ExoPie-rocky-Modellbereich "
            f"({EXOPIE_ROCKY_MIN_MASS_EARTH:g}–{EXOPIE_ROCKY_MAX_MASS_EARTH:g} Erdmassen)."
        )
    # ExoPie also uses NumPy's legacy global RNG for xSi/xFe draws. Preserve
    # the caller's RNG state while seeding those priors reproducibly.
    numpy_random_state = np.random.get_state()
    try:
        np.random.seed(random_seed)
        planet = exopie.planet(
            Mass=mass_samples,
            Radius=radius_samples,
            N=int(mass_samples.size),
            planet_type="rocky",
            xSi=[0.0, 0.2],
            xFe=[0.0, 0.2],
        )
        results = planet.run()
    except Exception as exc:
        message = str(exc)
        normalized_message = message.casefold()
        if (
            "out of bounds" in normalized_message
            or "outside the model range" in normalized_message
            or "no m-r pair in bounds" in normalized_message
        ):
            raise RuntimeError(
                "Für die gezogenen Masse-Radius-Kombinationen findet ExoPie keine Lösung "
                "im Gültigkeitsbereich des felsigen Modells. Probiere zunächst Gliese 12 b. "
                "Für Planeten mit volatiler Hülle wäre ein Wasser- oder H/He-Modell nötig; "
                "diese Modellklassen sind hier noch nicht angebunden."
            ) from exc
        raise RuntimeError(f"ExoPie konnte die Modellrechnung nicht abschließen: {message}") from exc
    finally:
        np.random.set_state(numpy_random_state)
    if results is None:
        results = planet

    cmf_samples = _posterior_samples(getattr(results, "CMF", None))
    iron_samples = _posterior_samples(getattr(results, "FeMF", None))
    if cmf_samples.size == 0 or iron_samples.size == 0:
        raise RuntimeError("ExoPie hat keine gültigen CMF- und FeMF-Posteriorwerte geliefert.")

    return ExoPieRockyResult(
        core_mass_fraction=_summarize(cmf_samples),
        iron_mass_fraction=_summarize(iron_samples),
        accepted_samples=int(cmf_samples.size),
        requested_samples=samples,
    )


def _posterior_samples(values: Any) -> np.ndarray:
    if values is None:
        return np.array([], dtype=float)
    samples = np.asarray(values, dtype=float).reshape(-1)
    return samples[np.isfinite(samples)]


def _sample_asymmetric_normal(
    center: float,
    uncertainty_plus: float,
    uncertainty_minus: float,
    samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Draw exactly ``samples`` values from a two-piece normal distribution."""
    if uncertainty_plus == 0 and uncertainty_minus == 0:
        return np.full(samples, center, dtype=float)

    upper_probability = uncertainty_plus / (uncertainty_plus + uncertainty_minus)
    upper_side = rng.random(samples) < upper_probability
    offsets = np.abs(rng.standard_normal(samples))
    values = np.empty(samples, dtype=float)
    values[upper_side] = center + offsets[upper_side] * uncertainty_plus
    values[~upper_side] = center - offsets[~upper_side] * uncertainty_minus
    return values


def _summarize(samples: np.ndarray) -> Estimate:
    lower, median, upper = np.quantile(samples, (0.16, 0.5, 0.84))
    return Estimate(
        value=float(median),
        uncertainty_plus=float(max(0.0, upper - median)),
        uncertainty_minus=float(max(0.0, median - lower)),
    )
