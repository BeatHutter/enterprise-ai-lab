#!/usr/bin/env python3
"""Kennzahlen der Muster AG abrufen. Liest Odoo nur, rechnet nach katalog.md.

Aufrufe:
  kennzahl.py liste
  kennzahl.py katalog <kennung>
  kennzahl.py <kennung> --von JJJJ-MM-TT --bis JJJJ-MM-TT [--aufteilung monat|quartal] [--vergleich vorjahr]
  kennzahl.py <kennung> --stichtag JJJJ-MM-TT [--nach kunde] [--vergleich vorjahr]
  Zusätzlich überall: --format json|text (Standard json)

Zugang zu Odoo aus der Umgebung: ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY.
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from kennzahlen.basis import FORMATE, Kontext, ch_datum, chf, datum, prozent, runde, teilzeitraeume, vorjahr  # noqa: E402
from kennzahlen.katalog import eintraege, pruefe_versionen  # noqa: E402
from kennzahlen.odoo import OdooFehler  # noqa: E402
from kennzahlen.register import MODULE  # noqa: E402

CHF_FELDER = ("wert", "betrag", "total", "vorjahr", "veraenderung")
PROZENT_FELDER = ("anteil", "marge", "marge_vorjahr", "veraenderung_prozent")
VERGLEICH_LISTEN = {"bestandteile": ("konto", "kennung", "name"), "segmente": ("segment",), "stufen": ("stufe",)}


class Abbruch(Exception):
    pass


# --- Aufbereitung -----------------------------------------------------------

def aufbereiten(obj, einheit_wert=None):
    """Rundet und ergänzt *_text-Felder in Schweizer Schreibweise. Nur oberste Ebene nutzt einheit_wert."""
    if isinstance(obj, list):
        return [aufbereiten(x) for x in obj]
    if not isinstance(obj, dict):
        return obj
    neu = {}
    for key, wert in obj.items():
        if isinstance(wert, (dict, list)):
            neu[key] = aufbereiten(wert)
        elif key in CHF_FELDER and isinstance(wert, (int, float)) and einheit_wert is None:
            neu[key] = round(wert, 2)
            neu[f"{key}_text"] = chf(wert)
        elif key in PROZENT_FELDER and isinstance(wert, (int, float)):
            neu[key] = round(wert, 1)
            neu[f"{key}_text"] = prozent(wert)
        elif key == "datum" and isinstance(wert, str):
            neu[key] = wert
            neu["datum_text"] = ch_datum(wert)
        else:
            neu[key] = wert
    return neu


def veraenderung(jetzt, frueher, einheit):
    if jetzt is None or frueher is None:
        return {}
    diff = jetzt - frueher
    if einheit == "%":
        return {"veraenderung_prozentpunkte": round(diff, 1),
                "veraenderung_text": f"{diff:+.1f} Prozentpunkte"}
    aus = {"veraenderung": runde(diff, einheit),
           "veraenderung_text": chf(diff) if einheit == "CHF" else f"{round(diff):+d} Tage"}
    if frueher != 0:
        aus["veraenderung_prozent"] = round(diff / abs(frueher) * 100, 1)
        aus["veraenderung_prozent_text"] = f"{diff / abs(frueher) * 100:+.1f} %"
    return aus


def vergleiche_listen(roh, roh_vj):
    """Ergänzt Listen (Konten, Segmente, Stufen) um Vorjahr und Veränderung, damit niemand selbst rechnet."""
    for liste, schluessel in VERGLEICH_LISTEN.items():
        if liste not in roh:
            continue
        def key(e):
            return next((e[s] for s in schluessel if e.get(s) is not None), None)
        vj = {key(e): e for e in roh_vj.get(liste, [])}
        feld = "betrag" if liste == "stufen" else "wert"
        for e in roh[liste]:
            alt = vj.pop(key(e), None)
            e["vorjahr"] = alt[feld] if alt else 0.0
            e["veraenderung"] = e[feld] - e["vorjahr"]
            if e["vorjahr"]:
                p = e["veraenderung"] / abs(e["vorjahr"]) * 100
                e["veraenderung_prozent"] = p
                e["veraenderung_prozent_text"] = f"{p:+.1f} %"
        for k, alt in vj.items():  # nur im Vorjahr vorhanden
            eintrag = {s: alt.get(s) for s in schluessel if alt.get(s) is not None}
            eintrag.update({feld: 0.0, "vorjahr": alt[feld], "veraenderung": -alt[feld]})
            roh[liste].append(eintrag)


# --- Rechnen ----------------------------------------------------------------

def rechne(ctx, modul, args, von=None, bis=None, stichtag=None):
    if modul.ART == "stichtag":
        return modul.berechne(ctx, stichtag, args.nach)
    return modul.berechne(ctx, von, bis)


def einzel(ctx, modul, args, von=None, bis=None, stichtag=None):
    roh = rechne(ctx, modul, args, von, bis, stichtag)
    vergleich = None
    if args.vergleich == "vorjahr":
        if modul.ART == "stichtag":
            vj_args = {"stichtag": vorjahr(datum(stichtag)).isoformat()}
        else:
            vj_args = {"von": vorjahr(datum(von)).isoformat(), "bis": vorjahr(datum(bis)).isoformat()}
        roh_vj = rechne(ctx, modul, args, **vj_args)
        vergleich = {"art": "vorjahr", **vj_args, "wert": runde(roh_vj["wert"], modul.EINHEIT),
                     "text": FORMATE[modul.EINHEIT](roh_vj["wert"]),
                     **veraenderung(roh["wert"], roh_vj["wert"], modul.EINHEIT)}
        if "marge" in roh:
            vergleich["marge_vorjahr"] = roh_vj.get("marge")
            if roh.get("marge") is not None and roh_vj.get("marge") is not None:
                d = roh["marge"] - roh_vj["marge"]
                vergleich["marge_veraenderung_text"] = f"{d:+.1f} Prozentpunkte"
        vergleiche_listen(roh, roh_vj)
        if roh_vj["hinweise"]:
            vergleich["hinweise"] = roh_vj["hinweise"]

    aus = {"wert": runde(roh["wert"], modul.EINHEIT), "einheit": modul.EINHEIT,
           "text": FORMATE[modul.EINHEIT](roh["wert"])}
    if stichtag:
        aus["stichtag"] = stichtag
    else:
        aus["zeitraum"] = {"von": von, "bis": bis, "text": f"{ch_datum(von)} bis {ch_datum(bis)}"}
    for key, wert in roh.items():
        if key != "wert":
            aus[key] = aufbereiten(wert) if isinstance(wert, (list, dict)) else wert
    if "marge" in roh:
        aus["marge"] = None if roh["marge"] is None else round(roh["marge"], 1)
        aus["marge_text"] = prozent(roh["marge"])
    if vergleich is not None:
        aus["vergleich"] = aufbereiten(vergleich, einheit_wert=modul.EINHEIT)
    return aus


def abrufen(modul, args):
    ctx = Kontext()
    kopf = {"kennung": modul.KENNUNG, "nr": modul.NR, "name": modul.NAME, "katalogversion": modul.KATALOGVERSION}
    if modul.ART == "stichtag":
        if not args.stichtag or args.von or args.bis or args.aufteilung:
            raise Abbruch(f"{modul.KENNUNG} ist ein Bestand: nur --stichtag angeben")
        datum(args.stichtag)
        aus = {**kopf, **einzel(ctx, modul, args, stichtag=args.stichtag)}
    else:
        if not (args.von and args.bis) or args.stichtag or args.nach:
            raise Abbruch(f"{modul.KENNUNG} gilt für einen Zeitraum: --von und --bis angeben")
        von, bis = datum(args.von), datum(args.bis)
        if von > bis:
            raise Abbruch("--von liegt nach --bis")
        aus = {**kopf, **einzel(ctx, modul, args, von=args.von, bis=args.bis)}
        if args.aufteilung:
            aus["aufteilung"] = []
            for t_von, t_bis, label in teilzeitraeume(von, bis, args.aufteilung):
                teil = einzel(ctx, modul, args, von=t_von.isoformat(), bis=t_bis.isoformat())
                aus["aufteilung"].append({"label": label, **teil})
    aus["quelle"] = (f"Odoo, Datenbank {ctx.odoo.db}, gebuchte Belege, "
                     f"gelesen am {dt.datetime.now():%d.%m.%Y um %H:%M}")
    return aus


# --- Text -------------------------------------------------------------------

def als_text(d):
    z = [f"{d['name']} ({d['kennung']}, Katalog {d['katalogversion']})"]
    z.append(f"Stichtag {ch_datum(d['stichtag'])}" if "stichtag" in d else f"Zeitraum {d['zeitraum']['text']}")
    z.append(f"Wert: {d['text']}" + (f"  (Marge {d['marge_text']})" if "marge_text" in d else ""))
    if d.get("vergleich"):
        v = d["vergleich"]
        z.append(f"Vorjahr: {v['text']}  Veränderung: {v.get('veraenderung_text', '–')}"
                 + (f" ({v['veraenderung_prozent_text']})" if "veraenderung_prozent_text" in v else ""))
    for b in d.get("bestandteile", []):
        z.append(f"  {b.get('konto') or ''} {b['name']}: {b['wert_text']}".replace("   ", "  "))
    for s in d.get("segmente", []):
        z.append(f"  {s['segment']}: {s['wert_text']} ({s.get('anteil_text', '–')})")
    for s in d.get("stufen", []):
        z.append(f"  {s['stufe']}: {s['betrag_text']}, {s['anzahl']} Posten ({s.get('anteil_text', '–')})")
    for k in d.get("kunden", []):
        teile = ", ".join(f"{s['stufe']} {s['betrag_text']}" for s in k["stufen"] if s["anzahl"])
        z.append(f"  {k['kunde']}: {k['total_text']} ({teile})")
    for b in d.get("bestaende", []):
        z.append(f"  Bestand {b['datum_text']}: {b['betrag_text']}")
    if "zahlungsfrist_tage" in d:
        z.append(f"  vereinbarte Zahlungsfrist: {d['zahlungsfrist_tage']} Tage")
    for t in d.get("aufteilung", []):
        zus = f"  Vorjahr {t['vergleich']['text']}" if t.get("vergleich") else ""
        z.append(f"  {t['label']}: {t['text']}{zus}")
    for h in d.get("hinweise", []):
        z.append(f"Hinweis: {h}")
    z.append(f"Quelle: {d['quelle']}")
    return "\n".join(z)


def erste_aussage(eintrag):
    if eintrag["bedeutung"]:
        return eintrag["bedeutung"]
    punkt = next((l[2:] for l in eintrag["text"].splitlines() if l.startswith("- ")), "")
    return punkt


# --- Hauptprogramm ----------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(prog="kennzahl.py", description="Kennzahlen der Muster AG nach Katalog.")
    p.add_argument("befehl", help="Kennung, «liste» oder «katalog»")
    p.add_argument("name", nargs="?", help="Kennung beim Befehl «katalog»")
    p.add_argument("--von")
    p.add_argument("--bis")
    p.add_argument("--stichtag")
    p.add_argument("--aufteilung", choices=["monat", "quartal"])
    p.add_argument("--vergleich", choices=["vorjahr"])
    p.add_argument("--nach", choices=["kunde"])
    p.add_argument("--format", choices=["json", "text"], default="json")
    args = p.parse_args(argv)

    try:
        fehler = pruefe_versionen(MODULE)
        if fehler:
            raise Abbruch("Katalog und Rechenwege passen nicht zusammen: " + "; ".join(fehler))
        katalog = eintraege()

        if args.befehl == "liste":
            liste = [{"kennung": m.KENNUNG, "nr": m.NR, "name": m.NAME, "art": m.ART, "einheit": m.EINHEIT,
                      "katalogversion": m.KATALOGVERSION, "bedeutung": erste_aussage(katalog[m.NR])}
                     for m in MODULE.values()]
            if args.format == "text":
                print("\n".join(f"{x['kennung']:<32} {x['art']:<9} {x['name']}: {x['bedeutung']}" for x in liste))
            else:
                print(json.dumps(liste, ensure_ascii=False, indent=1))
            return 0

        if args.befehl == "katalog":
            modul = MODULE.get(args.name or "")
            if modul is None:
                raise Abbruch(f"Kennung unbekannt: {args.name!r}. Alle Kennungen: kennzahl.py liste")
            print(katalog[modul.NR]["text"])
            return 0

        modul = MODULE.get(args.befehl)
        if modul is None:
            raise Abbruch(f"Kennung unbekannt: {args.befehl!r}. Alle Kennungen: kennzahl.py liste")
        if args.nach and modul.KENNUNG != "debitoren_altersstruktur":
            raise Abbruch("--nach kunde gibt es nur bei debitoren_altersstruktur")
        aus = abrufen(modul, args)
        print(als_text(aus) if args.format == "text" else json.dumps(aus, ensure_ascii=False, indent=1))
        return 0
    except (Abbruch, OdooFehler, RuntimeError, ValueError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
