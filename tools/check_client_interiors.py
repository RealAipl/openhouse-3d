"""Reopen delivery and collect checks from actual Blender objects, not schedules."""
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
from houses.blizniak_dwulokalowy import plan

OUT=ROOT/'houses/blizniak_dwulokalowy/output/final'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Wnetrza_4_lokale.blend'))
scene=bpy.context.scene
missing=[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file and not Path(bpy.path.abspath(i.filepath)).is_file()]
assert not missing, missing
units={key:len(bpy.data.collections['Lokal_'+key].objects) for key in ['A_ground','A_upper','B_ground','B_upper']}
assert min(units.values())>100
cameras=[o for o in scene.objects if o.type=='CAMERA']
assert len(cameras)==28
assert all(not any(s in o.name for s in ['hero','exterior','front_elevation']) for o in cameras)
# Directly test camera origins against the usable room rectangle.
checks=[]
for c in cameras:
 room=c['room'];bb=plan.ROOMS[room];p=c.location
 inside=bb[0]+.025<p.x<bb[1]-.025 and bb[2]+.025<p.y<bb[3]-.025 and bb[4]+.8<p.z<bb[5]-.2
 assert inside,(c.name,tuple(p),bb)
 direction=c.matrix_world.to_quaternion()@Vector((0,0,-1))
 hit,loc,normal,index,obj,matrix=scene.ray_cast(bpy.context.evaluated_depsgraph_get(),p,direction,distance=30)
 distance=(loc-p).length if hit else None
 assert distance is None or distance>.12,(c.name,obj.name,distance)
 checks.append({'camera':c.name,'room':room,'inside_room_bounds':inside,'center_ray_distance_m':distance,'center_object':obj.name if hit else None})
# Export exact lower-face wall footprints for drawing/model overlay.
polys={}
for segment in ['A','B']:
 for level,z in [('ground',0),('upper',2.93)]:
  ob=bpy.data.objects['BLI_Partitions_'+segment+'_'+level]
  parts=[]
  for p in ob.data.polygons:
   if p.normal.z<-.9 and abs(p.center.z-z)<.001:
    parts.append([[float(ob.data.vertices[i].co.x),float(ob.data.vertices[i].co.y)] for i in p.vertices])
  polys[segment+'_'+level]=parts
# Assets must fit within their assigned room; this caught and corrected the
# guest-bed source orientation before final rendering.
asset_bounds=[]
for room in plan.ROOMS:
    keys={o.get('source_asset') for o in scene.objects if o.get('room')==room and o.get('source_asset')}
    for key in keys:
        pts=[o.matrix_world@Vector(v) for o in scene.objects if o.get('room')==room and o.get('source_asset')==key for v in o.bound_box]
        lo=[min(v[i] for v in pts) for i in range(3)];hi=[max(v[i] for v in pts) for i in range(3)]
        bb=plan.ROOMS[room];tol=.04
        ok=lo[0]>=bb[0]-tol and hi[0]<=bb[1]+tol and lo[1]>=bb[2]-tol and hi[1]<=bb[3]+tol
        assert ok,(room,key,lo,hi,bb)
        asset_bounds.append({'room':room,'asset':key,'inside_room':ok,'min':lo,'max':hi})
for level in ['ground','upper']:
    a={tuple(round(v,5) for v in xy) for poly in polys['A_'+level] for xy in poly}
    b={(-round(x,5),round(y,5)) for poly in polys['B_'+level] for x,y in poly}
    assert a==b,level
result={'reopened_blend':True,'mirror_walls_match':True,'asset_bounds_checks':asset_bounds,'packed_images':sum(bool(i.packed_file) for i in bpy.data.images),'missing_images':missing,'unit_object_counts':units,'cameras':checks,'wall_footprints':polys,'wall_materials':list({m.name for o in scene.objects if o.name.startswith('BLI_') for m in o.data.materials}),'original_salon_sha256':hashlib.sha256((ROOT/'tmp/existing/salon_v4_editable.blend').read_bytes()).hexdigest(),'sha256_blend':hashlib.sha256((OUT/'Wnetrza_4_lokale.blend').read_bytes()).hexdigest()}
(OUT/'KONTROLA_PLIKU_BLEND.json').write_text(json.dumps(result,indent=2))
print('PASS: packed scene reopened; 4 furnished units; 28 room-safe cameras; original delivery retained.')
