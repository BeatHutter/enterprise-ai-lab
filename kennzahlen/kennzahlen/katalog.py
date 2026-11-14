"""Liest katalog.md: Einträge pro Kennzahl und deren Version.

Jeder Rechenweg trägt die Katalogversion, nach der er gebaut ist. Weicht sie vom
Katalog ab, rechnet die Bibliothek nicht. So laufen Katalog und Code nie auseinander.
"""

import re
from pathlib import Path

KATALOG = Path(__file__).resolve().parent.parent / "katalog.md"
_UEBERSCHRIFT = re.compile(r"^(##|###) ([KB]\d+) (.+)$")
_VERSION = re.compile(r"\*\*Version:\*\*\s*([0-9]+(?:\.[0-9]+)*)")
_BEDEUTUNG = re.compile(r"\*\*Bedeutung:\*\*\s*(.+)")


def eintraege():
    """{Nr: {"titel", "text", "version", "bedeutung"}} aus dem Katalog."""
    zeilen = KATALOG.read_text(encoding="utf-8").splitlines()
    ergebnis, aktuell, ebene = {}, None, None
    for zeile in zeilen:
        treffer = _UEBERSCHRIFT.match(zeile)
        if treffer:
            ebene, nr, titel = treffer.groups()
            aktuell = ergebnis.setdefault(nr, {"titel": titel, "zeilen": [zeile]})
            continue
        if aktuell is not None:
            # Ende des Eintrags: Trennlinie oder Überschrift gleicher oder höherer Stufe
            if zeile.strip() == "---" or (zeile.startswith("#") and len(zeile) - len(zeile.lstrip("#")) <= len(ebene)):
                aktuell = None
                continue
            aktuell["zeilen"].append(zeile)
    for eintrag in ergebnis.values():
        text = "\n".join(eintrag.pop("zeilen")).strip()
        version = _VERSION.search(text)
        bedeutung = _BEDEUTUNG.search(text)
        eintrag["text"] = text
        eintrag["version"] = version.group(1) if version else None
        eintrag["bedeutung"] = bedeutung.group(1).strip() if bedeutung else None
    return ergebnis


def pruefe_versionen(module):
    """Liste der Abweichungen zwischen Katalog und Rechenwegen, leer wenn alles stimmt."""
    katalog = eintraege()
    fehler = []
    for m in module.values():
        eintrag = katalog.get(m.NR)
        if eintrag is None:
            fehler.append(f"{m.NR} {m.KENNUNG}: fehlt im Katalog")
        elif eintrag["version"] != m.KATALOGVERSION:
            fehler.append(f"{m.NR} {m.KENNUNG}: Katalog {eintrag['version']}, Rechenweg {m.KATALOGVERSION}")
    return fehler
