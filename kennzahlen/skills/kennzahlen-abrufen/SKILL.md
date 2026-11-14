---
name: kennzahlen-abrufen
description: Kennzahlen der Muster AG (Nettoerlös, Materialquote, Bruttogewinn, EBITDA, EBIT, offene Debitoren, Debitorenfrist und weitere) nach dem festen Kennzahlen-Katalog abrufen. Für jede Zahl in Berichten und Antworten.
version: 1.1.0
author: Beat Hutter
license: MIT
platforms: [linux]
required_environment_variables:
  - name: ODOO_URL
  - name: ODOO_DB
  - name: ODOO_USER
  - name: ODOO_API_KEY
metadata:
  hermes:
    tags: [kennzahlen, odoo, bericht, muster-ag]
---

# Kennzahlen abrufen

Für jede Kennzahl der Muster AG gibt es eine feste Bedeutung und genau einen Rechenweg. Du rufst den Rechenweg auf und deutest das Ergebnis. Du zählst nie selbst zusammen.

Dieser Skill wird nur von Beat geändert. Die Bibliothek unter `/opt/muster-kennzahlen` ist für dich nur lesbar.

## Welche Kennzahlen es gibt

| Kennung | Kennzahl | Art |
| --- | --- | --- |
| `nettoerloes` | Nettoerlös | Zeitraum |
| `nettoerloes_nach_segment` | Nettoerlös nach Kundensegment | Zeitraum |
| `materialaufwand` | Materialaufwand | Zeitraum |
| `materialquote` | Materialquote | Zeitraum |
| `bruttogewinn` | Bruttogewinn | Zeitraum |
| `bruttogewinnmarge` | Bruttogewinnmarge | Zeitraum |
| `personalaufwand` | Personalaufwand | Zeitraum |
| `ebitda` | Betriebsergebnis vor Abschreibungen (EBITDA) | Zeitraum |
| `ebit` | Betriebsergebnis (EBIT) | Zeitraum |
| `debitoren_altersstruktur` | Offene Debitoren mit Altersstruktur | Stichtag |
| `debitorenfrist` | Debitorenfrist (DSO) | Zeitraum |
| `bestandesaenderungen` | Bestandesänderungen | Zeitraum |
| `kursdifferenzen` | Kursdifferenzen (netto) | Zeitraum |
| `uebriger_betrieblicher_aufwand` | Übriger betrieblicher Aufwand | Zeitraum |
| `abschreibungen` | Abschreibungen | Zeitraum |

Die Liste mit je einem Satz Bedeutung: `python3 -B /opt/muster-kennzahlen/kennzahl.py liste --format text`

## Bedeutung nachlesen

Bevor du eine Kennzahl deutest, lies ihren Katalogeintrag:

```
python3 -B /opt/muster-kennzahlen/kennzahl.py katalog <kennung>
```

Der ganze Katalog liegt in `/opt/muster-kennzahlen/katalog.md`. Dort stehen auch die Grundregeln (nur gebuchte Belege, Buchungsdatum, ohne MWST, in CHF, Vorzeichen).

## Wie aufrufen

Immer mit `terminal`. Die vier `ODOO_*`-Variablen kommen aus der Shell-Umgebung. Der `execute_code`-Kernel sieht sie nicht. Lade diesen Skill zuerst mit `skill_view`, damit sie ankommen.

Kennzahl für einen Zeitraum (beide Tage eingeschlossen):

```
python3 -B /opt/muster-kennzahlen/kennzahl.py nettoerloes --von 2026-01-01 --bis 2026-10-31
```

Bestand per Stichtag:

```
python3 -B /opt/muster-kennzahlen/kennzahl.py debitoren_altersstruktur --stichtag 2026-10-31
```

Schalter:

| Schalter | Wirkung |
| --- | --- |
| `--vergleich vorjahr` | gleicher Zeitraum bzw. Stichtag ein Jahr früher, mit Veränderung in CHF und Prozent (bei Quoten in Prozentpunkten), auch pro Konto, Segment und Altersstufe |
| `--aufteilung monat` oder `quartal` | dieselbe Kennzahl pro Monat bzw. Quartal, nur bei Zeiträumen |
| `--nach kunde` | offene Debitoren pro Kunde, nur bei `debitoren_altersstruktur` |
| `--format text` | kurze Lesefassung. Standard ist JSON |

Die Ausgabe in JSON enthält immer `kennung`, `name`, `katalogversion`, `zeitraum` oder `stichtag`, `wert`, `text`, `bestandteile`, `hinweise` und `quelle`, je nach Kennzahl dazu `segmente`, `stufen`, `kunden`, `bestaende`, `marge`, `vergleich` und `aufteilung`. Zu jedem Betrag gibt es ein Feld `…_text` in Schweizer Schreibweise.

## Regeln

1. Zahlen für Berichte und Antworten kommen aus diesem Skill. Du addierst, subtrahierst, teilst und rundest nicht selbst. Vergleiche und Verläufe holst du mit `--vergleich` und `--aufteilung`.
2. Übernimm Beträge und Prozente aus den Feldern `…_text`.
3. Nenne zu jeder Zahl Kennung, Zeitraum oder Stichtag, Katalogversion und Quelle, z. B. «Nettoerlös (`nettoerloes`, Katalog 1.0), 01.01.2026 bis 31.10.2026, Odoo».
4. Gibt es eine Kennzahl nicht, oder steht «nicht verfügbar» bzw. «nicht berechenbar» in der Ausgabe: sag das so und nenne den Grund. Keine Ersatzrechnung.
5. Findest du in der Liste keine passende Kennung, rate keine. Lies mit `kennzahl.py katalog <kennung>` den Eintrag der nächstverwandten Kennzahl. Dort steht unter «Nicht verfügbar», was es nicht gibt und warum. Diesen Grund nennst du.
6. Für Einzelheiten hinter einer Kennzahl (einzelne Belege, Kunden, Lieferanten) nimmst du `odoo-lesen`. Summen, die der Katalog als Kennzahl führt, rechnest du damit nicht nach.
7. Endet der Aufruf mit Exit-Code 2, steht die Meldung auf stderr. Melde sie Beat wörtlich. Das gilt besonders für «Katalog und Rechenwege passen nicht zusammen».
8. Du änderst, kopierst oder ersetzt weder Katalog noch Rechenwege, auch nicht als eigene Fassung in einem anderen Ordner. Fehlt dir eine Kennzahl oder hältst du eine Regel für falsch, schlag es Beat vor.
