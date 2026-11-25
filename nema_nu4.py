"""NEMA NU 4-2008 image-quality phantom (small-animal PET).

A PMMA cylinder with three sections along its axis:

* a solid part with five hot rods of 1, 2, 3, 4 and 5 mm diameter, 20 mm long,
  drilled on a circle around the axis and filled from the main chamber;
* the main chamber, 30 mm across and 30 mm long, filled with the same activity
  concentration (the uniform region);
* two cold chambers hanging from the lid into the main chamber, 8 mm across and
  14 mm long inside with 1 mm walls, one filled with non-radioactive water and
  one with air.

Dimensions from the phantom's datasheet (Data Spectrum, "NEMA PET Small Animal
Phantom": outside diameter ~33 mm, length ~63 mm, chamber 30 mm, rods 1-5 mm x
~20 mm, cold chambers ~8 mm x ~14 mm with ~1 mm walls). The datasheet does not
give the radius of the rod circle, the offset of the cold chambers or the end
wall thicknesses: ROD_CIRCLE_RADIUS (7 mm) and COLD_CHAMBER_OFFSET (7.5 mm) are
the values commonly quoted for NU 4-2008 and are not checked against the
standard's text; the end walls split the remaining length evenly.

Built in the same frame convention as `nema_wagi`: millimetres, cylinder axis
along +z (the rods at low z, the lid at high z), so that `placement.to_world()`
maps it the same way.
"""
import math

from build123d import *
from pymat import pmma
from pymat.factories import air, water

# --- Dimensions ---------------------------------------------------------------
OUTER_DIAMETER = 33.0
CHAMBER_DIAMETER = 30.0
CHAMBER_LENGTH = 30.0
ROD_LENGTH = 20.0
ROD_DIAMETERS = (1.0, 2.0, 3.0, 4.0, 5.0)
ROD_CIRCLE_RADIUS = 7.0         # not in the datasheet, see the module docstring
COLD_INNER_DIAMETER = 8.0
COLD_INNER_LENGTH = 14.0
COLD_WALL = 1.0
COLD_CHAMBER_OFFSET = 7.5       # not in the datasheet, see the module docstring
OVERALL_LENGTH = 63.0
END_WALL = (OVERALL_LENGTH - ROD_LENGTH - CHAMBER_LENGTH) / 2.0  # 6.5 mm each

# z of the sections (axis +z, base at z = 0)
ROD_Z0 = END_WALL
CHAMBER_Z0 = ROD_Z0 + ROD_LENGTH
CHAMBER_Z1 = CHAMBER_Z0 + CHAMBER_LENGTH

phantom_material = pmma
fill_material = water()
cold_water_material = water()
cold_air_material = air()


def rod_centre(i):
    """(x, y) of rod i (diameter ROD_DIAMETERS[i]): 72 degrees apart, the 1 mm rod on +x."""
    phi = math.radians(72.0 * i)
    return ROD_CIRCLE_RADIUS * math.cos(phi), ROD_CIRCLE_RADIUS * math.sin(phi)


def cold_centres():
    """(x, y) of the water and the air chamber: on the x axis, either side of the centre."""
    return {"cold_water": (-COLD_CHAMBER_OFFSET, 0.0), "cold_air": (COLD_CHAMBER_OFFSET, 0.0)}


def _cylinder(radius, z0, z1, x=0.0, y=0.0):
    return Solid.make_cylinder(radius, z1 - z0).moved(Location((x, y, z0)))


def build():
    """Build the phantom. Returns name -> (solid, material, fillable)."""
    # The cold chambers hang from the lid: their inside reaches the lid's
    # underside (the chamber top), their 1 mm bottom wall sits below it.
    cold_z1 = CHAMBER_Z1
    cold_z0 = cold_z1 - COLD_INNER_LENGTH
    cold_outer_r = COLD_INNER_DIAMETER / 2.0 + COLD_WALL

    chamber = _cylinder(CHAMBER_DIAMETER / 2.0, CHAMBER_Z0, CHAMBER_Z1)
    rods = {
        f"rod_{d:g}mm": _cylinder(d / 2.0, ROD_Z0, CHAMBER_Z0, *rod_centre(i))
        for i, d in enumerate(ROD_DIAMETERS)
    }
    cold_outer = {
        k: _cylinder(cold_outer_r, cold_z0 - COLD_WALL, cold_z1, *c) for k, c in cold_centres().items()
    }
    cold_inner = {
        k: _cylinder(COLD_INNER_DIAMETER / 2.0, cold_z0, cold_z1, *c) for k, c in cold_centres().items()
    }

    body = _cylinder(OUTER_DIAMETER / 2.0, 0.0, OVERALL_LENGTH) - chamber
    for rod in rods.values():
        body = body - rod
    for k in cold_outer:  # the cold chambers' walls belong to the PMMA body
        body = body + (cold_outer[k] - cold_inner[k])

    fill = chamber
    for outer in cold_outer.values():
        fill = fill - outer

    body.label = "NU 4 Phantom Body"
    fill.label = "Uniform Region"
    out = {
        "phantom_body": (body, phantom_material, False),
        "uniform_fill": (fill, fill_material, True),
        "cold_water": (cold_inner["cold_water"], cold_water_material, False),
        "cold_air": (cold_inner["cold_air"], cold_air_material, False),
    }
    for name, rod in rods.items():
        rod.label = f"Hot Rod {name[4:]}"
        out[name] = (rod, fill_material, True)
    return out


def compartments():
    """name -> (solid, material, fillable), as `nema_wagi.compartments()`."""
    return build()


def parameters():
    """The dimensions, in the CAD frame, for an analytic rasteriser downstream."""
    return {
        "outer_diameter_mm": OUTER_DIAMETER,
        "overall_length_mm": OVERALL_LENGTH,
        "chamber_diameter_mm": CHAMBER_DIAMETER,
        "chamber_z_mm": [CHAMBER_Z0, CHAMBER_Z1],
        "rod_z_mm": [ROD_Z0, CHAMBER_Z0],
        "rods": [
            {"name": f"rod_{d:g}mm", "diameter_mm": d, "centre_xy_mm": list(rod_centre(i))}
            for i, d in enumerate(ROD_DIAMETERS)
        ],
        "cold_inner_diameter_mm": COLD_INNER_DIAMETER,
        "cold_inner_z_mm": [CHAMBER_Z1 - COLD_INNER_LENGTH, CHAMBER_Z1],
        "cold_wall_mm": COLD_WALL,
        "cold_centres_xy_mm": {k: list(v) for k, v in cold_centres().items()},
    }


def nominal_volumes():
    """Analytic volumes in mL, for the tests to check the build against."""
    def cyl(r, h):
        return math.pi * r * r * h / 1000.0

    r_ci = COLD_INNER_DIAMETER / 2.0
    r_co = r_ci + COLD_WALL
    cold_outer = cyl(r_co, COLD_INNER_LENGTH + COLD_WALL)
    rods = {f"rod_{d:g}mm": cyl(d / 2.0, ROD_LENGTH) for d in ROD_DIAMETERS}
    out = {
        "uniform_fill": cyl(CHAMBER_DIAMETER / 2.0, CHAMBER_LENGTH) - 2 * cold_outer,
        "cold_water": cyl(r_ci, COLD_INNER_LENGTH),
        "cold_air": cyl(r_ci, COLD_INNER_LENGTH),
        "phantom_body": cyl(OUTER_DIAMETER / 2.0, OVERALL_LENGTH)
        - cyl(CHAMBER_DIAMETER / 2.0, CHAMBER_LENGTH)
        - sum(rods.values())
        + 2 * (cold_outer - cyl(r_ci, COLD_INNER_LENGTH)),
    }
    return out | rods


if __name__ == "__main__":
    for name, (solid, material, fillable) in compartments().items():
        print(f"{name:14s} {solid.volume / 1000:8.4f} mL  {material.name}  fillable={fillable}")
    print("nominal:", {k: round(v, 4) for k, v in nominal_volumes().items()})
