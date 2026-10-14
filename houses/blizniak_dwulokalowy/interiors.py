"""All 24 documented rooms are physically split and furnished as a conceptual interior.

Room areas remain the original PDF schedule, while partition geometry is approximate.
No internal stairs are present: independent upper dwellings use both external flights.
"""
from .plan import *
from archviz.mesh import MB
from archviz.lights import room_light


def _local_vertical(mesh, seg, u, y0, y1, z0, z1, door=None):
    x=seg_interval(seg,u,u)[0]
    holes=[] if door is None else [(door[0],door[1],z0,z0+2.10)]
    mesh.wall("Y",y0,y1,x-.05,x+.05,z0,z1,holes=holes)


def _local_horizontal(mesh, seg, u0, u1, y, z0, z1, door=None):
    x0,x1=seg_interval(seg,u0,u1)
    holes=[]
    if door is not None:
        a,b=seg_interval(seg,door[0],door[1])
        holes=[(a,b,z0,z0+2.10)]
    mesh.wall("X",x0,x1,y-.05,y+.05,z0,z1,holes=holes)


def _partitions(M):
    for seg in ("A","B"):
        for level in ("ground","upper"):
            z0=LEVEL_Z[level]
            z1=Z_LOWER_CEIL if level=="ground" else Z_UPPER_CEIL
            walls=MB()
            _local_horizontal(walls,seg,0,7.34,4.79,z0,z1,(2.60,3.51))
            _local_vertical(walls,seg,2.40,4.79,7.25,z0,z1,(6.15,7.06))
            _local_vertical(walls,seg,3.75,4.79,8.63,z0,z1,(6.03,6.96))
            if level=="ground":
                _local_vertical(walls,seg,2.50,.27,4.79,z0,z1,(3.51,4.38))
                _local_horizontal(walls,seg,0,3.75,7.25,z0,z1,(2.56,3.43))
                _local_vertical(walls,seg,1.60,7.25,8.63,z0,z1,(7.98,8.88))
            else:
                _local_horizontal(walls,seg,0,2.40,7.25,z0,z1,(1.10,1.97))
                _local_vertical(walls,seg,2.40,7.25,8.63,z0,z1,(8.06,8.94))
            walls.build("BLI_Partitions_" + seg + "_" + level,[M["party"]])


def _furnish_room(room, box, M):
    """Real rounded parametric furniture, sized for the local room program.

    Staging is a visual proposal, not the furnishings of the architect's drawing.
    """
    from archviz.parts import sofa, bed, table, dining_chair, round_table
    from archviz.parts import armchair, basin, faucet, cabinet_run, bathtub
    data = ROOM_META[room]
    seg,kind = data["segment"], data["name"]
    x0,x1,y0,y1,z0,z1=box
    w,d=x1-x0,y1-y0
    cx,cy=(x0+x1)/2,(y0+y1)/2
    furniture=MB()
    # per-face material slots: upholstery, timber, cabinets, ceramic, graphite, textiles
    if kind == "salon_z_aneksem":
        sofa_w=min(2.25,w-1.25)
        sy = max(y0+1.40,cy-0.38)
        sofa(furniture,cx-.22,sy,sofa_w,.87,z=z0,mi_seat=0,mi_back=0,
             mi_base=1,plinth=.08,mi_plinth=1,soft=.075,
             pillows=2,mi_pillow=5,cushion_gap=.025)
        round_table(furniture,cx-.18,sy-1.03,z0,.37,h=.39,mi=1,mi_leg=4)
        furniture.rbox(cx-1.35,cx+1.12,sy-1.63,sy-.20,z0+.035,z0+.056,.010,mi=5)
        # Kitchen runs along the central twin party wall, as shown in both plans.
        if seg=="A":
            k0,k1=x1-.72,x1-.13
            sink_x=x1-.42
        else:
            k0,k1=x0+.13,x0+.72
            sink_x=x0+.42
        ky0=y1-2.08;ky1=y1-.20
        cabinet_run(furniture,k0,k1,ky0,ky1,z0,z0+.87,mi=2,doors="Y",n=4,mi_gap=4)
        furniture.box(k0-.015,k1+.015,ky0-.015,ky1+.015,z0+.87,z0+.93,mi=3)
        # Worktop sink / hob are recognisable 3D objects, not blank cubes.
        furniture.box(sink_x-.23,sink_x+.23,ky1-.53,ky1-.16,z0+.934,z0+.945,mi=4)
        for yy in (ky0+.30,ky0+.60):
            furniture.cylinder(sink_x,yy,z0+.94,z0+.944,.105,seg=24,mi=4)
        # Dining zone, kept inside living footprint and separate from entry.
        dx=cx+1.02 if seg=="A" else cx-1.02
        ty=y1-1.22
        table(furniture,dx,ty,z0,.96,.68,h=.76,mi_top=1,mi_leg=4,leg_w=.055)
        for offset in (-.65,.65):
            dining_chair(furniture,dx+offset,ty,rot=(1.57 if offset>0 else -1.57),
                         z=z0,mi_wood=1,mi_seat=5)
        # Open shelving and artwork at far corner.
        furniture.box(x0+.18,x0+.38,y1-1.31,y1-.23,z0+.20,z0+1.75,mi=1)
        for zz in (.42,.82,1.22,1.62):
            furniture.box(x0+.12,x0+.47,y1-1.30,y1-.20,z0+zz,z0+zz+.035,mi=1)
    elif kind.startswith("pokoj"):
        # Bed does not block the front room doorway (placed near its rear end).
        bw=max(1.14,min(1.60,w-.70))
        bl=max(1.72,min(2.03,d-.72))
        bed(furniture,cx,cy+.24,z=z0,w=bw,l=bl,mi_frame=0,
            mi_linen=5,mi_pillow=3,mi_throw=1,
            mi_duvet=5,head_h=.96,seed=int((abs(cx)+cy)*10),channels=4)
        furniture.box(x0+.15,x0+.56,y1-.60,y1-.10,z0,z0+2.15,mi=1)
        furniture.box(x0+.57,x0+.61,y1-.60,y1-.10,z0+.08,z0+2.13,mi=4)
        for side in (-1,1):
            nx=cx+side*(bw/2+.24)
            furniture.rbox(nx-.21,nx+.21,cy+.75,cy+1.15,z0+.37,z0+.49,.04,mi=1)
        furniture.box(x1-.80,x1-.19,y0+.10,y0+.24,z0+.76,z0+.81,mi=1)
    elif kind == "lazienka":
        # Compact freestanding bath + vanity and WC in each of 4 bathrooms.
        bathtub(furniture,x0+.76,cy-.25,z0,l=1.55,w=.69,h=.55,mi=3)
        furniture.box(x1-.78,x1-.16,y1-.60,y1-.18,z0+.63,z0+.78,mi=1)
        basin(furniture,x1-.47,y1-.39,z0+.76,r=.18,mi=3)
        faucet(furniture,x1-.47,y1-.14,z0+.80,mi=4)
        furniture.box(x0+.19,x0+.62,y1-.70,y1-.27,z0+.24,z0+.47,mi=3)
        furniture.box(x0+.23,x0+.59,y1-.66,y1-.29,z0+.47,z0+.58,mi=3)
        furniture.box(x1-.82,x1-.14,y1-.12,y1-.09,z0+1.17,z0+2.05,mi=4)
    elif kind == "pom_gospodarcze":
        wm_x = x0+.51 if seg=="A" else x1-.51
        wm_y = y1-.45
        furniture.cylinder(wm_x,wm_y,z0,z0+.83,.34,seg=28,mi=3)
        furniture.cylinder(wm_x,wm_y,z0+.79,z0+.83,.20,seg=24,mi=4)
        cabinet_run(furniture,x0+.08,x0+.43,y0+.12,y1-.10,z0+1.21,z0+2.10,mi=2,n=2)
    elif kind in ("wiatrolap","przedpokoj"):
        # No 2-metre wardrobes directly in the camera path.
        furniture.box(x0+.15,x0+.44,y1-.73,y1-.13,z0,z0+1.87,mi=1)
        furniture.box(x1-.81,x1-.19,y1-.36,y1-.12,z0+.31,z0+.43,mi=1)
        furniture.cylinder(x1-.51,y1-.30,z0,z0+.12,.14,seg=16,mi=4)
    else:
        raise ValueError(kind)
    ob=furniture.build("BLI_Furniture_"+room,
        [M["soft"],M["wood"],M["kitchen"],M["white_int"],M["rail"],M["linen_white"]],
        smooth=True)
    ob["apartment"]=seg+"_"+data["level"]
    ob["room_key"]=room
    ob["pdf_area_m2"]=data["area_pdf_m2"]


def build(M):
    _partitions(M)
    for key,bb in ROOMS.items():
        x0,x1,y0,y1,z0,z1=bb
        floor=MB()
        floor.box(x0+.015,x1-.015,y0+.015,y1-.015,z0+.004,z0+.028)
        floor.build("BLI_Floor_" + key,
                    [M["tile_floor"] if ROOM_META[key]["finish"]=="tile" else M["wood_floor"]])
        ceiling=MB()
        ceiling.box(x0+.015,x1-.015,y0+.015,y1-.015,z1-.031,z1-.011)
        ceiling.build("BLI_Ceiling_" + key,[M["party"]])
        _furnish_room(key,bb,M)
        room_light("BLI_Light_"+key,key)
