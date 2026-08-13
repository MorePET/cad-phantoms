"""Tests for placement.py -- the CAD-to-world-frame mapping."""
import numpy as np
import pytest
from build123d import Location

SPHERE_DIAMETERS = [10, 13, 17, 22, 28, 37]


def _transform_point(location, point):
    """The world-frame image of a CAD-frame point, under a build123d Location."""
    moved = location * Location(point)
    v = moved.position
    return (v.X, v.Y, v.Z)


def test_body_phantom_sphere_plane_and_lung_axis(wagi, wagi_compartments, placement_mod):
    placed = placement_mod.place(wagi_compartments, placement_mod.body_phantom_placement())

    for diameter in SPHERE_DIAMETERS:
        solid, _material, _fillable = placed[f"sphere_{diameter}mm"]
        center = solid.center()
        assert center.Y == pytest.approx(0.0, abs=0.01), diameter

    filling, _material, _fillable = placed["lung_insert_filling"]
    bbox = filling.bounding_box()
    axis_x = (bbox.min.X + bbox.max.X) / 2.0
    axis_z = (bbox.min.Z + bbox.max.Z) / 2.0
    assert axis_x == pytest.approx(0.0, abs=0.01)
    assert axis_z == pytest.approx(0.0, abs=0.01)


def test_body_phantom_extent(placement_mod):
    y_min, y_max = placement_mod.body_phantom_extent()
    assert y_min == pytest.approx(-135.0)
    assert y_max == pytest.approx(82.0)


def test_scatter_phantom_placement_centred(scatter_compartments, placement_mod):
    placed = placement_mod.place(scatter_compartments, placement_mod.scatter_phantom_placement())

    body, _material, _fillable = placed["scatter_body"]
    bbox = body.bounding_box()
    center = (
        (bbox.min.X + bbox.max.X) / 2.0,
        (bbox.min.Y + bbox.max.Y) / 2.0,
        (bbox.min.Z + bbox.max.Z) / 2.0,
    )
    for c in center:
        assert c == pytest.approx(0.0, abs=0.01)

    source, _material, _fillable = placed["line_source"]
    source_center = source.center()
    assert source_center.X == pytest.approx(0.0, abs=0.01)
    assert source_center.Z == pytest.approx(-45.0, abs=0.01)


def test_abutted_scatter_placement(scatter_compartments, placement_mod):
    body_y_min, body_y_max = placement_mod.body_phantom_extent()

    head_placed = placement_mod.place(
        scatter_compartments, placement_mod.abutted_scatter_placement(end="head"))
    head_body, _m, _f = head_placed["scatter_body"]
    head_bbox = head_body.bounding_box()
    # "head" abuts the body's near (far-y) end with no gap and no overlap.
    assert head_bbox.max.Y == pytest.approx(body_y_min, abs=0.01)

    foot_placed = placement_mod.place(
        scatter_compartments, placement_mod.abutted_scatter_placement(end="foot"))
    foot_body, _m, _f = foot_placed["scatter_body"]
    foot_bbox = foot_body.bounding_box()
    assert foot_bbox.min.Y == pytest.approx(body_y_max, abs=0.01)


def test_rotation_is_proper(placement_mod):
    """A proper rotation preserves handedness: the signed volume of the
    tetrahedron formed by the images of a right-handed basis triad (relative
    to the image of the origin) stays positive. A reflection would flip it.
    """
    location = placement_mod.to_world()
    origin = np.array(_transform_point(location, (0, 0, 0)))
    ex = np.array(_transform_point(location, (1, 0, 0))) - origin
    ey = np.array(_transform_point(location, (0, 1, 0))) - origin
    ez = np.array(_transform_point(location, (0, 0, 1))) - origin

    signed_volume = np.dot(ex, np.cross(ey, ez))
    assert signed_volume > 0
