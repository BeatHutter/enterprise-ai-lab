"""Kleiner MCP-Client für das Prüfskript. Läuft im Container (dort ist das SDK installiert).

Aufruf: python - <werkzeug> [argumente-json]  mit Umgebungsvariablen
  SCHLUESSEL   Schlüssel für den Server (leer = ohne)
  RUECKFRAGE   wie der Client auf eine Rückfrage (Elicitation) antwortet:
               ablehnen (Standard), annehmen, keine (Client meldet keine Elicitation)
Gibt eine Zeile aus: OK <text> oder FEHLER <text>.
"""

import asyncio
import json
import os
import sys

import httpx2
from mcp import types
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = os.environ.get("URL", "http://127.0.0.1:8090/mcp")
RUECKFRAGE = os.environ.get("RUECKFRAGE", "ablehnen")


async def ablehnen(context, params):
    return types.ElicitResult(action="decline")


async def annehmen(context, params):
    # Wie Hermes: Zustimmung ohne Inhalt
    return types.ElicitResult(action="accept", content={})


async def main():
    werkzeug = sys.argv[1]
    argumente = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    kopf = {"Authorization": f"Bearer {os.environ['SCHLUESSEL']}"} if os.environ.get("SCHLUESSEL") else {}
    rueckruf = {"ablehnen": ablehnen, "annehmen": annehmen}.get(RUECKFRAGE)
    extra = {"elicitation_callback": rueckruf} if rueckruf else {}
    async with httpx2.AsyncClient(headers=kopf, timeout=30) as http:
        async with streamable_http_client(URL, http_client=http) as (lesen, schreiben, *_):
            async with ClientSession(lesen, schreiben, **extra) as sitzung:
                await sitzung.initialize()
                ergebnis = await sitzung.call_tool(werkzeug, argumente)
                text = " ".join(getattr(b, "text", "") for b in ergebnis.content)
                text = text.replace("\n", " | ")  # eine Zeile, auch bei mehrzeiligen Antworten
                print(("FEHLER " if ergebnis.is_error else "OK ") + text)


try:
    asyncio.run(main())
except BaseException as fehler:  # auch ExceptionGroup aus anyio
    print(f"FEHLER {type(fehler).__name__}: {fehler}")
