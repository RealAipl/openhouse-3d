"""Stage one full salon with actual Poly Haven CC0 models, then save and render.

Run after OpenHouse generated a .blend. This does not touch other apartments.
All scene content remains conceptual; not a CAD-verified reconstruction.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from houses.blizniak_dwulokalowy.plan import ROOMS

HERE=Path(__file__).resolve().parent
PACK=ROOT/"tmp"/"polyhaven-household-pack"
OUT=HERE/"output"/"polyhaven_test"
OUT.mkdir(parents=True,exist_ok=True)
MODEL_ROOT=PACK/"models"
EXPECTED_LICENSE="CC0 1.0"
ROOM="A_upper_5"
B=ROOMS[ROOM]
PLACEMENTS = [
    # slug, centre X,Y, world Z (floor/upper), visual width, rotation degrees
    ("sofa_03",                 -5.10,2.90,2.96,2.13, 180),
    ("modern_coffee_table_02", -4.70,1.65,2.96,1.00, 0),
    ("modern_arm_chair_01",     -6.43,3.75,2.96,.72, -25),
    ("dining_table",            -2.50,2.15,2.96,1.45, 90),
    ("dining_chair_02",         -2.52,1.18,2.96,.54, 0),
    ("potted_plant_01",        -6.72,4.18,2.96,.50, 0),
    ("modern_wooden_cabinet",   -1.34,3.72,2.96,1.30, 0),
    ("desk_lamp_arm_01",       -1.37,3.70,3.72,.38, 25),
    ("ceramic_vase_02",        -2.30,2.07,3.74,.18, 0),
]

def append_blend_asset(slug, location, target_width, angle):
    p=MODEL_ROOT/slug/(slug+".blend")
    if not p.exists():
        raise FileNotFoundError(f"Real Blender furniture model missing: {p}")
    # Poly Haven 1k .blend may store collection(s) and meshes under multiple parents.
    with bpy.data.libraries.load(str(p),link=False) as (source, target):
        target.objects=[n for n in source.objects if n]
    assets=[o for o in target.objects if o is not None]
    if not any(o.type=="MESH" for o in assets):
        raise ValueError(f"No mesh objects inside {p}")
    collection=bpy.data.collections.new("PH_CC0_"+slug)
    bpy.context.scene.collection.children.link(collection)
    for obj in assets:
        if obj.name not in collection.objects:
            collection.objects.link(obj)
    bpy.context.view_layer.update()
    meshes=[o for o in assets if o.type=="MESH"]
    points=[obj.matrix_world @ Vector(pt) for obj in meshes for pt in obj.bound_box]
    lo=Vector([min(v[i] for v in points) for i in range(3)])
    hi=Vector([max(v[i] for v in points) for i in range(3)])
    length=max(hi.x-lo.x,hi.y-lo.y)
    if length<.01 or length>1000:
        raise ValueError(f"Invalid mesh dimensions {slug}: {tuple(hi-lo)}")
    scale=target_width/length
    if not .01<scale<100:
        raise ValueError(f"Invalid scale {slug}: {scale}")
    anchor=bpy.data.objects.new("PH_Anchor_"+slug,None)
    bpy.context.scene.collection.objects.link(anchor)
    roots=[o for o in assets if o.parent not in assets]
    root_world={o:o.matrix_world.copy() for o in roots}
    for obj in roots:
        obj.parent=anchor
        obj.matrix_world=root_world[obj]
    origin=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    anchor.matrix_world=(Matrix.Translation(Vector(location)) @
                         Matrix.Rotation(math.radians(angle),4,"Z") @
                         Matrix.Scale(scale,4) @ Matrix.Translation(-origin))
    anchor["asset_source"]="https://polyhaven.com/a/"+slug
    anchor["asset_license"]="CC0"
    anchor["room"]=ROOM
    bpy.context.view_layer.update()

    # Material textures are external relative to their original source model.
    for obj in meshes:
        for mat in obj.data.materials:
            if not mat or not mat.use_nodes:continue
            for node in mat.node_tree.nodes:
                if node.type!="TEX_IMAGE" or not node.image: continue
                img=node.image
                original=Path(bpy.path.abspath(img.filepath)).name
                replacement=MODEL_ROOT/slug/"textures"/original
                if not replacement.exists():
                    # Poly Haven's 1K bundle sometimes retains references to the
                    # model author's original 8K filenames in the .blend.
                    # Resolve by semantic map channel + material component.
                    original_stem=original.lower().replace("roughness","rough")
                    candidates=list((MODEL_ROOT/slug/"textures").glob("*"))
                    kind=next((k for k in ("rough","diff","nor","metal","opacity","alpha","mask","spec")
                               if k in original_stem),None)
                    if kind=="opacity":kind="alpha"
                    segment=next((k for k in ("base","wood","legs","pillow","pot","leaves","fabric","glass")
                                  if k in original_stem),None)
                    ranked=[]
                    for image_path in candidates:
                        stem=image_path.stem.lower()
                        if kind is None or kind not in stem:continue
                        score=(10 if segment and segment in stem else 0)
                        score+=sum(1 for token in original_stem.split("_") if len(token)>3 and token in stem)
                        ranked.append((score,image_path))
                    if ranked:
                        replacement=sorted(ranked,key=lambda a:(-a[0],a[1].name))[0][1]
                        print(f"PBR remap ({slug}): {original} -> {replacement.name}",flush=True)
                    elif img.packed_file is not None:
                        continue
                    else:
                        # The official 1K distribution intentionally omits some
                        # AO / displacement / 8K-only optional maps. Use a neutral
                        # 1x1 texture (not a magenta missing-image placeholder).
                        channel=kind or "ao"
                        neutral_name="PH_Neutral_"+channel
                        neutral=bpy.data.images.get(neutral_name)
                        if neutral is None:
                            neutral=bpy.data.images.new(neutral_name,width=1,height=1,alpha=True)
                            color = (1,1,1,1) if channel=="ao" else (
                                    (.5,.5,1,1) if channel=="nor" else (
                                    (0,0,0,1) if channel=="metal" else (.65,.65,.65,1)))
                            neutral.pixels[:]=color
                            neutral.pack()
                        node.image=neutral
                        print(f"PBR optional missing ({slug}): {original} -> neutral {channel}",flush=True)
                        continue
                img.filepath=str(replacement)
                img.reload()
    return {
       "id":slug,"meshes":len(meshes),"scale":round(scale,5),
       "source_dims":[round(float(x),3) for x in hi-lo],
       "target":list(location),
    }

def new_area_light(name,position,energy,size,target):
    data=bpy.data.lights.new(name,"AREA")
    data.energy=energy
    data.shape="DISK"
    data.size=size
    ob=bpy.data.objects.new(name,data)
    bpy.context.scene.collection.objects.link(ob)
    ob.location=position
    direction=Vector(target)-ob.location
    ob.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
    return ob

def add_kitchen():
    # Retain kitchen cabinetry after replacing the merged parametric salon object.
    from archviz.mesh import MB
    unit=MB()
    x0,x1=-1.06,-.39
    for y0,y1 in ((1.02,2.00),(2.06,3.02),(3.08,4.02)):
        unit.box(x0,x1,y0,y1,2.96,3.81,mi=0)
        unit.box(x0-.035,x1+.020,y0-.035,y1+.035,3.81,3.86,mi=1)
    unit.box(x0,x1,1.02,4.04,4.44,5.12,mi=0)
    cabinet=bpy.data.materials.get("BliZniak_Cabinets")
    stone=bpy.data.materials.get("BliZniak_Slabs")
    assert cabinet is not None and stone is not None
    unit.build("PH_RetainedKitchen_A_upper_5",[cabinet,stone])

def main():
    manifest=json.loads((PACK/"manifest.json").read_text(encoding="utf-8"))
    if manifest["license"]!=EXPECTED_LICENSE or manifest["item_count"]<20:
        raise ValueError("Unknown licence or incomplete Poly Haven bundle")
    existing={a["id"] for a in manifest["models"]}
    assert {p[0] for p in PLACEMENTS}.issubset(existing)
    old=bpy.data.objects.get("BLI_Furniture_A_upper_5")
    if old is None:raise ValueError("Procedural salon object not found: wrong Blender scene?")
    bpy.data.objects.remove(old,do_unlink=True)

    add_kitchen()
    report=[]
    for slug,x,y,z,w,rot in PLACEMENTS:
        report.append(append_blend_asset(slug,(x,y,z),w,rot))
    loaded=[o for o in bpy.data.objects if o.name.startswith("PH_Anchor_")]
    assert len(loaded)==len(PLACEMENTS)
    assert sum(x["meshes"] for x in report)>len(PLACEMENTS)

    # Existing ceiling can mute sunlight in proof renders.
    new_area_light("PH_CeilingSoftbox_1",(-4.6,2.40,5.46),420,2.7,(-4.1,2.3,3.12))
    new_area_light("PH_CeilingSoftbox_2",(-2.1,3.20,5.48),240,2.1,(-2.2,2.2,3.20))
    scene=bpy.context.scene
    camera=bpy.data.objects.get("Cam_room_A_upper_5")
    assert camera is not None
    scene.camera=camera
    scene.render.engine="CYCLES"
    scene.cycles.samples=48
    scene.cycles.use_denoising=True
    scene.render.resolution_x=1280
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.view_settings.view_transform="AgX"
    scene.view_settings.look="AgX - Medium High Contrast"
    scene.render.image_settings.file_format="PNG"
    # Use existing Cycles illumination, HDRI/world and corrected room camera.
    scene.render.filepath=str(OUT/"salon_A_pietro_polyhaven_CC0.png")
    # Blender library-load can leave dangling 8K images as orphan datablocks.
    # They are not used by the 1K scene, but pack_all would still try to read them.
    for image in list(bpy.data.images):
        if image.users==0:
            bpy.data.images.remove(image)
    dangling=[]
    for image in bpy.data.images:
        if image.source=="FILE" and not image.packed_file and not Path(bpy.path.abspath(image.filepath)).exists():
            dangling.append((image.name,image.users,image.filepath))
    if dangling:
        raise ValueError("Unresolved source images after 1K remapping: "+repr(dangling[:12]))
    bpy.ops.file.pack_all()
    scene_file=OUT/"blizniak_salon_A_polyhaven_CC0.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_file))
    bpy.ops.render.render(write_still=True)
    image=OUT/"salon_A_pietro_polyhaven_CC0.png"
    if not image.exists() or image.stat().st_size<30000:
        raise RuntimeError("Missing or undersized proof render")
    report_file=OUT/"model_import_report.json"
    report_file.write_text(json.dumps({"license":"CC0 1.0","provider":"Poly Haven",
         "room":ROOM,"models":report,"proof_render":str(image),
         "note":"concept room; CAD fidelity unverified"},indent=2),encoding="utf8")
    print("PROOF_OK",image,scene_file,"real household models",len(loaded))
if __name__=="__main__":main()
