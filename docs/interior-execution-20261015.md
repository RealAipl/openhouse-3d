# Wnętrza - wykonanie 2026-10-15
Cel: końcowy pakiet reprezentatywnych wnętrz oraz edytowalny model czterech lokali.
Chronione: istniejące wydania i binaria salonu, produkcja LUXORIA, pozostałe domy.
Źródło: lokalnie dostarczony 4-stronicowy PDF, obejrzany w całości; strony 1/2 to rzuty parteru/piętra.
Ograniczenia: tylko wnętrza; chmura; zero płatnych usług; bez Manek orchestrator.
Korekty: głębokość 9.44 zamiast 8.90; podział 4.54/0.18/3.94; szerokości 2.13/1.57/3.44; wiatrołapy; okna 1.30 od hp .825; drzwi wewnętrzne 2.00.
Sprzeczność źródła: 4.14 wewnątrz salonu piętra vs 4.54 w łańcuchu; wybrano 4.54 zgodne z 33.32 m2.
Wysokość sufitu 2.69 pozostaje założeniem - brak przekroju.
Weryfikacja: Blender 5.2.1 w chmurze, mały render CPU szablonu wykonany poprawnie.

Kontrola: obrysy ścian działowych zostały wyeksportowane z rzeczywistej sceny i nałożone na oba oryginalne rzuty w plikach dostarczanych prywatnie. 57 testów repozytorium i Ruff przechodzą. Scena zawiera 24 pomieszczenia i 28 kamer wnętrz; tekstury spakowane; oryginalny plik salonu zachowany.

Dodatkowa kontrola: pełny pion instalacyjny zamknięty w czterech lokalach; 40 grup modeli mieści się w obrysach przypisanych pomieszczeń. Sprawdzono 86 spakowanych obrazów (brak brakujących). Pierwsze dwa kadry nie widzą zmienionego pionu (po 5184 promienie, 0 trafień), więc nie były niepotrzebnie renderowane ponownie. CI GitHub dla ecba381 zakończyło się sukcesem.

Uzupełniono 16 otwartych skrzydeł drzwi wewnętrznych i ościeżnice, poprawiono wolne dojście do gospodarczego. Kontrola widoczności potwierdziła brak nowych drzwi w czterech ukończonych kadrach; kolejne są liczone z kompletną stolarką.

Kontynuacja: zachowano 5 gotowych obrazów i dokończono pokój gościnny. Skorygowano kadry holu i wiatrołapu oraz szafkę/TV na piętrze, które naruszały dojście do salonu. Kontrola rzeczywistych siatek sprawdza teraz wolne podejście 80 x 68 cm w czterech lokalach. Ujęcia zmienionej szafki są liczone ponownie; pozostałe pozostają zachowane.

Kontrola ergonomii wykryła zbyt niskie stoły po jednolitej redukcji modeli. Skorygowano je do 75 cm we wszystkich czterech lokalach; kontrola rzeczywistych obwiedni wymaga tej wysokości przed akceptacją.
