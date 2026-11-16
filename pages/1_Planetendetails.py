"""Detailed view of a selected planet and its linked demo records."""

from math import isnan
from typing import Any
from uuid import uuid4

import streamlit as st
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from analysis.planet_models import (
    derive_bulk_properties,
    infer_rocky_core_mass_fraction,
)
from analysis.orbital_kinematics import calculate_orbital_kinematics
from analysis.visualization import mass_radius_figure
from database import get_session_factory, init_db
from models import ModelResult, ModelRun, Observation, Planet
from ui.theme import apply_space_background


def display_value(value: Any) -> Any:
    """Display absent catalog values explicitly instead of as blank cells."""
    if value is None or value == "" or (isinstance(value, float) and isnan(value)):
        return "Unknown"
    return value


def display_uncertainty(plus: Any, minus: Any) -> str:
    """Format both sides of an asymmetric uncertainty, including missing sides."""
    plus_text = display_value(plus)
    minus_text = display_value(minus)
    if plus_text == "Unknown" and minus_text == "Unknown":
        return "Unknown"
    return f"+ {plus_text} / − {minus_text}"


def display_estimate(value: Any, plus: Any, minus: Any, unit: str) -> str:
    """Format a derived value with asymmetric errors or explicit unknowns."""
    value = display_value(value)
    plus = display_value(plus)
    minus = display_value(minus)
    if value == "Unknown":
        return value
    if plus == "Unknown" and minus == "Unknown":
        return f"{value:.4g} {unit} (uncertainty unknown)"
    return f"{value:.4g} +{plus}/−{minus} {unit}"


def show_parameter_grid(values: dict[str, Any]) -> None:
    """Render key-value details without relying on a dataframe component."""
    columns = st.columns(2)
    for index, (label, value) in enumerate(values.items()):
        with columns[index % len(columns)]:
            st.markdown(f"**{label}**")
            st.write(value)


@st.cache_resource
def database_session_factory():
    """Initialize the local demo database once per Streamlit process."""
    return get_session_factory(init_db())


st.set_page_config(page_title="Planet details | PLATO Application Demo", page_icon="🪐", layout="wide")
apply_space_background()
st.title("Planet details")
st.page_link("app.py", label="← Back to home", icon="🏠")

planet_id = st.session_state.get("selected_planet_id")
if planet_id is None:
    st.info("Select a planet using the search on the home page.")
    st.page_link("app.py", label="Go to planet search")
    st.stop()

try:
    sessions = database_session_factory()
    with sessions() as session:
        planet = session.scalar(
            select(Planet).where(Planet.id == planet_id)
        )
        if planet is None:
            st.warning("The selected planet is no longer in the database.")
            st.stop()

        # Load linked rows while the session is open so the page does not depend
        # on lazy ORM access after the database session closes.
        star = planet.star
        observations = list(
            session.scalars(
                select(Observation)
                .where(Observation.planet_id == planet.id)
                .order_by(Observation.observable)
            )
        )
        chart_planets = [
            {
                "id": item.id,
                "name": item.name,
                "mass": item.mass_earth,
                "mass_plus": getattr(item, "mass_uncertainty_plus_earth", None),
                "mass_minus": getattr(item, "mass_uncertainty_minus_earth", None),
                "radius": item.radius_earth,
                "radius_plus": getattr(item, "radius_uncertainty_plus_earth", None),
                "radius_minus": getattr(item, "radius_uncertainty_minus_earth", None),
            }
            for item in session.scalars(select(Planet).order_by(Planet.name))
        ]
        observation_rows = [
            {
                "Observable": observation.observable,
                "Value": display_value(observation.value),
                "Uncertainty": display_value(observation.uncertainty),
                "Unit": display_value(observation.unit),
                "Data product": display_value(observation.product.product_key if observation.product else None),
                "Level": display_value(observation.product.level if observation.product else None),
                "Product version": display_value(observation.product.version if observation.product else None),
                "Provenance": display_value(observation.provenance),
                "Synthetic": observation.is_synthetic,
            }
            for observation in observations
        ]
        planet_info = {
            "Name": planet.name,
            "Catalogue ID": planet.catalog_id,
            "Orbital period (days)": display_value(planet.orbital_period_days),
            "Orbital period uncertainty + / − (days)": display_uncertainty(
                getattr(planet, "orbital_period_uncertainty_plus_days", None),
                getattr(planet, "orbital_period_uncertainty_minus_days", None),
            ),
            "Semimajor axis uncertainty + / − (AU)": display_uncertainty(
                getattr(planet, "semimajor_axis_uncertainty_plus_au", None),
                getattr(planet, "semimajor_axis_uncertainty_minus_au", None),
            ),
            "Semimajor axis (AU)": display_value(getattr(planet, "semimajor_axis_au", None)),
            "Eccentricity uncertainty + / −": display_uncertainty(
                getattr(planet, "eccentricity_uncertainty_plus", None),
                getattr(planet, "eccentricity_uncertainty_minus", None),
            ),
            "Eccentricity": display_value(getattr(planet, "eccentricity", None)),
            "Radius (Earth radii)": display_value(planet.radius_earth),
            "Radius uncertainty + / − (Earth radii)": display_uncertainty(
                getattr(planet, "radius_uncertainty_plus_earth", None),
                getattr(planet, "radius_uncertainty_minus_earth", None),
            ),
            "Mass (Earth masses)": display_value(planet.mass_earth),
            "Mass uncertainty + / − (Earth masses)": display_uncertainty(
                getattr(planet, "mass_uncertainty_plus_earth", None),
                getattr(planet, "mass_uncertainty_minus_earth", None),
            ),
            "Synthetic": planet.is_synthetic,
            "Provenance": display_value(planet.provenance),
            "Data release": display_value(getattr(planet, "data_release", None)),
            "Source": display_value(getattr(planet, "source_url", None)),
        }
        star_info = {
            "Host star": star.name,
            "Star catalogue ID": star.catalog_id,
            "Effective temperature (K)": display_value(star.effective_temperature_k),
            "Temperature uncertainty + / − (K)": display_uncertainty(
                getattr(star, "effective_temperature_uncertainty_plus_k", None),
                getattr(star, "effective_temperature_uncertainty_minus_k", None),
            ),
            "Stellar radius (Solar radii)": display_value(star.radius_solar),
            "Radius uncertainty + / − (Solar radii)": display_uncertainty(
                getattr(star, "radius_uncertainty_plus_solar", None),
                getattr(star, "radius_uncertainty_minus_solar", None),
            ),
            "Stellar mass (Solar masses)": display_value(getattr(star, "mass_solar", None)),
            "Stellar mass uncertainty + / − (Solar masses)": display_uncertainty(
                getattr(star, "mass_uncertainty_plus_solar", None),
                getattr(star, "mass_uncertainty_minus_solar", None),
            ),
            "Synthetic": star.is_synthetic,
            "Provenance": display_value(star.provenance),
            "Data release": display_value(getattr(star, "data_release", None)),
            "Source": display_value(getattr(star, "source_url", None)),
        }

    st.header(planet_info["Name"])
    st.caption(f"Catalogue ID: {planet_info['Catalogue ID']}")
    st.info(
        "Public catalogue values include their source. The demo dataset is explicitly synthetic "
        "and does not contain PLATO measurements."
    )
    if st.session_state.pop("analysis_saved_notice", False):
        st.success("Analysis results saved.")

    st.subheader("Planet parameters")
    show_parameter_grid(planet_info)
    st.subheader("Host star")
    show_parameter_grid(star_info)

    st.subheader("Orbital distance and velocity")
    orbit = calculate_orbital_kinematics(
        orbital_period_days=planet.orbital_period_days,
        stellar_mass_solar=getattr(star, "mass_solar", None),
        planet_mass_earth=planet.mass_earth,
        semimajor_axis_au=getattr(planet, "semimajor_axis_au", None),
        eccentricity=getattr(planet, "eccentricity", None),
    )
    if orbit.semimajor_axis_au is None:
        st.info("Semimajor axis or orbital period and stellar mass are missing for an orbital estimate.")
    else:
        orbit_columns = st.columns(3)
        orbit_columns[0].metric("Semimajor axis a", f"{orbit.semimajor_axis_au:.4g} AU")
        orbit_columns[1].metric(
            "Circular orbital speed at a",
            f"{orbit.circular_speed_km_s:.4g} km/s" if orbit.circular_speed_km_s is not None else "Unknown",
        )
        if orbit.periastron_distance_au is not None:
            orbit_columns[2].metric(
                "Periastron to apoastron distance",
                f"{orbit.periastron_distance_au:.4g}–{orbit.apastron_distance_au:.4g} AU",
            )
            speed_columns = st.columns(2)
            speed_columns[0].metric(
                "Speed at periastron",
                f"{orbit.periastron_speed_km_s:.4g} km/s" if orbit.periastron_speed_km_s is not None else "Unknown",
            )
            speed_columns[1].metric(
                "Speed at apoastron",
                f"{orbit.apastron_speed_km_s:.4g} km/s" if orbit.apastron_speed_km_s is not None else "Unknown",
            )
        st.caption(
            f"Distance source: {orbit.semimajor_axis_source}. Circular speed is an approximation. "
            "When eccentricity is available, periastron and apoastron show the estimated extreme "
            "distances and speeds. Measurement uncertainties are not propagated for these derived values."
        )

    st.subheader("1. Derived density and surface gravity")
    derived = derive_bulk_properties(
        planet.mass_earth,
        planet.radius_earth,
        getattr(planet, "mass_uncertainty_plus_earth", None),
        getattr(planet, "mass_uncertainty_minus_earth", None),
        getattr(planet, "radius_uncertainty_plus_earth", None),
        getattr(planet, "radius_uncertainty_minus_earth", None),
    )
    density_column, gravity_column = st.columns(2)
    density_column.metric(
        "Mean density",
        display_estimate(
            derived.bulk_density.value,
            derived.bulk_density.uncertainty_plus,
            derived.bulk_density.uncertainty_minus,
            "g/cm³",
        ),
    )
    gravity_column.metric(
        "Surface gravity",
        display_estimate(
            derived.surface_gravity.value,
            derived.surface_gravity.uncertainty_plus,
            derived.surface_gravity.uncertainty_minus,
            "m/s²",
        ),
    )
    st.caption(
        "Calculated from mass and radius in Earth units. When all four asymmetric input "
        "uncertainties are available, 20,000 independent mass-radius samples are drawn; "
        "density and gravity are recalculated for each sample to propagate measurement errors."
    )

    st.subheader("2. Two-layer model: iron core and silicate mantle")
    core_estimate = infer_rocky_core_mass_fraction(
        planet.mass_earth,
        planet.radius_earth,
        getattr(planet, "mass_uncertainty_plus_earth", None),
        getattr(planet, "mass_uncertainty_minus_earth", None),
        getattr(planet, "radius_uncertainty_plus_earth", None),
        getattr(planet, "radius_uncertainty_minus_earth", None),
    )
    if core_estimate.applicable and core_estimate.estimate is not None:
        estimate = core_estimate.estimate
        value_percent = estimate.value * 100 if estimate.value is not None else None
        plus_percent = estimate.uncertainty_plus * 100 if estimate.uncertainty_plus is not None else None
        minus_percent = estimate.uncertainty_minus * 100 if estimate.uncertainty_minus is not None else None
        st.metric(
            "Estimated iron core mass fraction (CMF)",
            display_estimate(value_percent, plus_percent, minus_percent, "%"),
        )
        st.caption(
            "Approximation from Zeng et al. (2016). It assumes a rocky planet without a water "
            "or H/He envelope and is used here for 1–8 Earth masses and CMF 0–0.4."
        )
        if core_estimate.valid_sample_fraction is not None:
            st.caption(
                "Measurement uncertainties in mass and radius are propagated through the inverse "
                "Zeng relation using 20,000 Monte Carlo samples. "
                f"{core_estimate.valid_sample_fraction:.0%} fell within the valid model domain."
            )
        if core_estimate.reason:
            st.warning(core_estimate.reason)
    else:
        st.info(core_estimate.reason or "The model is not applicable to this planet.")

    st.subheader("3. Mass–radius diagram")
    st.plotly_chart(mass_radius_figure(chart_planets), width="stretch")
    st.caption(
        "Logarithmic axes. Reference curves for CMF values of 0.0, 0.3 and 0.4 are shown in "
        "the Models section on the home page. Planets without a mass or radius cannot be plotted."
    )

    saveable_results = [
        ("bulk_density", derived.bulk_density, "g/cm³"),
        ("surface_gravity", derived.surface_gravity, "m/s²"),
    ]
    if core_estimate.applicable and core_estimate.estimate is not None:
        saveable_results.append(("iron_core_mass_fraction", core_estimate.estimate, "fraction"))
    can_save = any(estimate.value is not None for _, estimate, _ in saveable_results)
    if st.button("Save analysis results", disabled=not can_save):
        try:
            with database_session_factory()() as session:
                stored_planet = session.get(Planet, planet_id)
                run = ModelRun(
                    run_key=f"RUN-{uuid4().hex[:12]}",
                    planet_id=planet_id,
                    model_name="derived-properties-and-rocky-two-layer",
                    model_version="0.1.0",
                    status="completed",
                    is_synthetic=bool(stored_planet.is_synthetic) if stored_planet else False,
                    notes=(
                        "Density/gravity from M and R; optional rocky iron-core/silicate-mantle "
                        "CMF estimate using the Zeng et al. (2016) PREM-based relation."
                    ),
                )
                session.add(run)
                session.flush()
                for parameter, estimate, unit in saveable_results:
                    if estimate.value is None:
                        continue
                    plus = estimate.uncertainty_plus
                    minus = estimate.uncertainty_minus
                    symmetric = (plus + minus) / 2 if plus is not None and minus is not None else None
                    run.results.append(
                        ModelResult(
                            parameter=parameter,
                            value=estimate.value,
                            uncertainty=symmetric,
                            uncertainty_plus=plus,
                            uncertainty_minus=minus,
                            unit=unit,
                        )
                    )
                session.commit()
            st.session_state["analysis_saved_notice"] = True
            st.rerun()
        except SQLAlchemyError as exc:
            st.error("Could not save the analysis results.")
            st.exception(exc)

    st.subheader("Observations")
    if observation_rows:
        st.dataframe(observation_rows, hide_index=True, width="stretch")
    else:
        st.caption("No observations are stored for this planet.")

except SQLAlchemyError as exc:
    st.error("Could not load planet details from the local database.")
    st.exception(exc)
