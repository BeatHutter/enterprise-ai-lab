"""Liest die Zugangsdaten aus data-generator/.env.

Die Werte werden nie ausgegeben. Nur Schlüsselnamen erscheinen in Fehlermeldungen.
"""

import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / ".env"
REQUIRED_KEYS = ("ODOO_URL", "ODOO_DB", "ODOO_USER", "ODOO_API_KEY")


def load_config():
    if not ENV_PATH.exists():
        raise SystemExit(f"{ENV_PATH} fehlt. Vorlage: .env.example")

    values = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")

    # Umgebungsvariablen haben Vorrang, z. B. für einen Lauf vom Hauptrechner
    for key in REQUIRED_KEYS:
        if os.environ.get(key):
            values[key] = os.environ[key]

    missing = [key for key in REQUIRED_KEYS if not values.get(key)]
    if missing:
        raise SystemExit(f"In der .env fehlen Werte für: {', '.join(missing)}")
    return values
