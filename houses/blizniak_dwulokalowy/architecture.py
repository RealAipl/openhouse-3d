"""Actual Blender mesh construction: two floors, full twin envelope, openings, two external stairs.

All dimensions are in metres; see plan.py for PDF-versus-inferred uncertainty.
"""
from .plan import *
from archviz.mesh import MB


def _window_holes(segment, level, facade):
    z = LEVEL_Z[level]
    if facade == "front":
        spans = ((0.68, 2.18), (3.065, 4.565), (5.22, 6.72))
        return sorted((seg_interval(segment, a,b)[0], seg_interval(segment,a,b)[1],
                       z + (0.825 if level == "upper" or a < 2.5 else 0.0),
                       z + 2.125) for a,b in spans)
    if facade == "rear":
        spans = ((2.17,3.17,0.0,2.00), (4.77,6.27,0.825,2.125)) if level == "ground" else (
                 (4.77,6.27,0.825,2.125),)
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
                   holes=[(7.85,8.85,Z_UP,Z_UP+2.03)])
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
            for face,y in (("front",Y_IN_FRONT*.51),("rear",Y_REAR-.195)):
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
        doors.box(x-.028,x+.028,7.88,8.82,Z_UP+.02,Z_UP+2.00)
        frames.frame(x-.045,x+.045,7.85,8.85,Z_UP,Z_UP+2.03,.045,axis="X")
    glass.build("BLI_Clear_Glazing",[M["glass"]])
    frames.build("BLI_Anthracite_Window_Frames",[M["rail"]])
    doors.build("BLI_External_Entry_Doors",[M["door"]])


def _external_stair(M, sign):
    """Mirrored 2-flight switchback with genuine 3D clearance and upper entry access.

    Drawing shows side switchback stairs to four independent dwellings. Exact
    pitch, landings and railing assembly are concept interpretations.
    """
    mesh=MB()
    near=(8.03,9.12)
    far=(9.27,10.36)
    n=8
    lower,upper=5.55,8.02
    middle=Z_UPPER_LANDING/2
    step_h=middle/n

    def xr(a,b):
        return (a,b) if sign==1 else (-b,-a)

    # Outer flight: ground entrance at y=8.02, climbing towards y=5.55.
    for i in range(n):
        ya=upper-(upper-lower)*(i+1)/n
        yb=upper-(upper-lower)*i/n
        z=(i+1)*step_h
        a,b=xr(*far)
        mesh.box(a,b,ya,yb,max(-.01,z-.155),z)

    # U-turn mid-landing, with adequate tread depth.
    a,b=xr(near[0],far[1])
    mesh.box(a,b,4.94,lower,middle-.16,middle)

    # Inner flight returns towards the dwelling at y=8.02.
    for i in range(n):
        ya=lower+(upper-lower)*i/n
        yb=lower+(upper-lower)*(i+1)/n
        z=middle+(i+1)*step_h
        a,b=xr(*near)
        mesh.box(a,b,ya,yb,z-.155,z)

    # Small landing in front of upstairs entry y=7.76..8.68.
    a,b=xr(7.94,near[1])
    mesh.box(a,b,upper,8.87,Z_UPPER_LANDING-.15,Z_UPPER_LANDING)
    mesh.build("BLI_External_Stair_"+("R" if sign==1 else "L"),[M["stone"]])

    rail=MB()
    # Sloped handrails and real vertical posts on the open edges.
    for axis,y_start,y_stop,z_start,z_stop in (
        (far[1],upper,lower,0,middle),
        (near[1],lower,upper,middle,Z_UPPER_LANDING),
    ):
        x=sign*axis
        for k in range(5):
            t=k/4
            y=y_start+(y_stop-y_start)*t
            z=z_start+(z_stop-z_start)*t
            rail.tube((x,y,z),(x,y,z+.98),.022,.022)
        rail.tube((x,y_start,z_start+.98),(x,y_stop,z_stop+.98),.034,.034)
    x=sign*near[1]
    for y in (8.05,8.46,8.83):
        rail.tube((x,y,Z_UPPER_LANDING),(x,y,Z_UPPER_LANDING+1.0),.026,.026)
    rail.tube((x,8.05,Z_UPPER_LANDING+1.0),(x,8.83,Z_UPPER_LANDING+1.0),.034,.034)
    rail.build("BLI_Switchback_Rails_"+("R" if sign==1 else "L"),[M["rail"]])


def build(M):
    _make_walls(M)
    _make_glazing(M)
    _external_stair(M,-1)
    _external_stair(M,1)
