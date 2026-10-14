# Bliźniak dwulokalowy — OpenHouse 3D

**Faza:** pierwszy rzeczywiście wyrenderowany model koncepcyjny, nie projekt wykonawczy.

Model bazuje na czterostronicowym projekcie koncepcyjnym KORMET-PROJEKT dostarczonym przez użytkownika. **Oryginalny PDF nie jest przechowywany w tym publicznym repozytorium.**

## Zakres

- Dwa lustrzane segmenty A/B.
- Parter i piętro każdego segmentu = **cztery niezależne lokale**.
- 7 pomieszczeń na parterze i 5 na piętrze w każdym segmencie = **24 pomieszczenia**.
- Dwa zewnętrzne biegi schodowe z podestami prowadzące na piętra.
- Prosty dach płaski z attyką, okna i drzwi na elewacjach, wnętrza z roboczym wyposażeniem.
- 30 kamer: sześć zewnętrznych i po jednej w każdym pomieszczeniu.
- Scenariusz 27 ujęć: trzy zewnętrzne + 24 wnętrza.

## Parametry odczytane z projektu

| Element | Wartość |
|---|---|
| Cały budynek — szerokość | 15,87 m |
| Światło szerokości skrzydła | 7,34 m |
| Ściana środkowa | ok. 0,41 m |
| Poziom parteru | ±0,00 m |
| Poziom piętra | +2,93 m |
| Próg/podest wejścia na piętro | +3,01 m |
| Lokal parterowy A i B | po 60,32 m² |
| Lokal piętrowy A i B | po 60,98 m² |

Powierzchnie są z **tabel w PDF**, a nie z wygenerowanych przybliżonych pomieszczeń.

## Co jest przybliżeniem

- Głębokość bryły, skorygowana koncepcyjnie na ok. 8,90 m po ponownej analizie łańcuchów wymiarowych.
- Położenia części ścian działowych i dokładne otwory okienne / parapety.
- Wymiary i przebieg balustrad obu schodów oraz geometrię biegu powrotnego.
- Materiały i meble, które pokazują jedynie możliwą aranżację; nie są standardem deweloperskim.

Przed udostępnieniem klientowi w charakterze wiernej rekonstrukcji należy przeprowadzić **rysunek-model audit** na wszystkich czterech planszach. Zgodność powierzchni użytkowych z tabeli nie dowodzi zgodności rzeczywistej geometrii modelu.

## Pliki

- `plan.py` — program 24 pomieszczeń i podstawowe gabaryty.
- `architecture.py` — model 3D segmentów, ścian, otworów i schodów zewnętrznych.
- `interiors.py` — podziały i podstawowe wyposażenie.
- `site.py` — neutralne otoczenie, niezwiązane z projektem zagospodarowania.
- `shots.py` — trasa/ujęcia do filmu obejmujące każde pomieszczenie.
- `house.py` — materiały, oświetlenie, kamery i konfiguracja silnika.

## Pipeline w GitHub Actions

- `.github/workflows/render-blizniak-concept.yml` — realny render budynku i jednego wnętrza w Blender Cycles.
- `.github/workflows/render-blizniak-film-preview.yml` — roboczy film/storyboard: komplet ujęć 4 lokali, kontrola wnętrz i wejść.

Żadnych zmian w produkcyjnej stronie LUXORIA. **Brak integracji z witryną do czasu zatwierdzenia geometrii i jakości obrazu.**

## Zweryfikowany pipeline 3D i renderingu

- ✅ Rzeczywisty model zapisany do `blizniak_dwulokalowy.blend`.
- ✅ Eksport pełnego modelu do `GLB`: 89 siatek, 24 obiekty wyposażenia, 30 kamer, 2 osobne schody.
- ✅ Bezpośrednie mapy PBR CC0 Poly Haven (drewno i materiał tapicerski), pobierane z kontrolą SHA256.
- ✅ GLB eksportuje pełne UV zamiast niepoprawnych indeksów `texCoord=-1`.
- ✅ Test porównawczy z Blender Cycles dla kilku pomieszczeń.
- ✅ Storyboard Workbench obejmuje 27 ujęć, wszystkie 24 pomieszczenia.
- ✅ Audyt odległości kamer. Ostatni zmierzony przebieg: 0 zablokowanych, 2 zbyt ciasne ujęcia magazynowe; potem skorygowano ich położenie.
- 🕓 Film w Cycles jest renderowany równolegle jako pięć grup klatek 3D.
- 🕓 Wersja PBR final video uruchamia się automatycznie po sukcesie pierwszej wersji.

## Dokładność architektoniczna — pozostające ograniczenia

Na rzutach znajdują się wyłącznie projekt koncepcyjny i zestawienia powierzchni. Wielkość rzutowanego prostokąta pomieszczenia nie jest tożsama z powierzchnią użytkową netto z tabeli. W szczególności na piętrze wiatrołap i przedpokój mają układ bardziej złożony niż ich obecne prostokąty 3D; konieczna jest ręczna weryfikacja wszystkich ścian i otworów z dokumentacją CAD/przekrojami, jeżeli model ma być uznany za wierną dokumentację realizacyjną. Kamera filmowa może pokazać układ koncepcyjny, a nie potwierdzone wymiary wykonawcze.

**Bezpieczeństwo:** repozytorium forka jest PUBLICZNE. Pełnego oryginalnego PDF do niego nie wysłano, lecz w kodzie znajduje się zrekonstruowany układ lokali. Przed publikacją materiałów klienta lub dalszym udostępnianiem modelu trzeba ustalić uprawnienia do rozpowszechniania.
