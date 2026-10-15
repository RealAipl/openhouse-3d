# Salon A na piętrze — kontrolny render V4

Aranżacja koncepcyjna w istniejącym modelu bliźniaka. Rzut i otwory zachowane.

1920×1080, Blender Cycles CPU, do 192 próbek, adaptacyjne próbkowanie, denoising.

Nie jest to potwierdzona rekonstrukcja wykonawcza ani zatwierdzony fotorealizm.

## Użyte modele

| Model | Autor / dostawca | Trójkąty źródłowe | Licencja |
|---|---|---:|---|
| [haven-224-oatmeal-two-seat-sofa-40262c27](https://www.innerscene.com/tools/library/3d-parts/haven-224-oatmeal-two-seat-sofa-40262c27) | Innerscene / Innerscene | 96,220 | CC0 |
| [ember-leather-and-walnut-lounge-chair-9b9f3689](https://www.innerscene.com/tools/library/3d-parts/ember-leather-and-walnut-lounge-chair-9b9f3689) | Innerscene / Innerscene | 55,560 | CC0 |
| [trio-nesting-coffee-table-set-a1a295a4](https://www.innerscene.com/tools/library/3d-parts/trio-nesting-coffee-table-set-a1a295a4) | Innerscene / Innerscene | 13,548 | CC0 |
| [trace-180-walnut-sideboard-32858583](https://www.innerscene.com/tools/library/3d-parts/trace-180-walnut-sideboard-32858583) | Innerscene / Innerscene | 18,620 | CC0 |
| [span-225-extendable-dining-table-b5cc7e64](https://www.innerscene.com/tools/library/3d-parts/span-225-extendable-dining-table-b5cc7e64) | Innerscene / Innerscene | 11,676 | CC0 |
| [gather-dining-armchair-ee459660](https://www.innerscene.com/tools/library/3d-parts/gather-dining-armchair-ee459660) | Innerscene / Innerscene | 14,976 | CC0 |
| [paper-column-paper-column-floor-lamp-3b5a06e7](https://www.innerscene.com/tools/library/3d-parts/paper-column-paper-column-floor-lamp-3b5a06e7) | Innerscene / Innerscene | 21,200 | CC0 |
| [basket-woven-basket-pendant-baacdf33](https://www.innerscene.com/tools/library/3d-parts/basket-woven-basket-pendant-baacdf33) | Innerscene / Innerscene | 20,996 | CC0 |
| [brass_vase_01](https://polyhaven.com/a/brass_vase_01) | Rico Cilliers / Poly Haven | 21,440 | CC0 |
| [tea_set_01](https://polyhaven.com/a/tea_set_01) | James Ray Cock, Rico Cilliers, Jurita Burger / Poly Haven | 40,296 | CC0 |

## Materiały PBR

| Zastosowanie | Biblioteka | Zasób |
|---|---|---|
| walls | V3 | [PaintedPlaster003](https://ambientcg.com/a/PaintedPlaster003) |
| floor | V2 | [wood_floor](https://polyhaven.com/a/wood_floor) |
| walnut | V2 | [american_walnut_veneer](https://polyhaven.com/a/american_walnut_veneer) |
| rug | V3 | [Carpet003](https://ambientcg.com/a/Carpet003) |
| curtains | V1 | [rough_linen](https://polyhaven.com/a/rough_linen) |

## Sprawdzenie

Wszystkie 120 modeli V4 przeszły kontrolę struktury; 250 plików kontrolę SHA-256. Import w Blenderze sprawdzono dla 10 wybranych modeli (13 instancji).
Zachowano geometrię 88 oryginalnych siatek. Tekstury spakowane; plik .blend ponownie otwarty w Blenderze.
Czas samego renderowania: 1005.1 s.

## Ograniczenia

- Concept model; the private four-page source PDF is not available in this checkout.
- No changes to plan.py or architecture.py. Finishes, furnishings and light fittings are inferred staging.
- Only selected V4 models tested in Blender. Material maps are 1K/2K source assets.
- Single 1080p still with time-bounded CPU Cycles and denoising; no claim of photorealism.
- Original non-target rooms are preserved. Their illumination changes with the study world. No LUXORIA website changes.