"""Realistic look-dev scene: Cycles, floodlit night stadium, textured grass, articulated players.

    Blender -b -P video/scene_v2.py -- <moment.json> <out_dir> <first_frame> <last_frame> <width>

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
F0, F1 = int(args[2]), int(args[3])
WIDTH = int(args[4]) if len(args) > 4 else 1280
L, W = moment["pitch"]
FPS = moment["fps"]
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start, scene.frame_end = F0, F1
scene.render.engine = "CYCLES"
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.render.resolution_x, scene.render.resolution_y = WIDTH, WIDTH * 9 // 16
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 0.5
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(out_dir / "f_")
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for device in prefs.devices:
        device.use = True
    scene.cycles.device = "GPU"
except Exception as error:  # CPU fallback keeps the script portable
    print("GPU unavailable:", error)
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
except TypeError:
    scene.view_settings.view_transform = "Filmic"


# ------------------------------------------------------------------ helpers
def node_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes["Principled BSDF"]


def plain(name, color, rough=0.6, emission=0.0, metallic=0.0):
    m, _, _, bsdf = node_mat(name)
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    return m


def to_world(x, y, z=0.0):
    return Vector((x - L / 2, y - W / 2, z))


def add(obj_op, material=None, **kw):
    obj_op(**kw)
    o = bpy.context.object
    if material:
        o.data.materials.append(material)
    return o


# ------------------------------------------------------------------ sky
world = bpy.data.worlds.new("night")
scene.world = world
world.use_nodes = True
wn, wl = world.node_tree.nodes, world.node_tree.links
sky = wn.new("ShaderNodeTexGradient")
coord = wn.new("ShaderNodeTexCoord")
sep = wn.new("ShaderNodeSeparateXYZ")
ramp = wn.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.004, 0.006, 0.014, 1)
ramp.color_ramp.elements[1].color = (0.03, 0.045, 0.09, 1)
wl.new(coord.outputs["Generated"], sep.inputs[0])
wl.new(sep.outputs["Z"], ramp.inputs["Fac"])
wl.new(ramp.outputs["Color"], wn["Background"].inputs["Color"])
wn["Background"].inputs["Strength"].default_value = 1.0

# ------------------------------------------------------------------ grass
grass, gn, gl, gbsdf = node_mat("grass")
tc = gn.new("ShaderNodeTexCoord")
sepg = gn.new("ShaderNodeSeparateXYZ")
gl.new(tc.outputs["Object"], sepg.inputs[0])
stripe = gn.new("ShaderNodeMath")
stripe.operation = "SINE"
mul = gn.new("ShaderNodeMath")
mul.operation = "MULTIPLY"
mul.inputs[1].default_value = math.pi / (L / 18)
gl.new(sepg.outputs["X"], mul.inputs[0])
gl.new(mul.outputs[0], stripe.inputs[0])
sign = gn.new("ShaderNodeMath")
sign.operation = "GREATER_THAN"
sign.inputs[1].default_value = 0.0
gl.new(stripe.outputs[0], sign.inputs[0])
noise = gn.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = 0.35
noise.inputs["Detail"].default_value = 8
mix_s = gn.new("ShaderNodeMix")
mix_s.data_type = "RGBA"
mix_s.inputs[6].default_value = (0.045, 0.16, 0.035, 1)
mix_s.inputs[7].default_value = (0.065, 0.22, 0.05, 1)
gl.new(sign.outputs[0], mix_s.inputs[0])
mix_n = gn.new("ShaderNodeMix")
mix_n.data_type = "RGBA"
mix_n.inputs[0].default_value = 0.18
gl.new(mix_s.outputs[2], mix_n.inputs[6])
gl.new(noise.outputs["Color"], mix_n.inputs[7])
gl.new(mix_n.outputs[2], gbsdf.inputs["Base Color"])
gbsdf.inputs["Roughness"].default_value = 0.85
fine = gn.new("ShaderNodeTexNoise")
fine.inputs["Scale"].default_value = 900
bump = gn.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.25
gl.new(fine.outputs["Fac"], bump.inputs["Height"])
gl.new(bump.outputs["Normal"], gbsdf.inputs["Normal"])
add(bpy.ops.mesh.primitive_plane_add, grass, size=1, location=(0, 0, 0)).scale = (L + 14, W + 12, 1)

paint = plain("paint", (0.92, 0.92, 0.9), rough=0.7)


def line(x0, y0, x1, y1, w=0.12):
    a, b = to_world(x0, y0, 0.005), to_world(x1, y1, 0.005)
    o = add(bpy.ops.mesh.primitive_plane_add, paint, size=1, location=(a + b) / 2)
    o.scale = (max((b - a).length, w), w, 1)
    o.rotation_euler.z = math.atan2(b.y - a.y, b.x - a.x)


for seg in [(0, 0, L, 0), (0, W, L, W), (0, 0, 0, W), (L, 0, L, W), (L / 2, 0, L / 2, W)]:
    line(*seg)
for x_goal, d in ((0, 1), (L, -1)):
    for depth, half in ((16.5, 20.16), (5.5, 9.16)):
        line(x_goal, W / 2 - half, x_goal + d * depth, W / 2 - half)
        line(x_goal, W / 2 + half, x_goal + d * depth, W / 2 + half)
        line(x_goal + d * depth, W / 2 - half, x_goal + d * depth, W / 2 + half)
ring = add(bpy.ops.mesh.primitive_torus_add, paint, major_radius=9.15, minor_radius=0.06,
           location=(0, 0, 0.005))
ring.scale.z = 0.02

# goals with nets
post = plain("post", (0.95, 0.95, 0.95), rough=0.3)
net = plain("net", (0.9, 0.9, 0.9), rough=0.8)
for gx, d in ((-L / 2, -1), (L / 2, 1)):
    for gy in (-3.66, 3.66):
        add(bpy.ops.mesh.primitive_cylinder_add, post, radius=0.06, depth=2.44,
            location=(gx, gy, 1.22))
    bar = add(bpy.ops.mesh.primitive_cylinder_add, post, radius=0.06, depth=7.32,
              location=(gx, 0, 2.44))
    bar.rotation_euler.x = math.radians(90)
    back = add(bpy.ops.mesh.primitive_plane_add, net, size=1, location=(gx + d * 1.5, 0, 1.2))
    back.scale = (1, 7.32, 2.4)
    back.rotation_euler.y = math.radians(90 - 30 * d)
    wire = back.modifiers.new("net", "WIREFRAME")
    wire.thickness = 0.015
    sub = back.modifiers.new("cells", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 5
    back.modifiers.move(1, 0)

# ------------------------------------------------------------------ stadium
crowd, cn, cl, cbsdf = node_mat("crowd")
vor = cn.new("ShaderNodeTexVoronoi")
vor.inputs["Scale"].default_value = 3.2
ctc = cn.new("ShaderNodeTexCoord")
cl.new(ctc.outputs["Object"], vor.inputs["Vector"])
cramp = cn.new("ShaderNodeValToRGB")
cramp.color_ramp.interpolation = "CONSTANT"
palette = [(0.5, 0.02, 0.15), (0.02, 0.12, 0.4), (0.06, 0.06, 0.07), (0.6, 0.55, 0.5),
           (0.35, 0.3, 0.28), (0.75, 0.6, 0.1), (0.5, 0.02, 0.15), (0.02, 0.12, 0.4)]
for i, color in enumerate(palette):
    element = cramp.color_ramp.elements[i] if i < 2 else cramp.color_ramp.elements.new(i / len(palette))
    element.position = i / len(palette)
    element.color = (*color, 1)
cl.new(vor.outputs["Color"], cramp.inputs["Fac"])
cl.new(cramp.outputs["Color"], cbsdf.inputs["Base Color"])
cbsdf.inputs["Roughness"].default_value = 0.95
cbump = cn.new("ShaderNodeBump")
cbump.inputs["Strength"].default_value = 0.6
cl.new(vor.outputs["Distance"], cbump.inputs["Height"])
cl.new(cbump.outputs["Normal"], cbsdf.inputs["Normal"])

concrete = plain("concrete", (0.12, 0.12, 0.13), rough=0.9)
roof_mat = plain("roof", (0.03, 0.03, 0.035), rough=0.6, metallic=0.4)
flood = plain("flood", (1.0, 0.97, 0.9), emission=40.0)


def stand(cx, cy, length, rot, tiers=22, step_d=0.85, step_h=0.55, gap=9.0):
    """A tiered stand facing the pitch: stepped crowd blocks, back wall, roof with light strip."""
    for t in range(tiers):
        o = add(bpy.ops.mesh.primitive_cube_add, crowd, size=1)
        o.scale = (length, step_d, step_h)
        o.location = (0, gap + t * step_d, 1.0 + t * step_h)
        o.select_set(True)
    top = 1.0 + tiers * step_h
    roof = add(bpy.ops.mesh.primitive_cube_add, roof_mat, size=1)
    roof.scale = (length + 6, tiers * step_d + 8, 0.6)
    roof.location = (0, gap + tiers * step_d / 2 - 2, top + 9)
    strip = add(bpy.ops.mesh.primitive_cube_add, flood, size=1)
    strip.scale = (length, 0.6, 0.25)
    strip.location = (0, gap - 5.5, top + 8.6)
    back = add(bpy.ops.mesh.primitive_cube_add, concrete, size=1)
    back.scale = (length + 6, 1, top + 10)
    back.location = (0, gap + tiers * step_d + 0.5, (top + 10) / 2)
    bpy.ops.object.empty_add(location=(cx, cy, 0))
    pivot = bpy.context.object
    pivot.rotation_euler.z = rot
    for o in list(bpy.context.scene.objects):
        if o.parent is None and o is not pivot and o.location.y >= gap - 6 and o.get("placed") is None:
            if o.type == "MESH" and o.data.materials and o.data.materials[0] in (crowd, roof_mat, flood, concrete):
                o.parent = pivot
                o["placed"] = True
    # floodlights from the roof edge towards the pitch
    for i in range(-2, 3):
        bpy.ops.object.light_add(type="SPOT", location=(i * length / 5, gap - 5.5, top + 8.4))
        spot = bpy.context.object
        spot.data.energy = 1.4e6
        spot.data.spot_size = math.radians(55)
        spot.data.spot_blend = 0.6
        spot.data.shadow_soft_size = 1.5
        spot.parent = pivot
        aim = Vector((i * length / 12, -gap - W / 2 * 0.6, 0)) - spot.location
        spot.rotation_euler = aim.to_track_quat("-Z", "Y").to_euler()
        spot["placed"] = True


stand(0, W / 2 + 6, L + 30, 0)                       # far side (main view)
stand(L / 2 + 7, 0, W + 24, math.radians(90))         # right end
stand(-L / 2 - 7, 0, W + 24, math.radians(-90))       # left end
# near side: lights only (the camera gantry sits in front of the main stand)
for i in range(-2, 3):
    bpy.ops.object.light_add(type="SPOT", location=(i * 22, -W / 2 - 25, 34))
    spot = bpy.context.object
    spot.data.energy = 1.2e6
    spot.data.spot_size = math.radians(60)
    spot.data.spot_blend = 0.6
    aim = Vector((i * 8, 8, 0)) - spot.location
    spot.rotation_euler = aim.to_track_quat("-Z", "Y").to_euler()

# LED boards
for i, x in enumerate(range(int(-L / 2) - 6, int(L / 2) + 6, 12)):
    led, ln_, ll, lb = node_mat(f"led{i}")
    wave = ln_.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 2.0
    lr = ln_.new("ShaderNodeValToRGB")
    base = [(0.45, 0.0, 0.18), (0.0, 0.18, 0.45), (0.9, 0.7, 0.1)][i % 3]
    lr.color_ramp.elements[0].color = (*[c * 0.3 for c in base], 1)
    lr.color_ramp.elements[1].color = (*base, 1)
    ll.new(wave.outputs["Fac"], lr.inputs["Fac"])
    ll.new(lr.outputs["Color"], lb.inputs["Emission Color"])
    lb.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
    lb.inputs["Emission Strength"].default_value = 2.5
    board = add(bpy.ops.mesh.primitive_cube_add, led, size=1, location=(x + 6, W / 2 + 4, 0.45))
    board.scale = (11.8, 0.15, 0.9)

# ------------------------------------------------------------------ players
def kit_material(name, c1, c2, stripes):
    m, n, lk, bsdf = node_mat(name)
    tco = n.new("ShaderNodeTexCoord")
    wave = n.new("ShaderNodeTexWave")
    wave.wave_profile = "SAW" if stripes else "SIN"
    wave.inputs["Scale"].default_value = 5.0 if stripes else 0.0
    wave.bands_direction = "X"
    lk.new(tco.outputs["Object"], wave.inputs["Vector"])
    thr = n.new("ShaderNodeMath")
    thr.operation = "GREATER_THAN"
    thr.inputs[1].default_value = 0.5
    lk.new(wave.outputs["Fac"], thr.inputs[0])
    mix = n.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (*c1, 1)
    mix.inputs[7].default_value = (*c2, 1)
    lk.new(thr.outputs[0], mix.inputs[0])
    lk.new(mix.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.55
    sheen = "Sheen Weight" if "Sheen Weight" in bsdf.inputs else "Sheen"
    bsdf.inputs[sheen].default_value = 0.4
    return m


kits = {
    0: dict(shirt=kit_material("home_shirt", (0.45, 0.0, 0.14), (0.0, 0.12, 0.42), True),
            shorts=plain("home_shorts", (0.0, 0.07, 0.25), 0.5),
            socks=plain("home_socks", (0.0, 0.07, 0.25), 0.6)),
    1: dict(shirt=kit_material("away_shirt", (0.75, 0.03, 0.04), (0.9, 0.9, 0.9), True),
            shorts=plain("away_shorts", (0.03, 0.03, 0.03), 0.5),
            socks=plain("away_socks", (0.03, 0.03, 0.03), 0.6)),
}
skins = [plain(f"skin{i}", c, 0.45) for i, c in
         enumerate([(0.62, 0.43, 0.32), (0.42, 0.28, 0.18), (0.22, 0.14, 0.09), (0.7, 0.52, 0.42)])]
hair = plain("hair", (0.02, 0.015, 0.01), 0.5)
boot = plain("boot", (0.9, 0.9, 0.92), 0.35)


def capsule(material, radius, length, location, parent):
    o = add(bpy.ops.mesh.primitive_cylinder_add, material, radius=radius, depth=length,
            location=location, vertices=16)
    bevel = o.modifiers.new("round", "BEVEL")
    bevel.width = radius * 0.9
    bevel.segments = 4
    bpy.ops.object.shade_smooth()
    o.parent = parent
    return o


def limb(material, radius, length, hinge, parent, foot=None):
    """A limb hanging from a hinge empty, so it can swing around the hinge."""
    bpy.ops.object.empty_add(location=hinge)
    joint = bpy.context.object
    joint.parent = parent
    capsule(material, radius, length, (hinge[0], hinge[1], hinge[2] - length / 2), joint)
    if foot is not None:
        f = add(bpy.ops.mesh.primitive_cube_add, foot, size=1,
                location=(hinge[0] + 0.07, hinge[1], hinge[2] - length - 0.03))
        f.scale = (0.26, 0.1, 0.07)
        f.parent = joint
    return joint


players = []
for index, team in enumerate(moment["teams"]):
    k = kits[team]
    skin = random.choice(skins)
    bpy.ops.object.empty_add(location=(0, 0, 0))
    root = bpy.context.object
    capsule(k["shirt"], 0.19, 0.62, (0, 0, 1.25), root)                 # torso
    capsule(k["shorts"], 0.18, 0.22, (0, 0, 0.9), root)                 # hips
    head = add(bpy.ops.mesh.primitive_uv_sphere_add, skin, radius=0.11, location=(0, 0, 1.72))
    bpy.ops.object.shade_smooth()
    head.parent = root
    cap = add(bpy.ops.mesh.primitive_uv_sphere_add, hair, radius=0.115, location=(-0.01, 0, 1.75))
    cap.scale.z = 0.6
    cap.parent = root
    legs = [limb(k["socks"], 0.075, 0.85, (0, side * 0.1, 0.88), root, foot=boot) for side in (-1, 1)]
    arms = [limb(skin, 0.05, 0.62, (0, side * 0.25, 1.5), root) for side in (-1, 1)]
    players.append((root, legs, arms))

ball_mat = plain("ball", (0.95, 0.95, 0.95), 0.3)
ball = add(bpy.ops.mesh.primitive_uv_sphere_add, ball_mat, radius=0.11, location=(0, 0, 0.11))
bpy.ops.object.shade_smooth()

frames = moment["players"]
phase = [random.random() * 6.28 for _ in players]
for f in range(F0, F1 + 1):
    i = f - 1
    for p, (root, legs, arms) in enumerate(players):
        x, y = frames[i][p]
        nx, ny = frames[min(i + 1, len(frames) - 1)][p]
        speed = math.hypot(nx - x, ny - y) * FPS
        phase[p] += speed * 0.11 / FPS * 6.28 * 1.4
        swing = min(speed / 7.0, 1.0) * 0.75
        root.location = to_world(x, y, abs(math.sin(phase[p])) * swing * 0.06)
        if speed > 0.4:
            root.rotation_euler.z = math.atan2(ny - y, nx - x)
        root.rotation_euler.y = swing * 0.18  # lean into the run
        for side, joint in enumerate(legs):
            joint.rotation_euler.y = math.sin(phase[p] + side * math.pi) * swing
            joint.keyframe_insert("rotation_euler", frame=f)
        for side, joint in enumerate(arms):
            joint.rotation_euler.y = -math.sin(phase[p] + side * math.pi) * swing * 0.9
            joint.keyframe_insert("rotation_euler", frame=f)
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
    bx, by = moment["ball"][i]
    ball.location = to_world(bx, by, 0.11)
    ball.keyframe_insert("location", frame=f)

# ------------------------------------------------------------------ broadcast camera
bpy.ops.object.camera_add(location=(0, -(W / 2 + 36), 18))
cam = bpy.context.object
cam.data.lens = 62
cam.data.clip_end = 1000
scene.camera = cam
bpy.ops.object.empty_add()
aim = bpy.context.object
track = cam.constraints.new("TRACK_TO")
track.target, track.track_axis, track.up_axis = aim, "TRACK_NEGATIVE_Z", "UP_Y"
smooth = None
for f in range(1, F1 + 1):
    bx, by = moment["ball"][f - 1]
    target = to_world(bx, by)
    smooth = target.x if smooth is None else smooth + 0.08 * (target.x - smooth)
    if f >= F0:
        aim.location = Vector((smooth, target.y * 0.35, 0))
        aim.keyframe_insert("location", frame=f)

bpy.ops.render.render(animation=True)
print("RENDER DONE")
