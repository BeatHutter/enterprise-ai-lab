"""Werkzeug-Server der Muster AG (MCP über Streamable HTTP).

Manni liest Odoo direkt. Schreiben geht nur über die Werkzeuge dieses Servers.
Plan: werkzeug-server/plan-werkzeug-server.md, Architektur: docs/architektur-agenten.md.

Zwei Sperren für den Zugang:
1. Die HTTP-Schicht weist jede Anfrage ohne gültigen Schlüssel ab (401).
2. Jedes Werkzeug prüft beim Aufruf, ob der Schlüssel genau dieses Werkzeug darf.
"""

import asyncio
import functools
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from lieferantenrechnung import Position, entwurf_anlegen
from offerte import OffertPosition, angebot_anlegen
from odoo import Odoo, OdooFehler

ZUGANG_DATEI = Path(os.environ.get("ZUGANG_DATEI", "/run/zugang/zugang.json"))
PROTOKOLL_DATEI = Path(os.environ.get("PROTOKOLL_DATEI", "/daten/protokoll.jsonl"))
PORT = int(os.environ.get("PORT", "8090"))


# --- Zugang ---------------------------------------------------------------

def _hash(schluessel: str) -> str:
    return hashlib.sha256(schluessel.encode()).hexdigest()


def lade_zugang() -> dict:
    """Liest die Liste der Aufrufer: {hash: {"name": ..., "werkzeuge": [...]}}.

    Im Server liegen nur Hashes, nie die Schlüssel selbst.
    """
    daten = json.loads(ZUGANG_DATEI.read_text())
    return {eintrag["hash"]: eintrag for eintrag in daten["aufrufer"]}


def aufrufer_aus_kopfzeile(kopfzeile: str | None) -> dict | None:
    if not kopfzeile or not kopfzeile.startswith("Bearer "):
        return None
    gesuchter_hash = _hash(kopfzeile.removeprefix("Bearer ").strip())
    # Bei jeder Anfrage neu lesen: Änderungen gelten ohne Neustart
    for bekannter_hash, eintrag in lade_zugang().items():
        if hmac.compare_digest(bekannter_hash, gesuchter_hash):
            return eintrag
    return None


class SchluesselPruefung:
    """ASGI-Schicht vor dem MCP-Server: ohne gültigen Schlüssel keine Antwort."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            kopfzeilen = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
            if aufrufer_aus_kopfzeile(kopfzeilen.get("authorization")) is None:
                protokolliere({"ereignis": "abgewiesen", "pfad": scope.get("path"),
                               "grund": "kein oder falscher Schlüssel"})
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json"),
                                        (b"www-authenticate", b"Bearer")]})
                await send({"type": "http.response.body",
                            "body": b'{"fehler": "Schluessel fehlt oder ist falsch"}'})
                return
        await self.app(scope, receive, send)


# --- Protokoll ------------------------------------------------------------

def protokolliere(eintrag: dict) -> None:
    eintrag = {"zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"), **eintrag}
    PROTOKOLL_DATEI.parent.mkdir(parents=True, exist_ok=True)
    with PROTOKOLL_DATEI.open("a") as datei:
        # Pydantic-Objekte (z. B. Positionen) als Wörterbuch, alles andere als Text
        datei.write(json.dumps(eintrag, ensure_ascii=False,
                               default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o)) + "\n")


class ZugriffVerweigert(ToolError):
    """ToolError: Der Grund geht an den Aufrufer. Andere Ausnahmen zeigt das SDK nur als «Error executing tool»."""


def werkzeug(func):
    """Rahmen für jedes Werkzeug: Recht prüfen, Aufruf protokollieren.

    Das Werkzeug bekommt den Aufrufer nicht vom Modell, sondern aus dem Schlüssel.
    """

    @functools.wraps(func)
    async def rahmen(*args, ctx: Context, **kwargs):
        name = func.__name__
        headers = ctx.headers or {}
        aufrufer = aufrufer_aus_kopfzeile(headers.get("authorization"))
        start = time.monotonic()
        basis = {"werkzeug": name, "aufrufer": aufrufer["name"] if aufrufer else None, "argumente": kwargs}
        if aufrufer is None or name not in aufrufer.get("werkzeuge", []):
            protokolliere({**basis, "ereignis": "verweigert"})
            raise ZugriffVerweigert(f"Dieser Schlüssel darf das Werkzeug «{name}» nicht benutzen.")
        try:
            ergebnis = await func(*args, ctx=ctx, **kwargs)
        except Exception as fehler:
            protokolliere({**basis, "ereignis": "fehler", "fehler": str(fehler),
                           "dauer_s": round(time.monotonic() - start, 2)})
            raise
        protokolliere({**basis, "ereignis": "ausgefuehrt", "ergebnis": ergebnis,
                       "dauer_s": round(time.monotonic() - start, 2)})
        return ergebnis

    return rahmen


# --- Freigabe per Knopf ---------------------------------------------------

class Bestaetigung(BaseModel):
    """Leeres Formular: Gefragt ist nur ja oder nein. Hermes schickt bei Zustimmung keinen Inhalt mit."""


async def freigabe_einholen(ctx: Context, text: str) -> tuple[bool, str]:
    """Fragt den Menschen per Elicitation. Gibt (freigegeben, Grund) zurück.

    Schlägt immer geschlossen fehl: Ohne Elicitation beim Client, bei Ablehnung,
    Abbruch, Zeitablauf oder Fehler gilt «nicht freigegeben». Der Text kommt vom Server,
    nicht vom Modell, und Manni kann den Knopf nicht selbst drücken.
    """
    faehigkeiten = ctx.client_capabilities
    if faehigkeiten is None or faehigkeiten.elicitation is None:
        return False, "Der Client kann keine Rückfrage stellen, darum keine Freigabe möglich."
    try:
        antwort = await ctx.elicit(message=text, schema=Bestaetigung)
    except Exception as fehler:
        return False, f"Rückfrage gescheitert: {fehler}"
    if antwort.action == "accept":
        return True, "freigegeben"
    if antwort.action == "decline":
        return False, "abgelehnt"
    return False, "keine Antwort (abgebrochen oder Zeit abgelaufen)"


# --- Werkzeuge ------------------------------------------------------------

mcp = MCPServer(
    name="muster",
    title="Werkzeug-Server Muster AG",
    instructions=(
        "Werkzeuge zum Schreiben in Odoo der Muster AG. Lesen geht nicht über diesen Server. "
        "Jedes Werkzeug prüft seine Angaben selbst und lehnt ab, wenn etwas nicht stimmt."
    ),
    version="0.1.0",
)


@mcp.tool(
    title="Verbindung prüfen",
    description="Antwortet mit dem Namen des Aufrufers und der Uhrzeit. Schreibt nichts.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
@werkzeug
async def ping(ctx: Context) -> str:
    aufrufer = aufrufer_aus_kopfzeile((ctx.headers or {}).get("authorization"))
    return f"pong für {aufrufer['name']}, {datetime.now(timezone.utc).isoformat(timespec='seconds')}"


@mcp.tool(
    title="Probe: Freigabe per Knopf",
    description=(
        "Nur für Tests der Freigabe (Bauschritt W1). Fragt Beat per Knopf, ob er den übergebenen Text freigibt, "
        "und meldet zurück, ob er zugestimmt hat. Schreibt nichts, weder in Odoo noch anderswo. "
        "Eine Freigabe kann nur Beat mit dem Knopf erteilen, nicht der Agent."
    ),
)
@werkzeug
async def probe_freigabe(text: str, ctx: Context) -> str:
    frage = f"PROBE-FREIGABE (schreibt nichts)\n\n{text}"
    freigegeben, grund = await freigabe_einholen(ctx, frage)
    return f"Freigabe: {'JA' if freigegeben else 'NEIN'} ({grund})"


odoo = Odoo()


@mcp.tool(
    title="Lieferantenrechnung als Entwurf anlegen",
    description=(
        "Legt in Odoo eine Lieferantenrechnung als ENTWURF an (UC-001). Gebucht wird nie, das macht ein Mensch. "
        "Du liest den Beleg selbst und übergibst die Angaben. Den Lieferanten (ID) und eine Bestellung suchst du vorher "
        "mit odoo-lesen. Der Server prüft: Lieferant existiert, keine Doppelerfassung, Währung aktiv, nur Aufwandkonten "
        "4xxx/6xxx, nur Vorsteuer-Codes, und das Total aus den Positionen muss zum Total laut Beleg "
        "passen. Bei einem Verstoss legt er nichts an und antwortet mit «ABGELEHNT: Grund». Dann nicht anders umgehen, "
        "sondern Beat melden. Bei aussergewöhnlich hohen Beträgen legt er an und meldet «WARNUNG». Gib sie an Beat weiter."
    ),
)
@werkzeug
async def lieferantenrechnung_entwurf_anlegen(
    lieferant_id: int,
    rechnungsnummer: str,
    rechnungsdatum: str,
    waehrung: str,
    positionen: list[Position],
    total_brutto: float,
    ctx: Context,
    faelligkeit: str | None = None,
    zahlungsreferenz: str | None = None,
    bestellung: str | None = None,
) -> str:
    """rechnungsdatum und faelligkeit als JJJJ-MM-TT. waehrung CHF oder EUR. total_brutto = Total inkl. MWST laut Beleg.
    zahlungsreferenz = QR- oder Zahlungsreferenz. bestellung = Nummer der Bestellung in Odoo, z. B. P00123."""
    aufrufer = aufrufer_aus_kopfzeile((ctx.headers or {}).get("authorization"))["name"]
    try:
        return await asyncio.to_thread(
            entwurf_anlegen, odoo, aufrufer, lieferant_id, rechnungsnummer, rechnungsdatum, waehrung,
            positionen, total_brutto, faelligkeit, zahlungsreferenz, bestellung)
    except OdooFehler as fehler:
        raise ToolError(f"Odoo meldet einen Fehler: {fehler}")


@mcp.tool(
    title="Offerte als Entwurf anlegen",
    description=(
        "Legt in Odoo ein Angebot (Offerte) als ENTWURF an (UC-005). Versendet und bestätigt wird nie, das macht der "
        "Innendienst. Du übergibst nur Kunde (ID), Artikelcodes und Mengen. Preise und Rabatte setzt Odoo aus der "
        "Preisliste des Kunden, du kannst sie nicht beeinflussen. Kunde und Artikel suchst du vorher mit odoo-lesen. "
        "Der Server prüft: Kunde existiert und ist Kunde, Artikel existiert und ist verkäuflich, Mengen gültig. "
        "Bei einem Verstoss legt er nichts an und antwortet mit «ABGELEHNT: Grund». Bei möglichen Doppeln oder "
        "ungewöhnlichen Mengen legt er an und meldet «WARNUNG». Im hinweis gibst du dem Innendienst weiter, was "
        "das Werkzeug nicht abbildet: Rabattwunsch, gewünschter Termin, fehlende Artikel, Sonderwünsche."
    ),
)
@werkzeug
async def offerte_entwurf_anlegen(
    kunde_id: int,
    positionen: list[OffertPosition],
    ctx: Context,
    kundenreferenz: str | None = None,
    hinweis: str | None = None,
) -> str:
    """kundenreferenz = Bezug des Kunden, z. B. «Anfrage vom 10.11.2026, Herr Muster». hinweis = Notiz an den Innendienst."""
    aufrufer = aufrufer_aus_kopfzeile((ctx.headers or {}).get("authorization"))["name"]
    try:
        return await asyncio.to_thread(angebot_anlegen, odoo, aufrufer, kunde_id, positionen, kundenreferenz, hinweis)
    except OdooFehler as fehler:
        raise ToolError(f"Odoo meldet einen Fehler: {fehler}")


# --- Start ----------------------------------------------------------------

def app():
    # host="127.0.0.1" schaltet den Schutz gegen DNS-Rebinding ein (Host- und Origin-Prüfung)
    return SchluesselPruefung(mcp.streamable_http_app(host="127.0.0.1"))


if __name__ == "__main__":
    # Im Container auf allen Adressen, nach aussen gibt Docker nur 127.0.0.1 frei
    uvicorn.run(app(), host="0.0.0.0", port=PORT, log_level="info")
