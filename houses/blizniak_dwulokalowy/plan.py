"""Concept geometry of four independent dwellings, from KORMET-PROJEKT's four-sheet PDF.

Coordinates: x horizontal across front elevation, y front-to-rear, z above ground (metres).
A and B are mirrors. Plans, dimensions and areas are NOT a certified BIM reconstruction.
Measured directly from visible dimension strings: 15.87 total x, 7.34 internal x per wing,
0.41 party wall, lower floor ±0.00, upper ±2.93, outer staircase upper threshold +3.01.
Interiors and openings are traced at concept fidelity; exact partition coordinates unverified.
"""
X_MIN, X_MAX = -7.935, 7.935
X_INNER_LEFT, X_INNER_RIGHT = -7.545, 7.545
PARTY_HALF = 0.205
WING_INNER_WIDTH = 7.34
Y_FRONT, Y_REAR = 0.0, 9.44
Y_IN_FRONT, Y_IN_REAR = 0.27, 9.17
Z_GND, Z_UP = 0.0, 2.93
Z_LOWER_CEIL, Z_UPPER_CEIL = 2.69, 5.62
Z_ROOF, Z_PARAPET = 5.90, 6.30
Z_UPPER_LANDING = 3.01
WALL_T = 0.10
PARTITION_Y = 5.27

# Every area below is read from the PDF room schedule, not calculated from our conceptual boxes.
GROUND = (
    ("1", "wiatrolap", 2.47, "tile", (1.60, 3.75, 7.70, 9.17)),
    ("2", "pom_gospodarcze", 2.27, "tile", (0.00, 1.60, 7.70, 9.17)),
    ("3", "przedpokoj", 4.02, "wood", (2.40, 3.75, 5.27, 7.70)),
    ("4", "lazienka", 5.23, "tile", (0.00, 2.40, 5.27, 7.70)),
    ("5", "pokoj_tyl", 13.55, "wood", (3.75, 7.34, 5.27, 9.17)),
    ("6", "salon_z_aneksem", 21.43, "wood", (2.50, 7.34, 0.27, 5.27)),
    ("7", "pokoj_przod", 11.35, "wood", (0.00, 2.50, 0.27, 5.27)),
)
UPPER = (
    ("1", "wiatrolap", 4.86, "tile", (0.00, 2.40, 7.70, 9.17)),
    ("2", "lazienka", 5.23, "tile", (0.00, 2.40, 5.27, 7.70)),
    ("3", "przedpokoj", 4.02, "wood", (2.40, 3.75, 5.27, 9.17)),
    ("4", "pokoj_tyl", 13.55, "wood", (3.75, 7.34, 5.27, 9.17)),
    ("5", "salon_z_aneksem", 33.32, "wood", (0.00, 7.34, 0.27, 5.27)),
)
LEVEL_Z = {"ground": Z_GND, "upper": Z_UP}
PROGRAM = {"ground": GROUND, "upper": UPPER}
PDF_TOTALS_M2 = {"ground": 60.32, "upper": 60.98}


def seg_interval(segment, u0, u1):
    """Map outer-to-inner local u interval onto x; mirrored for segment B."""
    if segment == "A":
        return (X_INNER_LEFT + u0, X_INNER_LEFT + u1)
    if segment == "B":
        return (X_INNER_RIGHT - u1, X_INNER_RIGHT - u0)
    raise ValueError(segment)


def segment_wall_span(segment):
    return (X_MIN, -PARTY_HALF) if segment == "A" else (PARTY_HALF, X_MAX)


def room_id(segment, level, no):
    return segment + "_" + level + "_" + no


ROOM_META, ROOMS = {}, {}
for segment in ("A", "B"):
    for level, entries in PROGRAM.items():
        for no, name, area, finish, (u0, u1, y0, y1) in entries:
            x0, x1 = seg_interval(segment, u0, u1)
            key = room_id(segment, level, no)
            z0 = LEVEL_Z[level]
            z1 = Z_LOWER_CEIL if level == "ground" else Z_UPPER_CEIL
            ROOMS[key] = (x0, x1, y0, y1, z0, z1)
            ROOM_META[key] = dict(segment=segment, level=level, no=no, name=name,
                                  area_pdf_m2=area, finish=finish, local_bounds=(u0, u1, y0, y1))


def validate_program():
    assert len(ROOMS) == 24 and len(set(ROOMS)) == 24
    assert abs((X_MAX - X_MIN) - 15.87) < 1e-6
    for level, entries in PROGRAM.items():
        assert abs(sum(entry[2] for entry in entries) - PDF_TOTALS_M2[level]) < 0.011
    for x0, x1, y0, y1, z0, z1 in ROOMS.values():
        assert x0 < x1 and y0 < y1 and z0 < z1
    assert Z_GND < Z_UP < Z_ROOF


validate_program()
