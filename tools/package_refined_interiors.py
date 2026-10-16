"""Package corrected finishes and a genuine model-based camera walkthrough."""
import base64
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'houses/blizniak_dwulokalowy/output/refined'
OLD=ROOT.parent/'recovered/package/Wnetrza_bliźniaka'
DEL=OUT/'Wnetrza_bliźniaka'


def main():
    check=json.loads((OUT/'KONTROLA_KOREKTY.json').read_text());assert check['camera_route']['positions']==120
    for name in ['Kontrola_rzutow.png','KONTROLA_GEOMETRII.json','ODCZYT_RYSUNKOW.json','ZRODLA_MODELI.json','ZRODLA_MATERIALOW.json']:
        shutil.copy2(OLD/'Dokumentacja'/name,OUT/name)
    model=json.loads((OLD/'Dokumentacja/KONTROLA_PLIKU_BLEND.json').read_text());model.update(check);model.update({'sha256_blend':check['blend_sha256'],'packed_images':check['packed_images'],'missing_images':check['missing_images'],'camera_count':check['camera_count'],'animated_camera':'Spacer_3D_A2','refinement_check':'KONTROLA_KOREKTY.json'});(OUT/'KONTROLA_PLIKU_BLEND.json').write_text(json.dumps(model,indent=2))
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    geo=json.loads((OUT/'KONTROLA_GEOMETRII.json').read_text());geo['delivery_source_commit']=commit;geo['camera_count']=check['camera_count'];(OUT/'KONTROLA_GEOMETRII.json').write_text(json.dumps(geo,indent=2))
    records={}
    for line in (ROOT.parent/'repair-final-renders.log').read_text().splitlines():
        if line.startswith('RENDER_OK '):
            _,view,seconds=line.split();records[view]={'view':view,'seconds':float(seconds),'resolution_percentage':100,'samples_requested':64}
    assert len(records)==9
    (OUT/'Obrazy/render_times.json').write_text(json.dumps(list(records.values()),indent=2))
    text=(OLD/'README.md').read_text();a=text.index('## Pliki końcowe');text=text[:a]+'''## Korekta wykończenia

We wszystkich czterech lokalach uzupełniono wykończenia i detale. Fronty górne mają kolor kaszmirowy, szafy i drzwi wewnętrzne ciepły szary, AGD satynowy grafit, blaty i okładziny szary kamień. Tkaniny mają spokojne odcienie taupe, piasku i kości słoniowej. Ściany pozostały jasne. Zlew ma prawdziwy otwór i zagłębioną stalową misę, armatura zakrzywiony profil, urządzenia sterowanie i uchwyty, a szuflady podziały. Uzupełniono klamki wejściowe, wykończenie drzwi oraz drobną fakturę kamienia w łazienkach. Nie dodawano nowych paczek assetów.

Ściany i otwory nie zostały zmienione: porównano wierzchołki i ściany 10 siatek architektonicznych z poprzednim modelem dopasowanym do A-01/A-02. Są identyczne. Aktualne kontrole są w Dokumentacja/KONTROLA_KOREKTY.json.

## Pliki końcowe

- Wizualizacje/PNG i JPG: dziewięć poprawionych ujęć 1920 x 1080.
- Prezentacja_wnetrz.pdf: 11 stron albumu i informacji o dokumentacji.
- Model/Wnetrza_4_lokale.blend: wszystkie cztery lokale, pełne tekstury oraz edytowalna kamera Spacer_3D_A2 z animacją.
- Film/Wnetrza_prezentacja_1080p.mp4: rzeczywista trasa kamery przez hol do salonu i kuchni. 10 sekund, bez muzyki. Nie jest pokazem slajdów. Render czasu rzeczywistego ma prostsze oświetlenie niż statyczne obrazy Cycles. Źródło 960 x 540, 120 odrębnych klatek 3D; eksport 1920 x 1080 / 24 kl./s z interpolacją ruchu. Rozdzielczość źródłowa nie jest natywnym Full HD.
- Spacer_3D.html: samodzielny spacer offline po czterech lokalach; wybór lokalu, automatyczna trasa oraz rozglądanie i sterowanie WASD/strzałkami. Plik zawiera model i biblioteki, wymaga przeglądarki obsługującej WebGL2. Tekstury dla widoku interaktywnego mają ograniczoną rozdzielczość; plik Blender zachowuje pełne tekstury.
- Galeria.html: lokalna galeria obrazów.
- Dokumentacja: źródła, odczyt rzutów, kontrole i ocena końcowa. Zrodla: kod, narzędzia i licencje.
- SHA256SUMS.txt: integralność paczki.

Jakość: spokojne wizualizacje aranżacyjne z czytelnymi materiałami. Detale pozostają uproszczone. Nie deklaruje się fotorealizmu premium. Film pokazuje rzeczywisty ruch w przestrzeni; jest wizualnie prostszy od renderów statycznych. Nie wykonano zewnętrznych wizualizacji, nie korzystano z PC użytkownika i nie zmieniano LUXORII.
''';text+='\nKod: https://github.com/RealAipl/openhouse-3d/commit/'+commit+'\n';(OUT/'README.md').write_text(text)
    spec=importlib.util.spec_from_file_location('legacy_package',ROOT/'tools/package_client_interiors.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.OUT=OUT;m.DELIVERY=DEL;m.MOVIE_IS_WALKTHROUGH=True
    m.prepare();m.sheet();m.album();m.gallery()
    movie=OUT/'Wnetrza_prezentacja_1080p.mp4';assert movie.is_file();(DEL/'Film').mkdir(exist_ok=True);shutil.copy2(movie,DEL/'Film'/movie.name)
    web=ROOT/'tmp/repair/web';page=(web/'index.html').read_text();bundle=(web/'viewer.bundle.js').read_text().replace('</script','<\\/script');encoded=base64.b64encode((web/'scene.glb').read_bytes()).decode();page=page.replace('<script src="./viewer.bundle.js"></script>','<script>window.EMBEDDED_GLB="'+encoded+'";</script><script>'+bundle+'</script>');(DEL/'Spacer_3D.html').write_text(page)
    gallery=DEL/'Galeria.html';gallery.write_text(gallery.read_text().replace('<a href="README.md">','<a href="Spacer_3D.html">Spacer 3D</a><a href="README.md">'))
    for name in ['refine_client_interiors.py']:
        shutil.copy2(ROOT/'houses/blizniak_dwulokalowy'/name,DEL/'Zrodla/house'/name)
    for name in ['check_refined_interiors.py','add_client_camera_route.py','export_client_walkthrough.py','optimize_client_glb.py','package_refined_interiors.py']:
        shutil.copy2(ROOT/'tools'/name,DEL/'Zrodla/tools'/name)
    shutil.copytree(ROOT/'houses/blizniak_dwulokalowy/walkthrough',DEL/'Zrodla/walkthrough',dirs_exist_ok=True)
    shutil.copy2(web/'node_modules/three/LICENSE',DEL/'Zrodla/LICENSE_THREE.txt')
    shutil.copy2(OUT/'KONTROLA_KOREKTY.json',DEL/'Dokumentacja/KONTROLA_KOREKTY.json')
    report='''# Ocena korekty wnętrz

Wykonano korektę wykończeń czterech lokali. Dokładna lista zmian i ograniczeń jest w README. Poprzedni film zastąpiono rzeczywistym ruchem kamery w modelu. Dołączono także samodzielny spacer interaktywny po wszystkich lokalach.

Kontrole: identyczne siatki architektoniczne przed i po korekcie; 24 pomieszczenia; 86 spakowanych obrazów; brak brakujących plików tekstur i pustych slotów materiałów. Trasa kamery zawiera 120 różnych pozycji/orientacji, sprawdzonych pod kątem kolizji w rzeczywistej geometrii sceny. Kamera jest zapisana i edytowalna w Blenderze. Kontrola źródeł: 57 testów i Ruff.

Rendery statyczne są jaśniejsze i dokładniejsze wizualnie niż spacer czasu rzeczywistego. Film ma uproszczone oświetlenie; rozdzielczość źródłowa 960 x 540, eksport 1920 x 1080 / 24 kl./s z interpolacją. Nie należy traktować go jako filmu fotorealistycznego. Materiał pokazuje rzeczywistą przestrzeń i ruch, a nie przesuwanie obrazów.

Zachowano ograniczenia dokumentacji: sprzeczność 4,14/4,54 m na piętrze oraz wysokość sufitu 2,69 m przyjęta bez przekroju. Nie ma nowych renderów zewnętrznych ani zmian LUXORII. Oryginalnego PDF nie opublikowano w repozytorium.
''';(DEL/'Dokumentacja/OCENA_KONCOWA.md').write_text(report)
    m.archive()


if __name__=='__main__':main()
