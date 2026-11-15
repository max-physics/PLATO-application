"""Static seed datasets for the local demonstrator."""

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import DataProduct, Observation, Planet, Star

SYNTHETIC_SOURCE = "SYNTHETIC DEMO DATA — invented for PLATO Scientific Data Analysis Lab"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PLANETS_CSV = PROJECT_ROOT / "data" / "public_confirmed_planets.csv"
NASA_ARCHIVE_URL = "https://exoplanetarchive.ipac.caltech.edu/"
NASA_RELEASE = "PSCompPars snapshot 2026-11-14"


def seed_demo_data(session: Session) -> None:
    """Insert a compact synthetic dataset; safe to call only on an empty DB."""
    star = Star(catalog_id="SYNTH-STAR-001", name="Demo Star A", effective_temperature_k=5700.0,
                radius_solar=1.0, is_synthetic=True, provenance=SYNTHETIC_SOURCE)
    planet = Planet(catalog_id="SYNTH-PLANET-001", name="Demo Planet b", orbital_period_days=12.4,
                    radius_earth=1.8, mass_earth=5.2, is_synthetic=True, provenance=SYNTHETIC_SOURCE)
    star.planets.append(planet)
    l2 = DataProduct(product_key="SYNTH-L2-001", level="L2", version="0.1.0",
                     provenance=SYNTHETIC_SOURCE, description="Synthetic processed light-curve summary.", is_synthetic=True)
    l3 = DataProduct(product_key="SYNTH-L3-001", level="L3", version="0.1.0",
                     provenance=SYNTHETIC_SOURCE, description="Synthetic derived planet-parameter summary.", is_synthetic=True)
    session.add_all([star, l2, l3])
    session.flush()
    observation = Observation(planet=planet, product=l2, observable="transit_depth", value=320.0,
                              uncertainty=18.0, unit="ppm", is_synthetic=True, provenance=SYNTHETIC_SOURCE)
    session.add(observation)
    session.commit()


def seed_public_planets(session: Session) -> int:
    """Insert the checked-in public NASA Archive snapshot once per planet.

    Host stars are stored as catalog entities so each planet has a valid FK.
    This reads a static CSV shipped with the project and makes no network calls.
    """
    added = 0
    host_names: set[str] = set()
    with PUBLIC_PLANETS_CSV.open(encoding="utf-8", newline="") as csv_file:
        for row in csv.DictReader(csv_file):
            planet_name = row["pl_name"].strip()
            hostname = row["hostname"].strip()
            host_names.add(hostname)

            star = session.scalar(select(Star).where(Star.catalog_id == f"NASA-PS-{hostname}"))
            if star is None:
                star = Star(
                    catalog_id=f"NASA-PS-{hostname}",
                    name=hostname,
                    effective_temperature_k=_optional_float(row["st_teff"]),
                    effective_temperature_uncertainty_plus_k=_optional_float(row["st_tefferr1"]),
                    effective_temperature_uncertainty_minus_k=_absolute_optional_float(row["st_tefferr2"]),
                    radius_solar=_optional_float(row["st_rad"]),
                    radius_uncertainty_plus_solar=_optional_float(row["st_raderr1"]),
                    radius_uncertainty_minus_solar=_absolute_optional_float(row["st_raderr2"]),
                    mass_solar=_optional_float(row.get("st_mass", "")),
                    mass_uncertainty_plus_solar=_optional_float(row.get("st_masserr1", "")),
                    mass_uncertainty_minus_solar=_absolute_optional_float(row.get("st_masserr2", "")),
                    is_synthetic=False,
                    provenance="NASA Exoplanet Archive, Planetary Systems Composite Parameters table",
                    source_url=NASA_ARCHIVE_URL,
                    data_release=NASA_RELEASE,
                )
                session.add(star)
                session.flush()
            elif star.mass_solar is None:
                star.mass_solar = _optional_float(row.get("st_mass", ""))
                star.mass_uncertainty_plus_solar = _optional_float(row.get("st_masserr1", ""))
                star.mass_uncertainty_minus_solar = _absolute_optional_float(row.get("st_masserr2", ""))

            existing = session.scalar(select(Planet).where(Planet.catalog_id == f"NASA-PS-{planet_name}"))
            if existing is not None:
                if existing.semimajor_axis_au is None:
                    existing.semimajor_axis_au = _optional_float(row.get("pl_orbsmax", ""))
                    existing.semimajor_axis_uncertainty_plus_au = _optional_float(row.get("pl_orbsmaxerr1", ""))
                    existing.semimajor_axis_uncertainty_minus_au = _absolute_optional_float(
                        row.get("pl_orbsmaxerr2", "")
                    )
                    existing.eccentricity = _optional_float(row.get("pl_orbeccen", ""))
                    existing.eccentricity_uncertainty_plus = _optional_float(row.get("pl_orbeccenerr1", ""))
                    existing.eccentricity_uncertainty_minus = _absolute_optional_float(
                        row.get("pl_orbeccenerr2", "")
                    )
                continue
            session.add(
                Planet(
                    catalog_id=f"NASA-PS-{planet_name}",
                    name=planet_name,
                    star_id=star.id,
                    orbital_period_days=_optional_float(row["pl_orbper"]),
                    orbital_period_uncertainty_plus_days=_optional_float(row["pl_orbpererr1"]),
                    orbital_period_uncertainty_minus_days=_absolute_optional_float(row["pl_orbpererr2"]),
                    semimajor_axis_au=_optional_float(row.get("pl_orbsmax", "")),
                    semimajor_axis_uncertainty_plus_au=_optional_float(row.get("pl_orbsmaxerr1", "")),
                    semimajor_axis_uncertainty_minus_au=_absolute_optional_float(row.get("pl_orbsmaxerr2", "")),
                    eccentricity=_optional_float(row.get("pl_orbeccen", "")),
                    eccentricity_uncertainty_plus=_optional_float(row.get("pl_orbeccenerr1", "")),
                    eccentricity_uncertainty_minus=_absolute_optional_float(row.get("pl_orbeccenerr2", "")),
                    radius_earth=_optional_float(row["pl_rade"]),
                    radius_uncertainty_plus_earth=_optional_float(row["pl_radeerr1"]),
                    radius_uncertainty_minus_earth=_absolute_optional_float(row["pl_radeerr2"]),
                    mass_earth=_optional_float(row["pl_bmasse"]),
                    mass_uncertainty_plus_earth=_optional_float(row["pl_bmasseerr1"]),
                    mass_uncertainty_minus_earth=_absolute_optional_float(row["pl_bmasseerr2"]),
                    is_synthetic=False,
                    provenance="NASA Exoplanet Archive, Planetary Systems Composite Parameters table",
                    source_url=NASA_ARCHIVE_URL,
                    data_release=NASA_RELEASE,
                )
            )
            added += 1

    # Replace the earlier mistaken star-only sample with only host stars needed
    # by this planet snapshot. Never remove synthetic stars or linked records.
    stale_public_stars = session.scalars(
        select(Star).where(Star.catalog_id.like("NASA-PS-%"), Star.name.not_in(host_names))
    )
    for stale_star in stale_public_stars:
        if not stale_star.planets:
            session.delete(stale_star)
    session.commit()
    return added


def _optional_float(value: str) -> float | None:
    return float(value) if value else None


def _absolute_optional_float(value: str) -> float | None:
    parsed = _optional_float(value)
    return abs(parsed) if parsed is not None else None
