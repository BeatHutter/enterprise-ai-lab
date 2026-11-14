# Datengenerator

Legt die Geschichte der Muster AG über die Odoo-Schnittstelle an: Kunden, Lieferanten, Artikel, Offerten, Rechnungen, Zahlungen und Monatsbuchungen von Januar 2025 bis Oktober 2026. Grundlage ist [docs/drehbuch-muster-ag.md](../docs/drehbuch-muster-ag.md).

## Stand

Wird in Etappen gebaut, siehe Detailplan Testdaten (intern). Fertig: Etappe 1 (Verbindungstest), Etappe 2 (Stammdaten), Etappe 3 (Bewegungen bis 31.8.2025), Etappe 4a (September bis Dezember 2025), Etappe 4b (Januar bis Oktober 2026 mit den Prüffällen). Etappe 5 (Prüfskript `../tests/pruefskript.py` für P1 bis P5) ist fertig.

## Bedienung

Nur Python-Standardbibliothek, keine Zusatzpakete. Aufruf im Ordner `data-generator`:

| Etappe | Befehl | Schreibt in Odoo |
| --- | --- | --- |
| 1 Verbindungstest | `python3 etappe1_verbindung.py` | nein |
| 2 Stammdaten, Trockenlauf | `python3 etappe2_stammdaten.py` | nein |
| 2 Stammdaten | `python3 etappe2_stammdaten.py --schreiben` | ja, nur Fehlendes |
| 3 Trockenlauf | `python3 etappe3_4_bewegungen.py --bis 2025-08-31` | nein |
| 3 Schreiben | `python3 etappe3_4_bewegungen.py --bis 2025-08-31 --schreiben` | ja, Vorhandenes wird übersprungen |
| 3 Kontrolle | `python3 etappe3_4_bewegungen.py --bis 2025-08-31 --kontrolle` | nein |

Die Vorgaben stehen in `daten/` als CSV. Die Spalte «notiz» ist nur für uns und kommt nie nach Odoo.

## Anforderungen

- Python-Skript, spricht Odoo über XML-RPC an
- Zugang über einen API-Schlüssel, nie über das Passwort
- Wiederholbar: ein fester Zufallsstartwert (Seed), damit jeder Lauf dieselben Daten erzeugt
- Vor jedem Lauf eine Odoo-Sicherung ziehen
- Nach dem Lauf müssen die Prüffälle in [tests/prueffaelle.md](../tests/prueffaelle.md) in den Odoo-Berichten sichtbar sein

## Konfiguration

`.env.example` nach `.env` kopieren und den API-Schlüssel aus 1Password eintragen. Die `.env` wird nie committet.
