"""Numerical checks for the first demonstrator planet models."""

import pytest
import numpy as np
from types import SimpleNamespace

from analysis.planet_models import (
    derive_bulk_properties,
    infer_rocky_core_mass_fraction,
    rocky_reference_curves,
)
from analysis.visualization import mass_radius_figure, selected_planet_id


def test_earth_reference_derived_properties():
    result = derive_bulk_properties(1.0, 1.0)
    assert result.bulk_density.value == pytest.approx(5.514)
    assert result.surface_gravity.value == pytest.approx(9.80665)
    assert result.bulk_density.uncertainty_plus is None


def test_derived_properties_propagate_asymmetric_measurement_errors():
    result = derive_bulk_properties(1.0, 1.0, 0.1, 0.08, 0.02, 0.01, samples=2_000)
    assert result.bulk_density.uncertainty_plus is not None
    assert result.bulk_density.uncertainty_minus is not None
    assert result.surface_gravity.uncertainty_plus is not None


def test_rocky_model_inverts_earth_like_composition_and_checks_domain():
    result = infer_rocky_core_mass_fraction(1.0, 1.0)
    assert result.applicable
    assert result.estimate is not None
    assert result.estimate.value == pytest.approx(1 / 3)

    outside_mass_range = infer_rocky_core_mass_fraction(10.0, 2.0)
    assert not outside_mass_range.applicable
    assert outside_mass_range.reason is not None


def test_reference_curves_cover_only_the_documented_mass_range():
    curves = rocky_reference_curves()
    assert set(curves) == {0.0, 0.3, 0.4}
    assert all(
        mass[0] == pytest.approx(1.0) and mass[-1] == pytest.approx(8.0)
        for mass, _radius in curves.values()
    )


def test_reference_curves_accept_selected_cmf_but_reject_values_outside_domain():
    curves = rocky_reference_curves(core_mass_fractions=(0.26,))
    assert set(curves) == {0.26}
    with pytest.raises(ValueError, match="outside the supported interval"):
        rocky_reference_curves(core_mass_fractions=(0.41,))
    with pytest.raises(ValueError, match="only defined here for 1–8 Earth masses"):
        rocky_reference_curves(masses_earth=np.array([0.5, 1.0]))


def test_mass_radius_figure_uses_log_axes_and_embeds_planet_id_for_navigation():
    figure = mass_radius_figure([
        {
            "id": 42,
            "name": "Demo planet",
            "mass": 2.0,
            "radius": 1.4,
            "mass_plus": 0.2,
            "mass_minus": 0.1,
            "radius_plus": 0.1,
            "radius_minus": 0.1,
        }
    ])
    assert figure.layout.xaxis.type == "log"
    assert figure.layout.yaxis.type == "log"
    assert len(figure.data) == 1  # Homepage chart contains planet data only.
    planet_trace = figure.data[-1]
    assert list(planet_trace.customdata[0]) == [42]


def test_rocky_reference_curves_are_available_only_when_requested():
    planets = [{"id": 42, "name": "Demo", "mass": 2.0, "radius": 1.4}]
    figure = mass_radius_figure(planets, include_rocky_references=True)
    assert [trace.name for trace in figure.data[:3]] == [
        "Rocky reference, CMF 0%",
        "Rocky reference, CMF 30%",
        "Rocky reference, CMF 40%",
    ]


def test_mass_radius_figure_can_show_one_selected_cmf_in_a_fixed_valid_domain():
    figure = mass_radius_figure(
        [{"id": 42, "name": "Demo", "mass": 2.0, "radius": 1.4}],
        rocky_core_mass_fractions=(0.26,),
        mass_axis_range=(1.0, 8.0),
    )
    assert figure.data[0].name == "Rocky reference, CMF 26%"
    assert list(figure.data[0].x)[0] == pytest.approx(1.0)
    assert list(figure.data[0].x)[-1] == pytest.approx(8.0)
    assert list(figure.layout.xaxis.range) == pytest.approx((0.0, 0.90309), abs=1e-5)


def test_selected_planet_id_extracts_plotly_customdata():
    event = SimpleNamespace(
        selection=SimpleNamespace(points=[{"customdata": [42]}])
    )
    assert selected_planet_id(event) == 42
    assert selected_planet_id(SimpleNamespace(selection=SimpleNamespace(points=[]))) is None
