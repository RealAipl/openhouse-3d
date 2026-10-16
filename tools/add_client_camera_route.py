"""Keep the actual captured 3D camera route editable in the delivered Blender scene."""
import json
import math
import os
from pathlib import Path
import bpy
from mathutils import Quaternion

root=Path.cwd();out=root/'houses/blizniak_dwulokalowy/output/refined'
p=out/'Wnetrza_4_lokale.blend';poses=json.loads((root/'tmp/repair/walk-frames/camera.json').read_text());assert len(poses)==120
bpy.ops.wm.open_mainfile(filepath=str(p))
old=bpy.data.objects.get('Spacer_3D_A2')
if old:bpy.data.objects.remove(old,do_unlink=True)
data=bpy.data.cameras.new('Spacer_3D_A2');cam=bpy.data.objects.new(data.name,data);bpy.context.scene.collection.objects.link(cam)
data.sensor_width=36;data.lens=(36/(16/9))/(2*math.tan(math.radians(67/2)));data.clip_start=.045;data.clip_end=60
cam.rotation_mode='QUATERNION';conversion=Quaternion((1,0,0),math.pi/2)
for i,pose in enumerate(poses):
 x,y,z=pose['position'];q=pose['quaternion'];cam.location=(x,-z,y);cam.rotation_quaternion=conversion@Quaternion((q[3],q[0],q[1],q[2]));frame=i*2+1
 cam.keyframe_insert(data_path='location',frame=frame);cam.keyframe_insert(data_path='rotation_quaternion',frame=frame)
s=bpy.context.scene;s.camera=cam;s.render.fps=24;s.frame_start=1;s.frame_end=240;s.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(p),compress=True);print('EDITABLE_CAMERA_ROUTE_OK',len(poses),flush=True);os._exit(0)
