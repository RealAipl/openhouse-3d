"""Reopen the delivered scene without rendering and verify portability."""
import json
from pathlib import Path

import bpy

scene = bpy.context.scene
out = Path(__file__).resolve().parents[1] / "houses/blizniak_dwulokalowy/output/salon_v4"
report = json.loads((out / "asset_report.json").read_text())
assert scene.camera.name == "V4_SalonCamera"
assert scene.render.engine == "CYCLES"
assert (scene.render.resolution_x, scene.render.resolution_y) == (1920, 1080)
assert scene.cycles.samples == 192 and scene.cycles.use_denoising
assert len(report["models"]) == 14
assert report["preserved_original_meshes"] >= 50
assert not report["missing_images"]
used_images = [im for im in bpy.data.images if im.source == "FILE" and im.users > 0]
assert used_images and all(im.packed_file is not None for im in used_images)
print("REOPEN_OK", len(used_images), "packed images", len(report["models"]), "instances")
