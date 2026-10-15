"""Audit the published V4 bytes in a free GitHub-hosted runner."""
import hashlib
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.household_models_v4 import safe_relative, validate_glb, validate_scan

BASE = ROOT / "tmp" / "salon-v4"
PACK = BASE / "pack"
OUT = ROOT / "houses/blizniak_dwulokalowy/output/salon_v4"
OUT.mkdir(parents=True, exist_ok=True)
BASE.mkdir(parents=True, exist_ok=True)
PREFIX = "https://github.com/RealAipl/openhouse-3d/releases/download/"
PREVIOUS = [
    ("V1", "luxoria-interior-megapack-cc0-v1/LUXORIA_Manifest_Licencje_i_Zrodla.json"),
    ("V2", "luxoria-home-interiors-cc0-v2/MANIFEST_V2.json"),
    ("V3", "luxoria-home-interiors-cc0-v3/MANIFEST_V3.json"),
]
EXPECTED = "e67481101828ace86e8aefa5fe1d112078a60a06663ac6a4b6df3ea2cc2a6509"


def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def get(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "OpenHouse3D-SalonAudit/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r, path.open("wb") as f:
        while b := r.read(1048576):
            f.write(b)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def main():
    archive = BASE / "V4.zip"
    get(PREFIX + "household-models-cc0-v4/OpenHouse_Household_Models_V4_CC0.zip", archive)
    assert archive.stat().st_size == 858333380
    assert digest(archive) == EXPECTED, "Release SHA-256 mismatch"
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for n in z.namelist():
            safe_relative(n)
        z.extractall(PACK)
    checks = 0
    for line in (PACK / "SHA256SUMS.txt").read_text().splitlines():
        sha, rel = line.split("  ", 1)
        safe_relative(rel)
        assert digest(PACK / rel) == sha, rel
        checks += 1
    doc = json.loads((PACK / "MANIFEST_V4.json").read_text())
    assert len(doc["assets"]) == 120 and doc["license"] == "CC0-1.0"
    older, versions = [], []
    for version, url in PREVIOUS:
        dest = BASE / (version + ".json")
        get(PREFIX + url, dest)
        previous = json.loads(dest.read_text())
        older.extend(previous["assets"])
        versions.append({"version": version, "url": PREFIX + url, "sha256": digest(dest),
                         "items": len(previous["assets"])})
    prior_ids = {norm(a["id"]) for a in older}
    prior_titles = {norm(a.get("title", a.get("name", ""))) for a in older}
    catalog = json.loads((ROOT / "docs/assets/household-v4-candidates.json").read_text())
    old_hashes = set(catalog.get("previous_sha256", []))
    for a in older:
        if a.get("sha256"):
            old_hashes.add(a["sha256"])
    hashes, ids, rows = set(), set(), []
    for a in doc["assets"]:
        p = PACK / a["file"]
        sha = digest(p)
        assert sha == a["sha256"] and p.stat().st_size == a["bytes"]
        assert a["license"] == "CC0-1.0"
        assert sha not in hashes and sha not in old_hashes
        assert norm(a["id"]) not in ids and norm(a["id"]) not in prior_ids
        if a["provider"] == "Poly Haven":
            assert norm(a["title"]) not in prior_titles
        hashes.add(sha)
        ids.add(norm(a["id"]))
        stats = validate_glb(p) if p.suffix == ".glb" else validate_scan(p)
        assert stats["triangles"] == a["triangles"]
        rows.append({**a, "verified_geometry": stats})
        print("MODEL", a["id"], stats["triangles"], "tris", flush=True)
    licenses = json.loads((PACK / "licenses/LICENSE_EVIDENCE.json").read_text())
    for evidence in licenses:
        req = urllib.request.Request(evidence["url"], headers={"User-Agent": "OpenHouse3D-SalonAudit/1.0"})
        with urllib.request.urlopen(req, timeout=90) as r:
            page = r.read()
            assert r.status == 200 and b"CC0" in page
            evidence["rechecked_http"] = r.status
            evidence["rechecked_sha256"] = hashlib.sha256(page).hexdigest()
    mats = []
    for version, _ in PREVIOUS:
        d = json.loads((BASE / (version + ".json")).read_text())
        for a in d["assets"]:
            if a.get("kind") in ("material", "materials", "textures"):
                mats.append({**a, "library": version})
    report = {"archive_sha256": EXPECTED, "checked_files": checks, "models": len(rows),
              "duplicate_ids": 0, "duplicate_bytes": 0, "previous_manifests": versions,
              "license_evidence": licenses, "assets": rows, "materials_available": mats,
              "limits": "Structural and checksum audit of every V4 item. Blender import/render is tested only for the selected salon models. Similar designs with different geometry are not guaranteed absent. Provider previews are not republished."}
    (OUT / "v4_audit.json").write_text(json.dumps(report, indent=2))
    print("AUDIT_OK", len(rows), "models", checks, "files", "zero ID/binary duplicates", flush=True)
    print("SALON_CANDIDATES", json.dumps([{"id": a["id"], "triangles": a["triangles"],
          "images": a.get("embedded_images"), "title": a["title"]}
          for a in rows if a["category"] in ("furniture", "lighting", "decor")]), flush=True)
    print("PBR_CANDIDATES", json.dumps([{"id": a["id"], "library": a["library"],
          "provider": a["provider"], "group": a.get("group")} for a in mats
          if re.search("wood|floor|plaster|fabric|marble|carpet", a["id"], re.I)]), flush=True)
    print("MATERIAL_SCHEMA", json.dumps(mats[:2]), flush=True)


if __name__ == "__main__":
    main()
