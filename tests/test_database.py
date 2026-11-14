"""Database tests against isolated temporary SQLite files."""

from sqlalchemy import inspect, select

from analysis.formatting import display_uncertainty, display_value
from database import get_session_factory, init_db
from models import DataProduct, ModelResult, ModelRun, Observation, Planet, Star


def test_missing_scientific_values_are_rendered_as_unknown():
    assert display_value(None) == "unbekannt"
    assert display_uncertainty(None, None) == "unbekannt"
    assert display_uncertainty(0.2, None) == "+ 0.2 / − unbekannt"


def test_init_db_creates_schema_and_synthetic_demo_data(tmp_path):
    db_path = tmp_path / "test.db"
    engine = init_db(f"sqlite:///{db_path}")
    try:
        tables = set(inspect(engine).get_table_names())
        assert {"stars", "planets", "observations", "data_products", "model_runs", "model_results"} <= tables

        sessions = get_session_factory(engine)
        with sessions() as session:
            assert session.scalar(select(Star).where(Star.is_synthetic.is_(True))) is not None
            public_planets = list(session.scalars(select(Planet).where(Planet.is_synthetic.is_(False))))
            assert len(public_planets) == 50
            assert all(planet.source_url and planet.data_release for planet in public_planets)
            assert all(planet.star is not None and not planet.star.is_synthetic for planet in public_planets)
            assert all(planet.mass_earth is not None for planet in public_planets)
            assert session.scalar(select(Planet).where(Planet.is_synthetic.is_(True))) is not None
            products = list(session.scalars(select(DataProduct).order_by(DataProduct.level)))
            assert {product.level for product in products} == {"L2", "L3"}
            assert all(product.is_synthetic for product in products)
            assert session.scalar(select(Observation)) is not None
            run = session.scalar(select(ModelRun))
            assert run is not None and run.is_synthetic
            assert session.scalar(select(ModelResult).where(ModelResult.run_id == run.id)) is not None
    finally:
        engine.dispose()


def test_init_db_is_idempotent(tmp_path):
    url = f"sqlite:///{tmp_path / 'repeat.db'}"
    engine = init_db(url)
    sessions = get_session_factory(engine)
    with sessions() as session:
        before = session.query(Star).count()
    engine.dispose()

    engine = init_db(url)
    with get_session_factory(engine)() as session:
        assert session.query(Star).count() == before
        assert session.query(Planet).filter(Planet.is_synthetic.is_(False)).count() == 50
    engine.dispose()
