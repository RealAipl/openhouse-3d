#!/usr/bin/env python3
"""Download an audited models-only CC0 catalog and build one verified release ZIP.

Never executes model scripts, renders a movie, or modifies a house. A candidate
is not a delivered asset: only complete, validated downloads enter the manifest.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import html
import io
import json
import shutil
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
from PIL import Image, ImageDraw, ImageOps

UA = "OpenHouse3D-AssetAudit/1.0"
MIN_TRIANGLES = 10000
MAX_FILE_BYTES = 150_000_000
MAX_ARCHIVE_BYTES = 1_950_000_000
LICENSE_URLS = {
    "Innerscene": "https://www.innerscene.com/tools/library/terms",
    "ambientCG": "https://docs.ambientcg.com/license/",
    "Poly Haven": "https://polyhaven.com/license",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def thumbnail_rgb(source):
    """Composite source alpha; never reveal hidden RGB texels in transparent pixels."""
    rgba = source.convert("RGBA")
    background = Image.new("RGB", rgba.size, "#f5f5f5")
    background.paste(rgba, mask=rgba.getchannel("A"))
    return background


def safe_relative(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value:
        raise ValueError(f"Unsafe archive path: {value}")
    return path


class Downloader:
    """Serial, cached requests; honor the source's three-second crawl delay."""

    def __init__(self):
        self.last_inner = 0.0

    def fetch(self, url, path, expected=None, expected_sha=None):
        if path.exists():
            if (expected is None or path.stat().st_size == expected) and (
                expected_sha is None or sha256(path) == expected_sha
            ):
                return
            raise ValueError(f"Existing cache does not match metadata: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(3):
            if urllib.parse.urlparse(url).hostname == "www.innerscene.com":
                time.sleep(max(0, 3.2 - (time.monotonic() - self.last_inner)))
                self.last_inner = time.monotonic()
            temporary = path.with_suffix(path.suffix + ".part")
            try:
                request = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(request, timeout=120) as source:
                    if source.status != 200:
                        raise ValueError(f"Unexpected HTTP status: {source.status}")
                    total = 0
                    with temporary.open("wb") as target:
                        while block := source.read(1024 * 1024):
                            total += len(block)
                            if total > MAX_FILE_BYTES:
                                raise ValueError("File exceeded download limit")
                            target.write(block)
                if expected is not None and total != expected:
                    raise ValueError("Downloaded size differs from source metadata")
                if expected_sha and sha256(temporary) != expected_sha:
                    raise ValueError("Downloaded SHA-256 differs from source metadata")
                temporary.replace(path)
                return
            except urllib.error.HTTPError as error:
                temporary.unlink(missing_ok=True)
                if error.code == 429 and attempt < 2:
                    delay = max(60, int(error.headers.get("Retry-After", "60")))
                    print(f"Source rate limit; waiting {delay}s", flush=True)
                    time.sleep(delay)
                    continue
                # In particular, never retry/bypass a 403 or count HTML as a model.
                raise
            except Exception:
                temporary.unlink(missing_ok=True)
                raise


def validate_glb(path):
    raw = path.read_bytes()
    if len(raw) < 28 or struct.unpack_from("<4sII", raw) != (b"glTF", 2, len(raw)):
        raise ValueError("Invalid or truncated GLB header")
    offset = 12
    chunks = []
    while offset < len(raw):
        length, kind = struct.unpack_from("<II", raw, offset)
        offset += 8
        if offset + length > len(raw):
            raise ValueError("GLB chunk exceeds file")
        chunks.append((kind, raw[offset:offset + length]))
        offset += length
    if offset != len(raw) or chunks[0][0] != 0x4E4F534A:
        raise ValueError("Missing GLB JSON chunk")
    doc = json.loads(chunks[0][1])
    binary = next((data for kind, data in chunks if kind == 0x004E4942), b"")
    if len(doc.get("buffers", [])) != 1 or "uri" in doc["buffers"][0]:
        raise ValueError("Model requires external buffer")
    if doc["buffers"][0]["byteLength"] > len(binary):
        raise ValueError("Truncated embedded buffer")
    for view in doc.get("bufferViews", []):
        if view.get("buffer", 0) != 0 or view.get("byteOffset", 0) + view["byteLength"] > len(binary):
            raise ValueError("Invalid buffer view")

    def accessor(index):
        item = doc["accessors"][index]
        if "sparse" in item:
            raise ValueError("Sparse accessor needs a separate verifier")
        widths = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
        types = {5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
        dtype = np.dtype(types[item["componentType"]])
        width = widths[item["type"]]
        view = doc["bufferViews"][item["bufferView"]]
        stride = view.get("byteStride", width * dtype.itemsize)
        relative = item.get("byteOffset", 0)
        end = relative + max(0, item["count"] - 1) * stride + width * dtype.itemsize
        if item["count"] <= 0 or end > view["byteLength"]:
            raise ValueError("Accessor exceeds buffer view")
        return np.ndarray((item["count"], width), dtype=dtype, buffer=binary,
                          offset=view.get("byteOffset", 0) + relative,
                          strides=(stride, dtype.itemsize))

    triangles = vertices = 0
    for mesh in doc.get("meshes", []):
        for primitive in mesh["primitives"]:
            if primitive.get("mode", 4) != 4:
                raise ValueError("Non-triangle primitive")
            positions = accessor(primitive["attributes"]["POSITION"])
            if positions.shape[1] != 3 or not np.isfinite(positions).all():
                raise ValueError("Invalid mesh positions")
            indices = accessor(primitive["indices"]).reshape(-1)
            if len(indices) % 3 or indices.max() >= len(positions):
                raise ValueError("Invalid triangle indices")
            if "material" not in primitive:
                raise ValueError("Mesh primitive has no material")
            triangles += len(indices) // 3
            vertices += len(positions)
    if triangles < MIN_TRIANGLES:
        raise ValueError(f"Below detail threshold: {triangles} triangles")
    if not doc.get("materials"):
        raise ValueError("No materials")
    dimensions = []
    for image in doc.get("images", []):
        if "uri" in image or "bufferView" not in image:
            raise ValueError("Image is not embedded")
        view = doc["bufferViews"][image["bufferView"]]
        start = view.get("byteOffset", 0)
        with Image.open(io.BytesIO(binary[start:start + view["byteLength"]])) as loaded:
            loaded.verify()
        with Image.open(io.BytesIO(binary[start:start + view["byteLength"]])) as loaded:
            dimensions.append(list(loaded.size))
    return {"triangles": triangles, "vertices": vertices,
            "meshes": len(doc["meshes"]), "materials": len(doc["materials"]),
            "embedded_images": len(dimensions), "image_dimensions": dimensions,
            "self_contained": True, "validation": "GLB chunks, bounds, finite positions, indices, materials and embedded images"}


def validate_scan(path):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Corrupt source ZIP")
        for info in archive.infolist():
            safe_relative(info.filename)
            if info.file_size > 400_000_000:
                raise ValueError("Unexpected inflated archive member")
        obj = next((n for n in archive.namelist() if n.lower().endswith(".obj")), None)
        if not obj:
            raise ValueError("Source archive has no verifiable OBJ geometry")
        vertices = triangles = 0
        names = set(archive.namelist())
        obj_parent = PurePosixPath(obj).parent
        for line in archive.read(obj).splitlines():
            fields = line.split()
            if not fields:
                continue
            if fields[0] == b"v":
                point = np.array([float(x) for x in fields[1:4]])
                if len(point) != 3 or not np.isfinite(point).all():
                    raise ValueError("Invalid OBJ vertex")
                vertices += 1
            elif fields[0] == b"mtllib":
                reference = (obj_parent / line.split(maxsplit=1)[1].decode()).as_posix()
                safe_relative(reference)
                if reference not in names:
                    raise ValueError("Missing OBJ material library")
            elif fields[0] == b"f":
                indices = [int(x.split(b"/")[0]) for x in fields[1:]]
                if len(indices) < 3 or any(i == 0 for i in indices):
                    raise ValueError("Invalid OBJ face")
                triangles += len(indices) - 2
        # OBJ allows forward references; validate against the final vertex count.
        for line in archive.read(obj).splitlines():
            if line.startswith(b"f "):
                if any(abs(int(x.split(b"/")[0])) > vertices for x in line.split()[1:]):
                    raise ValueError("OBJ vertex index outside mesh")
        if triangles < MIN_TRIANGLES:
            raise ValueError("Scan below geometry threshold")
        images = [n for n in archive.namelist() if n.lower().endswith((".jpg", ".png"))]
        if not images:
            raise ValueError("Missing scan textures")
        for name in images:
            with Image.open(io.BytesIO(archive.read(name))) as loaded:
                loaded.verify()
        for name in names:
            if name.lower().endswith(".mtl"):
                for line in archive.read(name).decode().splitlines():
                    fields = line.split()
                    if fields and (fields[0].startswith("map_") or fields[0] in ("bump", "disp")):
                        reference = (PurePosixPath(name).parent / fields[-1]).as_posix()
                        safe_relative(reference)
                        if reference not in names:
                            raise ValueError("Missing referenced MTL texture")
        return {"triangles": triangles, "vertices": vertices,
                "geometry_files": [n for n in archive.namelist() if n.lower().endswith((".obj", ".blend", ".fbx"))],
                "texture_files": images,
                "validation": "ZIP CRC, safe paths, OBJ finite vertices and face indices, decoded texture images"}


def build(catalog_path, destination, cache):
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if destination.exists():
        raise ValueError("Use a new output directory; existing packages are preserved")
    destination.mkdir(parents=True)
    downloader = Downloader()
    delivered, rejected, hashes = [], [], set()
    previous = set(catalog["previous_ids"])
    previous_hashes = set(catalog.get("previous_sha256", []))
    for candidate in catalog["candidates"]:
        asset = dict(candidate)
        try:
            if asset["license"] != "CC0-1.0" or asset["id"] in previous:
                raise ValueError("Unapproved license or duplicate of V1-V3")
            if asset["provider"] == "Innerscene" and (
                "low-poly" in asset.get("tags", []) or asset.get("source_name") != "Innerscene - original model"
            ):
                raise ValueError("Excluded low-poly or third-party model")
            relative = safe_relative(asset["file"])
            local = cache.joinpath(*relative.parts)
            if asset["provider"] == "Poly Haven":
                try:
                    from tools.gltf_embedded_glb import embed_gltf
                except ModuleNotFoundError:
                    from gltf_embedded_glb import embed_gltf
                source_root = cache / "polyhaven-original" / asset["id"]
                for source_file in asset["original_source_files"]:
                    source_rel = safe_relative(source_file["path"])
                    downloader.fetch(source_file["url"], source_root.joinpath(*source_rel.parts),
                                     source_file["bytes"], source_file["sha256"])
                if not local.exists():
                    embed_gltf(source_root / asset["original_source_files"][0]["path"], local)
                if sha256(local) != asset["converted_sha256"] or local.stat().st_size != asset["bytes"]:
                    raise ValueError("Embedded GLB differs from audited source conversion")
            else:
                downloader.fetch(asset["download_url"], local, asset["bytes"], asset.get("source_sha256"))
            digest = sha256(local)
            if digest in hashes or digest in previous_hashes:
                raise ValueError("Duplicate binary")
            stats = validate_glb(local) if local.suffix == ".glb" else validate_scan(local)
            preview = cache / "thumbnails" / (asset["id"] + ".jpg")
            downloader.fetch(asset["preview_url"], preview)
            with Image.open(preview) as loaded:
                loaded.verify()
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(local, target)
            thumb_target = destination / "thumbnails" / (asset["id"] + ".jpg")
            thumb_target.parent.mkdir(exist_ok=True)
            with Image.open(preview) as loaded:
                ImageOps.contain(thumbnail_rgb(loaded), (600, 600)).save(thumb_target, quality=90)
            hashes.add(digest)
            asset.update(stats)
            asset.update(sha256=digest, thumbnail=thumb_target.relative_to(destination).as_posix(),
                         thumbnail_sha256=sha256(thumb_target), license_url=LICENSE_URLS[asset["provider"]])
            delivered.append(asset)
            print(f"OK {len(delivered)} {asset['id']} ({stats['triangles']} triangles)", flush=True)
        except Exception as error:
            rejected.append({"id": asset["id"], "reason": str(error)})
            print(f"REJECT {asset['id']}: {error}", flush=True)
        (destination / "progress.json").write_text(json.dumps({"delivered": delivered, "rejected": rejected}, indent=2), encoding="utf-8")
    if not delivered:
        raise ValueError("No validated models; refusing to create an empty release")
    counts = dict(collections.Counter(a["category"] for a in delivered))
    manifest = {"name": "OpenHouse Household Models V4", "checked_on": catalog["checked_on"],
                "models": len(delivered), "standalone_materials": 0,
                "counts": counts, "providers": dict(collections.Counter(a["provider"] for a in delivered)),
                "license": "CC0-1.0", "previous_releases": catalog["previous_releases"],
                "deduplication": "V1-V3 IDs, normalized Poly Haven IDs/titles, original-only Innerscene provenance; SHA-256 uniqueness within V4. No third-party Poly Haven mirrors included.",
                "quality_gate": f"No low-poly tags; at least {MIN_TRIANGLES} source triangles; decoded real previews; visual selection recorded in catalog. Triangle count alone does not establish photorealism.",
                "limits": "Structural validation and provider-thumbnail review; no Blender render/import test. Geometry and materials remain unmodified; Poly Haven glTF dependencies are embedded into GLB. Nominal source dimensions are not a building survey.",
                "source_audit": catalog["source_audit"], "assets": delivered, "rejected": rejected}
    (destination / "MANIFEST_V4.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    license_dir = destination / "licenses"
    license_dir.mkdir()
    evidence = []
    for provider, url in LICENSE_URLS.items():
        page = cache / "license-evidence" / (provider + "-license.html")
        downloader.fetch(url, page)
        if b"CC0" not in page.read_bytes():
            raise ValueError(f"Source license evidence no longer confirms CC0: {provider}")
        evidence.append({"provider": provider, "url": url, "checked_on": catalog["checked_on"],
                         "http_status": 200, "source_page_sha256": sha256(page),
                         "license": "CC0-1.0", "commercial_use_and_redistribution": True})
    (license_dir / "LICENSE_EVIDENCE.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    downloader.fetch("https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt", license_dir / "CC0-1.0.txt")
    (destination / "LICENSES.md").write_text(
        "# Model licenses\n\nAll delivered assets: CC0 1.0. Commercial use and redistribution are permitted.\n\n"
        "Authors and source URLs are recorded per asset in MANIFEST_V4.json. Original license files in source ZIPs are preserved.\n\n"
        + "\n".join(f"- {p}: {u}" for p, u in LICENSE_URLS.items())
        + "\n\nLICENSE_EVIDENCE.json records the checked source URLs, date, status and page SHA-256; the CC0 legal text is included. Provider website text retains its own rights.\n", encoding="utf-8")
    (destination / "README_PL.md").write_text(
        f"# Biblioteka modeli domu V4\n\n{len(delivered)} nowych modeli 3D CC0; 0 samodzielnych materiałów.\n\n"
        "GLB: Blender → Plik → Import → glTF 2.0. Tekstury są osadzone. "
        "ambientCG: rozpakuj wewnętrzny ZIP i importuj OBJ z plikiem MTL i mapami w tym samym katalogu; oryginalny USD również pozostaje w paczce.\n\n"
        "Sprawdź skalę skanów po imporcie — wymiary w metadanych API ambientCG nie zostały potwierdzone.\n\n"
        "Otwórz CATALOG.html dla rzeczywistych miniatur. Manifest zawiera autorów, linki źródłowe, licencje, liczbę trójkątów i SHA-256. "
        "Każda pozycja jest jednym modelem lub opisanym zestawem; części siatki i warianty formatu nie są liczone jako dodatkowe modele.\n\n"
        "Sprawdzono strukturę plików i miniatury. Nie wykonywano renderów filmu ani testu importu w Blenderze. "
        "Materiały i geometria pochodzą od autorów; nie generowano zastępczych modeli.\n", encoding="utf-8")
    rows = []
    for a in delivered:
        esc = html.escape
        rows.append(f'<article><a href="{esc(a["file"])}"><img loading="lazy" src="{esc(a["thumbnail"])}" alt="{esc(a["title"])}"></a><h2>{esc(a["title"])}</h2><p>{esc(a["category"])} · {a["triangles"]:,} tris</p><p>{esc(a["author"])} · CC0</p><a href="{esc(a["source"])}">Source</a> · <a href="{esc(a["file"])}">Model</a></article>')
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Household Models V4</title><style>body{font:16px system-ui;background:#f1f3f4;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}article{background:white;padding:16px;border-radius:10px}img{width:100%;height:210px;object-fit:contain}h2{font-size:18px}a{color:#1858a5}</style>'
    (destination / "CATALOG.html").write_text(page + f'<h1>{len(delivered)} Household Models V4 · CC0</h1><p>Real source previews. 0 standalone materials.</p><main>' + "".join(rows) + '</main></html>', encoding="utf-8")
    make_sheets(delivered, destination)
    (destination / "progress.json").unlink()
    files = sorted(p for p in destination.rglob("*") if p.is_file())
    (destination / "SHA256SUMS.txt").write_text("".join(f"{sha256(p)}  {p.relative_to(destination).as_posix()}\n" for p in files), encoding="utf-8")
    archive = destination.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as output:
        for path in sorted(destination.rglob("*")):
            if path.is_file():
                output.write(path, path.relative_to(destination).as_posix())
    if archive.stat().st_size >= MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds release upload safety limit")
    with zipfile.ZipFile(archive) as check:
        if check.testzip() is not None:
            raise ValueError("Final archive CRC failed")
    print(json.dumps({"archive": str(archive), "bytes": archive.stat().st_size, "sha256": sha256(archive), "models": len(delivered), "counts": counts}), flush=True)


def make_sheets(assets, root):
    for offset in range(0, len(assets), 30):
        batch = assets[offset:offset + 30]
        sheet = Image.new("RGB", (1500, 70 + 205 * ((len(batch) + 4) // 5)), "#f5f5f5")
        draw = ImageDraw.Draw(sheet)
        draw.text((20, 20), f"OpenHouse V4 - REAL model previews {offset + 1}-{offset + len(batch)} / {len(assets)}", fill="black", font_size=24)
        for i, asset in enumerate(batch):
            x, y = (i % 5) * 300, 70 + (i // 5) * 205
            with Image.open(root / asset["thumbnail"]) as loaded:
                thumb = ImageOps.contain(loaded.convert("RGB"), (290, 160))
                sheet.paste(thumb, (x + (300 - thumb.width) // 2, y))
            draw.text((x + 8, y + 162), asset["title"][:36], fill="black", font_size=13)
            draw.text((x + 8, y + 181), f'{offset+i+1}. {asset["triangles"]:,} tris / CC0', fill="#555555", font_size=12)
        sheet.save(root / f"PREVIEW_{offset // 30 + 1:02}.jpg", quality=92)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path("tmp/models-v4-cache"))
    args = parser.parse_args()
    build(args.catalog, args.output, args.cache)
