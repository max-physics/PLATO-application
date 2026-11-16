"""Tests for catalog-based Keplerian distances and velocity estimates."""

import pytest

from analysis.orbital_kinematics import calculate_orbital_kinematics


def test_earth_like_circular_orbit_speed_and_distance():
    result = calculate_orbital_kinematics(
        orbital_period_days=365.256,
        stellar_mass_solar=1.0,
        planet_mass_earth=1.0,
        semimajor_axis_au=1.0,
        eccentricity=0.0,
    )
    assert result.semimajor_axis_au == pytest.approx(1.0)
    assert result.circular_speed_km_s == pytest.approx(29.78, rel=0.002)
    assert result.periastron_distance_au == pytest.approx(1.0)
    assert result.apastron_distance_au == pytest.approx(1.0)


def test_elliptical_orbit_reports_distance_and_speed_extremes():
    result = calculate_orbital_kinematics(
        orbital_period_days=365.256,
        stellar_mass_solar=1.0,
        planet_mass_earth=None,
        semimajor_axis_au=1.0,
        eccentricity=0.2,
    )
    assert result.periastron_distance_au == pytest.approx(0.8)
    assert result.apastron_distance_au == pytest.approx(1.2)
    assert result.periastron_speed_km_s > result.circular_speed_km_s
    assert result.apastron_speed_km_s < result.circular_speed_km_s


def test_missing_semimajor_axis_is_derived_from_period_and_stellar_mass():
    result = calculate_orbital_kinematics(
        orbital_period_days=365.256,
        stellar_mass_solar=1.0,
        planet_mass_earth=None,
        semimajor_axis_au=None,
        eccentricity=None,
    )
    assert result.semimajor_axis_au == pytest.approx(1.0, rel=0.002)
    assert "Kepler's third law" in result.semimajor_axis_source
    assert result.periastron_distance_au is None


def test_missing_inputs_remain_unknown():
    result = calculate_orbital_kinematics(
        orbital_period_days=None,
        stellar_mass_solar=None,
        planet_mass_earth=None,
        semimajor_axis_au=None,
        eccentricity=None,
    )
    assert result.semimajor_axis_au is None
    assert result.circular_speed_km_s is None
