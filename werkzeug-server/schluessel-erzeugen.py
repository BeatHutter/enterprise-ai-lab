#!/usr/bin/env python3
"""Erzeugt einen Schlüssel für einen Aufrufer des Werkzeug-Servers.

In zugang.json kommt nur der Hash. Der Schlüssel selbst wird einmal ausgegeben
(oder mit --datei in eine Datei geschrieben, die nur operator lesen kann) und nirgends gespeichert.

Beispiele:
  python3 schluessel-erzeugen.py manni ping
      Beat führt das selbst aus und trägt den ausgegebenen Schlüssel in ~hermes/.hermes/.env ein.
  python3 schluessel-erzeugen.py pruefung ping --datei pruefschluessel.txt
      Schlüssel für das Prüfskript, darf nur «ping».

Ein bestehender Aufrufer mit gleichem Namen wird ersetzt (neuer Schlüssel, alter gilt nicht mehr).
"""

import argparse
import hashlib
import json
import os
import secrets
from pathlib import Path

ORDNER = Path(__file__).resolve().parent
ZUGANG = ORDNER / "zugang.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="Name des Aufrufers, z. B. manni")
    parser.add_argument("werkzeuge", help="erlaubte Werkzeuge, mit Komma getrennt, z. B. ping,probe_freigabe")
    parser.add_argument("--datei", help="Schlüssel in diese Datei schreiben statt ausgeben (Rechte 600)")
    parser.add_argument("--nur-werkzeuge", action="store_true",
                        help="Schlüssel behalten, nur die erlaubten Werkzeuge eines bestehenden Aufrufers ersetzen")
    args = parser.parse_args()
    werkzeuge = [w.strip() for w in args.werkzeuge.split(",") if w.strip()]
    daten = json.loads(ZUGANG.read_text()) if ZUGANG.exists() else {"aufrufer": []}

    if args.nur_werkzeuge:
        treffer = [a for a in daten["aufrufer"] if a["name"] == args.name]
        if not treffer:
            raise SystemExit(f"Aufrufer «{args.name}» gibt es nicht.")
        treffer[0]["werkzeuge"] = werkzeuge
        ZUGANG.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n")
        print(f"Aufrufer «{args.name}»: Werkzeuge jetzt {', '.join(werkzeuge) or '(keine)'}. Schlüssel unverändert.")
        return

    schluessel = secrets.token_urlsafe(32)
    eintrag = {
        "name": args.name,
        "hash": hashlib.sha256(schluessel.encode()).hexdigest(),
        "werkzeuge": werkzeuge,
    }

    daten["aufrufer"] = [a for a in daten["aufrufer"] if a["name"] != args.name] + [eintrag]
    ZUGANG.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n")
    # Der Container läuft als eigener Benutzer und muss die Liste lesen können. Sie enthält nur Hashes.
    os.chmod(ZUGANG, 0o644)

    print(f"Aufrufer «{args.name}» eingetragen, Werkzeuge: {', '.join(eintrag['werkzeuge'])}")
    if args.datei:
        ziel = Path(args.datei)
        ziel.write_text(schluessel + "\n")
        os.chmod(ziel, 0o600)
        print(f"Schlüssel geschrieben nach {ziel} (Rechte 600).")
    else:
        print("\nSchlüssel (wird nur jetzt angezeigt):\n")
        print(f"  {schluessel}\n")
        print("Für Manni als Zeile in ~hermes/.hermes/.env eintragen:")
        print("  WERKZEUG_SERVER_KEY=<Schlüssel>")


if __name__ == "__main__":
    main()
