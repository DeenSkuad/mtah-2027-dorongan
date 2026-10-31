"""SPIKE (throwaway): broadcast-camera render of a real IDSSE moment with mannequins.

    Blender -b -P video/spike_scene.py -- video/out/moment_J03WMX_13222.json video/out/spike/

Goal: check the TV look and M1 render speed before building the real film.
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
moment = json.loads(Path(args[0]).read_text())
out_dir = Path(args[1])
L, W = moment["pitch"]
FPS = moment["fps"]
N_FRAMES = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 100  # 4 s spike

# ---------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, N_FRAMES
for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = engine
        break
    except TypeError:
        continue
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(out_dir / "f_")
if hasattr(scene, "eevee"):
    scene.eevee.taa_render_samples = 16
scene.view_settings.view_transform = "AgX" if "AgX" in [
    t.identifier for t in scene.view_settings.bl_rna.properties["view_transform"].enum_items
] else "Filmic"


def mat(name, color, emission=0.0, rough=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    if emission:
        key = "Emission Color" if "Emission Color" in bsdf.inputs else "Emission"
        bsdf.inputs[key].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    return m


def to_world(x, y):
    return Vector((x - L / 2, y - W / 2, 0))


# ---------------------------------------------------------------- world light
world = bpy.data.worlds.new("night")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.01, 0.015, 0.03, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

bpy.ops.object.light_add(type="SUN", location=(0, 0, 50))
sun = bpy.context.object
sun.data.energy = 3.5
sun.rotation_euler = (math.radians(35), math.radians(15), math.radians(30))
for sx in (-1, 1):
    for sy in (-1, 1):
        bpy.ops.object.light_add(type="AREA", location=(sx * (L / 2 + 15), sy * (W / 2 + 15), 40))
        lamp = bpy.context.object
        lamp.data.energy = 60000
        lamp.data.size = 12
        lamp.rotation_euler = (Vector((0, 0, 0)) - lamp.location).to_track_quat("-Z", "Y").to_euler()

# ---------------------------------------------------------------- pitch
greens = (mat("g1", (0.05, 0.22, 0.06)), mat("g2", (0.07, 0.27, 0.08)))
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.02))
apron = bpy.context.object
apron.scale = (L + 16, W + 12, 1)
apron.data.materials.append(greens[0])
n_strips = 18
for i in range(n_strips):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-L / 2 + (i + 0.5) * L / n_strips, 0, 0))
    strip = bpy.context.object
    strip.scale = (L / n_strips, W, 1)
    strip.data.materials.append(greens[i % 2])

white = mat("line", (0.95, 0.95, 0.95), emission=0.3)


def line(x0, y0, x1, y1, w=0.12):
    a, b = to_world(x0, y0), to_world(x1, y1)
    bpy.ops.mesh.primitive_plane_add(size=1, location=((a + b) / 2) + Vector((0, 0, 0.01)))
    o = bpy.context.object
    o.scale = (max((b - a).length, w), w, 1)
    o.rotation_euler.z = math.atan2(b.y - a.y, b.x - a.x)
    o.data.materials.append(white)


for (x0, y0, x1, y1) in [(0, 0, L, 0), (0, W, L, W), (0, 0, 0, W), (L, 0, L, W), (L / 2, 0, L / 2, W)]:
    line(x0, y0, x1, y1)
for side in (0, 1):
    x_goal = 0 if side == 0 else L
    d = 16.5 if side == 0 else -16.5
    line(x_goal, W / 2 - 20.16, x_goal + d, W / 2 - 20.16)
    line(x_goal, W / 2 + 20.16, x_goal + d, W / 2 + 20.16)
    line(x_goal + d, W / 2 - 20.16, x_goal + d, W / 2 + 20.16)
bpy.ops.mesh.primitive_torus_add(major_radius=9.15, minor_radius=0.06, location=(0, 0, 0.01))
circle = bpy.context.object
circle.scale.z = 0.05
circle.data.materials.append(white)

# ---------------------------------------------------------------- stadium
crowd = mat("crowd", (0.05, 0.06, 0.09), rough=0.9)
# The main stand (camera side) is never in shot on TV: the camera gantry hangs in front of it.
for (cx, cy, sx, sy, rot) in [(0, W / 2 + 22, L + 60, 30, 0),
                              (L / 2 + 22, 0, 30, W + 20, 1), (-L / 2 - 22, 0, 30, W + 20, 1)]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, 8))
    stand = bpy.context.object
    stand.scale = (sx, sy, 16)
    stand.data.materials.append(crowd)
led_colors = [(0.65, 0.0, 0.27), (0.0, 0.3, 0.6), (1.0, 0.82, 0.25)]
for i, x in enumerate(range(int(-L / 2), int(L / 2), 15)):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x + 7.5, W / 2 + 4, 0.5))
    board = bpy.context.object
    board.scale = (14.5, 1, 1)
    board.rotation_euler.x = math.radians(90)
    board.data.materials.append(mat(f"led{i}", led_colors[i % 3], emission=4.0))

# ---------------------------------------------------------------- players + ball
kit = {0: (mat("home_top", (0.55, 0.02, 0.2)), mat("home_short", (0.02, 0.15, 0.45))),
       1: (mat("away_top", (0.85, 0.08, 0.08)), mat("away_short", (0.05, 0.05, 0.05)))}
skin = mat("skin", (0.55, 0.38, 0.28))
frames = moment["players"]
actors = []
for p, team in enumerate(moment["teams"]):
    top, short = kit[team]
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.75, location=(0, 0, 1.15))
    torso = bpy.context.object
    torso.data.materials.append(top)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=0.75, location=(0, 0, 0.4))
    legs = bpy.context.object
    legs.data.materials.append(short)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.13, location=(0, 0, 1.68))
    head = bpy.context.object
    head.data.materials.append(skin)
    bpy.ops.object.empty_add(location=(0, 0, 0))
    root = bpy.context.object
    for part in (torso, legs, head):
        part.parent = root
    actors.append(root)

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=(0, 0, 0.16))
ball = bpy.context.object
ball.data.materials.append(mat("ball", (1, 1, 1), emission=0.5))

for f in range(N_FRAMES):
    frame = f + 1
    for p, root in enumerate(actors):
        x, y = frames[f][p]
        nx, ny = frames[min(f + 1, len(frames) - 1)][p]
        pos = to_world(x, y)
        speed = math.hypot(nx - x, ny - y) * FPS
        pos.z = abs(math.sin(f * 0.9 + p)) * min(speed, 7) * 0.012  # running bob
        root.location = pos
        if speed > 0.5:
            root.rotation_euler.z = math.atan2(ny - y, nx - x)
        root.keyframe_insert("location", frame=frame)
        root.keyframe_insert("rotation_euler", frame=frame)
    bx, by = moment["ball"][f]
    ball.location = to_world(bx, by) + Vector((0, 0, 0.16))
    ball.keyframe_insert("location", frame=frame)

# ---------------------------------------------------------------- broadcast camera
# Main camera: halfway line, main stand, ~18 m up, ~70 m back -> ~14 deg line of sight (FIFA/UEFA).
bpy.ops.object.camera_add(location=(0, -(W / 2 + 36), 18))
cam = bpy.context.object
cam.data.lens = 62  # telephoto: ~32 deg horizontal field of view
scene.camera = cam
bpy.ops.object.empty_add(location=(0, 0, 0))
aim = bpy.context.object
track = cam.constraints.new("TRACK_TO")
track.target = aim
track.track_axis, track.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
smooth_x = None
for f in range(N_FRAMES):
    bx, by = moment["ball"][f]
    target = to_world(bx, by)
    smooth_x = target.x if smooth_x is None else smooth_x + 0.08 * (target.x - smooth_x)
    aim.location = Vector((smooth_x, target.y * 0.35, 0))
    aim.keyframe_insert("location", frame=f + 1)

bpy.ops.render.render(animation=True)
print("SPIKE DONE")
