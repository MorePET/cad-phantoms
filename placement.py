"""Placement of the phantoms into the simulation world frame.

The models are built in a natural CAD frame: millimetres, phantom axis along
+z, and for the body phantom +y is "up". The simulation's world frame is not
that frame -- the scanner axis is world **y** (the crystal map's `center_y`
spans -147..+147 mm, and the analysis chain refers to it as "reco z = sim y").

Everything here exists so the phantoms are rasterized *already in the world
frame*. The alternative -- rasterizing in the CAD frame and rotating at run
time -- is what the existing NEMA configs do, with `patientGeometry.rotation`
of [90,0,0] against a source `rotation` of [-90,0,0] and a translation of
[0,-134.875,0] to undo the frame difference. Doing it here instead means the
simulation configs carry identity rotation and translation, and the attenuation
grid, the source cloud and the activity maps cannot drift out of register with
each other because they all come from one rasterization.

The map is a proper rotation of +90 degrees about x,

    (x, y, z)_cad  ->  (x, -z, y)_world

followed by a translation. It preserves handedness (a reflection would mirror
the phantom) and keeps CAD "up" pointing at world +z, so figures read the way
the drawings do.
"""
from build123d import *

# --- Scanner, for the placements below --------------------------------------
FOV_AXIAL_MM = 150.0        # |world y| < 150 is the axial field of view
FOV_RADIAL_MM = 370.0

# --- Body phantom landmarks, in the CAD frame of nema_wagi -------------------
SPHERE_PLANE_Z = 82.0       # sphere centres, = sphere_center_depth + face_thickness
CIRCULAR_AXIS_Y = 35.0      # lung insert / sphere-circle centre, = sphere_y_offset
BODY_Z_MIN, BODY_Z_MAX = 0.0, 217.0


def to_world(translation=(0.0, 0.0, 0.0)):
    """The CAD -> world placement, as a build123d Location.

    `translation` is applied in world coordinates after the rotation.
    """
    return Location(translation) * Location((0, 0, 0), (90, 0, 0))


def body_phantom_placement():
    """IEC body phantom, positioned per NU 2-2018 section 7.3.3.

    Two requirements, both in the standard's words: the plane through the
    centres of the spheres is coplanar with the middle slice of the scanner,
    and the table height is set to centre the lung insert in the transaxial
    field of view.

    So the sphere plane goes to world y = 0 and the circular section's axis to
    world (x, z) = (0, 0). Note this does *not* centre the phantom's own length
    on the scanner -- the spheres sit 82 mm from one end, so the body spans
    world y in [-135, +82].
    """
    return to_world((0.0, SPHERE_PLANE_Z, -CIRCULAR_AXIS_Y))


def body_phantom_extent():
    """(y_min, y_max) of the body phantom in the world frame."""
    return (SPHERE_PLANE_Z - BODY_Z_MAX, SPHERE_PLANE_Z - BODY_Z_MIN)


def scatter_phantom_placement(length=700.0):
    """NU-2 scatter phantom alone, per section 4.3.3.

    "placed parallel to the scanner's axis and centred in the transverse and
    axial fields-of-view to within 5 mm" -- so its axis is world y, its centre
    is the origin, and the bore keeps the standard's radial offset below the
    axis (the real phantom is rotated so the line source lies nearest the
    patient table; there is no table here, but the asymmetry is what the
    scatter distribution depends on).
    """
    return to_world((0.0, 0.0, 0.0))


def abutted_scatter_placement(length=700.0, end="head"):
    """NU-2 scatter phantom abutting the body phantom, per section 7.3.3.

    "The test phantom shall then be placed at the head end of the body phantom
    and abutting the body phantom ... in order to approximate the clinical
    situation of having activity that extends beyond the scanner."

    Which physical end of the body phantom is the "head end" is not resolvable
    from the text -- it is shown in Figure 7-3 -- so it is a parameter.
    `end="head"` abuts the end away from the spheres (world y = -135), putting
    the 700 mm of extra activity on the far side of the sphere plane;
    `end="foot"` abuts the sphere end instead. The choice matters only through
    how close the extra activity sits to the field of view, and it must be
    stated wherever the resulting numbers are quoted.
    """
    y_min, y_max = body_phantom_extent()
    if end == "head":
        centre_y = y_min - length / 2.0
    elif end == "foot":
        centre_y = y_max + length / 2.0
    else:
        raise ValueError(f"end must be 'head' or 'foot', got {end!r}")
    return to_world((0.0, centre_y, 0.0))


def place(compartments, location):
    """Apply a placement to a `compartments()` mapping.

    Returns the same mapping with every solid moved into the world frame.
    """
    return {name: (location * solid, material, fillable)
            for name, (solid, material, fillable) in compartments.items()}
