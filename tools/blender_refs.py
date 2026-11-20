"""Runs INSIDE Blender (tools/render_refs.py starts it): render shape references for many jobs in one session.

    blender -b --python tools/blender_refs.py -- <jobs.json>

jobs.json: {"model": {model.json with "_dir"}, "jobs": {id: job}, "out": folder}. Each job: view, camera,
shot, lens, state, focus, canvas, elevation, fill (see tools/product_model.py). Output <id>_rgba.png per job
(transparent background) and <id>.json (camera facts). Shape only: approximate materials, no food or water.
"""
import fnmatch
import json
import math
import os
import sys
import time

import bmesh
import bpy
import mathutils
from bpy_extras.object_utils import world_to_camera_view

ARGS = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
MODEL, JOBS, OUT = ARGS["model"], ARGS["jobs"], ARGS["out"]
AXIS = {"+X": (1, 0, 0), "-X": (-1, 0, 0), "+Y": (0, 1, 0), "-Y": (0, -1, 0), "+Z": (0, 0, 1), "-Z": (0, 0, -1)}
VIEW_AZIMUTH = ARGS["table"]["VIEW_AZIMUTH"]
LENS_MM = ARGS["table"]["LENS_MM"]
CANVAS_PX = ARGS["table"]["CANVAS_PX"]


def matches(name, patterns):
    return any(fnmatch.fnmatch(name, p) for p in patterns or [])


def load():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(MODEL["_dir"], MODEL["mesh"]))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for o in meshes:
        if matches(o.name, MODEL.get("hide")):
            o.hide_render = True
    return meshes


def orient(meshes):
    """Rotate the product so its front faces -Y and it stands on +Z, resting on the floor."""
    axes = MODEL.get("axes") or {"front": "-Y", "up": "+Z"}
    f, u = mathutils.Vector(AXIS[axes["front"]]), mathutils.Vector(AXIS[axes["up"]])
    src = mathutils.Matrix((f, u, f.cross(u))).transposed()
    dst = mathutils.Matrix((mathutils.Vector((0, -1, 0)), mathutils.Vector((0, 0, 1)),
                            mathutils.Vector((0, -1, 0)).cross(mathutils.Vector((0, 0, 1))))).transposed()
    rot = (dst @ src.transposed()).to_4x4()
    for o in meshes:
        o.matrix_world = rot @ o.matrix_world
    bpy.context.view_layer.update()
    lo = min((o.matrix_world @ mathutils.Vector(c)).z for o in meshes if not o.hide_render for c in o.bound_box)
    for o in meshes:
        o.matrix_world = mathutils.Matrix.Translation((0, 0, -lo)) @ o.matrix_world
    bpy.context.view_layer.update()


def principled(name, color, rough, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def thin_clear():
    m = bpy.data.materials.new("clear")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out, mix = nt.nodes.new("ShaderNodeOutputMaterial"), nt.nodes.new("ShaderNodeMixShader")
    fr = nt.nodes.new("ShaderNodeLayerWeight")
    fr.inputs["Blend"].default_value = 0.25
    tr, gl = nt.nodes.new("ShaderNodeBsdfTransparent"), nt.nodes.new("ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.05
    nt.links.new(fr.outputs["Fresnel"], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(gl.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m


def fix_normals(o):
    """CAD exports often carry flipped faces and custom normals; a clear part looks black without this."""
    bpy.context.view_layer.objects.active = o
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True)
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()
    for p in o.data.polygons:
        p.use_smooth = True


def materials(meshes):
    """Approximate looks by class; colour and finish come from the product photo, not from here."""
    classes = {
        "black": principled("black", (0.012, 0.012, 0.014), 0.5),
        "white": principled("white", (0.78, 0.78, 0.76), 0.45),
        "grey": principled("grey", (0.35, 0.35, 0.36), 0.45),
        "steel": principled("steel", (0.78, 0.78, 0.78), 0.25, 1.0),
        "clear": thin_clear(),
    }
    spec = MODEL.get("materials") or {}
    default = spec.get("default", "grey")
    for o in meshes:
        cls = next((c for c, pats in spec.items() if c != "default" and matches(o.name, pats)), default)
        o.data.materials.clear()
        o.data.materials.append(classes.get(cls, classes["grey"]))
        if cls == "clear":
            fix_normals(o)


def apply_state(meshes, state, base):
    for o in meshes:
        o.matrix_world = base[o.name].copy()
        o.hide_render = matches(o.name, MODEL.get("hide"))
    spec = (MODEL.get("states") or {}).get(state) or {}
    for o in meshes:
        if matches(o.name, spec.get("hide")):
            o.hide_render = True
        for pat, delta in (spec.get("move") or {}).items():
            if fnmatch.fnmatch(o.name, pat):
                o.matrix_world = mathutils.Matrix.Translation(delta) @ o.matrix_world
        for pat, r in (spec.get("rotate") or {}).items():
            if fnmatch.fnmatch(o.name, pat):
                pivot = mathutils.Vector(r.get("pivot", (0, 0, 0)))
                rot = mathutils.Matrix.Rotation(math.radians(r["deg"]), 4, r.get("axis", "X"))
                o.matrix_world = mathutils.Matrix.Translation(pivot) @ rot @ mathutils.Matrix.Translation(-pivot) @ o.matrix_world
    bpy.context.view_layer.update()


def aimed(meshes, focus):
    if focus and focus != "whole":
        pats = (MODEL.get("parts") or {}).get(focus)
        hit = [o for o in meshes if not o.hide_render and matches(o.name, pats)] if pats else []
        if hit:
            return hit, True
    return [o for o in meshes if not o.hide_render], focus in (None, "", "whole")


def corners(objs):
    return [o.matrix_world @ mathutils.Vector(c) for o in objs for c in o.bound_box]


def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception:
        sc.cycles.device = "CPU"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    bg.inputs[1].default_value = 0.25
    gl = nt.nodes.new("ShaderNodeBackground")
    gl.inputs[1].default_value = 0.9
    lp, mix = nt.nodes.new("ShaderNodeLightPath"), nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Glossy Ray"], mix.inputs[0])
    nt.links.new(bg.outputs[0], mix.inputs[1])
    nt.links.new(gl.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["World Output"].inputs[0])
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    lights = []
    for name, energy, size in (("key", 160, 1.6), ("fill", 60, 1.8), ("rim", 90, 1.2)):
        l = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
        l.data.energy, l.data.size = energy, size
        sc.collection.objects.link(l)
        lights.append(l)
    return sc, cam, lights


def place(sc, cam, lights, objs, job):
    w, h = CANVAS_PX[job["canvas"]]
    sc.render.resolution_x, sc.render.resolution_y = w, h
    cam.data.lens = LENS_MM[job["lens"]]
    cam.data.sensor_fit = "AUTO"
    pts = corners(objs)
    lo = mathutils.Vector([min(p[i] for p in pts) for i in range(3)])
    hi = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
    target = (lo + hi) / 2
    a, e = math.radians(VIEW_AZIMUTH[job["view"]]), math.radians(job["elevation"])
    direction = mathutils.Vector((-math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    if abs(direction.z) > 0.999:
        direction = mathutils.Vector((-math.sin(a) * 0.02, -math.cos(a) * 0.02, 1)).normalized()

    def put(dist):
        loc = target + direction * dist
        loc.z = max(loc.z, 0.012)
        cam.location = loc
        cam.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()

    lo_d, hi_d = 0.05, 20.0
    for _ in range(28):
        mid = (lo_d + hi_d) / 2
        put(mid)
        cs = [world_to_camera_view(sc, cam, p) for p in pts]
        if any(c.z <= 0 for c in cs):
            lo_d = mid
            continue
        ext = max(max(c.x for c in cs) - min(c.x for c in cs), max(c.y for c in cs) - min(c.y for c in cs))
        if ext > job["fill"]:
            lo_d = mid
        else:
            hi_d = mid
    put(hi_d)
    for l, offset in zip(lights, ((-0.9, -1.1, 1.2), (1.2, -0.7, 0.5), (0.4, 1.2, 1.0))):
        l.location = target + mathutils.Matrix.Rotation(-a, 3, "Z") @ mathutils.Vector(offset) * max(1.0, hi_d / 1.5)
        l.rotation_euler = (target - l.location).to_track_quat("-Z", "Y").to_euler()
    return hi_d, target


def main():
    t0 = time.time()
    meshes = load()
    orient(meshes)
    materials(meshes)
    base = {o.name: o.matrix_world.copy() for o in meshes}
    sc, cam, lights = setup_scene()
    os.makedirs(OUT, exist_ok=True)
    for jid, job in JOBS.items():
        t = time.time()
        apply_state(meshes, job["state"], base)
        objs, found = aimed(meshes, job["focus"])
        dist, target = place(sc, cam, lights, objs, job)
        sc.render.filepath = os.path.join(OUT, jid + "_rgba.png")
        bpy.ops.render.render(write_still=True)
        facts = dict(job, id=jid, distance_m=round(dist, 4), focal_mm=cam.data.lens,
                     target=[round(v, 4) for v in target], focus_found=found)
        with open(os.path.join(OUT, jid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(facts, fh, indent=1)
        print("RENDERED %s %.1fs %s" % (jid, time.time() - t, json.dumps(job, sort_keys=True)))
    print("ALL %d jobs %.1fs" % (len(JOBS), time.time() - t0))


main()
