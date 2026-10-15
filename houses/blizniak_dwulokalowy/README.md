# Wnętrza bliźniaka - cztery lokale

Aktualna praca obejmuje wyłącznie wnętrza, na podstawie oryginalnego czterostronicowego PDF KORMET-PROJEKT dostarczonego 2026-10-15. Cały załącznik obejrzano; strony 1/2 zawierają rzut parteru/piętra. Oryginalnego PDF ani wycinków z niego nie umieszczamy w publicznym repozytorium.

## Model

- Segmenty A/B w odbiciu lustrzanym; dwa niezależne lokale na każdym poziomie, cztery łącznie.
- 24 pomieszczenia; osobne kolekcje wyposażenia czterech lokali.
- 16 otwartych skrzydeł drzwi wewnętrznych z ościeżnicami i klamkami.
- Dwie sypialnie w lokalu parterowym, jedna w lokalu piętrowym.
- Brak schodów wewnętrznych: wejścia na piętro znajdują się z boku budynku.
- Reprezentatywne kamery dla A oraz ich odpowiedniki dla B; nie powielamy identycznych renderów.

## Porównanie z rysunkami

Poprzedni model miał przybliżone podziały. Skorygowano: głębokość całkowitą **9,44 m**, głębokość strefy dziennej **4,54 m**, ścianę poprzeczną **18 cm**, tylną sypialnię **3,44 x 3,94 m**, hol **1,57 m**, wiatrołapy i gospodarcze oraz uskok instalacyjny łazienki. Kuchnie mają zabudowę L w miejscu wskazanym na rzutach. Standardowe okna: hp 82,5 cm / wysokość 130 cm; drzwi wewnętrzne: 200 cm.

Rysunek piętra zawiera konflikt: salon ma wewnętrzną etykietę 414 cm, lecz łańcuch zewnętrzny 454 cm, a tabela 33,32 m² = 7,34 x 4,54. Wybrano 4,54 m, z ujawnieniem rozbieżności. Wysokość sufitu **2,69 m jest założeniem**, ponieważ nie otrzymano przekroju. Odczyt rastrowy nie jest pomiarem CAD. Podane w projekcie powierzchnie nie są przedstawiane jako ponowny pomiar netto modelu.

## Kod i odtwarzanie

- `plan.py`: poprawiony układ, program i współrzędne.
- `architecture.py`: ściany i otwory istniejącego modelu.
- `interiors.py`: poprawione ściany działowe i wnęka instalacyjna.
- `client_interiors.py`: edytowalne wykończenie i wyposażenie wszystkich czterech lokali; tylko kamery wnętrz.
- `tools/check_client_interiors.py`: ponowne otwarcie sceny, kompletność, spakowane obrazy, położenie kamer i eksport faktycznych obrysów ścian.

Do odtworzenia używa się Blender/bpy 5.2.1, dotychczasowego wydania `salon-v4-premium-20261015` i istniejącego zweryfikowanego V4 ZIP. Pliki `salon_v4_editable.blend` i `v4_audit.json` trafiają do `tmp/existing/`, rozpakowane modele do `tmp/salon-v4/pack/`. Nie ma potrzeby tworzenia następnej biblioteki zasobów.

```bash
python -m houses.blizniak_dwulokalowy.client_interiors --build --views none
python -m houses.blizniak_dwulokalowy.client_interiors --views 01_pietro_salon,02_pietro_kuchnia_jadalnia,04_parter_salon,05_parter_kuchnia,06_sypialnia_glowna,08_pokoj_goscinny_gabinet,09_lazienka,11_hol,12_wiatrolap_pietro
python tools/check_client_interiors.py
```

Wyniki: `houses/blizniak_dwulokalowy/output/final/`. Oryginalny wcześniejszy salon i opublikowane wydania pozostają zachowane. Nie wykonywano zewnętrznych wizualizacji ani zmian strony LUXORIA. Meble, materiały i lampy są propozycją aranżacyjną, nie deklaracją standardu sprzedaży ani projektem wykonawczym.
