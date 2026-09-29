"""NEMA NU 2-2018 section 4 scatter phantom (count rate, scatter fraction, NECR).

The IEC body phantom measures image quality. The count-rate measurements --
scatter fraction, count losses and NECR -- are defined on a *different* object,
specified in NU 2-2018 section 4.3.2:

    a solid right circular cylinder of polyethylene, specific gravity
    0.96 +- 0.01, outside diameter 203 +- 3 mm, overall length 700 +- 5 mm,
    with a 6.4 +- 0.2 mm hole drilled parallel to the central axis at a radial
    distance of 45 +- 1 mm.

The line source insert is a tube of inside diameter 3.2 +- 0.2 mm and outside
diameter 4.8 +- 0.2 mm, of which the central 700 +- 20 mm is filled with
activity and threaded through the hole.

Its length is the point: at 700 mm against a 150 mm axial field of view, most of
the activity sits outside the scanner, which is what makes the measured count
rate representative. Section 7.3.3 also requires this phantom abutted at the
head end of the body phantom during the image-quality measurement, for the same
reason.

Built in the same frame convention as `nema_wagi`: millimetres, cylinder axis
along +z, so that `placement.to_world()` maps it the same way.
"""
import math

from build123d import *
from pymat import Material

# --- Section 4.3.2 dimensions ------------------------------------------------
PHANTOM_DIAMETER = 203.0        # +- 3
PHANTOM_LENGTH = 700.0          # +- 5
BORE_DIAMETER = 6.4             # +- 0.2
BORE_RADIAL_OFFSET = 45.0       # +- 1, from the central axis

INSERT_OUTER_DIAMETER = 4.8     # +- 0.2
INSERT_INNER_DIAMETER = 3.2     # +- 0.2
ACTIVE_LENGTH = 700.0           # +- 20, centred on the phantom

# The standard fixes the specific gravity at 0.96, which is not the density of
# pymat's stock polyethylene (0.94) -- the phantom is specified tighter than the
# generic material, so it gets its own.
POLYETHYLENE_SG = 0.96          # +- 0.01
phantom_material = Material(
    "Polyethylene (NU 2-2018 section 4.3.2)",
    density=POLYETHYLENE_SG,
    formula="-(CH2-CH2)n-",
)
# The insert tube is "clear polyethylene or polyethylene coated plastic".
insert_material = Material(
    "Polyethylene (line source insert)",
    density=0.94,
    formula="-(CH2-CH2)n-",
)
# The active volume is water carrying the tracer, per section 4.3.3 ("filled
# with water well mixed with the measured amount of radioactivity").
source_material = Material("Water (line source)", density=1.0, formula="H2O")


def _bore_center():
    """Bore centre in the transverse plane.

    Section 4.3.3 has the phantom mounted with the line source insert nearest
    the patient table, i.e. below the axis. There is no table in the
    simulation, but keeping the offset on the -y side preserves the standard's
    asymmetry, which is what the scatter distribution actually depends on.
    """
    return 0.0, -BORE_RADIAL_OFFSET


def build(active_length=ACTIVE_LENGTH):
    """Build the scatter phantom.

    Returns name -> (solid, material, fillable), matching
    `nema_wagi.compartments()` so both phantoms feed the same voxelizer.
    """
    bx, by = _bore_center()
    half = PHANTOM_LENGTH / 2.0

    body = Solid.make_cylinder(PHANTOM_DIAMETER / 2, PHANTOM_LENGTH).moved(
        Location((0, 0, -half)))
    bore = Solid.make_cylinder(BORE_DIAMETER / 2, PHANTOM_LENGTH).moved(
        Location((bx, by, -half)))
    body = body - bore

    # The insert spans the full drilled length; only its central `active_length`
    # is filled, so a short phantom-length source does not silently become a
    # 700 mm one.
    insert_outer = Solid.make_cylinder(INSERT_OUTER_DIAMETER / 2, PHANTOM_LENGTH).moved(
        Location((bx, by, -half)))
    insert_bore = Solid.make_cylinder(INSERT_INNER_DIAMETER / 2, PHANTOM_LENGTH).moved(
        Location((bx, by, -half)))
    insert_wall = insert_outer - insert_bore

    source = Solid.make_cylinder(INSERT_INNER_DIAMETER / 2, active_length).moved(
        Location((bx, by, -active_length / 2.0)))

    body.label = "Scatter Phantom Body"
    insert_wall.label = "Line Source Insert Wall"
    source.label = "Line Source"

    return {
        "scatter_body": (body, phantom_material, False),
        "line_insert_wall": (insert_wall, insert_material, False),
        "line_source": (source, source_material, True),
    }


def compartments():
    """name -> (solid, material, fillable), as `nema_wagi.compartments()`."""
    return build()


def nominal_volumes():
    """Analytic volumes in mL, for the tests to check the build against."""
    r_phantom = PHANTOM_DIAMETER / 2
    r_bore = BORE_DIAMETER / 2
    r_ins_o = INSERT_OUTER_DIAMETER / 2
    r_ins_i = INSERT_INNER_DIAMETER / 2
    return {
        "scatter_body": math.pi * (r_phantom ** 2 - r_bore ** 2) * PHANTOM_LENGTH / 1000.0,
        "line_insert_wall": math.pi * (r_ins_o ** 2 - r_ins_i ** 2) * PHANTOM_LENGTH / 1000.0,
        "line_source": math.pi * r_ins_i ** 2 * ACTIVE_LENGTH / 1000.0,
    }


if __name__ == "__main__":
    for name, (solid, material, fillable) in compartments().items():
        print(f"{name:20s} {solid.volume / 1000:9.2f} mL  {material.name}")
    print("nominal:", {k: round(v, 2) for k, v in nominal_volumes().items()})
