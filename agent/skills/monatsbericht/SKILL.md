---
name: monatsbericht
description: Monats- oder Quartalsbericht der Muster AG für die Geschäftsleitung erstellen. Zahlen mit klaren Bezügen, Treiber bis auf Belege verfolgen, Sondereffekte zeigen, Kommentar mit Kernaussage.
version: 1.0.0
author: Beat Hutter, Claude
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [bericht, monatsbericht, kennzahlen, muster-ag]
---

# Monatsbericht erstellen

Ein Monatsbericht sagt der Geschäftsleitung, wie die Firma dasteht und warum. Die Zahlen allein reichen nicht. Der Wert des Berichts liegt darin, dass er Auffälligkeiten bis zu ihrer Ursache verfolgt.

Dieser Skill wird nur von Beat geändert.

## 1. Woher die Zahlen kommen

- Kennzahlen holst du über den Skill `kennzahlen-abrufen`. Seine Regeln gelten weiter.
- Details holst du mit dem Skill `odoo-lesen`: einzelne Rechnungen, Kunden, Lieferanten, Artikel, Aufträge, Bestellungen.
- Felder erkundest du mit `fields_get`, nicht durch Raten.

## 2. Klare Bezüge

Wer den Bericht liest, muss bei jeder Zahl wissen, worauf sie sich bezieht.

- Jede Periode trägt einen Namen, zum Beispiel «Mär 2025», «Mär 2024», «Jan–Mär 2025», «Q1 2025», «Stichtag 31.03.2025».
- Jeder Satz mit einer Veränderung nennt die Grösse, beide Perioden, beide Beträge und die Veränderung.
- Prozentpunkte (bei Quoten und Margen) und Prozent (bei Beträgen) nie verwechseln.
- Einen Stichtag (zum Beispiel offene Debitoren) nie direkt mit einem Zeitraum (zum Beispiel Umsatz) vergleichen.

Beispiele mit erfundenen Zahlen:

| Unklar | Klar |
| --- | --- |
| «Der übrige Aufwand steigt um 6 %.» | «Übriger betrieblicher Aufwand Jan–Mär 2025 CHF 106'000.00 gegenüber Jan–Mär 2024 CHF 100'000.00, +6.0 %.» |
| «Der März bestätigt den Trend.» | «Auch im Mär 2025 liegt die Bruttogewinnmarge mit 58.0 % unter Mär 2024 (59.5 %), −1.5 Prozentpunkte.» |

## 3. Ablauf

### 3.1 Überblick

- Berichtsmonat und kumuliert seit Jahresbeginn, je mit Vorjahr.
- Verlauf Monat für Monat (`--aufteilung monat`), damit Ausreisser sichtbar werden.
- Aufteilung nach Kundensegment.

### 3.2 Auffälligkeiten finden

Wesentlich ist eine Auffälligkeit, wenn mindestens eines zutrifft:

- Eine Grösse weicht um mehr als 5 % oder mehr als CHF 10'000 vom Vorjahr ab.
- Eine Quote oder Marge verschiebt sich um mehr als 1 Prozentpunkt.
- Ein Monat fällt deutlich aus dem Verlauf, nach oben oder nach unten.
- Eine Veränderung im Total stammt aus wenigen Monaten, Kunden oder Lieferanten.
- Ein Segment oder ein grosser Kunde verändert sich deutlich.

### 3.3 Treiber verfolgen

Für jede wesentliche Auffälligkeit gehst du mit `odoo-lesen` mindestens eine Stufe tiefer, bis du sagen kannst, woher sie kommt. Gib dich nicht mit der ersten plausiblen Erklärung zufrieden.

| Auffälligkeit bei | Eine Stufe tiefer |
| --- | --- |
| Umsatz | nach Kunde, nach Auftrag (Quelldokument der Rechnung), grösste Rechnungen des Monats. Gehören mehrere Rechnungen zum selben Auftrag? |
| Material und Einkauf | nach Lieferant, nach Artikel. Preis pro Einheit über die Zeit vergleichen: Liegt es an der Menge oder am Preis? |
| Segment | welche Kunden die Veränderung tragen |
| übriger Aufwand | nach Konto und Lieferant |
| Debitoren | nach Kunde, Zahlungsverhalten über die Zeit |

Am Schluss steht für jede wesentliche Auffälligkeit eines von beiden:

- **Ursache belegt:** mit Belegen (Rechnungs- oder Bestellnummer, Kunde, Lieferant, Betrag).
- **Ursache offen:** mit dem Grund, warum Odoo sie nicht hergibt. «Steht nicht in den Kennzahlen» ist kein Grund, solange `odoo-lesen` weiterhilft.

### 3.4 Sondereffekte zeigen

Einmalige Ereignisse verzerren den Vergleich mit dem Vorjahr, zum Beispiel ein Grossauftrag, ein Projekt mit Teilrechnungen oder eine einmalige Kostenposition.

- Benenne den Sondereffekt mit Belegen.
- Zeige die Grösse mit und ohne den Sondereffekt. Die Rechnung dafür schreibst du offen hin: Kennzahl laut `kennzahlen-abrufen` minus Sondereffekt laut Belegen ergibt den bereinigten Wert. Beide Ausgangszahlen mit Quelle. Kennzeichne den bereinigten Wert als eigene Rechnung.
- Prüfe danach, ob deine Aussage noch stimmt. Wächst die Firma auch ohne den Sondereffekt?

### 3.5 Kommentar

- Beginne mit der Kernaussage in einem Satz.
- Prüfe jedes Wachstum und jeden Rückgang: Ist er breit abgestützt oder auf Einzelnes konzentriert?
- Trenne Fakten (aus den Daten) und Deutung (deine Einschätzung).
- Nenne eine Ursache nur, wenn du sie belegt hast. Sonst schreibe, was offen ist.
- Schlage Massnahmen vor, je mit Anlass und Ziel.

## 4. Aufbau des Berichts

1. Kernaussage in einem Satz, dann das Wichtigste in höchstens fünf Sätzen
2. Kennzahlen Berichtsmonat mit Vorjahr
3. Kennzahlen kumuliert mit Vorjahr, Verlauf Monat für Monat, Segmente
4. Treiber und Sondereffekte, je mit Belegen
5. Kommentar: Lage, was gut läuft, was auffällt, Massnahmen
6. Grenzen: was offen ist und warum
7. Arbeitsnachweis: benutzte Skills, Aufrufe, eigene Rechnungen

## 5. Was du nicht tust

- Keine Kennzahl selbst nachbauen, die `kennzahlen-abrufen` liefert.
- Keine Ursache erfinden. Lieber «offen» mit Grund.
- Nichts in Odoo schreiben, auch keine Notizen.
