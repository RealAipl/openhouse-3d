"""Reject malicious/incomplete assets before packaging downloaded geometry."""
import json
import struct
import zipfile

import pytest
from PIL import Image

from tools.household_models_v4 import safe_relative, thumbnail_rgb, validate_glb, validate_scan
from tools.gltf_embedded_glb import embed_gltf


@pytest.mark.parametrize("name", ["../outside.obj", "/absolute.obj", "C:/model.obj", "a\\..\\model.obj", ""])
def test_reject_archive_path_escape(name):
    with pytest.raises(ValueError):
        safe_relative(name)


def test_reject_html_disguised_as_model(tmp_path):
    path = tmp_path / "model.glb"
    path.write_bytes(b"<html>Sign in to download this model</html>")
    with pytest.raises(ValueError, match="header"):
        validate_glb(path)


def test_reject_truncated_glb_chunk(tmp_path):
    path = tmp_path / "model.glb"
    path.write_bytes(struct.pack("<4sIIII", b"glTF", 2, 28, 1000, 0x4E4F534A) + b"{}      ")
    with pytest.raises(ValueError, match="chunk"):
        validate_glb(path)


def test_reject_external_buffer(tmp_path):
    path = tmp_path / "model.glb"
    raw = json.dumps({"buffers": [{"uri": "https://example.com/model.bin", "byteLength": 1}]}).encode()
    raw += b" " * (-len(raw) % 4)
    path.write_bytes(struct.pack("<4sIIII", b"glTF", 2, 20 + len(raw), len(raw), 0x4E4F534A) + raw)
    with pytest.raises(ValueError, match="external"):
        validate_glb(path)


def test_reject_zip_with_parent_path(tmp_path):
    path = tmp_path / "model.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../outside.obj", "v 0 0 0\n")
    with pytest.raises(ValueError, match="Unsafe"):
        validate_scan(path)


def test_embedding_preserves_original_geometry_bytes_and_scene(tmp_path):
    binary = struct.pack("<fff", 1.25, -2.5, 3.75)
    (tmp_path / "original.bin").write_bytes(binary)
    original = {"asset": {"version": "2.0"}, "buffers": [{"uri": "original.bin", "byteLength": 12}],
                "bufferViews": [{"buffer": 0, "byteLength": 12}],
                "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
                "nodes": [{"mesh": 0, "translation": [1, 2, 3]}], "scenes": [{"nodes": [0]}]}
    source = tmp_path / "original.gltf"
    source.write_text(json.dumps(original), encoding="utf-8")
    target = tmp_path / "embedded.glb"
    embed_gltf(source, target)
    raw = target.read_bytes()
    length = struct.unpack_from("<I", raw, 12)[0]
    embedded = json.loads(raw[20:20 + length])
    for key in ("meshes", "nodes", "scenes", "bufferViews"):
        assert embedded[key] == original[key]
    assert raw[28 + length:] == binary


def test_exported_preview_hides_transparent_texels_and_preserves_model_pixels():
    source = Image.new("RGBA", (2, 1), (255, 0, 255, 0))
    source.putpixel((1, 0), (10, 20, 30, 255))
    thumbnail = thumbnail_rgb(source)
    assert thumbnail.getpixel((0, 0)) == (245, 245, 245)
    assert thumbnail.getpixel((1, 0)) == (10, 20, 30)
