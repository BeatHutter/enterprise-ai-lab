---
name: pipeline-bericht
description: Wöchentlicher Bericht über die Verkaufspipeline der Muster AG für die Geschäftsleitung. Zahlen und Befunde kommen fest gerechnet aus einem Skript, du schreibst den Kommentar mit Massnahmen.
version: 1.0.0
author: Beat Hutter, Claude
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [crm, pipeline, bericht, verkauf, muster-ag]
---

# Pipeline-Bericht erstellen

Die Geschäftsleitung will jede Woche wissen: Wie viel steckt in der Pipeline, wo hakt es, wer muss handeln? Der Wert des Berichts liegt in den Massnahmen, nicht in den Tabellen.

Dieser Skill wird nur von Beat geändert.

## 1. Arbeitsteilung: Skript rechnet, du kommentierst

Alle Zahlen und Befunde liefert das Skript `scripts/pipeline_fakten.py`. Es liest Odoo CRM über den Zugang von `odoo-lesen` und prüft feste Regeln. Starte es mit `terminal`:

```
python3 scripts/pipeline_fakten.py
```

- Übernimm Zahlen, Zuständige und Quoten **genau so**, wie das Skript sie ausgibt. Rechne nichts nach und nichts neu.
- Brauchst du eine Angabe, die das Skript nicht liefert (zum Beispiel die letzte Notiz einer Chance), hole sie mit `odoo-lesen`. Kennzeichne sie im Bericht als eigene Abfrage.
- Scheitert das Skript: nichts umgehen, nichts selbst nachbauen. Melde die Fehlermeldung und brich ab.

## 2. Was die Befunde bedeuten

| Befund des Skripts | Bedeutung | Typische Massnahme |
| --- | --- | --- |
| Ohne geplante Aktivität | Niemand kümmert sich gerade um die Chance | Zuständige Person fasst nach und setzt eine Aktivität |
| Erwarteter Abschluss überschritten | Die Prognose ist verzerrt | Datum neu setzen oder Chance als verloren schliessen |
| Mögliche Dublette | Zwei Chancen für dasselbe Vorhaben | Prüfen und zusammenführen, eine Person bleibt zuständig |
| Klumpenrisiko | Zu viel offener Wert bei einer Person | Stellvertretung regeln, neue Chancen breiter verteilen |
| Überfällige Aktivität | Termin verpasst | Nachholen oder neu planen |

Kein Befund, sondern normal:
- **Neue Anfragen ohne Kundenverknüpfung.** Der Kunde wird erst beim Qualifizieren verknüpft. Nur erwähnen, wenn eine solche Chance zugleich als mögliche Dublette erscheint.
- **Zwei Chancen derselben Firma bei derselben Person, beide verknüpft.** Das sind meist zwei Projekte.
- **Erstelldatum der Chancen.** Die Pipeline wurde im November 2026 aus Excel nachgetragen.

## 3. Gewichten

- Ordne Massnahmen nach dem **gewichteten Wert** der betroffenen Chance, die grösste zuerst.
- Liegt die grösste oder zweitgrösste Chance der Pipeline still, steht das an erster Stelle im Kommentar.
- Nenne bei jeder Massnahme die **zuständige Person aus dem Feld «Zuständig»** des Skripts, nie eine geschätzte.

## 4. Aufbau des Berichts

1. **Kernaussage** in einem Satz, dann höchstens drei Sätze zur Lage
2. **Pipeline in Zahlen:** offen total und gewichtet, nach Stufe, nach Person (Tabellen aus dem Skript)
3. **Abgeschlossen:** gewonnen, verloren, Gründe, Gewinnquote, diese Woche
4. **Handlungsbedarf:** jeder Befund mit Chance, Wert, zuständiger Person und Massnahme, nach gewichtetem Wert geordnet
5. **Kommentar für die Geschäftsleitung:** was gut läuft, was auffällt. Trenne **Fakten** (aus dem Skript) und **Deutung** (deine Einschätzung)
6. **Arbeitsnachweis:** Befehle, Stichtag und Regelversion des Skripts, eigene Abfragen

Kurz halten. Die Geschäftsleitung liest eine Seite, keine Datenbank.

## 5. Was du nicht tust

- Keine Zahl selbst rechnen, die das Skript liefert.
- Nichts in Odoo schreiben, auch keine Notizen oder Aktivitäten. Massnahmen sind Vorschläge an Menschen.
- Keine Ursache erfinden. Was die Daten nicht hergeben, steht als offen da.
