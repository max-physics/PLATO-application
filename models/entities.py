"""ORM entities for a project-specific, non-official PLATO-style demo schema."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Star(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True)
    catalog_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    effective_temperature_k: Mapped[float | None] = mapped_column(Float)
    effective_temperature_uncertainty_plus_k: Mapped[float | None] = mapped_column(Float)
    effective_temperature_uncertainty_minus_k: Mapped[float | None] = mapped_column(Float)
    radius_solar: Mapped[float | None] = mapped_column(Float)
    radius_uncertainty_plus_solar: Mapped[float | None] = mapped_column(Float)
    radius_uncertainty_minus_solar: Mapped[float | None] = mapped_column(Float)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    provenance: Mapped[str] = mapped_column(String(240), default="Synthetic demonstrator dataset")
    source_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    data_release: Mapped[str | None] = mapped_column(String(40), nullable=True)

    planets: Mapped[list[Planet]] = relationship(back_populates="star", cascade="all, delete-orphan")


class Planet(Base):
    __tablename__ = "planets"
    __table_args__ = (CheckConstraint("orbital_period_days IS NULL OR orbital_period_days > 0"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    catalog_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    star_id: Mapped[int] = mapped_column(ForeignKey("stars.id", ondelete="CASCADE"), index=True)
    orbital_period_days: Mapped[float | None] = mapped_column(Float)
    orbital_period_uncertainty_plus_days: Mapped[float | None] = mapped_column(Float)
    orbital_period_uncertainty_minus_days: Mapped[float | None] = mapped_column(Float)
    radius_earth: Mapped[float | None] = mapped_column(Float)
    radius_uncertainty_plus_earth: Mapped[float | None] = mapped_column(Float)
    radius_uncertainty_minus_earth: Mapped[float | None] = mapped_column(Float)
    mass_earth: Mapped[float | None] = mapped_column(Float)
    mass_uncertainty_plus_earth: Mapped[float | None] = mapped_column(Float)
    mass_uncertainty_minus_earth: Mapped[float | None] = mapped_column(Float)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    provenance: Mapped[str] = mapped_column(String(240), default="Synthetic demonstrator dataset")
    source_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    data_release: Mapped[str | None] = mapped_column(String(40), nullable=True)

    star: Mapped[Star] = relationship(back_populates="planets")
    observations: Mapped[list[Observation]] = relationship(back_populates="planet", cascade="all, delete-orphan")
    model_runs: Mapped[list[ModelRun]] = relationship(back_populates="planet", cascade="all, delete-orphan")


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    planet_id: Mapped[int] = mapped_column(ForeignKey("planets.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("data_products.id", ondelete="SET NULL"), nullable=True)
    observable: Mapped[str] = mapped_column(String(100))
    value: Mapped[float] = mapped_column(Float)
    uncertainty: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(40))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    provenance: Mapped[str] = mapped_column(String(240), default="Synthetic demonstrator dataset")

    planet: Mapped[Planet] = relationship(back_populates="observations")
    product: Mapped[DataProduct | None] = relationship(back_populates="observations")


class DataProduct(Base):
    __tablename__ = "data_products"
    __table_args__ = (CheckConstraint("level IN ('L2', 'L3')", name="ck_data_product_level"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    level: Mapped[str] = mapped_column(String(2))
    version: Mapped[str] = mapped_column(String(40))
    provenance: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    observations: Mapped[list[Observation]] = relationship(back_populates="product")
    model_runs: Mapped[list[ModelRun]] = relationship(back_populates="input_product")


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    planet_id: Mapped[int] = mapped_column(ForeignKey("planets.id", ondelete="CASCADE"), index=True)
    input_product_id: Mapped[int | None] = mapped_column(ForeignKey("data_products.id", ondelete="SET NULL"), nullable=True)
    model_name: Mapped[str] = mapped_column(String(120))
    model_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="prepared")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="Synthetic placeholder run; no physical model executed.")

    planet: Mapped[Planet] = relationship(back_populates="model_runs")
    input_product: Mapped[DataProduct | None] = relationship(back_populates="model_runs")
    results: Mapped[list[ModelResult]] = relationship(back_populates="run", cascade="all, delete-orphan")


class ModelResult(Base):
    __tablename__ = "model_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("model_runs.id", ondelete="CASCADE"), index=True)
    parameter: Mapped[str] = mapped_column(String(100))
    value: Mapped[float] = mapped_column(Float)
    uncertainty: Mapped[float | None] = mapped_column(Float)
    uncertainty_plus: Mapped[float | None] = mapped_column(Float)
    uncertainty_minus: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(40))

    run: Mapped[ModelRun] = relationship(back_populates="results")
