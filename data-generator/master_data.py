"""Lädt die Vorgaben aus daten/*.csv (Semikolon-getrennt, UTF-8)."""

import csv
from decimal import Decimal
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "daten"

SEGMENTS = [
    "Gemeinden und Städte",
    "Immobilienverwaltungen und Genossenschaften",
    "Garten- und Landschaftsbau",
    "Schulgemeinden",
    "Hotels und Bergbahnen",
]
# Gartenbauer sind Wiederverkäufer mit 10 % Rabatt (Drehbuch)
RESELLER_SEGMENT = "Garten- und Landschaftsbau"


def _read(name):
    with open(DATA_DIR / name, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def _dec(value):
    return Decimal(value) if value not in (None, "") else None


def load_articles():
    rows = _read("artikel.csv")
    for row in rows:
        row["verkaufspreis"] = _dec(row["verkaufspreis"])
        row["materialkosten"] = _dec(row["materialkosten"])
        row["einkaufspreis"] = _dec(row["einkaufspreis"])
        row["stahlartikel"] = row["stahlartikel"] == "ja"
    return rows


def load_customers():
    rows = _read("kunden.csv")
    for row in rows:
        if row["segment"] not in SEGMENTS:
            raise ValueError(f"Unbekanntes Segment bei {row['name']}: {row['segment']}")
        row["zahlt_nach_tagen"] = int(row["zahlt_nach_tagen"])
        row["gewicht"] = int(row["gewicht"])
    return rows


def load_suppliers():
    rows = _read("lieferanten.csv")
    for row in rows:
        row["anteil_einkauf"] = _dec(row["anteil_einkauf"])
    return rows


def load_eur_rates():
    rows = _read("kurse_eur.csv")
    for row in rows:
        row["chf_pro_eur"] = _dec(row["chf_pro_eur"])
    return rows
