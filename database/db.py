"""SQLite engine and schema lifecycle helpers."""

from pathlib import Path

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from database.seed import seed_demo_data, seed_public_planets
from models import Base

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = f"sqlite:///{PROJECT_ROOT / 'data' / 'plato_demo.db'}"


def get_engine(database_url: str = DEFAULT_DATABASE_URL) -> Engine:
    """Create a SQLite engine, enabling FK checks for each connection."""
    engine = create_engine(database_url, future=True)
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(connection, _record) -> None:  # type: ignore[no-untyped-def]
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_schema(engine: Engine) -> None:
    """Create all tables described by this demonstrator's ORM models."""
    Base.metadata.create_all(engine)
    _migrate_star_columns(engine)
    _migrate_planet_columns(engine)
    _migrate_model_result_columns(engine)


def _migrate_star_columns(engine: Engine) -> None:
    """Add source and uncertainty fields to databases created by earlier versions."""
    columns = {column["name"] for column in inspect(engine).get_columns("stars")}
    additions = {
        "effective_temperature_uncertainty_plus_k": "FLOAT",
        "effective_temperature_uncertainty_minus_k": "FLOAT",
        "radius_uncertainty_plus_solar": "FLOAT",
        "radius_uncertainty_minus_solar": "FLOAT",
        "mass_solar": "FLOAT",
        "mass_uncertainty_plus_solar": "FLOAT",
        "mass_uncertainty_minus_solar": "FLOAT",
        "source_url": "VARCHAR(300)",
        "data_release": "VARCHAR(40)",
    }
    with engine.begin() as connection:
        for column_name, column_type in additions.items():
            if column_name not in columns:
                connection.execute(text(f"ALTER TABLE stars ADD COLUMN {column_name} {column_type}"))


def _migrate_planet_columns(engine: Engine) -> None:
    """Add published parameter uncertainties and provenance to older DBs."""
    columns = {column["name"] for column in inspect(engine).get_columns("planets")}
    additions = {
        "orbital_period_uncertainty_plus_days": "FLOAT",
        "orbital_period_uncertainty_minus_days": "FLOAT",
        "semimajor_axis_au": "FLOAT",
        "semimajor_axis_uncertainty_plus_au": "FLOAT",
        "semimajor_axis_uncertainty_minus_au": "FLOAT",
        "eccentricity": "FLOAT",
        "eccentricity_uncertainty_plus": "FLOAT",
        "eccentricity_uncertainty_minus": "FLOAT",
        "radius_uncertainty_plus_earth": "FLOAT",
        "radius_uncertainty_minus_earth": "FLOAT",
        "mass_uncertainty_plus_earth": "FLOAT",
        "mass_uncertainty_minus_earth": "FLOAT",
        "source_url": "VARCHAR(300)",
        "data_release": "VARCHAR(40)",
    }
    with engine.begin() as connection:
        for column_name, column_type in additions.items():
            if column_name not in columns:
                connection.execute(text(f"ALTER TABLE planets ADD COLUMN {column_name} {column_type}"))


def _migrate_model_result_columns(engine: Engine) -> None:
    """Store asymmetric uncertainty intervals for computed model results."""
    columns = {column["name"] for column in inspect(engine).get_columns("model_results")}
    with engine.begin() as connection:
        for column_name in ("uncertainty_plus", "uncertainty_minus"):
            if column_name not in columns:
                connection.execute(text(f"ALTER TABLE model_results ADD COLUMN {column_name} FLOAT"))


def init_db(database_url: str = DEFAULT_DATABASE_URL) -> Engine:
    """Create schema and add synthetic records to an empty database."""
    if database_url.startswith("sqlite:///") and ":memory:" not in database_url:
        Path(database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = get_engine(database_url)
    create_schema(engine)
    factory = get_session_factory(engine)
    with factory() as session:
        if session.query(Base.metadata.tables["stars"]).count() == 0:
            seed_demo_data(session)
        seed_public_planets(session)
    return engine
