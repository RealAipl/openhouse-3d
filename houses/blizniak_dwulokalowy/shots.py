"""Moving film camera storyboard: both outdoor stairs and every single room (24 visits).

Positions are checked against each room's XY envelope in plan.py. Concept preview
and final film are two fidelity levels of the same genuine Blender 3D camera moves.
"""
from .plan import ROOMS, ROOM_META, room_camera_pose

TITLES = dict(main="BLIZNIAK DWULOKALOWY",
              sub="4 LOKALE | 2 SEGMENTY | 2 KONDYGNACJE",
              end="MODEL KONCEPCYJNY | DO WERYFIKACJI Z DOKUMENTACJA")

def _shot(name,points,caption,seconds=2.0,lens=22,exp=.40):
    return dict(name=name,sec=seconds,lens=(lens,lens),fstop=10,
                exp=exp,caption=caption,ease=(0.0,0.0),wp=points)

SHOTS = [
    _shot("exterior_front",[((24,-23,10),(0,4.4,2.8)),((13,-17,7),(0,4.4,2.7))],
          "CALY BUDYNEK | 4 NIEZALEZNE LOKALE",3.4,28),
    _shot("stair_A",[((-15,5.6,4.6),(-8.6,7,2.5)),((-11,5.1,4.2),(-8.7,7.6,2.3))],
          "SCHODY ZEWN. | SEGMENT A",2.2,25),
    _shot("stair_B",[((15,5.6,4.6),(8.6,7,2.5)),((11,5.1,4.2),(8.7,7.6,2.3))],
          "SCHODY ZEWN. | SEGMENT B",2.2,25),
]
# Split the film by apartment: A-ground, B-ground, A-upper, B-upper.
for segment in ("A","B"):
    for level in ("ground","upper"):
        for room in ROOMS:
            d=ROOM_META[room]
            if d["segment"]!=segment or d["level"]!=level:
                continue
            p,t,lens=room_camera_pose(room)
            x0,x1,y0,y1,z0,z1=ROOMS[room]
            # The camera translates only 0.16m and pans to avoid penetrating geometry.
            # Move INWARD from the nearest wall, never sideways through it.
            shift = .12 if p[0] < (x0+x1)/2 else (-.12 if p[0] > (x0+x1)/2 else 0.0)
            q=(p[0]+shift,p[1]+.06,p[2])
            t2=(t[0]+(0.23 if segment=="A" else -0.23),t[1],t[2])
            SHOTS.append(_shot("visit_"+room,[(p,t),(q,t2)],
              "SEGMENT %s | %s | %s" % (segment,level.upper(),d["name"].upper()),
              2.1,lens,.42))
BY_NAME={s["name"]:s for s in SHOTS}
assert len(SHOTS)==27 and len(BY_NAME)==27
