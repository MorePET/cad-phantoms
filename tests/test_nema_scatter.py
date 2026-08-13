"""Tests for the NEMA NU 2-2018 section 4 scatter phantom."""
import math

import pytest
from build123d import Location, Solid


def test_volumes_match_nominal(scatter, scatter_compartments):
    nominal = scatter.nominal_volumes()
    assert set(nominal) == set(scatter_compartments)
    for name, expected_ml in nominal.items():
        solid, _material, _fillable = scatter_compartments[name]
        actual_ml = solid.volume / 1000.0
        assert actual_ml == pytest.approx(expected_ml, rel=0.001), name


def test_bore_offset_and_diameter(scatter, scatter_compartments):
    """Measure the bore directly from the built geometry (not the module's
    own constants): subtract the actual phantom body from an un-bored
    cylinder of the same OD/length to recover the bore as its own solid.
    """
    body, _material, _fillable = scatter_compartments["scatter_body"]
    half = scatter.PHANTOM_LENGTH / 2.0
    full_cylinder = Solid.make_cylinder(
        scatter.PHANTOM_DIAMETER / 2, scatter.PHANTOM_LENGTH
    ).moved(Location((0, 0, -half)))

    bore_void = full_cylinder - body

    center = bore_void.center()
    radial_offset = math.hypot(center.X, center.Y)
    assert radial_offset == pytest.approx(scatter.BORE_RADIAL_OFFSET, abs=0.01)

    bbox = bore_void.bounding_box()
    diameter_x = bbox.max.X - bbox.min.X
    diameter_y = bbox.max.Y - bbox.min.Y
    assert diameter_x == pytest.approx(scatter.BORE_DIAMETER, abs=0.01)
    assert diameter_y == pytest.approx(scatter.BORE_DIAMETER, abs=0.01)


def test_overall_dimensions(scatter, scatter_compartments):
    body, _material, _fillable = scatter_compartments["scatter_body"]
    bbox = body.bounding_box()
    diameter_x = bbox.max.X - bbox.min.X
    diameter_y = bbox.max.Y - bbox.min.Y
    length_z = bbox.max.Z - bbox.min.Z
    assert diameter_x == pytest.approx(scatter.PHANTOM_DIAMETER, abs=0.01)
    assert diameter_y == pytest.approx(scatter.PHANTOM_DIAMETER, abs=0.01)
    assert length_z == pytest.approx(scatter.PHANTOM_LENGTH, abs=0.01)


def test_polyethylene_density(scatter):
    # Deliberately not pymat's stock polyethylene (0.94) -- the standard
    # fixes the specific gravity of this phantom at 0.96.
    assert scatter.phantom_material.density == pytest.approx(0.96)
