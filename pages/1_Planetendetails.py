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
        return "unbekannt"
    return value


def display_uncertainty(plus: Any, minus: Any) -> str:
    """Format both sides of an asymmetric uncertainty, including missing sides."""
    plus_text = display_value(plus)
    minus_text = display_value(minus)
    if plus_text == "unbekannt" and minus_text == "unbekannt":
        return "unbekannt"
    return f"+ {plus_text} / − {minus_text}"


def display_estimate(value: Any, plus: Any, minus: Any, unit: str) -> str:
    """Format a derived value with asymmetric errors or explicit unknowns."""
    value = display_value(value)
    plus = display_value(plus)
    minus = display_value(minus)
    if value == "unbekannt":
        return value
    if plus == "unbekannt" and minus == "unbekannt":
        return f"{value:.4g} {unit} (Unsicherheit unbekannt)"
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


st.set_page_config(page_title="Planetendetails | PLATO Lab", page_icon="🪐", layout="wide")
apply_space_background()
st.title("Planetendetails")
st.page_link("app.py", label="← Zurück zur Übersicht", icon="🏠")

planet_id = st.session_state.get("selected_planet_id")
if planet_id is None:
    st.info("Bitte wähle einen Planeten über die Suche auf der Startseite aus.")
    st.page_link("app.py", label="Zur Planetensuche")
    st.stop()

try:
    sessions = database_session_factory()
    with sessions() as session:
        planet = session.scalar(
            select(Planet).where(Planet.id == planet_id)
        )
        if planet is None:
            st.warning("Der ausgewählte Planet ist in der Datenbank nicht mehr vorhanden.")
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
                "Messgröße": observation.observable,
                "Wert": display_value(observation.value),
                "Unsicherheit": display_value(observation.uncertainty),
                "Einheit": display_value(observation.unit),
                "Datenprodukt": display_value(observation.product.product_key if observation.product else None),
                "Stufe": display_value(observation.product.level if observation.product else None),
                "Produktversion": display_value(observation.product.version if observation.product else None),
                "Herkunft": display_value(observation.provenance),
                "Synthetisch": observation.is_synthetic,
            }
            for observation in observations
        ]
        planet_info = {
            "Name": planet.name,
            "Katalog-ID": planet.catalog_id,
            "Umlaufperiode (Tage)": display_value(planet.orbital_period_days),
            "Umlaufperioden-Unsicherheit + / − (Tage)": display_uncertainty(
                getattr(planet, "orbital_period_uncertainty_plus_days", None),
                getattr(planet, "orbital_period_uncertainty_minus_days", None),
            ),
            "Große Halbachse + / − (AU)": display_uncertainty(
                getattr(planet, "semimajor_axis_uncertainty_plus_au", None),
                getattr(planet, "semimajor_axis_uncertainty_minus_au", None),
            ),
            "Große Halbachse (AU)": display_value(getattr(planet, "semimajor_axis_au", None)),
            "Bahnexzentrizität + / −": display_uncertainty(
                getattr(planet, "eccentricity_uncertainty_plus", None),
                getattr(planet, "eccentricity_uncertainty_minus", None),
            ),
            "Bahnexzentrizität": display_value(getattr(planet, "eccentricity", None)),
            "Radius (Erdradien)": display_value(planet.radius_earth),
            "Radiusunsicherheit + / − (Erdradien)": display_uncertainty(
                getattr(planet, "radius_uncertainty_plus_earth", None),
                getattr(planet, "radius_uncertainty_minus_earth", None),
            ),
            "Masse (Erdmassen)": display_value(planet.mass_earth),
            "Massenunsicherheit + / − (Erdmassen)": display_uncertainty(
                getattr(planet, "mass_uncertainty_plus_earth", None),
                getattr(planet, "mass_uncertainty_minus_earth", None),
            ),
            "Synthetisch": planet.is_synthetic,
            "Herkunft": display_value(planet.provenance),
            "Datenstand": display_value(getattr(planet, "data_release", None)),
            "Quelle": display_value(getattr(planet, "source_url", None)),
        }
        star_info = {
            "Stern": star.name,
            "Stern-Katalog-ID": star.catalog_id,
            "Effektive Temperatur (K)": display_value(star.effective_temperature_k),
            "Temperaturunsicherheit + / − (K)": display_uncertainty(
                getattr(star, "effective_temperature_uncertainty_plus_k", None),
                getattr(star, "effective_temperature_uncertainty_minus_k", None),
            ),
            "Sternradius (Sonnenradien)": display_value(star.radius_solar),
            "Radiusunsicherheit + / − (Sonnenradien)": display_uncertainty(
                getattr(star, "radius_uncertainty_plus_solar", None),
                getattr(star, "radius_uncertainty_minus_solar", None),
            ),
            "Sternmasse (Sonnenmassen)": display_value(getattr(star, "mass_solar", None)),
            "Sternmassenunsicherheit + / − (Sonnenmassen)": display_uncertainty(
                getattr(star, "mass_uncertainty_plus_solar", None),
                getattr(star, "mass_uncertainty_minus_solar", None),
            ),
            "Synthetisch": star.is_synthetic,
            "Herkunft": display_value(star.provenance),
            "Datenstand": display_value(getattr(star, "data_release", None)),
            "Quelle": display_value(getattr(star, "source_url", None)),
        }

    st.header(planet_info["Name"])
    st.caption(f"Katalog-ID: {planet_info['Katalog-ID']}")
    st.info(
        "Öffentliche Katalogwerte sind mit ihrer Quelle gekennzeichnet. "
        "Der Demo-Datensatz ist ausdrücklich synthetisch und keine PLATO-Messung."
    )
    if st.session_state.pop("analysis_saved_notice", False):
        st.success("Die Analyseergebnisse wurden gespeichert.")

    st.subheader("Planetenparameter")
    show_parameter_grid(planet_info)
    st.subheader("Zugehöriger Stern")
    show_parameter_grid(star_info)

    st.subheader("Bahnabstand und Umlaufgeschwindigkeit")
    orbit = calculate_orbital_kinematics(
        orbital_period_days=planet.orbital_period_days,
        stellar_mass_solar=getattr(star, "mass_solar", None),
        planet_mass_earth=planet.mass_earth,
        semimajor_axis_au=getattr(planet, "semimajor_axis_au", None),
        eccentricity=getattr(planet, "eccentricity", None),
    )
    if orbit.semimajor_axis_au is None:
        st.info("Für eine Bahnnäherung fehlen große Halbachse bzw. Umlaufperiode und Sternmasse.")
    else:
        orbit_columns = st.columns(3)
        orbit_columns[0].metric("Große Halbachse a", f"{orbit.semimajor_axis_au:.4g} AU")
        orbit_columns[1].metric(
            "Kreisbahn-Geschwindigkeit bei a",
            f"{orbit.circular_speed_km_s:.4g} km/s" if orbit.circular_speed_km_s is not None else "unbekannt",
        )
        if orbit.periastron_distance_au is not None:
            orbit_columns[2].metric(
                "Periastron bis Apoastron",
                f"{orbit.periastron_distance_au:.4g}–{orbit.apastron_distance_au:.4g} AU",
            )
            speed_columns = st.columns(2)
            speed_columns[0].metric(
                "Geschwindigkeit am Periastron",
                f"{orbit.periastron_speed_km_s:.4g} km/s" if orbit.periastron_speed_km_s is not None else "unbekannt",
            )
            speed_columns[1].metric(
                "Geschwindigkeit am Apoastron",
                f"{orbit.apastron_speed_km_s:.4g} km/s" if orbit.apastron_speed_km_s is not None else "unbekannt",
            )
        st.caption(
            f"Abstand: {orbit.semimajor_axis_source}. Die Kreisbahngeschwindigkeit ist eine Näherung. "
            "Wenn die Exzentrizität vorliegt, zeigen Periastron und Apoastron die modellierten Extremwerte "
            "der Entfernung und Geschwindigkeit. Messunsicherheiten werden für diese abgeleiteten Werte "
            "noch nicht fortgepflanzt."
        )

    st.subheader("1. Abgeleitete Dichte und Oberflächengravitation")
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
        "Mittlere Dichte",
        display_estimate(
            derived.bulk_density.value,
            derived.bulk_density.uncertainty_plus,
            derived.bulk_density.uncertainty_minus,
            "g/cm³",
        ),
    )
    gravity_column.metric(
        "Oberflächengravitation",
        display_estimate(
            derived.surface_gravity.value,
            derived.surface_gravity.uncertainty_plus,
            derived.surface_gravity.uncertainty_minus,
            "m/s²",
        ),
    )
    st.caption(
        "Aus Masse und Radius in Erdmassen bzw. Erdradien berechnet. "
        "Fehlerintervalle erscheinen nur, wenn alle vier Eingangsunsicherheiten bekannt sind."
    )

    st.subheader("2. Zwei-Schichten-Modell: Eisenkern und Silikatmantel")
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
            "Geschätzter Eisenkern-Massenanteil (CMF)",
            display_estimate(value_percent, plus_percent, minus_percent, "%"),
        )
        st.caption(
            "Näherung nach Zeng et al. (2016). Sie setzt einen felsigen Planeten ohne "
            "Wasser- oder H/He-Hülle voraus und gilt hier für 1–8 Erdmassen und CMF 0–0,4."
        )
        if core_estimate.valid_sample_fraction is not None:
            st.caption(
                f"{core_estimate.valid_sample_fraction:.0%} der Unsicherheitsziehungen lagen im Modellbereich."
            )
        if core_estimate.reason:
            st.warning(core_estimate.reason)
    else:
        st.info(core_estimate.reason or "Für diesen Planeten ist das Modell nicht anwendbar.")

    st.subheader("3. Masse-Radius-Diagramm")
    st.plotly_chart(mass_radius_figure(chart_planets), width="stretch")
    st.caption(
        "Logarithmische Achsen. Referenzkurven für die Modellannahmen CMF 0,0, 0,3 und 0,4 "
        "werden auf der Startseite im Bereich ‚Modelle‘ angezeigt. Planeten ohne Masse oder "
        "Radius können nicht als Punkte dargestellt werden."
    )

    saveable_results = [
        ("bulk_density", derived.bulk_density, "g/cm³"),
        ("surface_gravity", derived.surface_gravity, "m/s²"),
    ]
    if core_estimate.applicable and core_estimate.estimate is not None:
        saveable_results.append(("iron_core_mass_fraction", core_estimate.estimate, "fraction"))
    can_save = any(estimate.value is not None for _, estimate, _ in saveable_results)
    if st.button("Analyseergebnisse speichern", disabled=not can_save):
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
            st.error("Die Analyseergebnisse konnten nicht gespeichert werden.")
            st.exception(exc)

    st.subheader("Beobachtungen")
    if observation_rows:
        st.dataframe(observation_rows, hide_index=True, width="stretch")
    else:
        st.caption("Für diesen Planeten sind keine Beobachtungen hinterlegt.")

except SQLAlchemyError as exc:
    st.error("Die Planetendetails konnten nicht aus der lokalen Datenbank geladen werden.")
    st.exception(exc)
