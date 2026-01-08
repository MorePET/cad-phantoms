#%%
from build123d import *
from ocp_vscode import *
import copy
import math
from pymat import pmma, pe
from pymat.factories import air, water

# %%
# =============================================================================
# NEMA IEC Body Phantom Dimensions (IEC Standard 61675-1)
# All dimensions in millimeters
# =============================================================================

phantom_material = pmma
phantom_insert_material = air()
phantom_filling_material = water()

# --- Body Phantom (Figure 7-1) ---
# Overall dimensions
body_height = 230  # Total height of phantom cross-section
body_width = 150  # Width of flat bottom section
body_bottom_depth = 80  # Distance from horizontal center line to bottom
body_length = 217
body_interior_length = 193
# Radii
body_corner_radius = 77  # Bottom corner radius (r = 77)
body_top_radius = 147  # Top arc radius (r = 147)

# Wall thickness
body_wall_thickness = 3  # PMMA wall thickness

# Rod positions (from center of phantom)
rod_horizontal_spacing = 70  # Horizontal distance from center to rods
rod_vertical_offset_top = 35  # Vertical offset for top center rod
rod_vertical_offset_bottom = 77  # Vertical offset for bottom center rod

# --- Phantom Insert with Hollow Spheres (Figure 7-2) ---
# Sphere inner diameters (fillable volume)
sphere_diameters = [10, 13, 17, 22, 28, 37]  # mm

# Sphere tolerances
sphere_tolerance_small = 0.5  # For 10, 13, 17 mm spheres
sphere_tolerance_large = 1.0  # For 22, 28, 37 mm spheres

# Sphere arrangement
sphere_circle_diameter = 114.4  # Diameter of circle on which sphere centers lie
sphere_center_depth = 70  # Distance from mounting plate inside surface to sphere centers
sphere_y_offset = 35  # Offset of sphere centers from center of phantom

# Sphere wall thickness
sphere_wall_thickness = 1  # Maximum wall thickness of spheres

# Sphere filling tubing
tube_wall_thickness = 1.5
tube_inner_radius = 1.0

# sphere mounting plate
mounting_plate_thickness = 3
plate_to_body_tolerance = 1
mounting_plate_inner_diameter = 135
mounting_plate_outer_diameter = 155

# nema lung insert
insert_outside_diameter = 51
insert_inside_diameter = 45
insert_inside_height = 185
insert_outside_height = 203

# screws
screw_material = pe
screw_large_head_diameter = 20
screw_large_head_height = 15
screw_large_thread_diameter = 10

screw_small_head_diameter = 5
screw_small_head_height = 5
screw_small_thread_diameter = 2.5

# Filling screws placement
filling_screw_y_offset = -body_bottom_depth + 35  # Y offset from center
filling_screw_x_offset = 120  # X offset from center for side screws
filling_screw_top_y_inset = 15  # Distance from top of body for top screw

#%%

# --- Material ---
# Phantom material: Polymethylmethacrylate (PMMA/Acrylic)
# Spheres may alternatively be made from glass

# =============================================================================
# Body Phantom Geometry (Figure 7-1)
# =============================================================================
# The cross-section consists of:
# - Small flat bottom section (where corner arcs meet, ~4mm)
# - Two quarter-circle corner arcs (r = 77 mm) tangent to bottom and sides
# - Vertical sides connecting corner arcs to top arc
# - Large top dome arc (r = 147 mm)
# The shape is symmetric about the vertical center line

# Key coordinates
half_width = body_width / 2  # 75 mm
bottom_y = -body_bottom_depth  # -80 mm

# Corner arc centers (quarter-circle fillets tangent to bottom and sides)
right_corner_center_x = half_width # 
left_corner_center_x = -half_width #
corner_center_y = bottom_y + body_corner_radius  # -3

# Bottom line goes from left corner tangent point to right corner tangent point
# Tangent to bottom at x = corner_center_x (directly below each center)
bottom_line = Line((left_corner_center_x, bottom_y), (right_corner_center_x, bottom_y))

# Right corner arc: from bottom tangent (right_corner_center_x, bottom_y) to side tangent (half_width, corner_center_y)
# This is a quarter circle going from pointing down to pointing right
bottom_right_arc = RadiusArc(
    (right_corner_center_x+body_corner_radius, corner_center_y),
    (right_corner_center_x, bottom_y),  # (-2, -80)       # (75, -3)
    body_corner_radius                   # 77
)
# mirror bottom_right_arc to get bottom_left_arc
bottom_left_arc = copy.deepcopy(bottom_right_arc.mirror(Plane.YZ))

top_right_arc = RadiusArc(
    (0, body_height - body_bottom_depth),
    (right_corner_center_x+body_corner_radius, corner_center_y),
    body_top_radius
)

# mirror top_right_arc to get top_left_arc
top_left_arc = copy.deepcopy(top_right_arc.mirror(Plane.YZ))

# compound path
outer_wire = Wire([bottom_line, bottom_left_arc, top_left_arc, top_right_arc, bottom_right_arc])

# show the geometry
show(outer_wire)

#%%
# inner_path - offset the outer path inward by wall thickness

# First, combine edges into a Wire

# Offset inward (negative distance)
inner_wire = outer_wire.offset_2d(
    distance=-body_wall_thickness,  # -3mm inward
    kind=Kind.ARC
)

# Compound takes a list of shapes
body_cross_section = Compound([inner_wire, outer_wire])
show(body_cross_section)

# %%
# extrude to create 3D body
face_thickness = (body_length - body_interior_length) / 2  # 12mm end caps

# Create faces from wires first
# Solid end cap face (from outer wire only)
solid_end_face = Face(outer_wire)

# Hollow cross-section face (outer wire with inner wire as hole)
hollow_face = Face(outer_wire, inner_wires=[inner_wire])

# Extrude: Solid.extrude(face, direction) -> Solid
bottom_cap = Solid.extrude(solid_end_face, Vector(0, 0, face_thickness))
body_shell = Solid.extrude(hollow_face.moved(Location((0, 0, face_thickness))), Vector(0, 0, body_interior_length))
top_cap = Solid.extrude(solid_end_face.moved(Location((0, 0, face_thickness + body_interior_length))), Vector(0, 0, face_thickness))

# Combine into single solid
nema_body = bottom_cap + body_shell + top_cap
nema_body.label = "Nema Body"
phantom_material.apply_to(nema_body)
show(nema_body)

#%%
# spheres
# Create spheres arranged on a circle (Figure 7-2)
# 6 spheres evenly spaced at 60° intervals on a circle of diameter 114.4mm
# Sphere centers are at z = sphere_center_depth from the mounting plate

sphere_radius = sphere_circle_diameter / 2  # 57.2mm from center
sphere_center_z = sphere_center_depth + face_thickness  # 70mm from mounting plate

# Generate locations for 6 spheres at 60° intervals
# Starting angle can be adjusted to match the drawing orientation
sphere_locations = []
for i, diameter in enumerate(sphere_diameters):
    angle = math.radians(i * 60)  # 0°, 60°, 120°, 180°, 240°, 300°
    x = sphere_radius * math.cos(angle)
    y = sphere_radius * math.sin(angle) + sphere_y_offset
    z = sphere_center_z
    sphere_locations.append(Location((x, y, z)))

# Create spheres at their locations
spheres = []
for i, (diameter, loc) in enumerate(zip(sphere_diameters, sphere_locations)):
    sphere = Solid.make_sphere(diameter / 2).moved(loc)
    sphere.label = f"Sphere {diameter}mm"
    spheres.append(sphere)
    phantom_material.apply_to(sphere)

show(*spheres)

#%%
# sphere filling tubing (capillaries)
# Tubing goes from the top of each sphere up through the mounting plate

tube_outer_radius = tube_inner_radius + tube_wall_thickness
tube_height = sphere_center_z

# Mounting plate is at z = body_length (top of phantom)
mounting_plate_z = body_length

tubing = []
for i, loc in enumerate(sphere_locations):
    
    tube_loc = Location((loc.position.X, loc.position.Y, 0))
    tube = Solid.make_cylinder(radius=tube_outer_radius, height=tube_height).moved(tube_loc)
    tubing.append(tube)
    phantom_material.apply_to(tube)

show(nema_body,*spheres,*tubing)

#%%
# sphere mounting plate
sphere_mounting_plate_outer = Solid.make_cylinder(mounting_plate_outer_diameter / 2, mounting_plate_thickness).moved(Location((0, sphere_y_offset, -mounting_plate_thickness)))
sphere_mounting_plate_inner = Solid.make_cylinder(mounting_plate_inner_diameter / 2, face_thickness).moved(Location((0, sphere_y_offset, 0)))
sphere_mounting_plate = Compound([sphere_mounting_plate_outer,sphere_mounting_plate_inner], label="Sphere Mounting Plate")
phantom_material.apply_to(sphere_mounting_plate)

body_cutout_sketch = Circle(mounting_plate_inner_diameter / 2).edges()[0].offset_2d(distance=plate_to_body_tolerance)
body_cutout = Solid.extrude(Face(body_cutout_sketch), Vector(0, 0, face_thickness))
nema_body = nema_body - body_cutout.moved(Location((0, sphere_y_offset, 0)))

show(sphere_mounting_plate,nema_body)

#%%
# nema lung insert
insert_z_start = (face_thickness+body_interior_length/2)-insert_outside_height/2
insert = Solid.make_cylinder(insert_outside_diameter / 2, insert_outside_height).moved(Location((0, sphere_y_offset, insert_z_start)))
insert_filling = Solid.make_cylinder(insert_inside_diameter / 2, insert_inside_height).moved(Location((0, sphere_y_offset, insert_z_start + (insert_outside_height - insert_inside_height) / 2)))
insert_shell = insert.cut(insert_filling)
insert_shell.label = "Nema Lung Insert Shell"
phantom_material.apply_to(insert_shell)
phantom_insert_material.apply_to(insert_filling)
# insert.move(Location((0, sphere_y_offset, (insert_z_start))))
nema_body = nema_body - insert
sphere_mounting_plate = sphere_mounting_plate - insert
show(insert_shell, nema_body, sphere_mounting_plate)

#%%
# screws as cylinders
# large screw
large_screw = Compound([Solid.make_cylinder(screw_large_head_diameter / 2, screw_large_head_height).moved(Location((0, 0, 0))), 
                        Solid.make_cylinder(screw_large_thread_diameter / 2, face_thickness).moved(Location((0, 0, -face_thickness)))])
large_screw.label = "Large Screw"
screw_material.apply_to(large_screw)
show(large_screw)

#%% small screw
small_screw = Compound([Solid.make_cylinder(screw_small_head_diameter / 2, screw_small_head_height).moved(Location((0, 0, 0))), 
                        Solid.make_cylinder(screw_small_thread_diameter / 2, body_wall_thickness).moved(Location((0, 0, -body_wall_thickness)))])
small_screw.label = "Small Screw"
screw_material.apply_to(small_screw)
show(small_screw)

#%%

# bkg liquid
# fill liquid for inner volume of nema, i.e. extrud inner wire and substract nema_solid
bkg_liquid = Solid.extrude(Face(inner_wire), Vector(0, 0, body_length))
bkg_liquid = bkg_liquid - insert - spheres - tubing
bkg_liquid.label = "Background Liquid"
phantom_filling_material.apply_to(bkg_liquid)

show(bkg_liquid)

#%%
# make spheres hollow, i.e. substract inner sphere with - sphere_wall_thickness from outer sphere
sphere_fillings = []
hollow_spheres = []
for i, (sphere, diameter, loc) in enumerate(zip(spheres, sphere_diameters, sphere_locations)):
    inner_radius = diameter / 2 - sphere_wall_thickness
    # Create inner sphere at the same location (use sphere_locations, not sphere.location which gets reset after cut)
    inner_sphere = Solid.make_sphere(inner_radius).moved(loc)
    # Cut to make hollow
    hollow_sphere = sphere - inner_sphere
    hollow_sphere.label = f"Hollow Sphere {diameter}mm"
    phantom_material.apply_to(hollow_sphere)
    hollow_spheres.append(hollow_sphere)
    # Save the moved inner sphere for filling visualization
    inner_sphere.label = f"Sphere {i} {diameter}mm Filling"
    phantom_filling_material.apply_to(inner_sphere)
    sphere_fillings.append(inner_sphere)
show(*hollow_spheres, *sphere_fillings)

#%%
# make tubing hollow, i.e. substract inner tubing with - tube_wall_thickness from outer tubing
hollow_tubing = []
for i, tube in enumerate(tubing):
    inner_tube = Solid.make_cylinder(tube_inner_radius, tube_height).moved(tube.location)
    hollow_tube = tube.cut(inner_tube) - (spheres[i])
    hollow_tube.label = f"Hollow Tube {i}"
    phantom_material.apply_to(hollow_tube)
    hollow_tubing.append(hollow_tube)
show(*hollow_tubing)

#%% sphere + mounting plate
sphere_mounting_plate = sphere_mounting_plate - tubing
# place small screws on bottom surfaces of the mounting plate at each tube location
sphere_tubing_screws = []
for i, tube in enumerate(tubing):
    # Position screw so thread aligns with bottom of mounting plate
    screw_z = -mounting_plate_thickness
    screw_loc = Location((tube.location.position.X, tube.location.position.Y, screw_z))
    screw = small_screw.mirror(Plane.XY).moved(screw_loc)
    sphere_tubing_screws.append(screw)
    

# sphere_mounting_plate = sphere_mounting_plate - sphere_tubing_screws
show(sphere_mounting_plate, *sphere_tubing_screws, *hollow_tubing, *hollow_spheres)


# %%
# small screws mounting plate to nema, 12 screws at mounting plate outer + inner / 2
sphere_mounting_plate_screws = []
n_screws = 12
pitch = 360 / n_screws
screw_placement_radius = (mounting_plate_outer_diameter + mounting_plate_inner_diameter) / 4
for i in range(n_screws):
    angle = math.radians(i * pitch)
    x = screw_placement_radius * math.cos(angle)
    y = screw_placement_radius * math.sin(angle) + sphere_y_offset
    screw_loc = Location((x, y, -mounting_plate_thickness))
    screw = small_screw.mirror(Plane.XY).moved(screw_loc)
    sphere_mounting_plate_screws.append(screw)
sphere_mounting_plate = sphere_mounting_plate - sphere_mounting_plate_screws
show(*sphere_mounting_plate_screws, sphere_mounting_plate)

# %%
spheres_assemblies = []
for i, (sphere, tubing) in enumerate(zip(spheres, hollow_tubing)):
    spheres_assemblies.append(Compound(children=[sphere, tubing], label=f"{sphere.label}"))

spheres_empty = Compound(children=[*spheres_assemblies], label="Spheres & Tubing")
sphere_screws = Compound(children=[*sphere_mounting_plate_screws, *sphere_tubing_screws], label="Sphere Screws")
spheres_w_mount = Compound(children=[sphere_mounting_plate, sphere_screws, spheres_empty], label="Spheres Mounted")
show(spheres_w_mount)

#%%
# large filling screws
# 2 at lower side and bottom of nema body, mirrored to other end, plus 1 at top
filling_screws = []
filling_screws.append(large_screw.mirror(Plane.XY).moved(Location((filling_screw_x_offset, filling_screw_y_offset, 0))))
filling_screws.append(large_screw.mirror(Plane.XY).moved(Location((-filling_screw_x_offset, filling_screw_y_offset, 0))))
filling_screws.extend([screw.mirror(Plane.XY.offset(body_length / 2)) for screw in filling_screws])
filling_screws.append(large_screw.mirror(Plane.XY).moved(Location((0, nema_body.bounding_box().max.Y - filling_screw_top_y_inset, filling_screws[-1].location.position.Z))))
filling_screws = Compound(children=[*filling_screws], label="Filling Screws")
show(filling_screws, nema_body, reset_camera=Camera.TOP)

#%%
nema_phantom_assembly = Compound(children=[nema_body, spheres_w_mount, insert_shell, filling_screws], label="Nema Phantom Assembly")
sphere_liquids = Compound(children=[*sphere_fillings], label="Sphere Liquids")
nema_phantom_filled = Compound(children=[nema_phantom_assembly, sphere_liquids, bkg_liquid], label="Nema Phantom Filled")
show(nema_phantom_filled)

# %%
export_step(nema_phantom_filled, "nema_phantom_filled.step")

# %%
# Save screenshot for README
show(
    nema_phantom_filled,
    reset_camera=Camera.ISO
)
save_screenshot("images/nema_phantom.png")

# %%
