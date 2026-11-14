"""Streamlit entry point for the PLATO Scientific Data Analysis Lab."""

import streamlit as st
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from analysis.planet_models import derive_bulk_properties, infer_rocky_core_mass_fraction
from database import get_session_factory, init_db
from models import Planet
from analysis.visualization import mass_radius_figure, selected_planet_id


@st.cache_resource
def database_session_factory():
    """Initialize the local demo database once per Streamlit process."""
    engine = init_db()
    return get_session_factory(engine)


def format_model_estimate(value, plus, minus, unit: str) -> str:
    """Format a model value and its optional asymmetric uncertainty."""
    if value is None:
        return "unbekannt"
    if plus is None and minus is None:
        return f"{value:.4g} {unit} (Unsicherheit unbekannt)"
    plus_text = f"{plus:.3g}" if plus is not None else "unbekannt"
    minus_text = f"{minus:.3g}" if minus is not None else "unbekannt"
    return f"{value:.4g} +{plus_text}/−{minus_text} {unit}"


st.set_page_config(
    page_title="PLATO Scientific Data Analysis Lab",
    page_icon="🪐",
    layout="centered",
    initial_sidebar_state="collapsed",
)
st.title("PLATO Scientific Data Analysis Lab")
st.caption("Suche einen Planeten nach Name oder Katalog-ID, um seine Parameter anzusehen.")
search_term = st.text_input(
    "Suche nach Name oder Katalog-ID",
    placeholder="z. B. Demo Planet b oder SYNTH-PLANET-001",
    help="Die Suche berücksichtigt Planetenname und Katalog-ID.",
    label_visibility="collapsed",
)
all_planets = []
try:
    sessions = database_session_factory()
    with sessions() as session:
        all_planets = list(session.scalars(select(Planet).order_by(Planet.name)))

    if search_term.strip():
        normalized_term = search_term.strip().casefold()
        matching_planets = [
            planet for planet in all_planets
            if normalized_term in planet.name.casefold()
            or normalized_term in planet.catalog_id.casefold()
        ]
    else:
        matching_planets = []

    if search_term.strip() and matching_planets:
        selected_planet = st.selectbox(
            "Suchergebnis",
            matching_planets,
            format_func=lambda planet: f"{planet.name} ({planet.catalog_id})",
            key="planet_search_selection",
        )
        if st.button("Planetendetails öffnen", type="primary"):
            st.session_state["selected_planet_id"] = selected_planet.id
            st.switch_page("pages/1_Planetendetails.py")
    elif search_term.strip():
        st.caption("Kein Planet passt zu dieser Suche.")
except SQLAlchemyError as exc:
    st.error("Die Planetensuche konnte die lokale Datenbank nicht abfragen.")
    st.exception(exc)

st.subheader("Masse-Radius-Diagramm")
st.caption(
    "Bewege den Mauszeiger über einen Punkt für den Namen. Klicke auf einen Planetenpunkt, "
    "um seine Detailseite zu öffnen. Beide Achsen sind logarithmisch; Modellkurven findest du im Reiter darunter."
)
chart_planets = [
    {
        "id": planet.id,
        "name": planet.name,
        "mass": planet.mass_earth,
        "mass_plus": getattr(planet, "mass_uncertainty_plus_earth", None),
        "mass_minus": getattr(planet, "mass_uncertainty_minus_earth", None),
        "radius": planet.radius_earth,
        "radius_plus": getattr(planet, "radius_uncertainty_plus_earth", None),
        "radius_minus": getattr(planet, "radius_uncertainty_minus_earth", None),
    }
    for planet in all_planets
]
chart_event = st.plotly_chart(
    mass_radius_figure(chart_planets),
    width="stretch",
    key="home_mass_radius_chart",
    on_select="rerun",
    selection_mode="points",
)
planet_id_from_chart = selected_planet_id(chart_event)
if planet_id_from_chart is not None:
    st.session_state["selected_planet_id"] = planet_id_from_chart
    st.switch_page("pages/1_Planetendetails.py")

models_tab, = st.tabs(["Modelle"])
with models_tab:
    if all_planets:
        selected_model_planet = st.selectbox(
            "Planet für Modellrechnung",
            all_planets,
            format_func=lambda planet: f"{planet.name} ({planet.catalog_id})",
            key="home_model_planet",
        )
        density_tab, rocky_tab = st.tabs(["Dichte & Gravitation", "Zwei-Schichten-Modell"])

        with density_tab:
            derived = derive_bulk_properties(
                selected_model_planet.mass_earth,
                selected_model_planet.radius_earth,
                getattr(selected_model_planet, "mass_uncertainty_plus_earth", None),
                getattr(selected_model_planet, "mass_uncertainty_minus_earth", None),
                getattr(selected_model_planet, "radius_uncertainty_plus_earth", None),
                getattr(selected_model_planet, "radius_uncertainty_minus_earth", None),
            )
            density_col, gravity_col = st.columns(2)
            density_col.metric(
                "Mittlere Dichte",
                format_model_estimate(
                    derived.bulk_density.value,
                    derived.bulk_density.uncertainty_plus,
                    derived.bulk_density.uncertainty_minus,
                    "g/cm³",
                ),
            )
            gravity_col.metric(
                "Oberflächengravitation",
                format_model_estimate(
                    derived.surface_gravity.value,
                    derived.surface_gravity.uncertainty_plus,
                    derived.surface_gravity.uncertainty_minus,
                    "m/s²",
                ),
            )
            st.caption(
                "Aus Masse und Radius in Erdmassen bzw. Erdradien berechnet. "
                "Unsicherheiten werden fortgepflanzt, wenn alle Eingangsfehler verfügbar sind."
            )

        with rocky_tab:
            core = infer_rocky_core_mass_fraction(
                selected_model_planet.mass_earth,
                selected_model_planet.radius_earth,
                getattr(selected_model_planet, "mass_uncertainty_plus_earth", None),
                getattr(selected_model_planet, "mass_uncertainty_minus_earth", None),
                getattr(selected_model_planet, "radius_uncertainty_plus_earth", None),
                getattr(selected_model_planet, "radius_uncertainty_minus_earth", None),
            )
            if core.applicable and core.estimate is not None:
                estimate = core.estimate
                st.metric(
                    "Geschätzter Eisenkern-Massenanteil (CMF)",
                    format_model_estimate(
                        estimate.value * 100 if estimate.value is not None else None,
                        estimate.uncertainty_plus * 100 if estimate.uncertainty_plus is not None else None,
                        estimate.uncertainty_minus * 100 if estimate.uncertainty_minus is not None else None,
                        "%",
                    ),
                )
                if core.valid_sample_fraction is not None:
                    st.caption(f"{core.valid_sample_fraction:.0%} der Unsicherheitsziehungen lagen im Modellbereich.")
            else:
                st.info(core.reason or "Für diesen Planeten ist das Modell nicht anwendbar.")
            st.caption(
                "Die Kurven zeigen felsige Referenzmodelle für CMF 0,0, 0,3 und 0,4. "
                "Die Näherung nach Zeng et al. (2016) gilt hier für 1–8 Erdmassen und CMF 0–0,4."
            )
            st.plotly_chart(
                mass_radius_figure(chart_planets, include_rocky_references=True),
                width="stretch",
                key="home_rocky_model_comparison",
            )
    else:
        st.info("Es sind derzeit keine Planeten für Modellrechnungen vorhanden.")
