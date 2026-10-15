"""Compare original model bytes from actual V1-V3 release archives with V4."""
import hashlib
import json
import zipfile
from pathlib import Path

from audit_salon_v4 import BASE, OUT, digest, get

SOURCES = [{"tag":"luxoria-interior-megapack-cc0-v1","url":"https://github.com/RealAipl/openhouse-3d/releases/download/luxoria-interior-megapack-cc0-v1/LUXORIA_Interior_MegaPack_178_Zasobow_CC0.zip","bytes":828854317,"sha256":"ea93cafd6f530da4d578ca227fe870afbddb426efb93618b31ae64e3d13c5423"},{"tag":"luxoria-home-interiors-cc0-v3","url":"https://github.com/RealAipl/openhouse-3d/releases/download/luxoria-home-interiors-cc0-v3/LUXORIA_Dom_Wnetrza_V3_CC0_Materialy_I_Obiekty.zip","bytes":1461422076,"sha256":"bb2be50ba2fd9571320f1b16552eeaf1bc5be8e32f02d4a67306c5cc69d22505"},{"tag":"luxoria-home-interiors-cc0-v2","url":"https://github.com/RealAipl/openhouse-3d/releases/download/luxoria-home-interiors-cc0-v2/LUXORIA_Dom_Wnetrza_V2_CC0_Dodatkowe_Zasoby.zip","bytes":879142263,"sha256":"7abdaa1e40435a31299a1749d9063153cdc2ef37c7e0be87eb94dd51f2a0ad70"}]


def main():
    report_path = OUT / "v4_audit.json"
    report = json.loads(report_path.read_text())
    original_receipt = digest(report_path)
    v4_hashes = {a["sha256"] for a in report["assets"]}
    old_records = []
    compared = 0
    for source in SOURCES:
        p = BASE / (source["tag"] + ".zip")
        get(source["url"], p)
        assert p.stat().st_size == source["bytes"]
        actual = digest(p)
        if source.get("sha256"):
            assert actual == source["sha256"]
        model_hashes = []
        with zipfile.ZipFile(p) as archive:
            assert archive.testzip() is None
            for info in archive.infolist():
                if Path(info.filename).suffix.lower() in (".blend", ".glb", ".obj", ".fbx", ".gltf"):
                    h = hashlib.sha256()
                    with archive.open(info) as f:
                        for block in iter(lambda: f.read(1048576), b""):
                            h.update(block)
                    assert h.hexdigest() not in v4_hashes, info.filename
                    model_hashes.append({"path": info.filename, "sha256": h.hexdigest()})
                    compared += 1
        old_records.append({**source, "actual_sha256": actual, "model_files": model_hashes})
        print("CROSS_ARCHIVE_OK", source["tag"], len(model_hashes), "model/material blend files", flush=True)
        p.unlink()
    assert compared > 100
    report["initial_audit_receipt_sha256"] = original_receipt
    report["actual_previous_archives"] = old_records
    report["previous_model_files_compared"] = compared
    report["binary_comparison_limits"] = "Exact byte duplicates absent. Format conversion or visually similar models are not proven absent by binary hashes. Provider-ID/title deduplication separately checks V1-V3; source Innerscene mirrors excluded."
    report_path.write_text(json.dumps(report, indent=2))
    print("CROSS_V1_V3_OK", compared, "actual model/material files", flush=True)


if __name__ == "__main__":
    main()
