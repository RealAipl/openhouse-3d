"""Actual Blender mesh construction: two floors, full twin envelope, openings, two external stairs.

All dimensions are in metres; see plan.py for PDF-versus-inferred uncertainty.
"""
from .plan import *
from archviz.mesh import MB


def _window_holes(segment, level, facade):
    z = LEVEL_Z[level]
    if facade == "front":
        spans = ((0.38,1.86), (2.66,4.11), (4.88,6.34)) if level == "upper" else (
                 (0.38,1.83), (2.65,4.14), (4.82,6.32))
        return sorted((seg_interval(segment, a,b)[0], seg_interval(segment,a,b)[1],
                       z + (0.825 if level=="upper" else (0.05 if a>2.5 else 0.825)),
                       z + (2.31 if level=="upper" else (2.32 if a>2.5 else 2.31)))
                      for a,b in spans)
    if facade == "rear":
        spans = ((2.05,2.96,0.0,2.18), (4.77,6.27,0.825,2.31)) if level == "ground" else (
                 (4.77,6.27,0.825,2.31),)
        return sorted((seg_interval(segment,a,b)[0],seg_interval(segment,a,b)[1],
                       z+z0,z+z1) for a,b,z0,z1 in spans)
    raise ValueError(facade)


def _make_walls(M):
    shell = MB()
    shell.box(X_MIN,X_MAX,Y_FRONT,Y_REAR,-0.21,0)
    shell.box(X_MIN,X_MAX,Y_FRONT,Y_REAR,Z_LOWER_CEIL,Z_UP)
    shell.box(X_MIN-0.03,X_MAX+0.03,Y_FRONT-0.03,Y_REAR+0.03,
              Z_UPPER_CEIL,Z_ROOF)
    shell.box(-PARTY_HALF,PARTY_HALF,Y_FRONT,Y_REAR,Z_GND,Z_UPPER_CEIL)
    for segment in ("A","B"):
        sx0,sx1=segment_wall_span(segment)
        for level in ("ground","upper"):
            z0=LEVEL_Z[level]
            z1=Z_LOWER_CEIL if level=="ground" else Z_UPPER_CEIL
            shell.wall("X",sx0,sx1,Y_FRONT,Y_IN_FRONT,z0,z1,
                       holes=_window_holes(segment,level,"front"))
            shell.wall("X",sx0,sx1,Y_IN_REAR,Y_REAR,z0,z1,
                       holes=_window_holes(segment,level,"rear"))
    # Only the two outer flanks have the external-stair entry doors at upper level.
    shell.wall("Y",Y_FRONT,Y_REAR,X_MIN,X_INNER_LEFT,Z_GND,Z_LOWER_CEIL)
    shell.wall("Y",Y_FRONT,Y_REAR,X_INNER_RIGHT,X_MAX,Z_GND,Z_LOWER_CEIL)
    for a,b in ((X_MIN,X_INNER_LEFT),(X_INNER_RIGHT,X_MAX)):
        shell.wall("Y",Y_FRONT,Y_REAR,a,b,Z_UP,Z_UPPER_CEIL,
                   holes=[(7.76,8.68,Z_UP,Z_UP+2.20)])
    shell.build("BLI_Envelope_2_levels_4_units", [M["facade"]])
    parapet=MB()
    parapet.box(X_MIN-0.03,X_MAX+0.03,-0.03,0.19,Z_ROOF,Z_PARAPET)
    parapet.box(X_MIN-0.03,X_MAX+0.03,Y_REAR-0.19,Y_REAR+0.03,Z_ROOF,Z_PARAPET)
    parapet.box(X_MIN-0.03,X_MIN+0.17,0,Y_REAR,Z_ROOF,Z_PARAPET)
    parapet.box(X_MAX-0.17,X_MAX+0.03,0,Y_REAR,Z_ROOF,Z_PARAPET)
    parapet.build("BLI_Flat_Roof_Parapet",[M["facade"]])
    # Roof ventilation features are simplified, sourced from elevations.
    vent=MB()
    for x in (-4.2, -0.42, 0.42, 4.2):
        vent.box(x-.12,x+.12,5.6,5.88,Z_ROOF,Z_ROOF+.47)
    vent.build("BLI_Roof_Vents",[M["rail"]])


def _make_glazing(M):
    glass=MB(); frames=MB(); doors=MB()
    for segment in ("A","B"):
        for level in ("ground","upper"):
            for face,y in (("front",Y_IN_FRONT*.51),("rear",Y_REAR+.11)):
                for x0,x1,z0,z1 in _window_holes(segment,level,face):
                    if z0==LEVEL_Z[level] and face=="rear":
                        doors.box(x0+.04,x1-.04,y-.03,y+.03,z0+.015,z1-.02)
                    else:
                        glass.box(x0+.022,x1-.022,y-.012,y+.012,z0+.02,z1-.02)
                    frames.frame(x0,x1,y-.035,y+.035,z0,z1,.052,axis="Y")
                    if x1-x0>1.28:
                        x=(x0+x1)/2
                        frames.box(x-.018,x+.018,y-.045,y+.045,z0,z1)
        # Side entrance to the first-floor independent dwelling.
        x = X_MIN+.15 if segment=="A" else X_MAX-.15
        doors.box(x-.028,x+.028,7.79,8.65,Z_UP+.02,Z_UP+2.16)
        frames.frame(x-.045,x+.045,7.76,8.68,Z_UP,Z_UP+2.20,.045,axis="X")
    glass.build("BLI_Clear_Glazing",[M["glass"]])
    frames.build("BLI_Anthracite_Window_Frames",[M["rail"]])
    doors.build("BLI_External_Entry_Doors",[M["door"]])


def _external_stair(M, sign):
    """Two-flight switchback at each lateral façade; risers and landing are visually explicit."""
    b=MB()
    stair_inner=7.99; near0,near1=8.03,9.12; far0,far1=9.27,10.36
    yy0, yy1 = 6.08,8.50
    n=8; half=Z_UPPER_LANDING/2; riser=half/n
    def X(a,b): return (a,b) if sign==1 else (-b,-a)
    # Flight one: forward (towards rear), lower half.
    for i in range(n):
        y0=yy0+(yy1-yy0)*i/n; y1=yy0+(yy1-yy0)*(i+1)/n
        z=(i+1)*riser
        a,c=X(far0,far1)
        b.box(a,c,y0,y1,z-.16,z)
    # Continuous middle platform connects the two flights.
    a,c=X(near0,far1)
    b.box(a,c,yy1,yy1+.78,half-.16,half)
    # Flight two reverses direction and terminates at the upper side landing.
    for i in range(n):
        y0=yy1-(yy1-yy0)*(i+1)/n; y1=yy1-(yy1-yy0)*i/n
        z=half+(i+1)*riser
        a,c=X(near0,near1)
        b.box(a,c,y0,y1,z-.16,z)
    a,c=X(stair_inner,near1)
    b.box(a,c,5.83,8.87,Z_UPPER_LANDING-.12,Z_UPPER_LANDING)
    b.build("BLI_External_Stair_" + ("R" if sign==1 else "L"),[M["stone"]])
    rail=MB()
    for ax in (near0,far1):
        x=sign*ax
        rail.tube((x,yy0,Z_UPPER_LANDING+.8),
                  (x,yy1,Z_UPPER_LANDING/2+.95),.032,.032)
    for ax in (near0,far1):
        x=sign*ax
        rail.tube((x,yy0,.88), (x,yy1,half+.88),.028,.028)
    for yy in (5.83,7.2,8.85):
        rail.tube((sign*stair_inner,yy,Z_UPPER_LANDING),
                  (sign*stair_inner,yy,Z_UPPER_LANDING+1.05),.03,.03)
    rail.tube((sign*stair_inner,5.83,Z_UPPER_LANDING+1.05),
              (sign*stair_inner,8.85,Z_UPPER_LANDING+1.05),.03,.03)
    rail.build("BLI_Stair_Railings_" + ("R" if sign==1 else "L"),[M["rail"]])


def build(M):
    _make_walls(M)
    _make_glazing(M)
    _external_stair(M,-1)
    _external_stair(M,1)
