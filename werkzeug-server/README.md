# Tool server (MCP)

The only way the agent can write to the ERP. A small MCP server in Python (official MCP SDK) that runs in Docker, listens on localhost only and holds the ERP write credentials. Background: [architecture](../docs/architecture.md).

## Tools

| Tool | What it does | Checks before writing |
| --- | --- | --- |
| `lieferantenrechnung_entwurf_anlegen` | Supplier invoice as draft | supplier exists, no duplicate, currency active, expense accounts only, input-tax codes only, line totals match the invoice total. Unusually high amounts: created with a warning |
| `offerte_entwurf_anlegen` | Quote as draft | customer exists, items exist and are saleable, quantities valid. Prices come from the customer's price list in Odoo, the agent cannot set them. Possible duplicates and unusual quantities: created with a warning |
| `probe_freigabe` | Test of the approval button (MCP elicitation) | – |
| `ping` | Health check | – |

A failed check returns `ABGELEHNT: <reason>` and nothing is written. There is no tool for posting, sending, paying or deleting.

## How a call is handled

1. The caller sends its key as a bearer token. The server stores only SHA-256 hashes of the keys, together with the tools each caller may use (`zugang.example.json`).
2. The decorator `@werkzeug` in `server/app.py` checks the permission and writes every call to an audit log (JSON lines): executed, rejected, refused or failed.
3. The tool validates the input, then creates the draft through Odoo's API with its own technical user (no admin or manager groups).
4. The draft carries a note stating which caller created it.

## Files

| Path | Content |
| --- | --- |
| `server/app.py` | MCP server, authentication, audit log, tool definitions |
| `server/lieferantenrechnung.py`, `server/offerte.py` | Validation rules and draft creation per use case |
| `server/odoo.py` | Minimal JSON-RPC client |
| `docker-compose.yml` | Hardened container: read-only file system, all capabilities dropped, no new privileges, port bound to 127.0.0.1 |
| `schluessel-erzeugen.py` | Generates a caller key and stores only its hash |
| `odoo-benutzer-anlegen.py` | Creates the technical Odoo user with explicitly set groups |
| `pruefung/` | Tests: every validation rule with its own call (`regeln_pruefen.sh`), quote tool (`offerte_pruefen.sh`) |
| `pruefen.sh` | Checks of the setup: localhost-only port, non-root and read-only container, missing or wrong key rejected, only hashes stored, audit log written, agent's Linux user cannot read keys or reach Docker |

## Results

Validation rules 16 of 16. Supplier invoices from 10 test PDFs: 10 of 10 handled correctly, including a calculation error, a duplicate and a deception attempt. Quotes from 10 test requests: 10 of 10 after one skill fix. Details in [docs/erkenntnisse.md](../docs/erkenntnisse.md) (German).
