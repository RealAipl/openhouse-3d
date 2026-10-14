"""OpenHouse 3D project: complete four-apartment semi-detached concept, all floors."""
from .plan import *
from .shots import SHOTS, BY_NAME, TITLES

NAME = "blizniak_dwulokalowy"
TITLE = "Blizniak dwulokalowy - 4 lokale"
BLEND = NAME + ".blend"
MODULES = ["architecture", "interiors", "site"]

SKY = dict(sun_dir=(-0.65, -0.48, 0.70), sun_energy=2.4,
           sun_color=(1.0, 0.93, 0.83), strength=0.55, sun_elevation=0.9)
EXT = ["hero", "front", "rear", "top", "stairs_left", "stairs_right"]
EXPOSURE_DEFAULT = {"ext": 0.25, "int": 0.40}
EXPOSURE = {}
DOF = {}
PHOTO_PAIRS = []
GRASS = []
PROBE_WALLS = []


def materials():
    from archviz import materials as m
    M = m.build_materials(perf_z0=Z_UP + 0.1)
    M.update({
        "facade": m.plaster("BliZniak_Tynk_Piaskowy", base=(0.69, 0.69, 0.65, 1), rough=0.82, grain=0.08),
        "party": m.plaster("BliZniak_WhiteInterior", base=(0.89, 0.88, 0.84, 1), rough=0.88, grain=0.05),
        "rail": m.new_mat("BliZniak_Antracyt_Railing", (0.08, 0.10, 0.11, 1), rough=0.38, metal=0.55),
        "wood_floor": m.wood_planks("BliZniak_Oak", light=(0.61, 0.43, 0.28, 1),
                                    dark=(0.42, 0.30, 0.19, 1), plank=(1.4, 0.14), rough=0.40),
        "tile_floor": m.tiles("BliZniak_Ceramic", (0.66, 0.65, 0.61, 1),
                               grout=(0.43, 0.44, 0.43, 1), size=(0.6, 0.6), rough=0.55),
        "soft": m.new_mat("BliZniak_Upholstery", (0.56, 0.59, 0.58, 1), rough=0.85),
        "wood": m.new_mat("BliZniak_Woodwork", (0.45, 0.30, 0.19, 1), rough=0.48),
        "kitchen": m.new_mat("BliZniak_Cabinets", (0.83, 0.80, 0.74, 1), rough=0.40),
        "stone": m.new_mat("BliZniak_Slabs", (0.57, 0.57, 0.55, 1), rough=0.8),
        "roof": m.new_mat("BliZniak_Roof", (0.29, 0.31, 0.34, 1), rough=0.88),
        "door": m.new_mat("BliZniak_Door", (0.16, 0.18, 0.19, 1), rough=0.45),
    })
    return M


CAMS = {
    "hero": ((23.0, -23.0, 10.5), (0.0, 4.4, 2.7), 27),
    "front": ((0.0, -25.0, 4.0), (0.0, 4.3, 2.8), 34),
    "rear": ((0.0, 31.0, 6.3), (0.0, 4.3, 2.8), 31),
    "top": ((0.0, -11.0, 28.0), (0.0, 4.4, 1.9), 29),
    "stairs_left": ((-17.0, 9.5, 5.8), (-8.7, 7.8, 2.1), 29),
    "stairs_right": ((17.0, 9.5, 5.8), (8.7, 7.8, 2.1), 29),
}
# A fixed camera for every documented room, including small service rooms.
for room, (x0, x1, y0, y1, z0, z1) in ROOMS.items():
    cx, cy = (x0+x1)/2, (y0+y1)/2
    CAMS["room_" + room] = ((cx, cy - 0.24, z0 + 1.55),
                             (cx + (-0.6 if cx>0 else 0.6), cy + 0.48, z0 + 1.43), 19)

