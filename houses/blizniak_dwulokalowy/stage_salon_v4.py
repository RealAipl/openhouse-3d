"""One editable V4 living-room study; keep the concept shell and openings intact."""
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from houses.blizniak_dwulokalowy.plan import ROOMS

OUT = ROOT / "houses/blizniak_dwulokalowy/output/salon_v4"
PACK = ROOT / "tmp/salon-v4/pack"
ROOM = "A_upper_5"
FLOOR = 2.96
PREPARED = json.loads((OUT / "prepared_assets.json").read_text())
ASSETS = {a["id"]: a for a in PREPARED["models"]}
REPORT = []
MATERIAL_REPORT = []
rng = random.Random(31015)


def geometry_hash(ob):
    h = hashlib.sha256()
    h.update(str(tuple(tuple(row) for row in ob.matrix_world)).encode())
    for v in ob.data.vertices:
        h.update(str(tuple(v.co)).encode())
    for p in ob.data.polygons:
        h.update(str(tuple(p.vertices)).encode())
    return h.hexdigest()


def box(name, loc, dims, mat, bevel=0.002):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = "V4_" + name
    ob.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(mat)
    if bevel:
        b = ob.modifiers.new("Crafted edges", "BEVEL")
        b.width = bevel
        b.segments = 3
        ob.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return ob


def simple(name, color, rough=0.6, metal=0):
    mat = bpy.data.materials.new("V4_" + name)
    mat.use_nodes = True
    p = mat.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    return mat


def pbr(role, tint=None, normal_strength=0.3, repeat=1.0, projection="FLAT"):
    a = PREPARED["materials"][role]
    mat = simple(role, tint or (0.65, 0.61, 0.54))
    nt = mat.node_tree
    bs = nt.nodes.get("Principled BSDF")
    coords = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeVectorMath")
    mapping.operation = "SCALE"
    mapping.inputs[3].default_value = repeat
    nt.links.new(coords.outputs["UV"], mapping.inputs[0])
    paths = [ROOT / f["file"] for f in a["resolved_files"]]
    channels = {
        "color": ("_diff", "_color"),
        "rough": ("_rough",),
        "normal": ("_nor_gl", "_normalgl"),
    }
    used = {}
    for channel, tokens in channels.items():
        path = next((p for p in paths if any(t in p.name.lower() for t in tokens)), None)
        if path is None:
            raise ValueError(f"Required PBR channel missing: {role} / {channel}")
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(path), check_existing=True)
        tex.image.colorspace_settings.name = "sRGB" if channel == "color" else "Non-Color"
        tex.projection = projection
        tex.projection_blend = 0.15
        nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        if channel == "color":
            if tint:
                mix = nt.nodes.new("ShaderNodeMixRGB")
                mix.blend_type = "MULTIPLY"
                mix.inputs[0].default_value = 0.78
                mix.inputs[2].default_value = (*tint, 1)
                nt.links.new(tex.outputs["Color"], mix.inputs[1])
                nt.links.new(mix.outputs[0], bs.inputs["Base Color"])
            else:
                nt.links.new(tex.outputs["Color"], bs.inputs["Base Color"])
        elif channel == "rough":
            nt.links.new(tex.outputs["Color"], bs.inputs["Roughness"])
        else:
            # All new finish surfaces receive explicit UV coordinates in metres.
            normal = nt.nodes.new("ShaderNodeNormalMap")
            normal.inputs["Strength"].default_value = normal_strength
            nt.links.new(tex.outputs["Color"], normal.inputs["Color"])
            nt.links.new(normal.outputs["Normal"], bs.inputs["Normal"])
        used[channel] = str(path.relative_to(ROOT))
    mat["provider"] = a.get("provider", "Poly Haven")
    mat["source"] = a["source"]
    mat["library"] = a["library"]
    mat["license"] = "CC0-1.0"
    MATERIAL_REPORT.append({"role": role, "id": a["id"], "library": a["library"],
                            "source": a["source"], "maps": used,
                            "mapping_repeat_per_metre": repeat, "tint": tint,
                            "normal_strength": normal_strength,
                            "files": a["resolved_files"]})
    return mat


def import_asset(key, loc, width, angle=0, label=None):
    a = ASSETS[key]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(PACK / a["file"]))
    objects = list(set(bpy.data.objects) - before)
    meshes = [o for o in objects if o.type == "MESH"]
    assert meshes, key
    bpy.context.view_layer.update()
    points = [o.matrix_world @ Vector(p) for o in meshes for p in o.bound_box]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    source_dims = hi - lo
    scale = width / max(source_dims.x, source_dims.y)
    assert 0.01 < scale < 100
    root = bpy.data.objects.new("V4_Asset_" + (label or key), None)
    bpy.context.scene.collection.objects.link(root)
    for o in objects:
        if o.parent not in objects:
            transform = o.matrix_world.copy()
            o.parent = root
            o.matrix_world = transform
    origin = Vector(((hi.x + lo.x) / 2, (hi.y + lo.y) / 2, lo.z))
    root.matrix_world = (Matrix.Translation(Vector(loc)) @
                         Matrix.Rotation(math.radians(angle), 4, "Z") @
                         Matrix.Scale(scale, 4) @ Matrix.Translation(-origin))
    root["asset_source"] = a["source"]
    root["asset_sha256"] = a["sha256"]
    root["asset_license"] = "CC0-1.0"
    root["room"] = ROOM
    bpy.context.view_layer.update()
    points = [o.matrix_world @ Vector(p) for o in meshes for p in o.bound_box]
    bounds = [[min(p[i] for p in points) for i in range(3)],
              [max(p[i] for p in points) for i in range(3)]]
    REPORT.append({"id": key, "instance": root.name, "provider": a["provider"],
                   "author": a["author"], "source": a["source"], "license": a["license"],
                   "sha256": a["sha256"], "source_triangles": a["triangles"],
                   "imported_meshes": len(meshes), "embedded_images": a.get("embedded_images"),
                   "original_dimensions_m": list(source_dims), "uniform_scale": scale,
                   "world_bounds_m": bounds, "rotation_z_degrees": angle})
    print("IMPORTED", key, list(source_dims), "scale", scale, flush=True)
    return root, bounds


def area(name, pos, target, energy, size, color=(1, 0.9, 0.76)):
    d = bpy.data.lights.new("V4_" + name, "AREA")
    d.energy = energy
    d.shape = "DISK"
    d.size = size
    d.color = color
    o = bpy.data.objects.new(d.name, d)
    bpy.context.scene.collection.objects.link(o)
    o.location = pos
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()
    return o


def curtain(name, xmin, xmax, mat):
    vertices, faces, uv = [], [], []
    nu, nv = 100, 28
    for j in range(nv + 1):
        v = j / nv
        for i in range(nu + 1):
            u = i / nu
            x = xmin + (xmax - xmin) * u
            y = 0.42 + 0.055 * math.cos(u * math.pi * 16) + 0.009 * math.sin(v * 7 + u * 12)
            z = FLOOR + 0.025 + v * 2.48
            vertices.append((x, y, z))
            uv.append((u * (xmax - xmin) * 2, v * 5))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    layer = mesh.uv_layers.new()
    for poly in mesh.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            layer.data[li].uv = uv[mesh.loops[li].vertex_index]
    ob = bpy.data.objects.new("V4_" + name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    solid = ob.modifiers.new("Linen thickness", "SOLIDIFY")
    solid.thickness = 0.001
    return ob


def main():
    scene = bpy.context.scene
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    preserved = {o.name: geometry_hash(o) for o in bpy.data.objects if o.type == "MESH"
                 and o.name.startswith("BLI_") and o.name != "BLI_Furniture_" + ROOM}
    old = bpy.data.objects.get("BLI_Furniture_" + ROOM)
    assert old is not None
    bpy.data.objects.remove(old, do_unlink=True)
    # Only this room's finishes are hidden beneath the new finish layers.
    floor_ob = bpy.data.objects["BLI_Floor_" + ROOM]
    floor_ob.hide_render = True
    floor_ob.hide_viewport = True

    walls = pbr("walls", (0.95, 0.91, 0.82), 0.08, 0.7)
    oak = pbr("floor", None, 0.22, 0.45)
    walnut = pbr("walnut", None, 0.2, 0.8)
    carpet = pbr("rug", (0.8, 0.73, 0.61), 0.35, 2)
    linen = pbr("curtains", (0.92, 0.90, 0.84), 0.2, 3)
    paint = simple("warm white satin trim", (0.77, 0.74, 0.67), 0.46)
    stone = simple("honed limestone", (0.62, 0.58, 0.49), 0.55)
    charcoal = simple("matte graphite", (0.025, 0.03, 0.031), 0.38)
    brass = simple("brushed bronze", (0.31, 0.19, 0.08), 0.3, 0.75)
    # Refinish original shell polygons only where their face belongs to this room.
    shell = bpy.data.objects["BLI_Envelope_2_levels_4_units"]
    shell.data.materials.append(walls)
    ix = len(shell.data.materials) - 1
    for p in shell.data.polygons:
        c, n = p.center, p.normal
        if 2.93 < c.z < 5.62 and -7.546 <= c.x <= -0.204 and 0 <= c.y < 4.79:
            if ((abs(c.y - 0.27) < 0.001 and n.y > 0.9) or
                (abs(c.x + 7.545) < 0.001 and n.x > 0.9) or
                (abs(c.x + 0.205) < 0.001 and n.x < -0.9)):
                p.material_index = ix
    partitions = bpy.data.objects["BLI_Partitions_A_upper"]
    partitions.data.materials.append(walls)
    for p in partitions.data.polygons:
        if abs(p.center.y - 4.74) < 0.001 and p.normal.y < -0.9:
            p.material_index = len(partitions.data.materials) - 1
    ceiling = bpy.data.objects["BLI_Ceiling_" + ROOM]
    ceiling.data.materials.clear()
    ceiling.data.materials.append(walls)

    # Real-scale floor; PBR texture already contains individual timber boards.
    box("OakFloor", (-3.875, 2.52, 2.949), (7.30, 4.47, 0.022), oak, 0.001)
    # Thin finish layers do not move wall axes, windows, doors or room bounds.
    for name, loc, dims in [
        ("SkirtingWest", (-7.527, 2.51, 3.012), (0.024, 4.46, 0.104)),
        ("SkirtingEast", (-0.224, 2.51, 3.012), (0.024, 4.46, 0.104)),
        ("SkirtingFront", (-3.875, 0.286, 3.012), (7.28, 0.024, 0.104)),
        ("SkirtingBackLeft", (-6.245, 4.723, 3.012), (2.57, 0.024, 0.104)),
        ("SkirtingBackRight", (-2.12, 4.723, 3.012), (3.80, 0.024, 0.104)),
    ]:
        box(name, loc, dims, paint)
    for x in (-7.49, -0.26):
        box("CeilingPerimeter", (x, 2.51, 5.55), (0.07, 4.46, 0.055), paint)
    for y in (0.32, 4.69):
        box("CeilingPerimeter", (-3.875, y, 5.55), (7.30, 0.07, 0.055), paint)
    box("Rug", (-5.86, 2.82, 2.971), (3.10, 2.36, 0.022), carpet, 0.028)

    sofa, sb = import_asset("haven-224-oatmeal-two-seat-sofa-40262c27", (-6.10, 4.02, FLOOR), 2.28)
    import_asset("ember-leather-and-walnut-lounge-chair-9b9f3689", (-6.88, 1.60, FLOOR), 0.86, 125)
    table, tb = import_asset("trio-nesting-coffee-table-set-a1a295a4", (-5.80, 2.66, 2.984), 1.10, 18)
    side, sidebounds = import_asset("trace-180-walnut-sideboard-32858583", (-2.24, 4.40, FLOOR), 1.82)
    dining, dining_bounds = import_asset("span-225-extendable-dining-table-b5cc7e64", (-2.94, 2.60, FLOOR), 2.25, 90)
    for i, (x, y, angle) in enumerate([(-3.83, 2.02, 90), (-3.83, 3.12, 90),
                                      (-2.05, 2.02, -90), (-2.05, 3.12, -90)]):
        import_asset("gather-dining-armchair-ee459660", (x, y, FLOOR), 0.68, angle, "DiningChair_" + str(i))
    lamp, lb = import_asset("paper-column-paper-column-floor-lamp-3b5a06e7", (-7.27, 3.10, FLOOR), 0.302)
    # Paper Column's 1.13m native height is preserved by its uniform scale.
    import_asset("basket-woven-basket-pendant-baacdf33", (-2.94, 2.60, 4.73), 0.44, 0)
    import_asset("brass_vase_01", (-1.86, 4.39, sidebounds[1][2] + 0.001), 0.18)
    # The complete tea set is placed on the dining surface, with no fake texture substitution.
    import_asset("tea_set_01", (-2.94, 2.63, dining_bounds[1][2] + 0.002), 0.63, 20)

    # Preserve the kitchen's documented position along the twin party wall.
    # Door gaps, toe-kick, worktop, sink and tap are explicit editable components.
    for i in range(4):
        y = 2.91 + i * 0.45
        box("KitchenCarcass", (-0.65, y, 3.42), (0.64, 0.445, 0.79), paint)
        box("KitchenFront", (-0.984, y, 3.44), (0.024, 0.438, 0.75), walnut)
        box("KitchenPull", (-1.005, y, 3.78), (0.016, 0.16, 0.012), brass)
    box("KitchenToeKick", (-0.62, 3.585, 3.01), (0.55, 1.80, 0.10), charcoal)
    box("KitchenStone", (-0.67, 3.585, 3.88), (0.70, 1.84, 0.04), stone)
    box("KitchenBacksplash", (-0.222, 3.585, 4.08), (0.025, 1.84, 0.40), stone)
    box("SinkInset", (-0.68, 4.12, 3.904), (0.42, 0.34, 0.012), charcoal)
    for yy in (2.96, 3.22):
        for xx in (-0.80, -0.52):
            bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.09, depth=0.007, location=(xx, yy, 3.906))
            ob = bpy.context.object
            ob.name = "V4_CooktopRing"
            ob.data.materials.append(charcoal)
    from archviz.mesh import MB
    tap = MB()
    tap.tube((-0.35, 4.12, 3.91), (-0.35, 4.12, 4.15), 0.012, 0.012)
    tap.tube((-0.35, 4.12, 4.15), (-0.59, 4.12, 4.15), 0.012, 0.012)
    tap.build("V4_KitchenTap", [brass], smooth=True)
    for x0, x1 in ((-7.16, -6.97), (-5.84, -5.68), (-4.88, -4.71),
                   (-3.60, -3.44), (-2.66, -2.49), (-1.37, -1.20)):
        curtain("LinenPanel", x0, x1, linen)

    # Original editable abstract relief; no third-party artwork is implied.
    box("ArtOakFrame", (-6.08, 4.69, 4.63), (1.63, 0.04, 0.91), walnut, 0.006)
    box("ArtLinenCanvas", (-6.08, 4.662, 4.63), (1.55, 0.022, 0.83), paint)
    for i, (x, z, r) in enumerate([(-6.53, 4.54, 0.24), (-6.04, 4.70, 0.20), (-5.62, 4.49, 0.16)]):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=(x, 4.637, z))
        ob = bpy.context.object
        ob.name = "V4_OriginalRelief_" + str(i)
        ob.scale = (r, 0.015, r)
        ob.data.materials.append(stone if i != 1 else brass)
        for p in ob.data.polygons:
            p.use_smooth = True

    # Replace the room's invisible ceiling fill with daylight and practical fixtures.
    for o in bpy.data.objects:
        if o.type == "LIGHT":
            o.hide_render = True
    world = bpy.data.worlds.new("V4_PhysicalDaylight")
    world.use_nodes = True
    nt = world.node_tree
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(32)
    sky.sun_rotation = math.radians(210)
    sky.sun_disc = False
    nt.links.new(sky.outputs["Color"], nt.nodes["Background"].inputs["Color"])
    nt.nodes["Background"].inputs["Strength"].default_value = 0.28
    scene.world = world
    for i, x in enumerate((-6.425, -4.16, -1.935)):
        area("WindowDaylight_" + str(i), (x, 0.30, 4.51), (x + 0.35, 3.2, 3.8), 170, 1.35, (0.83, 0.91, 1))
    sun = bpy.data.lights.new("V4_Sun", "SUN")
    sun.energy = 1.6
    sun.angle = math.radians(5)
    sun.color = (1, 0.88, 0.70)
    sun_ob = bpy.data.objects.new(sun.name, sun)
    scene.collection.objects.link(sun_ob)
    sun_ob.rotation_euler = Vector((0.2, 0.75, -1)).to_track_quat("-Z", "Y").to_euler()
    for i, (x, y) in enumerate([(-6, 2.3), (-4.6, 3.6), (-1.25, 2.6), (-1.25, 4)]):
        box("DownlightTrim", (x, y, 5.575), (0.11, 0.11, 0.012), paint, 0.01)
        area("Downlight_" + str(i), (x, y, 5.56), (x, y, 2.96), 12, 0.10)
    area("DiningPendant", (-2.94, 2.60, 4.77), (-2.94, 2.60, 3.7), 22, 0.25)
    d = bpy.data.lights.new("V4_PaperColumnGlow", "POINT")
    d.energy = 7
    d.color = (1, 0.73, 0.42)
    d.shadow_soft_size = 0.12
    glow = bpy.data.objects.new(d.name, d)
    scene.collection.objects.link(glow)
    glow.location = (-7.27, 3.10, FLOOR + 0.7)

    camera_data = bpy.data.cameras.new("V4_SalonCamera")
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    camera.location = (-1.30, 0.97, 4.51)
    target = Vector((-5.08, 3.12, 4.27))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.lens = 27
    camera_data.sensor_width = 36
    camera_data.clip_start = 0.05
    camera_data.clip_end = 200
    scene.camera = camera
    assert ROOMS[ROOM] == (-7.545, -0.20500000000000007, 0.27, 4.79, 2.93, 5.62) or (
        abs(ROOMS[ROOM][0] + 7.545) < 1e-7 and abs(ROOMS[ROOM][1] + 0.205) < 1e-7)
    after = {name: geometry_hash(bpy.data.objects[name]) for name in preserved}
    assert after == preserved, "Original architecture or another room's mesh changed"
    missing = []
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
        elif image.source == "FILE" and not image.packed_file and not Path(bpy.path.abspath(image.filepath)).is_file():
            missing.append(image.filepath)
    assert not missing, missing
    uv_objects = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("V4_")]
    uv_objects += [shell, partitions, ceiling]
    for o in uv_objects:
        layer = o.data.uv_layers.active or o.data.uv_layers.new(name="PhysicalMetres")
        for poly in o.data.polygons:
            axis = max(range(3), key=lambda i: abs(poly.normal[i]))
            axes = [(1, 2), (0, 2), (0, 1)][axis]
            for li in poly.loop_indices:
                p = o.matrix_world @ o.data.vertices[o.data.loops[li].vertex_index].co
                layer.data[li].uv = (p[axes[0]], p[axes[1]])

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 192
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.time_limit = 1200
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 10
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 8
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -0.40
    scene.render.film_transparent = False
    scene.render.filepath = str(OUT / "salon_v4_1920x1080.png")
    bpy.ops.file.pack_all()
    # Actual final camera and render settings are saved before the single still.
    scene_file = OUT / "salon_v4_editable.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_file))
    started = time.monotonic()
    bpy.ops.render.render(write_still=True)
    elapsed = time.monotonic() - started
    report = {"room": ROOM, "image": "salon_v4_1920x1080.png", "scene": scene_file.name,
              "source_commit": __import__("os").environ.get("GITHUB_SHA"),
              "models": REPORT, "materials": MATERIAL_REPORT,
              "settings": {"engine": "Cycles", "device": "CPU", "resolution": [1920, 1080],
                           "maximum_samples": 192, "adaptive_threshold": 0.02,
                           "time_limit_seconds": 1200, "denoising": True,
                           "elapsed_render_seconds": elapsed, "camera_lens_mm": 27,
                           "camera_eye_height_m": 1.58},
              "preserved_original_meshes": len(preserved),
              "preserved_geometry_sha256": preserved,
              "missing_images": missing,
              "limits": ["Concept model; the private four-page source PDF is not available in this checkout.",
                         "No changes to plan.py or architecture.py. Finishes, furnishings and light fittings are inferred staging.",
                         "Only selected V4 models tested in Blender. Material maps are 1K/2K source assets.",
                         "Single 1080p still with time-bounded CPU Cycles and denoising; no claim of photorealism.",
                         "Original non-target rooms are preserved. Their illumination changes with the study world. No LUXORIA website changes."]}
    (OUT / "asset_report.json").write_text(json.dumps(report, indent=2))
    print("SALON_RENDER_OK", elapsed, "seconds", len(REPORT), "model instances", flush=True)


if __name__ == "__main__":
    main()
