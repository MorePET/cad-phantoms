"""Export the phantom compartments for the downstream voxelizer.

Each named phantom configuration below is written as one STEP/STL file per
compartment, plus a `manifest.json` describing them, into
`<out>/<phantom>/`. Every file is already in the world frame (see
`placement.py`) and in millimetres, so the voxelizer and the simulation
configs never have to apply a rotation or translation of their own.

Usage:
    python3 export_phantoms.py --out build/ \\
        [--phantom nemaiq|nemasp|nemaabut|all] \\
        [--formats step,stl] \\
        [--abut-end head|foot]
"""
import argparse
import json
from pathlib import Path

from build123d import export_step, export_stl
from build123d.topology.shape_core import downcast
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy

import nema_scatter
import nema_wagi
import placement

PHANTOM_NAMES = ("nemaiq", "nemasp", "nemaabut")
FORMAT_EXTENSIONS = {"step": "step", "stl": "stl"}


def _independent_copy(solid):
    """A solid/compound with its own, unshared OCCT shape data.

    `nema_wagi.py` reuses every `compartments()` solid as a child of the
    `nema_phantom_filled` assembly it builds at import time (for the
    standalone-script viewer/export), including as an operand of later
    boolean subtractions. That leaves the individual solids' underlying
    TopoDS_TShape in a state the STEP writer refuses ("Failed to write STEP
    file") even though the shape is otherwise geometrically valid and meshes
    fine for STL. `Shape.__deepcopy__` does not clear this up (verified).
    An explicit `BRepBuilderAPI_Copy` produces a fully independent shape, so
    it is applied here to every compartment before export.
    """
    copied = downcast(BRepBuilderAPI_Copy(solid.wrapped, True, True).Shape())
    return type(solid)(copied)


def _sanitize(compartments):
    """Apply `_independent_copy` to every compartment's solid."""
    return {
        name: (_independent_copy(solid), material, fillable)
        for name, (solid, material, fillable) in compartments.items()
    }


def _build_compartments(phantom, abut_end):
    """name -> (solid, material, fillable), already placed in the world frame."""
    if phantom == "nemaiq":
        return _sanitize(
            placement.place(nema_wagi.compartments(), placement.body_phantom_placement()))

    if phantom == "nemasp":
        return _sanitize(
            placement.place(nema_scatter.compartments(), placement.scatter_phantom_placement()))

    if phantom == "nemaabut":
        body = placement.place(nema_wagi.compartments(), placement.body_phantom_placement())
        scatter = placement.place(
            nema_scatter.compartments(),
            placement.abutted_scatter_placement(end=abut_end),
        )
        combined = dict(body)
        for name, entry in scatter.items():
            # Prefix on collision only -- today the two modules' compartment
            # names do not overlap, but a future rename in either one must
            # not produce a silently-merged compartment here.
            key = f"scatter_{name}" if name in combined else name
            if key in combined:
                raise RuntimeError(
                    f"compartment name collision even after prefixing: {key!r}")
            combined[key] = entry
        return _sanitize(combined)

    raise ValueError(f"unknown phantom {phantom!r}, expected one of {PHANTOM_NAMES}")


def _export_compartment(name, solid, out_dir, formats):
    """Write one compartment's requested formats; return name -> relative path."""
    files = {}
    for fmt in formats:
        ext = FORMAT_EXTENSIONS[fmt]
        path = out_dir / f"{name}.{ext}"
        if fmt == "step":
            # Default unit is Unit.MM, matching the world frame's millimetres.
            export_step(solid, str(path))
        elif fmt == "stl":
            # build123d's default STL tolerance (0.001 mm) was checked against
            # the smallest feature in these phantoms (the 10 mm sphere): it
            # meshes to ~10,000 triangles, far above "visibly coarse", so the
            # default is used as-is rather than overridden.
            export_stl(solid, str(path))
        files[fmt] = path.name
    return files


def _manifest_entry(name, solid, material, fillable, files):
    bbox = solid.bounding_box()
    return {
        "name": name,
        "fillable": fillable,
        "material": {
            "name": material.name,
            "density_g_cm3": material.density,
            "formula": material.formula,
        },
        "volume_ml": solid.volume / 1000.0,
        "bbox_mm": {
            "min": [bbox.min.X, bbox.min.Y, bbox.min.Z],
            "max": [bbox.max.X, bbox.max.Y, bbox.max.Z],
        },
        "files": files,
    }


def export_phantom(phantom, out, formats, abut_end):
    """Build, export and write the manifest for one phantom. Returns the manifest dict."""
    out_dir = out / phantom
    out_dir.mkdir(parents=True, exist_ok=True)

    compartments = _build_compartments(phantom, abut_end)

    entries = []
    for name in sorted(compartments):
        solid, material, fillable = compartments[name]
        files = _export_compartment(name, solid, out_dir, formats)
        entries.append(_manifest_entry(name, solid, material, fillable, files))

    manifest = {
        "phantom": phantom,
        "frame": "world",
        "units": "mm",
        "abut_end": abut_end if phantom == "nemaabut" else None,
        "compartments": entries,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    n_fillable = sum(1 for e in entries if e["fillable"])
    fillable_volume = sum(e["volume_ml"] for e in entries if e["fillable"])
    print(
        f"{phantom}: {len(entries)} compartments ({n_fillable} fillable), "
        f"{fillable_volume:.1f} mL fillable volume -> {out_dir}"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="output directory")
    parser.add_argument(
        "--phantom", default="all", choices=(*PHANTOM_NAMES, "all"),
        help="which phantom configuration to export (default: all)")
    parser.add_argument(
        "--formats", default="step,stl",
        help="comma-separated export formats: step, stl (default: step,stl)")
    parser.add_argument(
        "--abut-end", default="head", choices=("head", "foot"),
        help="for nemaabut, which end of the body phantom the scatter "
             "phantom abuts (default: head)")
    args = parser.parse_args()

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    for fmt in formats:
        if fmt not in FORMAT_EXTENSIONS:
            parser.error(f"unknown format {fmt!r}, expected one of {sorted(FORMAT_EXTENSIONS)}")

    phantoms = PHANTOM_NAMES if args.phantom == "all" else (args.phantom,)

    args.out.mkdir(parents=True, exist_ok=True)
    for phantom in phantoms:
        export_phantom(phantom, args.out, formats, args.abut_end)


if __name__ == "__main__":
    main()
