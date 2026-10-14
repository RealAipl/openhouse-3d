"""Place legitimately downloaded Blendkit (BlenderKit) furniture into the twin house.

Run *inside Blender* on an existing .blend scene:
 blender -b scene.blend --python houses/blizniak_dwulokalowy/import_blendkit_models.py \
    -- --manifest /private/placements.json --asset-dir /private/blendkit-downloads \
       --output /private/with-blendkit.blend --format film

The addon source is pinned as git submodule vendor/Blendkit; its asset catalogue
is NOT included in the GPL source. Licences belong to individual creators.
Royalty Free content must not be redistributed as raw or extractable GLB.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector, Matrix

def args():
    argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--asset-dir",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--format",choices=["film","model"],default="film")
    return p.parse_args(argv)

def resolve_asset(root:Path, file:str)->Path:
    p=(root/file).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError(f"Path traversal in asset file: {file}")
    if p.suffix.lower()!=".blend" or not p.is_file():
        raise ValueError(f"Missing properly downloaded Blendkit .blend: {p}")
    return p

def validate(row,root,mode):
    for field in ("asset_base_id","name","license","file","source_url","room","kind","location_m","width_m"):
        if field not in row: raise ValueError(f"Asset field missing: {field}")
    if row["room"] not in ("A_upper_5",):
        raise ValueError("Only validated proof-room A_upper_5 is enabled until CAD audit")
    if row["license"] not in ("cc_zero","royalty_free"):
        raise ValueError("Unknown or incompatible asset license")
    if row["license"]=="royalty_free" and mode=="model":
        raise ValueError("Royalty Free raw 3D redistribution is not permitted")
    if row.get("is_free") is not True:
        raise ValueError("Only verified free assets permitted")
    if not str(row["source_url"]).startswith(("https://www.blendkit.com/","https://www.blenderkit.com/")):
        raise ValueError("Source URL must be official Blendkit asset page")
    if row["kind"] not in ("sofa","dining_table","chair","cabinet","kitchen"):
        raise ValueError("Unsupported placement kind")
    if len(row["location_m"])!=3 or any(not isinstance(x,(int,float)) for x in row["location_m"]):
        raise ValueError("location_m must be x,y,z in metres")
    if not 0.4 <= float(row["width_m"]) <= 5.0: raise ValueError("Suspicious size")
    p=resolve_asset(root,row["file"])
    if row.get("sha256"):
        actual=hashlib.sha256(p.read_bytes()).hexdigest()
        if actual!=row["sha256"]:
            raise ValueError(f"Checksum mismatch for {p.name}")
    return p

def append_asset(path:Path, row:dict):
    with bpy.data.libraries.load(str(path), link=False) as (data, out):
        names=[n for n in data.collections if not n.startswith(("Camera","Light"))]
        out.collections=names
    attached=[]
    for collection in out.collections:
        if collection is None: continue
        bpy.context.scene.collection.children.link(collection)
        attached.extend(o for o in collection.all_objects if o.type=="MESH")
    if not attached:
        # Some free Blendkit assets are stored as direct objects, not collections.
        with bpy.data.libraries.load(str(path),link=False) as (data,out):
            out.objects=list(data.objects)
        collection=bpy.data.collections.new("BK_"+row["kind"]+"_"+str(row["asset_base_id"])[:8])
        bpy.context.scene.collection.children.link(collection)
        for obj in out.objects:
            if obj is not None and obj.name not in collection.objects:
                collection.objects.link(obj)
        attached=[o for o in collection.all_objects if o.type=="MESH"]
    if not attached:
        raise ValueError(f"Download contains no mesh: {path.name}")
    objects=set()
    for mesh in attached:
        obj=mesh
        while obj.parent is not None: obj=obj.parent
        objects.add(obj)
    # Source BlenderKit models vary in axis, units, parent empties and transform.
    corners=[obj.matrix_world @ Vector(corner) for obj in attached for corner in obj.bound_box]
    a=Vector([min(v[i] for v in corners) for i in range(3)])
    b=Vector([max(v[i] for v in corners) for i in range(3)])
    current=max(b.x-a.x,b.y-a.y)
    if current<=.0001: raise ValueError(f"Invalid zero-size asset {path.name}")
    factor=float(row["width_m"])/current
    if not .01<=factor<=100: raise ValueError(f"Unexpected source scale {factor}")
    origin=Vector(((a.x+b.x)/2,(a.y+b.y)/2,a.z))
    anchor=bpy.data.objects.new("BK_Anchor_"+row["kind"]+"_"+str(row["asset_base_id"])[:8],None)
    bpy.context.scene.collection.objects.link(anchor)
    old_world={obj:obj.matrix_world.copy() for obj in objects}
    for obj in objects:
        obj.parent=anchor
        obj.matrix_world=old_world[obj]
    target=Vector(row["location_m"])
    angle=math.radians(float(row.get("rotation_z_degrees",0)))
    anchor.matrix_world=(Matrix.Translation(target) @
                         Matrix.Rotation(angle,4,"Z") @
                         Matrix.Scale(factor,4) @
                         Matrix.Translation(-origin))
    anchor["blendkit_asset_id"]=str(row["asset_base_id"])
    anchor["blendkit_license"]=row["license"]
    anchor["blendkit_source_url"]=row["source_url"]
    anchor["not_redistributable_raw"]=(row["license"]=="royalty_free")
    return len(attached),factor

def main():
    opt=args()
    rows=json.loads(Path(opt.manifest).read_text(encoding="utf8"))
    if not isinstance(rows,list) or not rows:
        raise ValueError("Manifest must contain at least one authorized asset")
    asset_root=Path(opt.asset_dir).resolve()
    if not asset_root.is_dir(): raise ValueError(f"Missing asset directory: {asset_root}")
    report=[]
    for row in rows:
        path=validate(row,asset_root,opt.format)
        n,factor=append_asset(path,row)
        report.append({"name":row["name"],"kind":row["kind"],
                       "source_url":row["source_url"],"licence":row["license"],
                       "meshes":n,"scale":round(factor,4)})
    destination=Path(opt.output).resolve();destination.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    result=destination.with_suffix(".asset-report.json")
    result.write_text(json.dumps({"assets":report,"count":len(report),
                                  "model_raw_export_permitted":all(x["licence"]=="cc_zero" for x in report)},
                                 indent=2,ensure_ascii=False))
    print("Imported real BlenderKit assets:",len(report),"in",destination)
if __name__=="__main__": main()
