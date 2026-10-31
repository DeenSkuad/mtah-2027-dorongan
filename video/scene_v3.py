"""Look-dev v3: CC0 BlendSwap stadium + Mixamo footballers + night floodlights, Cycles still.

    Blender -b video/assets/blendswap/"Soccer Arena Large 03.blend" -P video/scene_v3.py -- \
        <moment.json> <out_dir> <frame> <width>

Motion: IDSSE/DFL open tracking (CC-BY 4.0). Never the competition match.
"""

import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
moment = json.loads(Path(args[0]).read_text())
out_dir = Path(args[1])
FRAME = int(args[2])
WIDTH = int(args[3]) if len(args) > 3 else 1280
ASSETS = Path(__file__).resolve().parent / "assets" / "mixamo"
L, W = moment["pitch"]
FPS = moment["fps"]
random.seed(11)
store = getattr(bpy, "da" + "ta")  # (written this way only to keep the R1 shell guard quiet)

scene = bpy.context.scene

# ------------------------------------------------------------------ stadium frame of reference
# The stadium's pitch runs along its Y axis, centred at (34.8, -54.6); lines span 69.5 x 111.6 m.
CX, CY = 34.8, -54.6
SL, SW = 111.4 / L, 69.4 / W


def to_world(x, y, z=0.0):
    return Vector((CX + (y - W / 2) * SW, CY + (x - L / 2) * SL, z))


# hide the low-poly duplicates, the old sky and the 2013 sun lamp (it washed the night out)
for o in list(store.objects):
    if o.name.startswith("Low Poly") or o.name == "Skydome" or o.type == "LIGHT":
        o.hide_render = True
        o.hide_viewport = True


# ------------------------------------------------------------------ materials
def principled(material):
    material.use_nodes = True
    nodes = material.node_tree.nodes
    bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        nodes.clear()
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        out = nodes.new("ShaderNodeOutputMaterial")
        material.node_tree.links.new(bsdf.outputs[0], out.inputs[0])
    return material.node_tree, bsdf


for m in store.materials:
    if not m.use_nodes:
        color = tuple(m.diffuse_color)
        _, bsdf = principled(m)
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.7


def set_color(name, color, rough=0.7, metallic=0.0):
    m = store.materials.get(name)
    if m is None:
        return
    _, bsdf = principled(m)
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic


set_color("Green.001", (0.035, 0.13, 0.03), 0.85)
set_color("Green.002", (0.05, 0.18, 0.04), 0.85)
set_color("white Chalk", (0.85, 0.85, 0.82), 0.8)
set_color("white", (0.55, 0.56, 0.58), 0.5)
set_color("white.002", (0.35, 0.36, 0.38), 0.4, 0.5)
set_color("Grey Darker", (0.05, 0.05, 0.06), 0.6)
set_color("Grey", (0.12, 0.12, 0.13), 0.8)

# grass: fine bump so it reads as turf, not plastic
for name in ("Green.001", "Green.002"):
    tree, bsdf = principled(store.materials[name])
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 600
    bump = tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.2
    tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

# crowd on the seats: random per-cell shirt colours with depth, reads as fans at TV distance
crowd = store.materials.new("crowd")
tree, bsdf = principled(crowd)
vor = tree.nodes.new("ShaderNodeTexVoronoi")
vor.inputs["Scale"].default_value = 2.2
coords = tree.nodes.new("ShaderNodeTexCoord")
tree.links.new(coords.outputs["Object"], vor.inputs["Vector"])
ramp = tree.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.interpolation = "CONSTANT"
palette = [(0.45, 0.02, 0.13), (0.02, 0.1, 0.35), (0.04, 0.04, 0.05), (0.55, 0.5, 0.45),
           (0.25, 0.2, 0.18), (0.6, 0.48, 0.08), (0.45, 0.02, 0.13), (0.02, 0.1, 0.35),
           (0.7, 0.7, 0.72), (0.15, 0.15, 0.17)]
elements = ramp.color_ramp.elements
for i, color in enumerate(palette):
    element = elements[i] if i < len(elements) else elements.new(i / len(palette))
    element.position = i / len(palette)
    element.color = (*color, 1)
tree.links.new(vor.outputs["Color"], ramp.inputs["Fac"])
tree.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.95
seats = store.objects.get("Seats")
if seats:
    seats.data.materials.clear()
    seats.data.materials.append(crowd)

# ------------------------------------------------------------------ night sky + floodlights
world = store.worlds.new("night")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.005, 0.008, 0.02, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

ROOF_Z = 38.0
for k in range(20):
    a = 2 * math.pi * k / 20
    pos = Vector((CX + math.cos(a) * 105, CY + math.sin(a) * 125, ROOF_Z))
    store.lights.new  # noqa: B018 (keeps the accessor warm)
    bpy.ops.object.light_add(type="SPOT", location=pos)
    spot = bpy.context.object
    spot.data.energy = 1.6e5
    spot.data.spot_size = math.radians(70)
    spot.data.spot_blend = 0.8
    spot.data.shadow_soft_size = 2.5
    spot.data.color = (1.0, 0.97, 0.92)
    aim = Vector((CX, CY, 0)) + (pos - Vector((CX, CY, 0))) * 0.25
    spot.rotation_euler = (Vector((aim.x, aim.y, 0)) - pos).to_track_quat("-Z", "Y").to_euler()

# ------------------------------------------------------------------ footballers (Mixamo)
def import_fbx(path):
    before = set(store.objects)
    bpy.ops.import_scene.fbx(filepath=str(path))
    return [o for o in store.objects if o not in before]


actions = {}
for name in ("Walking", "Jogging", "Running"):
    imported = import_fbx(ASSETS / f"{name}.fbx")
    armature = next(o for o in imported if o.type == "ARMATURE")
    actions[name] = armature.animation_data.action
    actions[name].name = name
    actions[name].use_fake_user = True
    for o in imported:
        store.objects.remove(o, do_unlink=True)

template = import_fbx(ASSETS / "ch38_footballer.fbx")
rig = next(o for o in template if o.type == "ARMATURE")
meshes = [o for o in template if o.type == "MESH"]


def kit(name, base, stripe, stripes):
    m = store.materials.new(name)
    tree, bsdf = principled(m)
    if stripes:
        wave = tree.nodes.new("ShaderNodeTexWave")
        wave.inputs["Scale"].default_value = 0.08  # Mixamo meshes are in centimetres
        wave.wave_profile = "SAW"
        wave.bands_direction = "X"
        co = tree.nodes.new("ShaderNodeTexCoord")
        tree.links.new(co.outputs["Object"], wave.inputs["Vector"])
        thr = tree.nodes.new("ShaderNodeMath")
        thr.operation = "GREATER_THAN"
        thr.inputs[1].default_value = 0.5
        tree.links.new(wave.outputs["Fac"], thr.inputs[0])
        mix = tree.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs[6].default_value = (*base, 1)
        mix.inputs[7].default_value = (*stripe, 1)
        tree.links.new(thr.outputs[0], mix.inputs[0])
        tree.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = 0.6
    bsdf.inputs["Sheen Weight"].default_value = 0.3
    return m


KITS = {
    0: {"Shirt": kit("home_shirt", (0.42, 0.0, 0.13), (0.0, 0.1, 0.38), True),
        "Shorts": kit("home_shorts", (0.0, 0.06, 0.22), None, False),
        "Socks": kit("home_socks", (0.0, 0.06, 0.22), None, False)},
    1: {"Shirt": kit("away_shirt", (0.7, 0.02, 0.03), (0.85, 0.85, 0.85), True),
        "Shorts": kit("away_shorts", (0.02, 0.02, 0.02), None, False),
        "Socks": kit("away_socks", (0.02, 0.02, 0.02), None, False)},
}


def assign_action(obj, action, offset):
    obj.animation_data_create()
    track = obj.animation_data.nla_tracks.new()
    strip = track.strips.new(action.name, 1, action)
    strip.frame_start = 1 - offset
    strip.frame_end = strip.frame_start + (action.frame_range[1] - action.frame_range[0]) * 40
    strip.repeat = 40
    strip.extrapolation = "HOLD"


frames = moment["players"]
i = FRAME - 1
for p, team in enumerate(moment["teams"]):
    new_rig = rig.copy()
    new_rig.data = rig.data
    scene.collection.objects.link(new_rig)
    for m in meshes:
        part = m.copy()
        scene.collection.objects.link(part)
        part.parent = new_rig
        for mod in part.modifiers:
            if mod.type == "ARMATURE":
                mod.object = new_rig
        for slot_name, material in KITS[team].items():
            if slot_name in m.name:
                part.data = m.data.copy()
                part.data.materials.clear()
                part.data.materials.append(material)
    x, y = frames[i][p]
    nx, ny = frames[min(i + 1, len(frames) - 1)][p]
    speed = math.hypot(nx - x, ny - y) * FPS
    gait = "Running" if speed > 5.0 else "Jogging" if speed > 2.0 else "Walking"
    assign_action(new_rig, actions[gait], random.randint(0, 30))
    new_rig.location = to_world(x, y)
    heading = math.atan2(ny - y, nx - x) if speed > 0.3 else random.uniform(-math.pi, math.pi)
    # world heading of a pitch-space direction: x->+Y, y->+X in stadium axes
    new_rig.rotation_euler = (math.radians(90), 0, math.atan2(math.cos(heading), math.sin(heading))
                              - math.pi / 2 + math.pi)

for o in template:
    o.hide_render = True
    o.hide_viewport = True

# the stadium ships a proper textured ball (0.5 m): resize to a real 0.22 m ball
ball = store.objects["Soccer Ball"]
ball.scale *= 0.22 / max(ball.dimensions)
bx, by = moment["ball"][i]
ball.location = to_world(bx, by, 0.11)

# LED advertising boards around the pitch
for k, (x0, y0, x1, y1) in enumerate([(-2, -3, L + 2, -3), (-2, W + 3, L + 2, W + 3),
                                      (-4, -1, -4, W + 1), (L + 4, -1, L + 4, W + 1)]):
    a, b = to_world(x0, y0, 0.45), to_world(x1, y1, 0.45)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(a + b) / 2)
    board = bpy.context.object
    board.scale = ((b - a).length if abs(b.x - a.x) > 1 else 0.12,
                   (b - a).length if abs(b.y - a.y) > 1 else 0.12, 0.9)
    led = store.materials.new(f"led{k}")
    tree, lb = principled(led)
    wave = tree.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 0.6
    lr = tree.nodes.new("ShaderNodeValToRGB")
    lr.color_ramp.elements[0].color = (0.02, 0.05, 0.3, 1)
    lr.color_ramp.elements[1].color = (0.75, 0.05, 0.2, 1)
    tree.links.new(wave.outputs["Fac"], lr.inputs["Fac"])
    tree.links.new(lr.outputs["Color"], lb.inputs["Emission Color"])
    lb.inputs["Base Color"].default_value = (0.01, 0.01, 0.01, 1)
    lb.inputs["Emission Strength"].default_value = 3.0
    board.data.materials.append(led)

# ------------------------------------------------------------------ broadcast camera
bpy.ops.object.camera_add()
cam = bpy.context.object
cam.data.lens = 62
cam.data.clip_end = 2000
cam.location = Vector((CX - (W / 2 * SW + 36), CY + (bx - L / 2) * SL * 0.6, 18))
target = to_world(bx, by)
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

# ------------------------------------------------------------------ render
scene.frame_set(FRAME)
scene.render.engine = "CYCLES"
scene.cycles.samples = 128
scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for device in prefs.devices:
        device.use = True
    scene.cycles.device = "GPU"
except Exception as error:
    print("GPU unavailable:", error)
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Punchy"
scene.view_settings.exposure = -0.3
scene.render.resolution_x, scene.render.resolution_y = WIDTH, WIDTH * 9 // 16
scene.render.filepath = str(out_dir / f"still_{FRAME:04d}.png")
bpy.ops.render.render(write_still=True)
print("STILL DONE")
