#!/usr/bin/env python3
"""gmail_anmelden.py - erzeugt einmalig das Lese-Token für Gmail. Nur Beat führt es aus.

Aufruf (als hermes, damit das Token bei hermes liegt):
    sudo -u hermes -H python3 /home/hermes/hermes-skills/gemeinsam/gmail-lesen/scripts/gmail_anmelden.py
    sudo -u hermes -H python3 .../gmail_anmelden.py --schreibprobe

Ablauf:
1. Das Programm zeigt eine Adresse. Beat öffnet sie im Browser, meldet sich mit
   musterag.labor@gmail.com an und erlaubt «E-Mails lesen».
2. Google leitet auf http://localhost:8765/?code=... weiter. Das Programm hört dort
   kurz zu (nur 127.0.0.1) und übernimmt die Adresse selbst. Erreicht der Browser die
   Kiste nicht, kopiert Beat die ganze Adresse aus der Adresszeile und fügt sie ein.
3. Das Programm tauscht den Code gegen ein Token, prüft den Bereich (nur gmail.readonly)
   und speichert es mit Rechten 600 in ~/.hermes/gmail/token.json.

--schreibprobe: versucht ein Label anzulegen. Erwartet: Google lehnt ab (403).
Damit ist belegt, dass der Zugang nicht schreiben kann.

Im Testmodus der Google-App läuft das Token nach 7 Tagen ab (OP-41). Dann dieses
Programm erneut ausführen. Nur Python-Standardbibliothek. Gibt keine Geheimnisse aus.
"""

import argparse
import http.server
import queue
import threading
import base64
import hashlib
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BEREICH = "https://www.googleapis.com/auth/gmail.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PROFIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
LABEL_URL = "https://gmail.googleapis.com/gmail/v1/users/me/labels"
REDIRECT = "http://localhost:8765/"
ERWARTETES_KONTO = "musterag.labor@gmail.com"

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
CLIENT_DATEI = Path(os.environ.get("GMAIL_CLIENT_DATEI", HERMES_HOME / "gmail" / "client.json"))
TOKEN_DATEI = Path(os.environ.get("GMAIL_TOKEN_DATEI", HERMES_HOME / "gmail" / "token.json"))


def client_laden() -> dict:
    if not CLIENT_DATEI.exists():
        raise SystemExit(f"OAuth-Client fehlt: {CLIENT_DATEI}. Zuerst die JSON-Datei von Google dorthin legen.")
    daten = json.loads(CLIENT_DATEI.read_text(encoding="utf-8"))
    return daten.get("installed") or daten


def post(url: str, felder: dict) -> dict:
    anfrage = urllib.request.Request(url, data=urllib.parse.urlencode(felder).encode(), method="POST")
    try:
        with urllib.request.urlopen(anfrage, timeout=30) as antwort:
            return json.load(antwort)
    except urllib.error.HTTPError as fehler:
        try:
            art = json.load(fehler).get("error", "")
        except Exception:
            art = ""
        raise SystemExit(f"Google lehnt ab: HTTP {fehler.code} {art}")


def access_token(client: dict) -> str:
    token = json.loads(TOKEN_DATEI.read_text(encoding="utf-8"))
    return post(TOKEN_URL, {
        "client_id": client["client_id"],
        "client_secret": client.get("client_secret", ""),
        "refresh_token": token["refresh_token"],
        "grant_type": "refresh_token",
    })["access_token"]


def antwort_abwarten() -> str:
    """Wartet auf die Weiterleitung von Google: entweder kommt sie am Port 8765 an,
    oder Beat fügt die Adresse von Hand ein. Was zuerst da ist, gilt."""
    eingang: queue.Queue = queue.Queue()

    class Empfang(http.server.BaseHTTPRequestHandler):
        timeout = 10  # leere Verbindungen des Browsers nicht ewig offen halten

        def do_GET(self):
            if "state=" not in self.path:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<p>Angekommen. Dieses Fenster kann geschlossen werden. Weiter im Terminal.</p>".encode())
            eingang.put(REDIRECT.rstrip("/") + self.path)

        def log_message(self, *args):  # nichts ausgeben: die Adresse enthält den Code
            pass

    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), Empfang)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print("2. Das Programm wartet auf die Weiterleitung (localhost:8765).")
        print("   Lädt die Seite im Browser endlos: in VS Code unter «Ports» den Port 8765 weiterleiten,")
        print("   oder die ganze Adresse aus der Adresszeile hier einfügen und Enter drücken.")
    except OSError:
        print("2. Port 8765 ist belegt. Danach lädt die Seite localhost:8765 nicht.")
        print("   Ganze Adresse aus der Adresszeile hier einfügen und Enter drücken.")

    def von_hand():
        try:
            eingang.put(input("   Warte ... ").strip())
        except EOFError:
            pass

    threading.Thread(target=von_hand, daemon=True).start()
    try:
        return eingang.get(timeout=600)
    except queue.Empty:
        raise SystemExit("\nAbbruch: Nach 10 Minuten keine Antwort. Bitte neu starten.")


def anmelden() -> None:
    client = client_laden()
    pruefer = secrets.token_urlsafe(64)
    herausforderung = base64.urlsafe_b64encode(hashlib.sha256(pruefer.encode()).digest()).decode().rstrip("=")
    zustand = secrets.token_urlsafe(16)
    adresse = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client["client_id"],
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": BEREICH,
        "access_type": "offline",
        "prompt": "consent",
        "login_hint": ERWARTETES_KONTO,
        "code_challenge": herausforderung,
        "code_challenge_method": "S256",
        "state": zustand,
    })
    print("\n1. Diese Adresse im Browser öffnen und mit", ERWARTETES_KONTO, "anmelden:\n")
    print(adresse)
    print("\n   «Google hat diese App nicht überprüft» → Erweitert → Weiter zu Muster AG (Labor).")
    print("   Auf der Zustimmungsseite darf nur «E-Mails lesen» stehen. Steht mehr da: abbrechen.\n")
    eingabe = antwort_abwarten()

    teile = urllib.parse.parse_qs(urllib.parse.urlparse(eingabe).query)
    if teile.get("state", [""])[0] != zustand:
        raise SystemExit("Abbruch: Die Adresse passt nicht zu dieser Anmeldung (state). Bitte neu starten.")
    if "error" in teile:
        raise SystemExit(f"Abbruch: Google meldet {teile['error'][0]}.")
    code = teile.get("code", [""])[0]
    if not code:
        raise SystemExit("Abbruch: Kein Code in der Adresse gefunden.")

    antwort = post(TOKEN_URL, {
        "client_id": client["client_id"],
        "client_secret": client.get("client_secret", ""),
        "code": code,
        "code_verifier": pruefer,
        "redirect_uri": REDIRECT,
        "grant_type": "authorization_code",
    })
    bereiche = antwort.get("scope", "").split()
    if bereiche != [BEREICH]:
        raise SystemExit(f"Abbruch: Google hat andere Bereiche erteilt ({', '.join(bereiche)}). Token nicht gespeichert.")
    if "refresh_token" not in antwort:
        raise SystemExit("Abbruch: Kein Refresh-Token erhalten. Zugriff unter myaccount.google.com/permissions entfernen und neu starten.")

    # Konto prüfen, bevor gespeichert wird
    anfrage = urllib.request.Request(PROFIL_URL)
    anfrage.add_header("Authorization", "Bearer " + antwort["access_token"])
    with urllib.request.urlopen(anfrage, timeout=30) as r:
        konto = json.load(r).get("emailAddress", "")
    if konto.lower() != ERWARTETES_KONTO:
        raise SystemExit(f"Abbruch: Angemeldet als {konto}, erwartet {ERWARTETES_KONTO}. Token nicht gespeichert.")

    TOKEN_DATEI.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    inhalt = json.dumps({
        "refresh_token": antwort["refresh_token"],
        "scope": BEREICH,
        "konto": konto,
        "erzeugt_am": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2)
    alt = os.umask(0o077)
    try:
        TOKEN_DATEI.write_text(inhalt, encoding="utf-8")
    finally:
        os.umask(alt)
    os.chmod(TOKEN_DATEI, 0o600)
    print(f"\nFertig: Token für {konto} gespeichert ({TOKEN_DATEI}), Bereich nur gmail.readonly.")
    print("Im Testmodus gültig für 7 Tage. Erinnerung kommt ab Tag 6 per Telegram.")


def schreibprobe() -> None:
    client = client_laden()
    anfrage = urllib.request.Request(
        LABEL_URL,
        data=json.dumps({"name": "schreibprobe-sollte-scheitern"}).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + access_token(client)},
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=30):
            print("WARNUNG: Google hat das Schreiben erlaubt. Der Zugang ist NICHT nur lesend. Label in Gmail löschen und melden.")
            sys.exit(1)
    except urllib.error.HTTPError as fehler:
        if fehler.code == 403:
            print("OK: Google lehnt Schreiben ab (403). Der Zugang kann nur lesen.")
        else:
            print(f"Unerwartete Antwort: HTTP {fehler.code}")
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gmail-Lesezugang einrichten (nur Beat).")
    parser.add_argument("--schreibprobe", action="store_true", help="prüfen, dass Schreiben abgelehnt wird")
    args = parser.parse_args()
    schreibprobe() if args.schreibprobe else anmelden()


if __name__ == "__main__":
    main()
