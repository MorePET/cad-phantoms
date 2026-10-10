"""The body phantom's compartments are pairwise disjoint, leaf solid by leaf solid.

A simulation assigns every point in space to exactly one compartment, so two
compartments that claim the same volume make the material there ambiguous. At
f3ee0a0 they did: the five filling-screw threads ran through the 12 mm end caps
of a body with no holes in it, 942.5 mm^3 each (gerchowl/strata#1497 R6,
MorePET/cad-phantoms#8). The body now carries a threaded hole at each port.

Compartments are compared per OCCT leaf solid (`shape.solids()`), labelled
`<name>.<i>` when a compartment has more than one, which is how strata maps
them to volumes. Every pair is intersected, including two leaves of the same
compartment.

The negative control rebuilds the f3ee0a0 body (the current body with the
holes filled back in, checked against the f3ee0a0 body's volume pinned below)
and requires the same check to find exactly the five overlaps.
"""
import itertools

import pytest
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

# Largest intersection volume that still counts as disjoint (touching faces).
DISJOINT_TOL_MM3 = 1e-6

# Volume of each filling-screw thread inside the body: pi x 5^2 x 12 mm^3.
THREAD_MM3 = 942.5
FILLING_PORTS = 5
# What the body loses to the holes: 5 x pi x 5^2 x 12 mm^3.
BODY_LOSS_MM3 = 4712.4

# Every compartment's volume at f3ee0a0 (mm^3, `BRepGProp.VolumeProperties`),
# measured in the image built from that commit (build123d 0.11.1).
F3EE0A0_VOLUMES_MM3 = {
    "background_liquid": 10093111.32547979,
    "body_shell": 1683496.7627191187,
    "lung_insert_shell": 120462.79950557384,
    "lung_insert_filling": 294229.786962769,
    "sphere_mounting_plate": 216569.6165660294,
    "filling_screws": 28274.33388230814,
    "sphere_10mm": 523.5987755982989,
    "sphere_13mm": 1150.346509989463,
    "sphere_17mm": 2572.4407845144415,
    "sphere_22mm": 5575.279762570685,
    "sphere_28mm": 11494.040321933857,
    "sphere_37mm": 26521.84878038063,
    "sphere_10mm_wall": 381.17990863556133,
    "sphere_13mm_wall": 616.7993576547949,
    "sphere_17mm_wall": 1018.92321731429,
    "sphere_22mm_wall": 1662.9497113001971,
    "sphere_28mm_wall": 2643.126619220213,
    "sphere_37mm_wall": 4537.506989334848,
    "sphere_tube_10mm": 1258.635743303558,
    "sphere_tube_13mm": 1232.8201060202693,
    "sphere_tube_17mm": 1198.9535872941353,
    "sphere_tube_22mm": 1157.04521093234,
    "sphere_tube_28mm": 1107.0576939353205,
    "sphere_tube_37mm": 1032.372445349589,
}


def _volume(shape):
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped if hasattr(shape, "wrapped") else shape, props)
    return props.Mass()


def _leaves(compartments):
    """[(label, solid)] over every compartment's leaf solids, in strata's labelling."""
    out = []
    for name, (shape, _material, _fillable) in compartments.items():
        solids = shape.solids()
        assert solids, f"compartment {name!r} has no solids"
        if len(solids) == 1:
            out.append((name, solids[0]))
        else:
            out.extend((f"{name}.{i}", s) for i, s in enumerate(solids))
    return out


def _overlaps(leaves):
    """{(label_a, label_b): volume} for every pair intersecting by > DISJOINT_TOL_MM3."""
    found = {}
    for (la, a), (lb, b) in itertools.combinations(leaves, 2):
        common = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
        assert common.IsDone(), f"BRepAlgoAPI_Common failed on {la} x {lb}"
        volume = _volume(common.Shape())
        if volume > DISJOINT_TOL_MM3:
            found[(la, lb)] = volume
    return found


@pytest.fixture(scope="module")
def leaves(wagi_compartments):
    return _leaves(wagi_compartments)


def f3ee0a0_body(wagi):
    """The body as it was at f3ee0a0: the current body with its filling holes filled."""
    return wagi.nema_body.fuse(*wagi.filling_holes).clean()


def test_every_compartment_is_valid(leaves):
    invalid = [label for label, solid in leaves if not BRepCheck_Analyzer(solid.wrapped).IsValid()]
    assert invalid == []


def test_compartments_pairwise_disjoint(leaves):
    assert len(leaves) == 34   # a lost leaf would shrink the check silently
    assert _overlaps(leaves) == {}


def test_body_lost_exactly_the_five_holes(wagi_compartments):
    body = _volume(wagi_compartments["body_shell"][0])
    removed = F3EE0A0_VOLUMES_MM3["body_shell"] - body
    assert removed == pytest.approx(BODY_LOSS_MM3, abs=0.5)


def test_every_other_compartment_unchanged(wagi_compartments):
    assert set(wagi_compartments) == set(F3EE0A0_VOLUMES_MM3)
    for name, (shape, _material, _fillable) in wagi_compartments.items():
        if name != "body_shell":
            assert _volume(shape) == pytest.approx(F3EE0A0_VOLUMES_MM3[name], rel=1e-9), name


def test_negative_control_f3ee0a0_body_overlaps_the_screws(wagi, wagi_compartments):
    old_body = f3ee0a0_body(wagi)
    assert BRepCheck_Analyzer(old_body.wrapped).IsValid()
    assert _volume(old_body) == pytest.approx(F3EE0A0_VOLUMES_MM3["body_shell"], rel=1e-9)

    compartments = dict(wagi_compartments)
    _shell, material, fillable = compartments["body_shell"]
    compartments["body_shell"] = (old_body, material, fillable)
    found = _overlaps(_leaves(compartments))

    assert len(found) == FILLING_PORTS
    assert sorted(found) == [("body_shell", f"filling_screws.{i}") for i in (1, 3, 5, 7, 9)]
    for pair, volume in found.items():
        assert volume == pytest.approx(THREAD_MM3, abs=0.1), pair
