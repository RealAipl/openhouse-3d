"""Walkthrough storyboard: external establishing shots plus every scheduled room (all 24)."""
from .plan import ROOMS, ROOM_META

TITLES = dict(main="BLIZNIAK DWULOKALOWY",
              sub="4 MIESZKANIA | 2 SEGMENTY | 2 KONDYGNACJE",
              end="WIZUALIZACJA KONCEPCYJNA - UKLAD WG RZUTOW")

def _shot(name,points,caption,seconds=2.0,lens=22):
    return dict(name=name,sec=seconds,lens=(lens,lens),fstop=9,
                exp=0.35,caption=caption,ease=(0.05,0.05),wp=points)

SHOTS = [
    _shot("exterior_front",[((23,-22,10),(0,4.4,2.9)),((12,-17,7),(0,4.4,2.8))],
          "CALY BUDYNEK | 4 LOKALE",3.5,28),
    _shot("stair_A",[((-15,5.6,4.5),(-8.5,7,2.4)),((-11,5.1,4.0),(-8.7,7.8,2.2))],
          "SCHODY ZEWN. | SEGMENT A",2.0,25),
    _shot("stair_B",[((15,5.6,4.5),(8.5,7,2.4)),((11,5.1,4.0),(8.7,7.8,2.2))],
          "SCHODY ZEWN. | SEGMENT B",2.0,25),
]
for room,(x0,x1,y0,y1,z0,z1) in ROOMS.items():
    d=ROOM_META[room]; cx,cy=(x0+x1)/2,(y0+y1)/2
    offset=min(.35,max(.09,(y1-y0)/8))
    pts=[((cx,cy-offset,z0+1.57),(cx,cy+.38,z0+1.35)),
         ((cx+.12,cy,z0+1.57),(cx-.42,cy+.20,z0+1.38))]
    SHOTS.append(_shot("visit_"+room,pts,
                ("SEGMENT %s | %s | %s" %(d["segment"],d["level"].upper(),d["name"].upper())).replace("_"," ")))
BY_NAME={shot["name"]:shot for shot in SHOTS}
