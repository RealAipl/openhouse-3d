"""Minimal neutral site; no paid assets. This is not a landscape proposal."""
from .plan import *
from archviz.mesh import MB

def build(M):
    land=MB()
    land.box(-36,36,-36,36,-.31,-.22)
    land.build("BLI_Site_Ground",[M["ground"]],coll="Site")
    paving=MB()
    paving.box(-12.0,12.0,-5.0,-1.2,-.22,-.185)
    for x in (-5.3,5.3):
        paving.box(x-.85,x+.85,Y_REAR,Y_REAR+3.2,-.22,-.175)
    paving.build("BLI_Walkways",[M["pavers"]],coll="Site")
    green=MB()
    green.box(-21,21,13.0,27.0,-.22,-.17)
    green.box(-21,21,-23,-6.0,-.22,-.17)
    green.build("BLI_Lawn",[M["lawn"]],coll="Site")
