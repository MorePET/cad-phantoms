"""Tests for export_phantoms.py, run as a subprocess against the scatter
phantom (builds in ~1 s, unlike the body phantom).
"""
import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _stl_triangle_count(path):
    data = path.read_bytes()
    return struct.unpack("<I", data[80:84])[0]


@pytest.fixture(scope="module")
def export_result(tmp_path_factory, scatter_compartments):
    out_dir = tmp_path_factory.mktemp("export")
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "export_phantoms.py"),
         "--out", str(out_dir), "--phantom", "nemasp"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return result, out_dir


def test_exit_code(export_result):
    result, _out_dir = export_result
    assert result.returncode == 0, result.stderr


def test_manifest_matches_built_solids(export_result, scatter_compartments):
    _result, out_dir = export_result
    manifest_path = out_dir / "nemasp" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    assert manifest["phantom"] == "nemasp"
    assert manifest["frame"] == "world"
    assert manifest["units"] == "mm"

    names = {c["name"] for c in manifest["compartments"]}
    assert names == set(scatter_compartments)
    # Manifest is sorted by name.
    assert [c["name"] for c in manifest["compartments"]] == sorted(names)

    for entry in manifest["compartments"]:
        solid, _material, fillable = scatter_compartments[entry["name"]]
        assert entry["fillable"] == fillable
        assert entry["volume_ml"] == pytest.approx(solid.volume / 1000.0, rel=1e-6)


def test_exported_files_exist_and_are_nontrivial(export_result):
    _result, out_dir = export_result
    manifest_path = out_dir / "nemasp" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    for entry in manifest["compartments"]:
        for fmt, filename in entry["files"].items():
            path = out_dir / "nemasp" / filename
            assert path.exists(), path
            assert path.stat().st_size > 0, path

        step_path = out_dir / "nemasp" / entry["files"]["step"]
        assert step_path.stat().st_size > 1000, "STEP file looks too small to be real geometry"

        stl_path = out_dir / "nemasp" / entry["files"]["stl"]
        assert stl_path.stat().st_size > 1000, "STL file looks too small to be real geometry"
        assert _stl_triangle_count(stl_path) > 50, "STL mesh looks trivially coarse"
