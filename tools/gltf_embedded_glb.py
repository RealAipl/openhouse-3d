"""Embed an original glTF's local buffer and images without changing geometry."""
import json
import mimetypes
import struct
import urllib.parse
from pathlib import Path, PurePosixPath


def embed_gltf(source: Path, destination: Path):
    doc = json.loads(source.read_text(encoding="utf-8"))
    if len(doc.get("buffers", [])) != 1:
        raise ValueError("Only one original buffer is supported")

    def read_uri(uri):
        if urllib.parse.urlparse(uri).scheme:
            raise ValueError("Only audited local source dependencies are supported")
        decoded = urllib.parse.unquote(uri)
        relative = PurePosixPath(decoded)
        if relative.is_absolute() or ".." in relative.parts or "\\" in decoded or ":" in decoded:
            raise ValueError("Unsafe source dependency path")
        return source.parent.joinpath(*relative.parts).read_bytes()

    buffer = doc["buffers"][0]
    raw = read_uri(buffer.pop("uri"))
    if len(raw) != buffer["byteLength"]:
        raise ValueError("Original buffer size mismatch")
    binary = bytearray(raw)
    binary.extend(b"\0" * (-len(binary) % 4))
    views = doc.setdefault("bufferViews", [])
    for image in doc.get("images", []):
        if "uri" not in image:
            continue
        uri = image.pop("uri")
        raw_image = read_uri(uri)
        image["mimeType"] = mimetypes.guess_type(uri)[0]
        if image["mimeType"] not in ("image/jpeg", "image/png"):
            raise ValueError("Unsupported source image type")
        image["bufferView"] = len(views)
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(raw_image)})
        binary.extend(raw_image)
        binary.extend(b"\0" * (-len(binary) % 4))
    buffer["byteLength"] = len(binary)
    metadata = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()
    metadata += b" " * (-len(metadata) % 4)
    result = struct.pack("<4sII", b"glTF", 2, 28 + len(metadata) + len(binary))
    result += struct.pack("<II", len(metadata), 0x4E4F534A) + metadata
    result += struct.pack("<II", len(binary), 0x004E4942) + binary
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(result)
    return destination
