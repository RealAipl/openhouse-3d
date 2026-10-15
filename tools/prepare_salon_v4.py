"""Prepare only audited assets and a few existing-library PBR sets."""
import hashlib
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.audit_salon_v4 import BASE, EXPECTED, PACK, PREFIX, PREVIOUS, digest, get
from tools.household_models_v4 import safe_relative

OUT = ROOT / "houses/blizniak_dwulokalowy/output/salon_v4"
MODEL_IDS = [
    "haven-224-oatmeal-two-seat-sofa-40262c27",
    "ember-leather-and-walnut-lounge-chair-9b9f3689",
    "trio-nesting-coffee-table-set-a1a295a4",
    "trace-180-walnut-sideboard-32858583",
    "span-225-extendable-dining-table-b5cc7e64",
    "gather-dining-armchair-ee459660",
    "paper-column-paper-column-floor-lamp-3b5a06e7",
    "basket-woven-basket-pendant-baacdf33",
    "brass_vase_01",
    "tea_set_01",
]


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    receipt = OUT / "v4_audit.json"
    get(PREFIX + "salon-v4-premium-20261015/v4_audit.json", receipt)
    audit = json.loads(receipt.read_text())
    assert audit["archive_sha256"] == EXPECTED and audit["models"] == 120
    archive = BASE / "V4.zip"
    get(PREFIX + "household-models-cc0-v4/OpenHouse_Household_Models_V4_CC0.zip", archive)
    assert digest(archive) == EXPECTED
    with zipfile.ZipFile(archive) as z:
        for n in z.namelist():
            safe_relative(n)
        z.extractall(PACK)
    models = []
    for key in MODEL_IDS:
        a = next(a for a in audit["assets"] if a["id"] == key)
        assert a["license"] == "CC0-1.0"
        assert digest(PACK / a["file"]) == a["sha256"]
        models.append(a)
    mats = []
    for version, url in PREVIOUS:
        dest = BASE / (version + ".json")
        get(PREFIX + url, dest)
        d = json.loads(dest.read_text())
        for a in d["assets"]:
            if a.get("kind", a.get("type")) in ("material", "materials", "textures"):
                mats.append({**a, "library": version})
    # Each role is selected from actual previous manifests, not from a new catalog.
    chosen = {
        "floor": ("V2", "wood_floor"),
        "walls": ("V3", "PaintedPlaster003"),
        "rug": ("V3", "Carpet003"),
        "walnut": ("V2", "american_walnut_veneer"),
    }
    v1_fabric = [a for a in mats if a["library"] == "V1" and
                 any(w in a["id"].lower() for w in ("linen", "fabric", "cotton"))]
    if not v1_fabric:
        raise ValueError("V1 fabric material missing")
    fabric = sorted(v1_fabric, key=lambda a: (not ("linen" in a["id"]), a["id"]))[0]
    chosen["curtains"] = ("V1", fabric["id"])
    prepared = {}
    for role, (version, key) in chosen.items():
        a = next(a for a in mats if a["id"] == key and a["library"] == version)
        folder = BASE / "materials" / role
        folder.mkdir(parents=True, exist_ok=True)
        files = []
        if a.get("provider", "Poly Haven") == "Poly Haven":
            for f in a["files"]:
                rel = f.get("relative", f.get("path"))
                safe_relative(rel)
                if rel.endswith(".blend"):
                    continue
                p = folder / Path(rel).name
                get(f["url"], p)
                assert p.stat().st_size == f["bytes"]
                if f.get("md5"):
                    assert hashlib.md5(p.read_bytes()).hexdigest() == f["md5"]
                files.append({"file": str(p.relative_to(ROOT)), "sha256": digest(p), "source_url": f["url"]})
        else:
            p = folder / (key + ".zip")
            get(a["download_url"], p)
            assert p.stat().st_size == a["bytes"]
            with zipfile.ZipFile(p) as z:
                assert z.testzip() is None
                for n in z.namelist():
                    safe_relative(n)
                z.extractall(folder)
            for f in sorted(folder.iterdir()):
                if f.suffix.lower() in (".jpg", ".png", ".exr"):
                    files.append({"file": str(f.relative_to(ROOT)), "sha256": digest(f),
                                  "source_url": a["download_url"]})
        assert any("diff" in f["file"].lower() or "color" in f["file"].lower() for f in files)
        assert any("rough" in f["file"].lower() for f in files)
        prepared[role] = {**a, "resolved_files": files}
        print("PBR_SELECTED", role, version, key, len(files), flush=True)
    (OUT / "prepared_assets.json").write_text(json.dumps({"models": models, "materials": prepared}, indent=2))


if __name__ == "__main__":
    main()
