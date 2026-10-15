"""Client interior delivery, using the existing OpenHouse house and audited V4 assets.

Run with Blender 5.2 bpy: python -m houses.blizniak_dwulokalowy.client_interiors
The architectural source stays private; derived audit records remain explicit.
"""
import argparse
import hashlib
import json
import math
import os
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from archviz.mesh import MB
from . import architecture, interiors, plan

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'houses/blizniak_dwulokalowy/output/final'
PACK = ROOT / 'tmp/salon-v4/pack'
CATALOG = json.loads((ROOT / 'tmp/existing/v4_audit.json').read_text())
ASSETS = {a['id']: a for a in CATALOG['assets']}
CACHE = {}
RECEIPTS = []
COLLECTIONS = {}
M = {}
SEG = 'A'
LEVEL = 'upper'
ROOM = ''
Z = 2.93

SOFA = 'haven-224-oatmeal-two-seat-sofa-40262c27'
CHAIR = 'ember-leather-and-walnut-lounge-chair-9b9f3689'
COFFEE = 'trio-nesting-coffee-table-set-a1a295a4'
DINING = 'span-225-extendable-dining-table-b5cc7e64'
DCHAIR = 'gather-dining-armchair-ee459660'
LAMP = 'paper-column-paper-column-floor-lamp-3b5a06e7'
BED = 'haven-160-upholstered-oak-queen-bed-0d6b78d0'
BED2 = 'harbor-captain-twin-bed-3111b6ce'
VANITY = 'basin-90-freestanding-bathroom-vanity-c58c9ba0'


def collection(name):
    if name not in COLLECTIONS:
        c = bpy.data.collections.get(name)
        if c is None:
            c = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(c)
        COLLECTIONS[name] = c
    return COLLECTIONS[name]


def move(ob, name=None):
    c = collection(name or ('Lokal_' + SEG + '_' + LEVEL))
    for x in list(ob.users_collection):
        x.objects.unlink(ob)
    c.objects.link(ob)
    ob['room'] = ROOM
    return ob


def point(u, y, z):
    return ((-7.545 + u) if SEG == 'A' else (7.545-u), y, Z+z)


def unit_matrix():
    return Matrix.Translation(Vector((-7.545 if SEG == 'A' else 7.545, 0, Z))) @ Matrix.Diagonal((1 if SEG == 'A' else -1, 1, 1, 1))


def mat(name, color, rough=.6, metal=0):
    m = bpy.data.materials.new('WNETRZA_' + name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    return m


def box(name, loc, dims, material='white', bevel=.008, rot=0):
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object
    ob.name = ROOM + '_' + name
    ob.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.matrix_world = unit_matrix() @ Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(rot), 4, 'Z')
    ob.data.materials.append(M[material] if isinstance(material, str) else material)
    if bevel:
        b = ob.modifiers.new('Soft manufactured edges', 'BEVEL')
        b.width = bevel
        b.segments = 3
        ob.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    # Metre-scale UV mapping, including the existing packed oak textures.
    layer = ob.data.uv_layers.new(name='Metres')
    for p in ob.data.polygons:
        ax = max(range(3), key=lambda i: abs(p.normal[i]))
        axes = [(1, 2), (0, 2), (0, 1)][ax]
        for li in p.loop_indices:
            co = ob.data.vertices[ob.data.loops[li].vertex_index].co
            layer.data[li].uv = (co[axes[0]], co[axes[1]])
    return move(ob)


def sphere(name, loc, dims, material='white'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20)
    ob = bpy.context.object
    ob.name = ROOM + '_' + name
    ob.scale = tuple(d/2 for d in dims)
    ob.matrix_world = unit_matrix() @ Matrix.Translation(Vector(loc)) @ Matrix.Diagonal((*ob.scale, 1))
    ob.data.materials.append(M[material])
    for p in ob.data.polygons:
        p.use_smooth = True
    return move(ob)


def tube(name, a, b, radius, material='metal'):
    mb = MB()
    mb.tube(point(*a), point(*b), radius, radius, seg=20)
    return move(mb.build(ROOM+'_'+name, [M[material]], smooth=True))


def asset(key, loc, size, angle=0, name=None):
    """Reuse verified GLB geometry, sharing meshes across four dwellings."""
    if key not in CACHE:
        a = ASSETS[key]
        f = PACK/a['file']
        assert hashlib.sha256(f.read_bytes()).hexdigest() == a['sha256'], key
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(f))
        obs = list(set(bpy.data.objects)-before)
        bpy.context.view_layer.update()
        meshes = [o for o in obs if o.type == 'MESH']
        pts = [o.matrix_world@Vector(v) for o in meshes for v in o.bound_box]
        lo = Vector([min(v[i] for v in pts) for i in range(3)])
        hi = Vector([max(v[i] for v in pts) for i in range(3)])
        if key == DCHAIR:
            for material in {m for o in meshes for m in o.data.materials}:
                if material.name.startswith(('Textile |', 'Upholstery |')):
                    bs = material.node_tree.nodes.get('Principled BSDF')
                    for link in list(bs.inputs['Base Color'].links):
                        material.node_tree.links.remove(link)
                    bs.inputs['Base Color'].default_value = (.55, .53, .48, 1)
                    bs.inputs['Roughness'].default_value = .85
        data = [(o.data, o.matrix_world.copy()) for o in meshes]
        CACHE[key] = (data, lo, hi)
        for o in obs:
            bpy.data.objects.remove(o, do_unlink=True)
        RECEIPTS.append({k:a.get(k) for k in ['id','title','source','author','license','sha256','file','provider']})
    data, lo, hi = CACHE[key]
    scale = size/max((hi-lo).x, (hi-lo).y)
    origin = Vector(((lo.x+hi.x)/2, (lo.y+hi.y)/2, lo.z))
    transform = unit_matrix() @ Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(angle),4,'Z') @ Matrix.Scale(scale,4) @ Matrix.Translation(-origin)
    objs = []
    for mesh, matrix in data:
        ob = bpy.data.objects.new(ROOM+'_'+(name or key), mesh)
        collection('Lokal_'+SEG+'_'+LEVEL).objects.link(ob)
        ob.matrix_world = transform@matrix
        ob['source_asset'] = key
        ob['room'] = ROOM
        objs.append(ob)
    return objs


def area(name, loc, target, power, size, color=(1,.90,.78)):
    d = bpy.data.lights.new(ROOM+'_'+name, 'AREA')
    d.energy = power
    d.shape = 'DISK'
    d.size = size
    d.color = color
    o = bpy.data.objects.new(d.name, d)
    collection('Lokal_'+SEG+'_'+LEVEL).objects.link(o)
    o.location = point(*loc)
    o.visible_glossy = False
    o.rotation_euler = (Vector(point(*target))-o.location).to_track_quat('-Z','Y').to_euler()
    return o


def curtain(u, y, width, height=2.48):
    vs, fs = [], []
    nu, nv = 36, 18
    for j in range(nv+1):
        for i in range(nu+1):
            t=i/nu
            vs.append(point(u-width/2+width*t, y+.035*math.cos(t*math.pi*12), .04+height*j/nv))
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i
            fs.append((a,a+1,a+nu+2,a+nu+1))
    me=bpy.data.meshes.new('Linen folds')
    me.from_pydata(vs,[],fs)
    ob=bpy.data.objects.new(ROOM+'_Linen curtain',me)
    collection('Lokal_'+SEG+'_'+LEVEL).objects.link(ob)
    me.materials.append(M['linen'])
    for p in me.polygons:p.use_smooth=True
    return ob


def art(u,y,z,w=1.20,h=.70,axis='Y'):
    if axis=='Y':
        box('Oak art frame',(u,y,z),(w,.035,h),'oak',.005)
        box('Neutral canvas',(u,y-.022,z),(w-.045,.014,h-.045),'canvas',.002)
        for i,(du,dz,r) in enumerate([(-.28,-.09,.24),(.05,.10,.20),(.32,-.10,.15)]):
            sphere('Sculpted relief',(u+du*w,y-.037,z+dz*h),(r*w,.012,r*w),'stone' if i!=1 else 'taupe')
    else:
        box('Oak art frame',(u,y,z),(.035,w,h),'oak',.005)
        face = -1 if u > 2 else 1
        box('Neutral canvas',(u+face*.022,y,z),(.014,w-.045,h-.045),'canvas',.002)
        for i in range(3):
            sphere('Sculpted relief',(u+face*.037,y+(i-1)*w*.26,z+(.08 if i==1 else -.07)),(.012,.21*w,.34*h),'taupe' if i==1 else 'stone')


def downlights(bounds):
    u0,u1,y0,y1=bounds
    for u in (u0+.42,u1-.42):
        y=(y0+y1)/2
        box('Recessed ceiling trim',(u,y,2.665),(.105,.105,.012),'white',.01)
        area('Warm ceiling downlight',(u,y,2.65),(u,y,.3),18,.16)


def skirting(bounds, doors=()):
    u0,u1,y0,y1=bounds
    # Front and outer long walls; back segments must respect door openings.
    box('Skirting',(u0+.012,(y0+y1)/2,.075),(.018,y1-y0,.10),'white',.002)
    box('Skirting',(u1-.012,(y0+y1)/2,.075),(.018,y1-y0,.10),'white',.002)
    box('Skirting',((u0+u1)/2,y0+.012,.075),(u1-u0,.018,.10),'white',.002)
    # Only non-door rear pieces are added at ground level of other rooms.


def door_vertical(u,ya,yb,angle=0):
    # Casing on both faces; leaf stays open and never seals an entry view.
    for du in (-.066,.066):
        for y in (ya-.025,yb+.025):
            box('Door casing',(u+du,y,1.025),(.02,.06,2.05),'white',.003)
        box('Door casing',(u+du,(ya+yb)/2,2.035),(.02,yb-ya+.10,.06),'white',.003)
    if angle:
        box('Open door leaf',(u+.34,(ya+yb)/2,1.02),(.037,yb-ya-.025,1.97),'white',.005,angle)


def open_leaf(name, loc, width=.78, along='X'):
    dims = (width, .038, 1.96) if along == 'X' else (.038, width, 1.96)
    box(name + ' open door leaf', (loc[0], loc[1], 1.01), dims, 'cabinet', .004)
    if along == 'X':
        tube(name + ' lever', (loc[0]+width/2-.12,loc[1]+.035,1.02),
             (loc[0]+width/2-.23,loc[1]+.035,1.02), .009)
    else:
        tube(name + ' lever', (loc[0]+.035,loc[1]+width/2-.12,1.02),
             (loc[0]+.035,loc[1]+width/2-.23,1.02), .009)


def finish_doors():
    # Bathroom opens into the hall; bedroom leaf opens into the bedroom.
    open_leaf('Bathroom', (2.58,6.63))
    open_leaf('Bedroom', (4.25,5.83))
    if LEVEL == 'ground':
        open_leaf('Guest room', (2.15,4.13))
        open_leaf('Utility', (2.17,8.68), .68)
        open_leaf('Vestibule', (2.10,8.12), along='Y')
        door_vertical(1.82,7.98,8.68)
    else:
        open_leaf('Vestibule', (3.17,8.12), along='Y')
    # Casing for the vestibule threshold, as shown on the drawing.
    a,b=(2.10,2.90) if LEVEL=='ground' else (2.37,3.17)
    for yy in (7.654,7.786):
        for u in (a-.025,b+.025):
            box('Vestibule door casing',(u,yy,1.025),(.06,.02,2.05),'white',.003)
        box('Vestibule door casing',((a+b)/2,yy,2.035),(b-a+.10,.02,.06),'white',.003)


def kitchen():
    # L plan: the drawing places worktops against the rear partition and party wall.
    for i in range(5):
        u=4.20+i*.60
        box('Oak lower cabinet',(u,4.57,.46),(.594,.62,.80),'oak',.006)
        box('Handleless drawer',(u,4.245,.47),(.586,.025,.75),'oak',.003)
        box('Shadow handle',(u,4.23,.825),(.54,.012,.018),'dark',.001)
    box('Continuous stone worktop',(5.40,4.55,.89),(3.04,.68,.04),'stone',.004)
    box('Stone backsplash',(5.42,4.914,1.16),(3.15,.018,.48),'stone',.002)
    for i in range(3):
        yy=3.00+i*.60
        box('Party-wall base cabinet',(6.99,yy,.46),(.62,.594,.80),'oak',.004)
        box('Party-wall drawer',(6.665,yy,.47),(.025,.586,.75),'oak',.003)
    box('Party worktop',(6.99,3.60,.89),(.67,1.83,.04),'stone',.004)
    box('Party backsplash',(7.326,3.61,1.16),(.016,1.84,.48),'stone',.002)
    # Tall fridge is on the terminal garden-side end of the party run.
    box('Integrated fridge',(7.00,2.20,1.19),(.62,.74,2.34),'cabinet',.008)
    box('Fridge reveal',(6.677,2.20,1.19),(.015,.012,2.22),'dark',.001)
    for i in range(4):
        u=4.34+i*.63
        box('White upper cabinet',(u,4.735,1.86),(.624,.34,.74),'cabinet',.004)
        box('Upper shadow gap',(u,4.557,1.50),(.59,.008,.015),'dark',.001)
    # Recessed sink: rim, bowl and gooseneck tap.
    box('Sink rim',(5.95,4.54,.915),(.54,.43,.012),'metal',.05)
    box('Sink dark interior',(5.95,4.54,.921),(.48,.37,.007),'dark',.045)
    tube('Kitchen tap',(6.0,4.78,.92),(6.0,4.78,1.20),.012)
    tube('Kitchen tap',(6.0,4.78,1.20),(6.0,4.54,1.20),.012)
    box('Induction glass',(6.99,3.32,.919),(.53,.59,.012),'blackglass',.016)
    for u in (6.86,7.11):
        for yy in (3.17,3.47):
            # Fine burner rings, not large solid cylinders.
            bpy.ops.mesh.primitive_torus_add(major_radius=.075,minor_radius=.0018,major_segments=36,minor_segments=8,location=point(u,yy,.927))
            ob=bpy.context.object;ob.data.materials.append(M['metal']);move(ob)
    box('Oven glass',(6.651,3.31,.49),(.014,.54,.49),'blackglass',.008)
    tube('Oven handle',(6.627,3.10,.72),(6.627,3.51,.72),.012)
    area('Kitchen task strip',(5.40,4.54,1.48),(5.4,4.5,.85),24,1.6)
    # Small, sourced tea set on the worktop.
    asset('tea_set_01',(4.61,4.53,.916),.46,10)


def living(upper):
    kitchen()
    if upper:
        sofa=(1.42,2.12,.03);size=2.48;rotation=90
        asset(SOFA,sofa,size,rotation)
        asset(CHAIR,(2.83,1.37,.03),.83,-30)
        box('Woven wool rug',(2.12,2.40,.039),(3.04,2.70,.018),'rug',.035)
        asset(COFFEE,(2.18,2.40,.064),1.03,12)
        box('Oak TV console',(1.50,4.67,.35),(1.95,.36,.50),'oak',.018)
        box('TV screen',(1.50,4.871,1.34),(1.35,.032,.83),'blackglass',.015)
        asset(LAMP,(.40,3.95,.03),.30)
        art(.055,2.47,1.57,1.48,.86,'X')
        dining_u,dining_y=5.25,1.67
        asset(DINING,(dining_u,dining_y,.03),1.62,90)
        chairs=[(4.52,1.24,90),(4.52,2.08,90),(5.98,1.24,-90),(5.98,2.08,-90)]
    else:
        box('Woven wool rug',(3.65,2.34,.039),(1.94,2.40,.018),'rug',.025)
        asset(SOFA,(4.43,2.28,.03),1.92,-90)
        asset(COFFEE,(3.48,2.24,.064),.79,0)
        box('Floating media cabinet',(2.78,2.18,.43),(.30,1.50,.37),'oak',.012)
        box('TV screen',(2.675,2.18,1.40),(.033,1.13,.67),'blackglass',.012)
        asset(LAMP,(2.94,3.12,.03),.27)
        dining_u,dining_y=5.95,1.33
        asset(DINING,(dining_u,dining_y,.03),1.42,0)
        chairs=[(5.47,.76,0),(6.29,.76,0),(5.47,1.90,180),(6.29,1.90,180)]
    for i,(u,y,ang) in enumerate(chairs):asset(DCHAIR,(u,y,.03),.52,ang,'Dining chair '+str(i))
    # Slim custom pendant avoids an oversized hanging object in the shot.
    tube('Pendant cable',(dining_u,dining_y,2.67),(dining_u,dining_y,2.18),.004,'dark')
    sphere('Opal dining pendant',(dining_u,dining_y,2.19),(.26,.26,.26),'opal')
    area('Dining practical',(dining_u,dining_y,2.06),(dining_u,dining_y,.70),12,.20)
    for a,b in ((.68,2.18),(3.065,4.565),(5.22,6.72)):
        if not upper and a<2.5:continue
        curtain(a-.13,.51,.22);curtain(b+.13,.51,.22)
        area('Window daylight',((a+b)/2,.46,1.60),((a+b)/2,3.0,1.05),125,1.35,(.88,.94,1.0))
    bounds=(0,7.34,.39,4.93) if upper else (2.60,7.34,.39,4.93)
    skirting(bounds)
    downlights(bounds)


def bedroom(front=False):
    if front:
        # Small second room: a single bed, desk and full-height wardrobe.
        asset(BED2,(.68,1.92,.035),2.10,-90)
        box('Desk',(1.93,1.22,.78),(.80,.52,.045),'oak',.012)
        for u in (1.60,2.25):tube('Desk leg',(u,1.23,.03),(u,1.23,.76),.018,'dark')
        asset(DCHAIR,(1.94,1.85,.03),.51,180)
        for i in range(4):
            u=.32+i*.60
            box('White wardrobe',(u,4.59,1.26),(.594,.62,2.46),'cabinet',.008)
            box('Wardrobe line',(u,4.268,1.27),(.012,.006,2.30),'taupe',.001)
        art(2.445,2.73,1.63,.78,.65,'X')
        asset(LAMP,(2.10,2.74,.03),.26)
        box('Small bedside',(1.50,2.75,.36),(.38,.38,.48),'oak',.018)
        curtain(.53,.52,.22);curtain(2.31,.52,.22)
        area('Window daylight',(1.43,.46,1.60),(1.40,3.0,1.05),110,1.30,(.89,.95,1))
        skirting((0,2.50,.39,4.93));downlights((0,2.5,.39,4.93))
    else:
        # Double bed headboard stays at the party wall as drawn.
        box('Light grey bedroom feature',(7.326,7.31,1.34),(.012,2.92,2.61),'grey',.001)
        asset(BED,(6.12,7.31,.03),2.19,-90)
        box('Bedside',(6.97,6.06,.39),(.50,.45,.48),'oak',.025)
        box('Bedside',(6.97,8.51,.39),(.50,.45,.48),'oak',.025)
        for yy in (6.06,8.51):
            tube('Wall lamp stem',(7.28,yy,1.20),(7.04,yy,1.20),.010)
            sphere('Opal bedside globe',(7.00,yy,1.12),(.16,.16,.19),'opal')
            area('Bedside practical',(7.00,yy,1.13),(6.8,yy,.45),4,.14)
        box('Textured bed rug',(5.62,7.30,.04),(2.35,2.77,.02),'rug',.03)
        for i in range(5):
            u=4.22+i*.60
            box('Wardrobe',(u,5.43,1.25),(.594,.58,2.44),'cabinet',.006)
            box('Wardrobe recessed pull',(u+.22,5.128,1.23),(.012,.012,.68),'metal',.002)
        art(7.29,7.30,1.64,1.35,.62,'X')
        curtain(4.61,8.91,.26);curtain(6.43,8.91,.26)
        area('Rear daylight',(5.52,8.97,1.53),(5.60,6.0,.93),150,1.30,(.87,.94,1))
        skirting((3.90,7.34,5.11,9.05));downlights((3.90,7.34,5.11,9.05))


def bathroom():
    # Source: shower at garden-side wall, WC and sink on rear installations.
    box('Limestone side wall',(.009,6.39,1.31),(.012,2.55,2.56),'bathstone',.001)
    for yy in (5.71,6.31,6.91,7.51):
        for u in (.30,.90,1.50):
            box('Limestone wall tile',(u,7.656,.34+(yy-5.71)),(.596,.012,.596),'bathstone',.001)
    # Floor tile pattern from physical grout joints.
    for u in (.60,1.20,1.80):box('Floor grout',(u,6.39,.031),(.002,2.54,.002),'grout',0)
    for yy in (5.71,6.31,6.91,7.51):box('Floor grout',(1.06,yy,.031),(2.10,.002,.002),'grout',0)
    box('Shower tray',(1.02,5.53,.065),(1.93,.78,.06),'porcelain',.03)
    box('Shower glass',(1.33,5.934,1.05),(1.39,.009,2.0),'glass',.001)
    tube('Shower screen edge',(.64,5.934,.09),(.64,5.934,2.05),.007,'metal')
    tube('Shower rail',(.055,5.51,1.0),(.055,5.51,2.14),.015)
    tube('Shower arm',(.055,5.51,2.14),(.40,5.51,2.14),.015)
    sphere('Rain shower',(.40,5.51,2.12),(.25,.25,.025),'metal')
    # Freestanding CC0 bathroom vanity, sized into the 0.77m recess.
    asset(VANITY,(1.31,7.34,.035),.77,0)
    box('Vanity mirror',(1.30,7.633,1.53),(.76,.018,.82),'mirror',.12)
    # Smooth wall-hung ceramic WC with separate rim, lid and concealed cistern.
    box('Concealed WC cistern',(.51,7.55,.62),(.69,.20,1.18),'bathstone',.012)
    sphere('Wall hung ceramic WC',(.51,7.13,.34),(.41,.62,.33),'porcelain')
    sphere('WC seat lid',(.51,7.13,.515),(.42,.59,.055),'porcelain')
    box('Flush plate',(.51,7.439,.94),(.22,.013,.14),'metal',.008)
    # Folded towel, bath rug and hooks are neutral and functional.
    box('Bath rug',(1.10,6.30,.043),(.83,.47,.025),'linen',.05)
    for z in (.88,1.0,1.12,1.24,1.36):tube('Towel rail',(.10,6.18,z),(.10,6.69,z),.012,'dark')
    box('Folded towel',(.13,6.43,1.17),(.08,.37,.34),'linen',.014)
    downlights((0,2.13,5.11,7.67))
    area('Bathroom soft fill',(1.10,6.30,2.60),(1.0,6.5,.5),65,1.20,(1,.95,.87))


def hall(vest=False):
    if vest:
        if LEVEL=='upper':
            bounds=(0,3.80,7.77,9.05)
            u=.90
            box('Entrance bench',(1.24,8.83,.40),(1.40,.37,.12),'oak',.018)
            box('Bench upholstered seat',(1.24,8.83,.49),(1.38,.36,.08),'linen',.025)
            box('Entrance mirror',(1.30,9.024,1.48),(.91,.02,1.10),'mirror',.10)
            for yy in (8.11,8.48,8.85):box('Vestibule wardrobe',(3.52,yy,1.26),(.53,.364,2.46),'cabinet',.005)
        else:
            bounds=(1.87,3.80,7.77,9.05)
            u=2.20
            box('Entrance bench',(3.53,8.42,.43),(.37,.84,.12),'oak',.014)
            box('Entrance mirror',(3.779,8.45,1.44),(.015,.71,1.12),'mirror',.08)
            # Keep the utility doorway on the left completely clear.
            box('Coat cupboard above bench',(3.53,8.42,2.07),(.37,.84,.76),'cabinet',.005)
            box('Entrance mat',(2.80,8.40,.039),(.67,.48,.016),'rug',.02)
        downlights(bounds)
        area('Vestibule warm fill',((bounds[0]+bounds[1])/2,8.40,2.58),(u,8.3,.4),38,.8,(1,.96,.91))
    else:
        bounds=(2.23,3.80,5.11,7.67)
        # Narrow consoles must leave the 1.57m documented communication clear.
        box('Slender hall console',(3.65,7.12,.82),(.24,.66,.055),'oak',.01)
        box('Hall wall mirror',(3.778,7.13,1.52),(.015,.60,.84),'mirror',.07)
        downlights(bounds)
        area('Hall fill',(3.0,6.50,2.58),(3,6.3,.5),35,.8,(1,.96,.91))
        skirting(bounds)


def utility():
    box('Washer body',(.41,8.65,.46),(.60,.60,.85),'white',.025)
    sphere('Washer dark seal',(.41,8.339,.46),(.43,.035,.43),'dark')
    sphere('Washer drum glass',(.41,8.313,.46),(.33,.025,.33),'blackglass')
    box('Washer control panel',(.41,8.336,.78),(.50,.018,.10),'metal',.008)
    box('Laundry worktop',(.87,8.64,.92),(1.62,.64,.035),'oak',.008)
    for u in (.40,1.10):box('Utility wall cabinet',(u,8.85,1.78),(.66,.36,.83),'cabinet',.008)
    box('Laundry basket',(1.20,8.60,.39),(.52,.50,.69),'linen',.06)
    area('Utility fill',(.88,8.37,2.56),(.88,8.5,.5),45,.8,(1,.96,.91))


# Camera positions in local coordinates, z is eye height above finished floor.
# All perspectives are interior; no exterior camera is created.
VIEWS = [
 ('01_pietro_salon','upper','5',(6.33,.98,1.55),(1.75,2.82,1.28),26),
 ('02_pietro_kuchnia_jadalnia','upper','5',(1.02,1.00,1.57),(5.61,3.19,1.27),26),
 ('03_pietro_strefa_dzienna','upper','5',(3.44,4.28,1.53),(3.41,1.58,1.23),23),
 ('04_parter_salon','ground','6',(2.97,4.36,1.53),(4.76,1.91,1.18),24),
 ('05_parter_kuchnia','ground','6',(3.00,2.89,1.54),(6.02,4.05,1.27),24),
 ('06_sypialnia_glowna','upper','4',(4.29,8.59,1.52),(6.17,7.05,1.18),24),
 ('07_sypialnia_garderoba','ground','5',(4.36,7.61,1.51),(6.20,6.45,1.23),24),
 ('08_pokoj_goscinny_gabinet','ground','7',(2.08,3.91,1.51),(.98,1.85,1.07),22),
 ('09_lazienka','upper','2',(1.91,5.27,1.50),(.81,7.15,1.14),20),
 ('10_lazienka_prysznic','ground','4',(.38,7.05,1.52),(1.36,5.59,1.12),20),
 ('11_hol','upper','3',(3.56,7.28,1.50),(2.96,5.10,1.33),24),
 ('12_wiatrolap_pietro','upper','1',(2.97,8.02,1.50),(1.10,8.86,1.24),20),
 ('13_wiatrolap_parter','ground','1',(2.82,8.87,1.49),(3.28,7.92,1.27),20),
 ('14_pomieszczenie_gospodarcze','ground','2',(1.40,7.99,1.50),(.62,8.70,1.13),19),
]


def build():
    global M, SEG, LEVEL, ROOM, Z
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tmp/existing/salon_v4_editable.blend'))
    floor = bpy.data.materials['V4_floor']
    oak = bpy.data.materials['V4_walnut']
    rug = bpy.data.materials['V4_rug']
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    for c in list(bpy.data.collections):bpy.data.collections.remove(c)
    floor.name='WNETRZA_Natural oak PBR CC0 V2'
    oak.name='WNETRZA_Walnut PBR CC0 V2'
    rug.name='WNETRZA_Woven carpet PBR CC0 V3'
    nt=oak.node_tree
    bs=nt.nodes.get('Principled BSDF')
    old=bs.inputs['Base Color'].links[0].from_socket
    warm=nt.nodes.new('ShaderNodeMixRGB');warm.blend_type='MULTIPLY'
    warm.inputs[0].default_value=1;warm.inputs[2].default_value=(.73,.52,.31,1)
    nt.links.new(old,warm.inputs[1]);nt.links.new(warm.outputs[0],bs.inputs['Base Color'])
    M={
        'white':mat('Soft white walls',(.78,.78,.76),.78),
        'ceiling':mat('White ceiling',(.84,.84,.82),.85),
        'grey':mat('Light grey feature wall',(.60,.61,.60),.80),
        'cabinet':mat('Warm white cabinetry',(.75,.74,.70),.42),
        'oak':oak,'floor':floor,'rug':rug,
        'stone':mat('Honed pale stone',(.62,.59,.54),.48),
        'bathstone':mat('Light limestone bathroom',(.69,.68,.64),.62),
        'grout':mat('Fine pale grout',(.43,.44,.42),.76),
        'taupe':mat('Calm taupe',(.42,.40,.36),.72),
        'linen':mat('Ivory linen',(.73,.72,.68),.94),
        'canvas':mat('Art canvas',(.77,.75,.69),.94),
        'dark':mat('Charcoal metal',(.032,.038,.041),.40),
        'metal':mat('Brushed satin metal',(.40,.42,.43),.28,.85),
        'porcelain':mat('White porcelain',(.82,.83,.82),.16),
        'mirror':mat('Silver mirror',(.88,.90,.91),.015,1),
        'blackglass':mat('Smoked appliance glass',(.018,.025,.029),.13,.25),
        'opal':mat('Opal glass',(.86,.83,.75),.3),
        'glass':mat('Clear glass',(.91,.96,.98),.035),
    }
    for key in ['glass']:
        p=M[key].node_tree.nodes.get('Principled BSDF')
        p.inputs['Transmission Weight'].default_value=1.0
        p.inputs['IOR'].default_value=1.45
    p=M['opal'].node_tree.nodes.get('Principled BSDF')
    p.inputs['Emission Color'].default_value=(1,.79,.52,1)
    p.inputs['Emission Strength'].default_value=.7
    # Fine neutral surface detail, without colored image textures on walls.
    for key in ['white','grey','linen','bathstone']:
        nt=M[key].node_tree
        noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=150 if key=='linen' else 90
        bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.003
        nt.links.new(noise.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],nt.nodes['Principled BSDF'].inputs['Normal'])
    archm={'facade':M['white'],'rail':M['dark'],'door':M['cabinet'],'glass':M['glass'],'party':M['white']}
    architecture._make_walls(archm)
    architecture._make_glazing(archm)
    interiors._partitions(archm)
    for ob in list(bpy.context.scene.objects):move(ob,'Architektura - obydwa segmenty')
    # Floor and ceiling surfaces cover exact clear rectangular envelopes;
    # service recesses are defined by permanent partitions above these finishes.
    for SEG in ['A','B']:
        for LEVEL in ['ground','upper']:
            Z=plan.LEVEL_Z[LEVEL]
            for no,kind,area_pdf,finish,bounds in plan.PROGRAM[LEVEL]:
                ROOM=plan.room_id(SEG,LEVEL,no)
                u0,u1,y0,y1=bounds
                floor_key='bathstone' if finish=='tile' else 'floor'
                box('Finished floor',((u0+u1)/2,(y0+y1)/2,.018),(u1-u0,y1-y0,.024),floor_key,.001)
                box('White ceiling',((u0+u1)/2,(y0+y1)/2,2.675),(u1-u0,y1-y0,.025),'ceiling',.001)
                if kind=='salon_z_aneksem':living(LEVEL=='upper')
                elif kind=='pokoj_tyl':bedroom()
                elif kind=='pokoj_przod':bedroom(True)
                elif kind=='lazienka':bathroom()
                elif kind=='wiatrolap':hall(True)
                elif kind=='przedpokoj':hall()
                elif kind=='pom_gospodarcze':utility()
            ROOM=SEG+'_'+LEVEL+'_Doors'
            door_vertical(2.18,5.83,6.63)
            door_vertical(3.85,5.83,6.63)
            if LEVEL=='ground':door_vertical(2.55,3.33,4.13)
            finish_doors()
    # Remove unused old scene data, keeping only materials and images with users.
    for mesh in list(bpy.data.meshes):
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    for material in list(bpy.data.materials):
        if material.users==0:bpy.data.materials.remove(material)
    for im in list(bpy.data.images):
        if im.users==0:bpy.data.images.remove(im)
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC'
    world=bpy.data.worlds.new('Neutral daylight sky');world.use_nodes=True
    nt=world.node_tree
    sky=nt.nodes.new('ShaderNodeTexSky');sky.sky_type='MULTIPLE_SCATTERING';sky.sun_disc=False
    sky.sun_elevation=math.radians(38);sky.sun_rotation=math.radians(195)
    nt.nodes['Background'].inputs['Color'].default_value=(.73,.79,.85,1);nt.nodes['Background'].inputs['Strength'].default_value=.55
    scene.world=world
    sun=bpy.data.lights.new('Daylight','SUN');sun.energy=1.25;sun.angle=math.radians(8);sun.color=(1,.94,.84)
    o=bpy.data.objects.new('Daylight',sun);collection('Swiatlo dzienne').objects.link(o);o.rotation_euler=Vector((.35,.90,-1.2)).to_track_quat('-Z','Y').to_euler()
    scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.render.threads_mode='FIXED';scene.render.threads=8
    scene.cycles.samples=128;scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.018
    scene.cycles.use_denoising=True;scene.cycles.max_bounces=10;scene.cycles.diffuse_bounces=5;scene.cycles.glossy_bounces=4;scene.cycles.transmission_bounces=8
    scene.cycles.sample_clamp_indirect=4
    scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.20
    scene.render.film_transparent=False
    # Create saved, named cameras for representative units A, plus all mirrored B cameras.
    for segment in ['A','B']:
        SEG=segment
        for name,LEVEL,no,loc,target,lens in VIEWS:
            Z=plan.LEVEL_Z[LEVEL]
            camera=bpy.data.cameras.new(segment+'_'+name);ob=bpy.data.objects.new(camera.name,camera)
            collection('Kamery - wnetrza').objects.link(ob)
            ob.location=point(*loc);ob.rotation_euler=(Vector(point(*target))-ob.location).to_track_quat('-Z','Y').to_euler()
            camera.lens=lens;camera.sensor_width=36;camera.clip_start=.035
            ob['room']=plan.room_id(segment,LEVEL,no)
    scene.camera=bpy.data.objects['A_'+VIEWS[0][0]]
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Wnetrza_4_lokale.blend'),compress=True)
    (OUT/'ZRODLA_MODELI.json').write_text(json.dumps(RECEIPTS,indent=2,ensure_ascii=False))
    # Structural evidence is generated from the actual edited plan and camera positions.
    audit={'source':'Supplied original four-sheet concept PDF, inspected pages 1-4',
           'units':['A_ground','A_upper','B_ground','B_upper'],'room_count':len(plan.ROOMS),
           'bounds_m':{'width':15.87,'depth':9.44,'wing_clear_width':7.34,'ground_living_depth':4.54,'upper_living_depth':4.54,'rear_bedroom':[3.44,3.94]},
           'rooms':plan.ROOM_META,'camera_count':28,'wall_colors':['soft white','light grey'],
           'source_conflict':'Upper living label 4.14 vs dimension chain 4.54 and schedule 33.32; chose 4.54',
           'inferred':['2.69 m ceiling height - no section provided','furnishings, finishes, light fixtures are design proposals','raster tracing of positions, not CAD survey'],
           'models_used':len(RECEIPTS),'mesh_objects':len([o for o in scene.objects if o.type=='MESH']),
           'blender':bpy.app.version_string,'base_repository_commit':'c3d3ab3c4602e76e214c0ac5dc6abbf2340a21d9'}
    (OUT/'KONTROLA_GEOMETRII.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False))
    print('BUILD_OK',audit['mesh_objects'],flush=True)


def render(names, scale=100, samples=128):
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Wnetrza_4_lokale.blend'))
    scene=bpy.context.scene
    scene.render.resolution_percentage=scale
    scene.cycles.samples=samples
    scene.cycles.time_limit=420 if scale==100 else 55
    folder=OUT/'Obrazy' if scale==100 else OUT/'kontrola'
    folder.mkdir(exist_ok=True)
    results=[]
    for name in names:
        scene.camera=bpy.data.objects['A_'+name]
        scene.cycles.time_limit = (180 if name.startswith(('11_', '12_')) else 420) if scale == 100 else 55
        scene.render.filepath=str(folder/(name+'.png'))
        # One view should not change the noise/lighting balance of other units.
        level=next(v[1] for v in VIEWS if v[0]==name)
        for key in ['A_ground','A_upper','B_ground','B_upper']:
            c=bpy.data.collections['Lokal_'+key]
            # The shell remains complete, but distant furnishing never contributes.
            c.hide_render=key!='A_'+level
        t=time.monotonic()
        bpy.ops.render.render(write_still=True)
        results.append({'view':name,'seconds':time.monotonic()-t,'resolution_percentage':scale,'samples':samples})
        print('RENDER_OK',results[-1],flush=True)
    (folder/'render_times.json').write_text(json.dumps(results,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build',action='store_true');p.add_argument('--views',default='all');p.add_argument('--scale',type=int,default=100);p.add_argument('--samples',type=int,default=128)
    args=p.parse_args()
    if args.build:build()
    if args.views!='none':render([v[0] for v in VIEWS] if args.views=='all' else args.views.split(','),args.scale,args.samples)
