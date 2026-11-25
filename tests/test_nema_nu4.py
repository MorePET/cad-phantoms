"""Tests for the NEMA NU 4-2008 image-quality phantom and its export."""
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def nu4():
    import nema_nu4
    return nema_nu4


@pytest.fixture(scope="session")
def nu4_compartments(nu4):
    return nu4.compartments()


def test_volumes_match_nominal(nu4, nu4_compartments):
    nominal = nu4.nominal_volumes()
    assert set(nominal) == set(nu4_compartments)
    for name, expected_ml in nominal.items():
        solid, _material, _fillable = nu4_compartments[name]
        assert solid.volume / 1000.0 == pytest.approx(expected_ml, rel=1e-4), name


def test_compartments_are_disjoint(nu4_compartments):
    names = sorted(nu4_compartments)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            common = nu4_compartments[a][0] & nu4_compartments[b][0]
            assert common is None or common.volume < 1e-6, (a, b)


def test_rods_measured_from_geometry(nu4, nu4_compartments):
    for i, d in enumerate(nu4.ROD_DIAMETERS):
        bbox = nu4_compartments[f"rod_{d:g}mm"][0].bounding_box()
        assert bbox.max.X - bbox.min.X == pytest.approx(d, abs=1e-3)
        assert bbox.max.Z - bbox.min.Z == pytest.approx(nu4.ROD_LENGTH, abs=1e-3)
        cx, cy = (bbox.max.X + bbox.min.X) / 2, (bbox.max.Y + bbox.min.Y) / 2
        assert math.hypot(cx, cy) == pytest.approx(nu4.ROD_CIRCLE_RADIUS, abs=1e-3)


def test_overall_dimensions(nu4, nu4_compartments):
    bbox = nu4_compartments["phantom_body"][0].bounding_box()
    assert bbox.max.X - bbox.min.X == pytest.approx(nu4.OUTER_DIAMETER, abs=1e-3)
    assert bbox.max.Z - bbox.min.Z == pytest.approx(nu4.OVERALL_LENGTH, abs=1e-3)


def test_fillable_and_materials(nu4_compartments):
    fillable = {k for k, (_s, _m, f) in nu4_compartments.items() if f}
    assert fillable == {"uniform_fill", *(f"rod_{d}mm" for d in range(1, 6))}
    assert nu4_compartments["cold_air"][1].density < 0.01
    assert nu4_compartments["cold_water"][1].density == pytest.approx(1.0, abs=0.01)


def test_export_manifest(tmp_path):
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "export_phantoms.py"),
         "--out", str(tmp_path), "--phantom", "nu4", "--formats", "stl"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads((tmp_path / "nu4" / "manifest.json").read_text())
    assert manifest["phantom"] == "nu4" and manifest["frame"] == "world"
    by_name = {c["name"]: c for c in manifest["compartments"]}
    # World frame: the axis is y, the phantom centred on the origin.
    body = by_name["phantom_body"]["bbox_mm"]
    assert body["min"][1] == pytest.approx(-31.5, abs=1e-3)
    assert body["max"][1] == pytest.approx(31.5, abs=1e-3)
    # The rods are on the +y side (the CAD base maps to world y = +31.5).
    rod = by_name["rod_5mm"]["bbox_mm"]
    assert rod["min"][1] > 0
    assert manifest["parameters"]["cold_wall_mm"] == 1.0
