"""Finish the existing four-unit scene without changing the architectural layout."""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import bpy
from mathutils import Vector

from . import client_interiors as c

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'houses/blizniak_dwulokalowy/output/refined'
BASE=ROOT/'tmp/repair/original.blend'


def principled(m):
    return next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')


def tint(m,color):
    nt=m.node_tree;p=principled(m);socket=p.inputs['Base Color']
    if socket.is_linked:
        original=socket.links[0].from_socket
        node=nt.nodes.new('ShaderNodeMixRGB');node.blend_type='MULTIPLY';node.inputs[0].default_value=1
        node.inputs[2].default_value=(*color,1)
        nt.links.new(original,node.inputs[1]);nt.links.new(node.outputs[0],socket)
    else:socket.default_value=(*color,1)
    m.diffuse_color=(*color,1)


def finish(name,color,rough=.5,metal=0,scale=160,bump=.0003):
    m=c.mat('Finished '+name,color,rough,metal);n=m.node_tree.nodes;l=m.node_tree.links;p=principled(m)
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=scale;tex.inputs['Detail'].default_value=2
    b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.25;b.inputs['Distance'].default_value=bump
    l.new(tex.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],p.inputs['Normal'])
    return m


def assign(ob,m):
    ob.data=ob.data.copy();ob.data.materials.clear();ob.data.materials.append(m)
    if not ob.data.uv_layers and any(n.type=='TEX_IMAGE' for n in m.node_tree.nodes):
        layer=ob.data.uv_layers.new(name='Metres')
        for p in ob.data.polygons:
            ax=max(range(3),key=lambda i:abs(p.normal[i]));a,b=[(1,2),(0,2),(0,1)][ax]
            for li in p.loop_indices:
                co=ob.data.vertices[ob.data.loops[li].vertex_index].co;layer.data[li].uv=(co[a],co[b])


def remove_named(*names):
    prefix=c.ROOM+'_'
    for ob in list(bpy.data.objects):
        if any(ob.name.startswith(prefix+n) for n in names):bpy.data.objects.remove(ob,do_unlink=True)


def curve(name,points,radius,material):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.resolution_u=16;data.bevel_depth=radius;data.bevel_resolution=4
    sp=data.splines.new('BEZIER');sp.bezier_points.add(len(points)-1)
    for p,co in zip(sp.bezier_points,points):p.co=c.point(*co);p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    ob=bpy.data.objects.new(c.ROOM+'_'+name,data);c.collection('Lokal_'+c.SEG+'_'+c.LEVEL).objects.link(ob);ob['room']=c.ROOM;data.materials.append(material)
    return ob


def bowl(name,center,loops,material):
    verts=[]
    for rx,ry,z in loops:
        for i in range(64):
            a=2*math.pi*i/64
            x=math.copysign(abs(math.cos(a))**.30,math.cos(a))*rx
            y=math.copysign(abs(math.sin(a))**.30,math.sin(a))*ry
            verts.append(c.point(center[0]+x,center[1]+y,z))
    faces=[]
    for j in range(len(loops)-1):
        for i in range(64):faces.append((j*64+i,j*64+(i+1)%64,(j+1)*64+(i+1)%64,(j+1)*64+i))
    faces.append(tuple((len(loops)-1)*64+i for i in reversed(range(64))))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(material)
    ob=bpy.data.objects.new(c.ROOM+'_'+name,mesh);c.collection('Lokal_'+c.SEG+'_'+c.LEVEL).objects.link(ob);ob['room']=c.ROOM
    for p in mesh.polygons:p.use_smooth=True
    return ob


def stone_material():
    m=finish('warm grey quartz',(.40,.39,.36),.28,scale=320,bump=.00015)
    nt=m.node_tree;n=nt.nodes;l=nt.links;p=principled(m)
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=4.2;noise.inputs['Detail'].default_value=5;noise.inputs['Roughness'].default_value=.65
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.24;ramp.color_ramp.elements[0].color=(.25,.24,.22,1)
    ramp.color_ramp.elements[1].position=.72;ramp.color_ramp.elements[1].color=(.52,.50,.46,1)
    l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],p.inputs['Base Color'])
    return m


def limestone(m):
    n=m.node_tree.nodes;l=m.node_tree.links;p=principled(m)
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=110;tex.inputs['Detail'].default_value=3
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.32,.315,.29,1);ramp.color_ramp.elements[1].color=(.52,.50,.46,1)
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.0008
    l.new(tex.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],p.inputs['Base Color']);l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal']);p.inputs['Roughness'].default_value=.62


def entrance_details():
    if c.LEVEL=='upper':
        c.box('Entry handle rose',(-.177,8.62,1.0),(.018,.045,.13),'steel',.004)
        c.tube('Entry lever',(-.16,8.62,1.01),(-.16,8.48,1.01),.009,'steel')
    else:
        c.box('Entry handle rose',(3.00,9.20,1.0),(.045,.018,.13),'steel',.004)
        c.tube('Entry lever',(3.00,9.18,1.01),(2.86,9.18,1.01),.009,'steel')


def kitchen_details():
    # A real opening and a three-dimensional bowl replace the old flat inset.
    remove_named('Sink rim','Sink dark interior','Kitchen tap')
    top=next(o for o in bpy.data.objects if o.name==c.ROOM+'_Continuous stone worktop')
    cutter=c.box('temporary sink opening',(5.95,4.54,.90),(.48,.37,.16),'dark',.035)
    bpy.context.view_layer.objects.active=cutter
    bpy.ops.object.modifier_apply(modifier=cutter.modifiers[0].name)
    mod=top.modifiers.new('Actual recessed basin opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.context.view_layer.objects.active=top;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    bowl('Recessed brushed steel sink',(5.95,4.54),[(.27,.215,.915),(.238,.183,.914),(.20,.14,.748),(.16,.10,.744)],c.M['steel'])
    c.sphere('Sink waste',(5.95,4.54,.748),(.055,.055,.004),'dark')
    curve('Curved mixer spout',[(6.0,4.78,.915),(6.0,4.78,1.18),(6.0,4.73,1.28),(6.0,4.61,1.28),(6.0,4.52,1.17)],.012,c.M['steel'])
    c.tube('Mixer control',(6.05,4.78,.93),(6.05,4.78,1.05),.009,'steel')
    for i in range(5):
        u=4.20+i*.60
        for z in (.34,.60):c.box('Drawer reveal',(u,4.224,z),(.582,.006,.004),'dark',.0005)
    for i in range(3):
        yy=3+i*.60
        for z in (.34,.60):c.box('Party drawer reveal',(6.646,yy,z),(.006,.578,.004),'dark',.0005)
    c.box('Oven control fascia',(6.637,3.31,.804),(.018,.54,.082),'blackglass',.004)
    for yy in (3.12,3.49):c.sphere('Oven rotary control',(6.617,yy,.805),(.025,.038,.038),'steel')
    for yy in (3.025,3.595):c.box('Oven edge',(6.635,yy,.49),(.018,.009,.50),'dark',.002)
    c.box('Freezer split',(6.675,2.20,.81),(.010,.72,.005),'dark',.001)
    for z,h in ((.55,.35),(1.43,.83)):
        c.tube('Fridge satin pull',(6.65,2.47,z-h/2),(6.65,2.47,z+h/2),.008,'steel')
    for u in (4.30,6.45):
        c.box('Double socket face',(u,4.899,1.18),(.135,.018,.075),'cabinet',.006)
        for du in (-.031,.031):c.box('Socket insert',(u+du,4.886,1.18),(.038,.007,.038),'dark',.009)
    # Table settings make the compact dining area a furnished space.
    upper=c.LEVEL=='upper';u,y=(5.25,1.67) if upper else (5.95,1.33)
    for delta in (-.43,.43):
        pos=(u,y+delta) if upper else (u+delta,y)
        c.sphere('Woven place mat',(*pos,.755),(.34,.32,.006),'cloth')
        bowl('Stoneware plate',pos,[(.125,.125,.763),(.113,.113,.778),(.097,.097,.766)],c.M['ceramic'])
    bowl('Low dining vessel',(u,y),[(.07,.07,.76),(.10,.10,.825),(.105,.105,.826),(.083,.083,.785)],c.M['ceramic'])


def build():
    OUT.mkdir(parents=True,exist_ok=True);bpy.ops.wm.open_mainfile(filepath=str(BASE));c.COLLECTIONS.clear()
    walls={o.name:hashlib.sha256(repr([(tuple(v.co)) for v in o.data.vertices]).encode()).hexdigest() for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('BLI_')}
    keys={'white':'Soft white walls','ceiling':'White ceiling','grey':'Light grey feature wall','cabinet':'Warm white cabinetry','oak':'Walnut PBR CC0 V2','floor':'Natural oak PBR CC0 V2','stone':'Honed pale stone','bathstone':'Light limestone bathroom','grout':'Fine pale grout','taupe':'Calm taupe','linen':'Ivory linen','dark':'Charcoal metal','metal':'Brushed satin metal','porcelain':'White porcelain','blackglass':'Smoked appliance glass','mirror':'Silver mirror','glass':'Clear glass'}
    c.M={k:bpy.data.materials['WNETRZA_'+v] for k,v in keys.items()}
    c.M.update({'upper':finish('cashmere lacquer',(.40,.365,.31),.35),'joinery':finish('warm greige joinery',(.29,.275,.245),.42),'fridge':finish('satin graphite appliance',(.13,.15,.15),.29,.55),'steel':finish('brushed nickel',(.50,.53,.55),.23,1,scale=600,bump=.00008),'cloth':finish('woven taupe linen',(.23,.19,.15),.9,scale=900,bump=.0007),'olive':finish('muted olive wool',(.15,.18,.125),.9,scale=800,bump=.0006),'ceramic':finish('warm glazed stoneware',(.48,.43,.35),.23,scale=400,bump=.00005),'quartz':stone_material()})
    limestone(c.M['bathstone'])
    # Preserve all existing packed PBR maps, but recover readable tonal differences.
    for m in bpy.data.materials:
        if m.name.startswith('Oatmeal |'):tint(m,(.57,.53,.46))
        elif m.name.startswith(('Cotton | warm','Ivory | woven')):tint(m,(.70,.62,.49))
        elif m.name.startswith('Textile | original'):tint(m,(.09,.075,.055))
        elif m.name.startswith('Upholstery | matching'):tint(m,(.075,.06,.045))
        if m.name.startswith(('Textile |','Upholstery | matching','Oatmeal |','Cotton |','Ivory | woven')):
            p=principled(m)
            for name,value in [('Roughness',.85),('Metallic',0),('Specular IOR Level',.25)]:
                for link in list(p.inputs[name].links):m.node_tree.links.remove(link)
                p.inputs[name].default_value=value
    tint(c.M['linen'],(.53,.49,.42));tint(c.M['taupe'],(.28,.24,.19))
    principled(c.M['blackglass']).inputs['Base Color'].default_value=(.003,.005,.007,1)
    principled(c.M['blackglass']).inputs['Roughness'].default_value=.17
    for ob in list(bpy.data.objects):
        if ob.type!='MESH':continue
        if any(t in ob.name for t in ['White upper cabinet']):assign(ob,c.M['upper'])
        elif any(t in ob.name for t in ['Wardrobe','Coat cupboard','open door leaf']) and 'pull' not in ob.name:assign(ob,c.M['joinery'])
        elif 'Integrated fridge' in ob.name:assign(ob,c.M['fridge'])
        elif any(t in ob.name for t in ['worktop','backsplash']):assign(ob,c.M['quartz'])
        elif 'Linen curtain' in ob.name:assign(ob,c.M['cloth'])
        elif ob.name=='BLI_External_Entry_Doors':assign(ob,c.M['oak'])
    # Refined detail and restrained color, duplicated in all four existing flats.
    for seg in ('A','B'):
        for level,z in [('ground',0),('upper',2.93)]:
            c.SEG=seg;c.LEVEL=level;c.Z=z;c.ROOM=seg+'_'+level+('_6' if level=='ground' else '_5')
            kitchen_details()
            c.ROOM=seg+'_'+level+'_1';entrance_details()
    for name,digest in walls.items():
        ob=bpy.data.objects[name];assert hashlib.sha256(repr([tuple(v.co) for v in ob.data.vertices]).encode()).hexdigest()==digest,name
    s=bpy.context.scene;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.38
    s.view_settings.exposure=-.35;s.view_settings.look='AgX - Medium High Contrast'
    s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.adaptive_threshold=.025;s.cycles.use_denoising=True
    s.render.threads_mode='FIXED';s.render.threads=8
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Wnetrza_4_lokale.blend'),compress=True)
    report={'architectural_geometry_unchanged':True,'source_blend_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'packed_images':sum(bool(i.packed_file) for i in bpy.data.images),'unassigned_meshes':[o.name for o in bpy.data.objects if o.type=='MESH' and not len(o.data.materials)],'material_count':len(bpy.data.materials),'changes':['Warm grey quartz and restrained cashmere/greige joinery','Textured and toned upholstery and bedding','Real cut sink opening with a recessed metal bowl and curved tap','Appliance controls, drawer reveals, sockets and handles','Dining stoneware and controlled textile finishes','Architectural shell preserved in all four units']}
    (OUT/'KOREKTA_WYKONCZEN.json').write_text(json.dumps(report,indent=2));print('FINISH_OK',report,flush=True)


def render(views,scale=100):
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Wnetrza_4_lokale.blend'));s=bpy.context.scene;s.render.resolution_percentage=scale;s.cycles.samples=64
    folder=OUT/('Obrazy' if scale==100 else 'Kontrola');folder.mkdir(exist_ok=True)
    for view in views:
        s.cycles.time_limit=(120 if view.startswith(('11_','12_')) else 210) if scale==100 else 40
        level=next(v[1] for v in c.VIEWS if v[0]==view);s.camera=bpy.data.objects['A_'+view]
        for key in ['A_ground','A_upper','B_ground','B_upper']:bpy.data.collections['Lokal_'+key].hide_render=key!='A_'+level
        s.render.filepath=str(folder/(view+'.png'));t=time.monotonic();bpy.ops.render.render(write_still=True);print('RENDER_OK',view,time.monotonic()-t,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build',action='store_true');p.add_argument('--views',default='none');p.add_argument('--scale',type=int,default=100);a=p.parse_args()
    if a.build:build()
    if a.views!='none':render(a.views.split(','),a.scale)
