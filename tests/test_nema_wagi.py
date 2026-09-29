"""Tests for the IEC/NEMA NU 2-2018 body phantom."""
import math

import pytest

SPHERE_DIAMETERS = [10, 13, 17, 22, 28, 37]


def test_sphere_filling_volumes(wagi_compartments):
    for diameter in SPHERE_DIAMETERS:
        solid, _material, _fillable = wagi_compartments[f"sphere_{diameter}mm"]
        radius = diameter / 2.0
        expected_ml = (4.0 / 3.0) * math.pi * radius ** 3 / 1000.0
        actual_ml = solid.volume / 1000.0
        assert actual_ml == pytest.approx(expected_ml, rel=0.005), diameter


def test_outer_cross_section(wagi_compartments):
    # NU 2-2018 Figure 7-1: 300 mm wide x 230 mm tall cross-section.
    body, _material, _fillable = wagi_compartments["body_shell"]
    bbox = body.bounding_box()
    width_x = bbox.max.X - bbox.min.X
    height_y = bbox.max.Y - bbox.min.Y
    assert width_x == pytest.approx(300.0, abs=1.0)
    assert height_y == pytest.approx(230.0, abs=1.0)


def _intersection_volume_ml(a, b):
    inter = a.intersect(b)
    return 0.0 if inter is None else inter.volume / 1000.0


def test_compartments_disjoint(wagi_compartments):
    # The expensive check is all-pairs; restrict to a representative subset:
    # background liquid vs. each sphere filling, and the lung shell vs. its
    # own filling.
    background, _m, _f = wagi_compartments["background_liquid"]
    pairs = [
        (background, wagi_compartments[f"sphere_{d}mm"][0], f"background vs sphere_{d}mm")
        for d in SPHERE_DIAMETERS
    ]
    shell, _m, _f = wagi_compartments["lung_insert_shell"]
    filling, _m, _f = wagi_compartments["lung_insert_filling"]
    pairs.append((shell, filling, "lung_insert_shell vs lung_insert_filling"))

    for a, b, label in pairs:
        inter_ml = _intersection_volume_ml(a, b)
        smaller_ml = min(a.volume, b.volume) / 1000.0
        assert inter_ml < 0.001 * smaller_ml, label


def test_fillable_compartment_count(wagi_compartments):
    fillable = [name for name, (_s, _m, f) in wagi_compartments.items() if f]
    assert len(fillable) == 7
    assert set(fillable) == {"background_liquid", *(f"sphere_{d}mm" for d in SPHERE_DIAMETERS)}
