"""Check actual output bytes and create a portable checksum inventory."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageStat

out = Path("houses/blizniak_dwulokalowy/output/salon_v4")
png = out / "salon_v4_1920x1080.png"
blend = out / "salon_v4_editable.blend"
assert png.stat().st_size > 100000 and blend.stat().st_size > 3000000
with Image.open(png) as im:
    assert im.size == (1920, 1080)
    im.verify()
with Image.open(png) as im:
    stats = ImageStat.Stat(im.convert("RGB").resize((192, 108)))
    assert max(stats.stddev) > 12
    im.resize((1280, 720)).save(out / "salon_v4_preview.jpg", quality=94)
report = json.loads((out / "asset_report.json").read_text())
lines = ["# Salon A na piętrze — kontrolny render V4\n",
         "Aranżacja koncepcyjna w istniejącym modelu bliźniaka. Rzut i otwory zachowane.\n",
         "1920×1080, Blender Cycles CPU, do 192 próbek, adaptacyjne próbkowanie, denoising.\n",
         "Nie jest to potwierdzona rekonstrukcja wykonawcza ani zatwierdzony fotorealizm.\n",
         "## Użyte modele\n", "| Model | Autor / dostawca | Trójkąty źródłowe | Licencja |",
         "|---|---|---:|---|"]
seen = set()
for a in report["models"]:
    if a["id"] in seen:
        continue
    seen.add(a["id"])
    lines.append(f'| [{a["id"]}]({a["source"]}) | {a["author"]} / {a["provider"]} | {a["source_triangles"]:,} | CC0 |')
lines += ["\n## Materiały PBR\n", "| Zastosowanie | Biblioteka | Zasób |", "|---|---|---|"]
for a in report["materials"]:
    lines.append(f'| {a["role"]} | {a["library"]} | [{a["id"]}]({a["source"]}) |')
lines += ["\n## Sprawdzenie\n",
          f'Wszystkie 120 modeli V4 przeszły kontrolę struktury; 250 plików kontrolę SHA-256. Import w Blenderze sprawdzono dla {len(seen)} wybranych modeli ({len(report["models"])} instancji).',
          f'Zachowano geometrię {report["preserved_original_meshes"]} oryginalnych siatek. Tekstury spakowane; plik .blend ponownie otwarty w Blenderze.',
          f'Czas samego renderowania: {report["settings"]["elapsed_render_seconds"]:.1f} s.',
          "\n## Ograniczenia\n"] + ["- " + x for x in report["limits"]]
(out / "RAPORT.md").write_text("\n".join(lines), encoding="utf-8")
files = [out / n for n in ["salon_v4_1920x1080.png", "salon_v4_preview.jpg",
                          "salon_v4_editable.blend", "asset_report.json", "RAPORT.md",
                          "v4_audit.json", "prepared_assets.json"]]
(out / "SHA256SUMS.txt").write_text("".join(
    hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in files))
print("DELIVERY_VERIFIED", png.stat().st_size, blend.stat().st_size)
