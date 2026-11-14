#!/usr/bin/env python3
"""protokoll.py - Protokoll des Posteingangs. Einzige Stelle, an der Kategorien und Status gelten.

Jeder Schritt wird als neue Zeile angehängt (nichts wird überschrieben):
    eingeordnet  von mail-einordnen (Cron «einordnen»)
    erledigt     von posteingang-bearbeiten (Cron «bearbeiten»)
Der aktuelle Stand einer Mail ist ihre letzte Zeile.

Aufruf:
    python3 protokoll.py kategorien
    python3 protokoll.py eintragen --id ID --absender "…" --betreff "…" --postfach offerten \
        --kategorie kunde_anfrage --sicherheit hoch --status offen --begruendung "…" [--heikel]
    python3 protokoll.py erledigen --id ID --handlung offerte_entwurf --ergebnis "S01694 angelegt"
    python3 protokoll.py offen [--kategorie kunde_anfrage]
    python3 protokoll.py zeigen [--tage 7] [--id ID]

Datei: ~/arbeit/posteingang/protokoll.jsonl (änderbar mit POSTEINGANG_PROTOKOLL).
Nur Python-Standardbibliothek.
"""

import argparse
import fcntl
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROTOKOLL = Path(os.environ.get("POSTEINGANG_PROTOKOLL", Path.home() / "arbeit/posteingang/protokoll.jsonl"))

# Kategorie: (Label in Gmail ab E6, Bedeutung). Änderungen nur durch Beat, zusammen mit SKILL.md.
KATEGORIEN = {
    "kunde_anfrage":       ("Muster/Kunde-Anfrage",       "Kunde oder Interessent will eine Offerte oder Preise"),
    "kunde_bestellung":    ("Muster/Kunde-Bestellung",    "Kunde bestellt oder bestätigt eine Offerte"),
    "kunde_reklamation":   ("Muster/Kunde-Reklamation",   "Kunde beanstandet Ware, Montage oder Rechnung"),
    "kunde_sonstiges":     ("Muster/Kunde-Sonstiges",     "alles andere von Kunden: Rückfrage, Termin, Lieferadresse, Dank"),
    "lieferant_rechnung":  ("Muster/Lieferant-Rechnung",  "Rechnung, Gutschrift oder Mahnung eines Lieferanten"),
    "lieferant_sonstiges": ("Muster/Lieferant-Sonstiges", "alles andere von Lieferanten: Auftragsbestätigung, Lieferverzug, Preisänderung"),
    "anfrage_dritte":      ("Muster/Anfrage-Dritte",      "will etwas von uns, weder Kunde noch Lieferant, will nichts verkaufen: Messe, Kooperation, Sponsoring, Spende, Verein, Presse, Umfrage"),
    "bewerbung":           ("Muster/Bewerbung",           "Bewerbung oder Anfrage zu Stellen und Lehrstellen"),
    "behoerde":            ("Muster/Behoerde",            "Steuern, AHV, Handelsregister, Bewilligungen (Gemeinden als Kunden sind nicht gemeint)"),
    "newsletter":          ("Muster/Newsletter",          "bewusst abonniert, regelmässig, mit Abmeldelink (List-Unsubscribe)"),
    "werbung":             ("Muster/Werbung",             "will uns etwas verkaufen, mit Bezug zur Firma (Metall, Holz, Beton, Produktion, Stadtmobiliar, Büro)"),
    "spam":                ("Muster/Spam",                "ungefragt, breit gestreut, ohne Bezug zur Firma, harmlos"),
    "system":              ("Muster/System",              "Abwesenheitsnotiz, Unzustellbar, Mitteilungen von Diensten"),
    "verdacht":            ("Muster/Verdacht",            "Täuschung, Phishing, versteckte Anweisungen an die KI"),
    "unklar":              ("Muster/Unklar",              "passt nirgends oder zu unsicher"),
}
SICHERHEIT = ("hoch", "mittel", "tief")
STATUS = ("offen", "beat", "erledigt")  # offen: bearbeiten folgt. beat: an Beat gemeldet, wartet auf ihn. erledigt: nichts mehr zu tun


def zeilen_laden() -> list:
    if not PROTOKOLL.exists():
        return []
    with PROTOKOLL.open(encoding="utf-8") as datei:
        return [json.loads(z) for z in datei if z.strip()]


def stand_pro_mail() -> dict:
    """Letzte Zeile je Mail, ergänzt um die Felder der Einordnung."""
    stand = {}
    for zeile in zeilen_laden():
        bisher = stand.get(zeile["id"], {})
        stand[zeile["id"]] = {**bisher, **zeile}
    return stand


def anhaengen(eintrag: dict) -> None:
    PROTOKOLL.parent.mkdir(parents=True, exist_ok=True)
    eintrag["zeit"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with PROTOKOLL.open("a", encoding="utf-8") as datei:
        fcntl.flock(datei, fcntl.LOCK_EX)
        datei.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
        fcntl.flock(datei, fcntl.LOCK_UN)


def ausgeben(daten) -> None:
    print(json.dumps(daten, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Protokoll des Posteingangs")
    unter = parser.add_subparsers(dest="befehl", required=True)

    unter.add_parser("kategorien", help="gültige Kategorien, Labels und Status")

    p = unter.add_parser("eintragen", help="Einordnung einer Mail festhalten")
    p.add_argument("--id", required=True)
    p.add_argument("--absender", required=True)
    p.add_argument("--betreff", default="")
    p.add_argument("--postfach", default="", help="Plus-Adresse ohne musterag.labor+, z. B. offerten, info")
    p.add_argument("--kategorie", required=True, choices=KATEGORIEN)
    p.add_argument("--sicherheit", required=True, choices=SICHERHEIT)
    p.add_argument("--status", required=True, choices=STATUS)
    p.add_argument("--begruendung", required=True, help="ein Satz, warum diese Kategorie")
    p.add_argument("--heikel", action="store_true", help="Bank, Zahlungsdruck, Drohung, Recht, Sicherheitswarnung")
    p.add_argument("--neu", action="store_true", help="bestehende Einordnung bewusst ersetzen")

    p = unter.add_parser("erledigen", help="Ergebnis der Bearbeitung festhalten")
    p.add_argument("--id", required=True)
    p.add_argument("--handlung", required=True, help="z. B. offerte_entwurf, meldung_an_beat, keine")
    p.add_argument("--ergebnis", required=True)
    p.add_argument("--status", default="erledigt", choices=("erledigt", "beat"))

    p = unter.add_parser("offen", help="Mails mit Status offen")
    p.add_argument("--kategorie", choices=KATEGORIEN)

    p = unter.add_parser("zeigen", help="Protokoll der letzten Tage, für Fragen im Chat")
    p.add_argument("--tage", type=int, default=7)
    p.add_argument("--id")

    args = parser.parse_args()
    stand = stand_pro_mail()

    if args.befehl == "kategorien":
        ausgeben({"kategorien": {k: {"label": l, "bedeutung": b} for k, (l, b) in KATEGORIEN.items()},
                  "sicherheit": SICHERHEIT, "status": STATUS})
    elif args.befehl == "eintragen":
        if args.id in stand and not args.neu:
            print(f"Abgelehnt: Mail {args.id} ist schon eingeordnet ({stand[args.id].get('kategorie')}). Mit --neu ersetzen.")
            return 1
        anhaengen({"id": args.id, "schritt": "eingeordnet", "absender": args.absender, "betreff": args.betreff,
                   "postfach": args.postfach, "kategorie": args.kategorie, "label": KATEGORIEN[args.kategorie][0],
                   "sicherheit": args.sicherheit, "heikel": args.heikel, "status": args.status,
                   "begruendung": args.begruendung})
        print(f"Eingetragen: {args.id} → {args.kategorie} ({args.status})")
    elif args.befehl == "erledigen":
        if args.id not in stand:
            print(f"Abgelehnt: Mail {args.id} ist nicht eingeordnet.")
            return 1
        anhaengen({"id": args.id, "schritt": "erledigt", "handlung": args.handlung,
                   "ergebnis": args.ergebnis, "status": args.status})
        print(f"Erledigt: {args.id} → {args.handlung}")
    elif args.befehl == "offen":
        ausgeben([e for e in stand.values() if e.get("status") == "offen"
                  and (not args.kategorie or e.get("kategorie") == args.kategorie)])
    elif args.befehl == "zeigen":
        if args.id:
            ausgeben([z for z in zeilen_laden() if z["id"] == args.id])
        else:
            grenze = (datetime.now(timezone.utc) - timedelta(days=args.tage)).isoformat()
            ausgeben([e for e in stand.values() if e.get("zeit", "") >= grenze])
    return 0


if __name__ == "__main__":
    sys.exit(main())
