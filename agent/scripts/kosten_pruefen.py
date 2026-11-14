#!/usr/bin/env python3
"""kosten_pruefen.py - täglicher Cron-Job «kosten» ohne Modell (--no-agent). FinOps Stufe 2 (O3).

Plan: observability/plan-observability.md. Liest die geschätzten Modellkosten aus der
Sitzungsdatenbank von Hermes (state.db, nur lesend) und meldet Beat, wenn eine Grenze
überschritten ist. Läuft täglich um 10:00 (Europe/Zurich) und prüft den Vortag, dann ist der Tag vollständig.

Ausgabe wird von Hermes wörtlich an Beat geschickt (Telegram). Leere Ausgabe = keine Meldung.
- Tageskosten über TAG_GRENZE oder ein einzelner Lauf über LAUF_GRENZE → Meldung mit Aufteilung.
- sonst → nichts.

Aufruf von Hand (zum Testen):
    python3 kosten_pruefen.py               wie im Cron-Job, nur bei Überschreitung
    python3 kosten_pruefen.py --bericht     immer eine Übersicht ausgeben
    python3 kosten_pruefen.py --datum 2026-11-13 --bericht

Grenzen per Umgebung änderbar: KOSTEN_TAG_GRENZE, KOSTEN_LAUF_GRENZE (USD). Start nach OE3.
Nur Python-Standardbibliothek.
"""

import argparse
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

HOME = Path.home()
STATE_DB = Path(os.environ.get("STATE_DB", HOME / ".hermes/state.db"))
TAG_GRENZE = float(os.environ.get("KOSTEN_TAG_GRENZE", "0.50"))
LAUF_GRENZE = float(os.environ.get("KOSTEN_LAUF_GRENZE", "0.10"))


def gruppe(source: str, title: str) -> str:
    """Cron-Jobs nach Namen («einordnen · Nov 13 10:44» → «einordnen»), sonst nach Quelle."""
    if source == "cron" and title:
        return "Cron " + title.split(" · ")[0].strip()
    return source or "unbekannt"


def lese_tag(tag: date) -> list[tuple[str, str, float]]:
    """Sitzungen des Tages (lokale Zeit) mit Kosten: (Gruppe, Titel, USD)."""
    beginn = datetime.combine(tag, datetime.min.time()).timestamp()
    ende = beginn + 86400
    # nur lesend öffnen, Hermes schreibt parallel weiter
    con = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True, timeout=10)
    try:
        zeilen = con.execute(
            "SELECT source, COALESCE(title, ''), COALESCE(estimated_cost_usd, 0) FROM sessions "
            "WHERE started_at >= ? AND started_at < ? AND COALESCE(estimated_cost_usd, 0) > 0",
            (beginn, ende)).fetchall()
    finally:
        con.close()
    return [(gruppe(s, t), t, float(c)) for s, t, c in zeilen]


def main() -> None:
    parser = argparse.ArgumentParser(description="Tageskosten von Manni prüfen")
    parser.add_argument("--datum", help="Tag im Format JJJJ-MM-TT, Standard: gestern")
    parser.add_argument("--bericht", action="store_true", help="immer eine Übersicht ausgeben")
    args = parser.parse_args()
    tag = date.fromisoformat(args.datum) if args.datum else date.today() - timedelta(days=1)

    try:
        laeufe = lese_tag(tag)
    except sqlite3.Error as fehler:
        print(f"Kostenprüfung {tag:%d.%m.%Y}: state.db nicht lesbar ({fehler}).")
        return

    total = sum(c for _, _, c in laeufe)
    teure = [(g, t, c) for g, t, c in laeufe if c > LAUF_GRENZE]
    if not args.bericht and total <= TAG_GRENZE and not teure:
        return

    pro_gruppe: dict[str, list[float]] = {}
    for g, _, c in laeufe:
        pro_gruppe.setdefault(g, []).append(c)

    if total > TAG_GRENZE or teure:
        kopf = f"Kostenalarm {tag:%d.%m.%Y}: Manni hat USD {total:.3f} verbraucht"
        kopf += f" (Grenze Tag USD {TAG_GRENZE:.2f}, Lauf USD {LAUF_GRENZE:.2f})."
    else:
        kopf = f"Kosten {tag:%d.%m.%Y}: USD {total:.3f}, alle Grenzen eingehalten."
    zeilen = [kopf]
    for g, werte in sorted(pro_gruppe.items(), key=lambda kv: -sum(kv[1])):
        zeilen.append(f"- {g}: {len(werte)} Läufe, USD {sum(werte):.3f}")
    if teure:
        zeilen.append("Teure Einzelläufe:")
        for g, t, c in sorted(teure, key=lambda x: -x[2])[:5]:
            zeilen.append(f"- USD {c:.3f} {g}: {t[:60]}")
    zeilen.append("Details pro Aufruf in Langfuse.")
    print("\n".join(zeilen))


if __name__ == "__main__":
    sys.exit(main())
