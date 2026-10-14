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
            _local_horizontal(walls,seg,0,7.34,5.27,z0,z1,(2.60,3.51))
            _local_vertical(walls,seg,2.40,5.27,7.70,z0,z1,(6.15,7.06))
            _local_vertical(walls,seg,3.75,5.27,9.17,z0,z1,(6.03,6.96))
            if level=="ground":
                _local_vertical(walls,seg,2.50,.27,5.27,z0,z1,(3.51,4.38))
                _local_horizontal(walls,seg,0,3.75,7.70,z0,z1,(2.56,3.43))
                _local_vertical(walls,seg,1.60,7.70,9.17,z0,z1,(7.98,8.88))
            else:
                _local_horizontal(walls,seg,0,2.40,7.70,z0,z1,(1.10,1.97))
                _local_vertical(walls,seg,2.40,7.70,9.17,z0,z1,(8.06,8.94))
            walls.build("BLI_Partitions_" + seg + "_" + level,[M["party"]])


def _furnish_room(room,box,M):
    data=ROOM_META[room]
    seg,level,no=data["segment"],data["level"],data["no"]
    kind=data["name"]; x0,x1,y0,y1,z0,z1=box
    cx,cy=(x0+x1)/2,(y0+y1)/2
    b=MB()
    # Slots: upholstery, timber, cabinets, sanitary white, charcoal.
    if kind=="salon_z_aneksem":
        # Compact sectional, rug, coffee table and kitchen on the dividing wall.
        b.rbox(cx-1.25,cx+0.45,cy-1.15,cy-.38,z0+.14,z0+.53,.07,mi=0)
        b.rbox(cx-1.25,cx+.45,cy-.46,cy-.25,z0+.14,z0+.91,.05,mi=0)
        b.box(cx-.60,cx+.48,cy+.03,cy+.55,z0+.31,z0+.37,mi=1)
        b.box(cx-.55,cx+.42,cy+.04,cy+.54,z0+.37,z0+.40,mi=2)
        b.box(cx-1.45,cx+1.30,cy-1.68,cy+.7,z0+.035,z0+.046,mi=2)
        # Kitchen countertop and upper storage, along the rear part of the room.
        b.box(cx-1.95,cx+1.95,y1-.73,y1-.15,z0,z0+.89,mi=2)
        b.box(cx-1.95,cx+1.95,y1-.74,y1-.11,z0+.89,z0+.935,mi=1)
        for dx in (-1.5,-.5,.5,1.5):
            b.box(cx+dx-.30,cx+dx+.30,y1-.72,y1-.12,z0+1.43,z0+2.12,mi=2)
        # Dining set on the open-plan side, behind the lounge.
        bx=cx+1.18 if seg=="A" else cx-1.18
        b.box(bx-.55,bx+.55,cy+.32,cy+1.04,z0+.71,z0+.76,mi=1)
        for dx in (-.42,.42):
            for yy in (cy+.14,cy+1.17):
                b.box(bx+dx-.17,bx+dx+.17,yy-.17,yy+.17,z0+.40,z0+.47,mi=0)
    elif kind.startswith("pokoj"):
        # Double bed plus headboard, pillows, side console, wardrobe.
        w=min(1.62,x1-x0-.70)
        l=min(2.04,y1-y0-.55)
        b.rbox(cx-w/2,cx+w/2,cy-l/2,cy+l/2,z0+.25,z0+.54,.05,mi=0)
        b.box(cx-w/2-.08,cx+w/2+.08,cy+l/2-.01,cy+l/2+.10,z0,z0+1.02,mi=1)
        for dd in (-.37,.37):
            b.rbox(cx+dd-.28,cx+dd+.28,cy+l/2-.52,cy+l/2-.19,z0+.52,z0+.68,.04,mi=3)
        b.box(x0+.12,x0+.55,y1-.76,y1-.16,z0,z0+2.16,mi=1)
        b.box(cx+.60,cx+1.04,y0+.25,y0+.75,z0+.42,z0+.53,mi=1)
    elif kind=="lazienka":
        b.box(x0+.15,x1-.18,y0+.12,y0+.87,z0+.05,z0+.10,mi=3)  # shower tray
        b.box(x0+.15,x0+.84,y0+.09,y0+.61,z0+.09,z0+1.90,mi=3)  # glass partition concept
        b.box(x1-.88,x1-.20,y1-.64,y1-.18,z0+.72,z0+.88,mi=3)
        b.box(x1-.83,x1-.25,y1-.63,y1-.22,z0+.90,z0+.96,mi=3)
        b.box(x0+.31,x0+.73,y1-.86,y1-.33,z0+.33,z0+.63,mi=3)  # WC
    elif kind=="pom_gospodarcze":
        b.box(cx-.36,cx+.36,cy-.45,cy+.31,z0,z0+.87,mi=3)
        b.box(x0+.09,x0+.48,y0+.07,y1-.06,z0+1.20,z0+2.16,mi=2)
    elif kind in ("wiatrolap","przedpokoj"):
        b.box(x0+.14,x0+.44,y0+.18,y0+.95,z0,z0+1.96,mi=1)
        b.box(x1-.88,x1-.18,y1-.45,y1-.22,z0+.30,z0+.68,mi=1)
    else:
        raise ValueError(kind)
    ob=b.build("BLI_Furniture_" + room,
               [M["soft"],M["wood"],M["kitchen"],M["white_int"],M["door"]])
    ob["apartment"]=seg+"_"+level
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
