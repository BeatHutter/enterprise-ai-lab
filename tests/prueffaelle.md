# Prüffälle

In die Daten der Muster AG sind fünf Auffälligkeiten eingebaut. Die richtige Antwort ist bekannt. Findet ein Agent sie, funktioniert der Skill. Nach jeder Änderung an einem Skill werden diese Fälle erneut geprüft.

Agenten, die gegen diese Prüffälle getestet werden, haben keinen Lesezugriff auf das Repository (siehe `docs/entscheide.md`).

| Nr. | Was passiert | Wann | Wo sichtbar | Der Agent muss finden |
| --- | --- | --- | --- | --- |
| P1 | Stahlcenter Limmat erhöht die Preise um 25 %. Die Muster AG erhöht ihre Verkaufspreise für Stahlartikel erst ab Juli, und nur um 6 %. | April bis Juni 2026 | Erfolgsrechnung, Lieferantenrechnungen | Materialquote steigt von rund 40 % auf rund 44 bis 45 % im Q2 2026. Ursache Stahlcenter, betroffen vor allem Velo- und Abfallartikel. Offerten vor dem 1.7.2026 behalten den alten Verkaufspreis (gewollt). Die Preisänderung des Stahlcenters ist nur über die Lieferantenrechnungen erkennbar, Odoo führt keine Preishistorie (gewollt, realistisch). |
| P2 | Rietli Immobilien AG zahlt immer später: nach 45, dann 60, dann über 90 Tagen, ab Mai 2026 gar nicht mehr. | ab September 2025 | Offene Posten, Partnersalden nach Alter | Einziger Kunde mit Posten über 90 Tage überfällig, rund CHF 27'000 von total CHF 42'000 offen. Dritte Mahnstufe für zwei Rechnungen fällig. |
| P3 | Grossprojekt Bahnhofplatz der Stadt Seefeld: Offerte CHF 186'000 im Februar, Zuschlag im April, Teilrechnungen 40 % im Juni und 60 % im September. | Januar bis September 2026 | Umsatz nach Monat und Kunde, Materialquote nach Monat | Spitzen im Juni und September stammen aus einem Projekt. Ohne das Projekt liegt Januar bis Oktober 2026 rund 2.6 % unter dem Vorjahr. Die Materialquote ist im Juli und August 2026 hoch (51 %, 54 %) und im September tief (33 %), weil das Projektmaterial vor der Schlussrechnung eingekauft wird. |
| P4 | Die Schulgemeinden sparen, allen voran die Schulgemeinde Hinterberg. | 2026 | Umsatz nach Kundensegment | Segment Schulen minus rund 60 %, Hinterberg minus rund 70 %. |
| P5 | Eine Rechnung der Pulverbeschichtung Glatttal über CHF 8'640 ist doppelt erfasst und bezahlt (PB-2026-0613 und PB 2026 613). | Juni 2026 | Lieferantenrechnungen, Zahlungen | Doppelzahlung erkennen und CHF 8'640 zurückfordern. IKS-Fall: Die zweite Rechnung ist ohne Bestellung erfasst. Schwierigkeitshinweis: Gleicher Lieferant und gleicher Betrag innerhalb von 7 Tagen liefert 10 Fehlalarme (alles Stahlcenter-Lieferungen mit zufällig gleichem Betrag). Eindeutig wird es erst mit «mindestens eine Rechnung ohne Bestellung» oder mit der bereinigten Referenz (Sonderzeichen und führende Nullen weg, «PB-2026-0613» und «PB 2026 613» werden gleich). |

## Begriffe

- **Alter eines Postens** = Tage nach Fälligkeit, nicht nach Rechnungsdatum. Stichtag ist der 31.10.2026.
- **Mahnstufen:** Stufe 1 ab 30 Tagen, Stufe 2 ab 60 Tagen, Stufe 3 ab 90 Tagen nach Fälligkeit. Odoo Community hat kein Mahnwesen; die Stufe ergibt sich aus dieser Regel.
- **Vergleichszeitraum:** Januar bis Oktober 2026 gegenüber Januar bis Oktober 2025. Die Daten enden am 31.10.2026.
- **Mahnstufe:** Alter ≥ 30 Tage = Stufe 1, ≥ 60 = Stufe 2, ≥ 90 = Stufe 3. «Über 90 Tage überfällig» heisst Alter ≥ 90, also Stufe 3. Im Datenbestand fällt kein Posten genau auf eine Grenze.
- **Umsatz** = Nettobetrag der gebuchten Kundenrechnungen nach Rechnungsdatum, einschliesslich Anzahlungen. Das entspricht den Konten 3000 und 3400. Kursdifferenzen (3806) gehören nicht dazu.
- **Material** = Konten 4000 und 4400. Kursdifferenzen (4906) gehören nicht dazu.
- **Materialquote** = Material geteilt durch Umsatz, also (4000 + 4400) / (3000 + 3400), ohne Kursdifferenzen 3806 und 4906.
- **EBITDA** = alle Ertrags- und Aufwandskonten der Klassen 3 bis 6 ausser 6800 Abschreibungen. Die Kursdifferenzen 3806 und 4906 sind enthalten, die Steuern (8900) nicht. Gleiche Definition im Plan des Generators und im Prüfskript.
- **Projektmaterial Bahnhofplatz** = Nettobetrag der Lieferantenrechnungen zu den Bestellungen, deren Ursprung «Projekt Bahnhofplatz» lautet: CHF 87'831 (Mai 17'573, Juni 17'579, Juli 22'061, August 30'618). Der Generator plante die Mengen mit CHF 81'101 (Standardkosten 72'090 × 1.125). Die Lieferungen von Stahlcenter kommen nach dem 1.4.2026 aber zum um 25 % höheren Preis. Der Stahlcenter-Anteil beträgt 35'478, ohne den Aufschlag wären es 28'382, also 7'096 mehr. Die Differenz zu 81'101 ist 6'730. Die restlichen 366 sind nicht einzeln belegt, vermutlich Rundung der Mengen bei den übrigen Lieferanten. In Odoo nachweisbar sind die 87'831.

## Zielwerte für das Prüfskript

Aus dem Plan des Datengenerators (Startwert 20250101) berechnet. Das Prüfskript in Etappe 5 rechnet sie in Odoo nach.

| Nr. | Zielwert | Toleranz |
| --- | --- | --- |
| P1 | Materialquote Q2 2026: 44.6 % (Q1 2026: 40.5 %, Q2 2025: 40.2 %). Zerlegung des Anstiegs: rund 3.5 Punkte Stahlcenter, 0.6 Punkte Doppelzahlung P5, 0.3 Punkte Projektmaterial Seefeld. | ± 1.0 Punkt |
| P2 | Rietli offen CHF 41'736, davon über 90 Tage überfällig CHF 26'954 (Rechnungen vom Mai und Juni 2026). Kein anderer Kunde über 90 Tage überfällig. Mahnstufe 3: zwei Rechnungen, Stufe 2: eine, Stufe 1: eine. Kein anderer Kunde mit Mahnstufe. | ± CHF 2'000 |
| P3 | Projekt netto CHF 186'000: CHF 74'400 im Juni, CHF 111'600 im September. Umsatz Januar bis Oktober 2026 +3.0 %, ohne Projekt −2.6 % gegenüber Vorjahr. Materialquote Juli 51 %, August 54 %, September 33 %. | Projekt exakt, Umsatz ± 1.5 Punkte, Quoten ± 2 Punkte |
| P4 | Segment Schulen −58.8 %, Hinterberg −71 % (Januar bis Oktober). | ± 5 Punkte |
| P5 | Zwei Rechnungen à CHF 8'640.00 brutto, beide bezahlt, Rückforderung CHF 8'640.00. | exakt |
| Gesamt | EBITDA Januar bis Oktober 2026 rund CHF 263'000 (Vorjahr 290'000), ohne Projekt rund CHF 165'000. | ± CHF 15'000 |

Gegentest: Dieselben Abfragen für 2025 bzw. per 31.10.2025 müssen «nicht gefunden» melden.

| Nr. | Gegentest | Erwartung |
| --- | --- | --- |
| P1 | Materialquote pro Monat 2025, Preissprung eines Lieferanten von Quartal zu Quartal 2025 | Höchster Monat unter 42 %. Kein Preissprung über 10 %. |
| P2 | Offene Posten per 31.10.2025 | Kein Kunde mit Alter ≥ 90 Tage, keine Mahnstufe 3. |
| P3 | Aufträge ab CHF 100'000 netto, bestätigt 2025 | Keiner. |
| P4 | Vor 2025 gibt es keinen Umsatz, ein Vorjahresvergleich ist nicht möglich. Ersatz: die vier übrigen Segmente Januar bis Oktober 2026 gegenüber 2025. | Keines fällt um mehr als 20 %. |
| P5 | Gleicher Lieferant, Währung und Betrag innerhalb von 7 Tagen, mindestens eine ohne Bestellung, Rechnungsdatum 2025 | Kein Paar. |

## Gesamtbild 2026

Umsatz Januar bis Oktober 2026 +3.0 %, ohne das Projekt Bahnhofplatz −2.6 %. EBITDA Januar bis Oktober 2026 rund CHF 263'000 gegenüber 290'000 im Vorjahr, ohne Projekt rund CHF 165'000. Das Ergebnis sinkt wegen des Stahlpreises, ohne Seefeld bricht es ein. Ein guter Monatsbericht zeigt: Der Umsatz wächst nur dank eines Einzelprojekts, das Kerngeschäft schwächelt.
