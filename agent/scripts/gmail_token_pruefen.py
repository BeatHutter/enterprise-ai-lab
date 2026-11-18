#!/usr/bin/env python3
"""gmail_token_pruefen.py - täglicher Cron-Job «gmail-token» ohne Modell (--no-agent).

Hintergrund: Seit 13.11.2026 ist die Google-App veröffentlicht. Das Lese-Token
läuft nicht mehr nach 7 Tagen ab. Google kann es aber widerrufen (Passwortwechsel,
lange nicht genutzt, Widerruf im Konto). Darum prüft der Job weiter jeden Tag den Zugang.

Ausgabe wird von Hermes wörtlich an Beat geschickt (Telegram). Leere Ausgabe = keine Meldung.
- Zugang abgelaufen, widerrufen oder fehlt → Meldung mit dem Befehl zum Neu-Anmelden.
- Prüfung fehlgeschlagen → kurze Meldung.
- sonst → nichts.

Die Erinnerung nach Alter des Tokens (Testmodus, bis 13.11.2026) ist entfernt.
Nur Python-Standardbibliothek.
"""

import os
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
LESER = Path(os.environ.get("GMAIL_LESER", HOME / "hermes-skills/gemeinsam/gmail-lesen/scripts/gmail_lesen.py"))
BEFEHL = ("sudo -u hermes -H python3 "
          "/home/hermes/hermes-skills/gemeinsam/gmail-lesen/scripts/gmail_anmelden.py")
# Erfahrung 12.11.2026: Im falschen Browser-Profil hängt die Anmeldung bei Google.
HINWEIS = "Die Adresse im Browser-Profil der Muster AG öffnen (dort ist musterag.labor@gmail.com angemeldet)."


def main() -> None:
    lauf = subprocess.run([sys.executable, str(LESER), "profil"], capture_output=True, text=True, timeout=60)
    if lauf.returncode == 3:
        print("Gmail-Zugang von Manni ist abgelaufen. Der Posteingang wird nicht mehr gelesen.\n"
              f"Neu anmelden auf der Kiste:\n{BEFEHL}\n{HINWEIS}")
        return
    if lauf.returncode != 0:
        print(f"Gmail-Zugang: Prüfung fehlgeschlagen ({lauf.stdout.strip()[:200]}).")


if __name__ == "__main__":
    main()
