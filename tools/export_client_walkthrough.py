import bpy,json,time
from pathlib import Path
root=Path.cwd();p=root/'houses/blizniak_dwulokalowy/output/refined/Wnetrza_4_lokale.blend'
bpy.ops.wm.open_mainfile(filepath=str(p))
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
 if o.type in ('MESH','CURVE'):o.select_set(True)
out=root/'tmp/repair/web/scene.glb';out.parent.mkdir(exist_ok=True)
t=time.monotonic();bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_apply=True,export_extras=True,export_cameras=False,export_lights=False,export_image_format='AUTO')
print('EXPORT_OK',out.stat().st_size,time.monotonic()-t,flush=True)
