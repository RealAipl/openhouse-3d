import bpy,json,hashlib,sys
from pathlib import Path
from mathutils import Vector
root=Path.cwd();sys.path.insert(0,str(root));from houses.blizniak_dwulokalowy import plan
out=root/'houses/blizniak_dwulokalowy/output/refined'
def architectural_fingerprints():
 return {o.name:hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])).encode()).hexdigest() for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('BLI_')}
bpy.ops.wm.open_mainfile(filepath=str(root/'tmp/repair/original.blend'));before=architectural_fingerprints()
bpy.ops.wm.open_mainfile(filepath=str(out/'Wnetrza_4_lokale.blend'));after=architectural_fingerprints();assert before==after
missing=[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file and not Path(bpy.path.abspath(i.filepath)).is_file()];assert not missing
unassigned=[o.name for o in bpy.data.objects if o.type=='MESH' and (not len(o.data.materials) or any(m is None for m in o.data.materials))];assert not unassigned
assert len(plan.ROOMS)==24
counts={k:len(bpy.data.collections['Lokal_'+k].objects) for k in ['A_ground','A_upper','B_ground','B_upper']}
result={'unit_object_counts':counts,'mesh_object_count':sum(o.type=='MESH' for o in bpy.data.objects),'architectural_meshes_unchanged':True,'architectural_mesh_count':len(before),'packed_images':sum(bool(i.packed_file) for i in bpy.data.images),'missing_images':missing,'unassigned_meshes':unassigned,'rooms':24,'units':['A_ground','A_upper','B_ground','B_upper'],'blend_sha256':hashlib.sha256((out/'Wnetrza_4_lokale.blend').read_bytes()).hexdigest(),'camera_count':sum(o.type=='CAMERA' for o in bpy.data.objects),'camera_route':None}
poses_path=root/'tmp/repair/walk-frames/camera.json'
if poses_path.exists():
 poses=json.loads(poses_path.read_text());s=bpy.context.scene;deps=bpy.context.evaluated_depsgraph_get();hits=[]
 assert len(poses)==480
 assert len({tuple(p['position']) for p in poses})==len(poses)
 assert s.frame_end==len(poses) and s.render.fps==24
 camera=bpy.data.objects['Spacer_3D_A2']
 assert camera.animation_data and camera.animation_data.action
 for i,pose in enumerate(poses):
  a=pose['position'];p=Vector((a[0],-a[2],a[1]));assert abs(p.z-(2.93+1.55))<.01
  s.frame_set(i+1);assert (camera.location-p).length<1e-5
  for z in (.35,1.0,1.55):
   origin=Vector((p.x,p.y,2.93+z))
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(.7,.7),(.7,-.7),(-.7,.7),(-.7,-.7)]:
    hit,loc,normal,index,obj,matrix=s.ray_cast(deps,origin,Vector((dx,dy,0)).normalized(),distance=.18)
    if hit:hits.append({'frame':i,'object':obj.name,'height':z})
 assert not hits,hits[:8]
 result['camera_route']={'positions':len(poses),'swept_clearance_m':.18,'collision_hits':hits,'geometry_based':True}
(out/'KONTROLA_KOREKTY.json').write_text(json.dumps(result,indent=2));print('REFINEMENT_CHECK',json.dumps(result),flush=True)
import os;os._exit(0)
