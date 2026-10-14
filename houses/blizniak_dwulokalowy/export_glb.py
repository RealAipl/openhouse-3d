"""Export the actual four-apartment Blender scene to browser-ready glTF GLB.

This exports real geometry, not Cycles appearance. Procedural shaders can look
different in WebGL; use the Cycles MP4 for photorealistic presentation.
"""
import json
import sys
from pathlib import Path
import bpy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
from houses.blizniak_dwulokalowy import plan, house

OUT=HERE/"output"/"export"
OUT.mkdir(parents=True,exist_ok=True)
target=OUT/"blizniak_4_lokale.glb"
bpy.ops.export_scene.gltf(filepath=str(target),export_format="GLB",export_cameras=True)
assert target.exists() and target.stat().st_size>50_000
with target.open("rb") as fp:
    assert fp.read(4)==b"glTF"

details={
  "name":"Blizniak 4 lokale / twin house",
  "source":"Four-page conceptual architectural PDF, geometry interpreted by assistant",
  "precision":"CONCEPTUAL - verify partitions and wall-opening positions against original drawings",
  "rooms":[],
  "cameras":{},
  "apartment_count":4,
  "staircases":2
}
for key,b in plan.ROOMS.items():
    m=plan.ROOM_META[key]
    details["rooms"].append({"id":key,"segment":m["segment"],"level":m["level"],
                             "name":m["name"],"source_pdf_area_m2":m["area_pdf_m2"],
                             "approx_bounds_m":b})
for name,(loc,tgt,lens) in house.CAMS.items():
    details["cameras"][name]={"position_m":loc,"look_at_m":tgt,"lens_mm":lens}
(OUT/"model_metadata.json").write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding="utf-8")
print("GLB generated:",target,target.stat().st_size,"bytes")
