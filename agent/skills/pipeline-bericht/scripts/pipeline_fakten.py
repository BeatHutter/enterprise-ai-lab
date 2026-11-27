#!/usr/bin/env python3
"""Fakten für den Pipeline-Bericht der Muster AG, fest gerechnet aus Odoo CRM.

Deterministisch vor agentisch: Dieses Skript rechnet alle Zahlen und prüft feste Regeln.
Das Modell schreibt nur den Kommentar. Es liest nur (search_read über odoo-lesen).

Aufruf (über terminal, damit die ODOO_*-Variablen da sind):
    python3 scripts/pipeline_fakten.py                 Stichtag heute, Ausgabe als Markdown
    python3 scripts/pipeline_fakten.py --stichtag 2026-11-27
    python3 scripts/pipeline_fakten.py --json          dieselben Fakten als JSON

Regeln (Version 1.0.0, Schwellen oben im Code):
- Ohne geplante Aktivität: offene Chance ohne nächste Aktivität.
- Überfällige Aktivität: nächste Aktivität vor dem Stichtag.
- Abschluss überschritten: erwarteter Abschluss vor dem Stichtag, Chance noch offen.
- Mögliche Dublette: zwei offene Chancen derselben Organisation, bei denen eine nicht mit
  einem Kunden verknüpft ist oder die Zuständigen verschieden sind.
- Klumpenrisiko: eine Person hält mehr als die Hälfte des offenen Werts.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

SCHWELLE_KLUMPEN = 0.5          # Anteil am offenen Wert
WOCHE_TAGE = 7                  # «diese Woche» = die letzten 7 Tage bis Stichtag
ORGANISATIONS_WOERTER = {"gemeinde", "stadt", "wohnbaugenossenschaft", "genossenschaft", "immobilien",
                         "ag", "gmbh", "bergbahnen", "schule", "schulen", "hotel", "verwaltung"}

FELDER = ["name", "stage_id", "user_id", "expected_revenue", "probability", "prorated_revenue",
          "date_deadline", "date_last_stage_update", "activity_date_deadline", "partner_id",
          "partner_name", "active", "lost_reason_id", "date_closed"]


# ---------- Lesen ----------

def leser_aus_odoo_lesen():
    """Liest mit dem Zugang von odoo-lesen (ODOO_*-Variablen, Benutzer nur lesend)."""
    pfad = Path(__file__).resolve().parents[2] / "odoo-lesen" / "scripts"
    sys.path.insert(0, str(pfad))
    import odoo_lesen  # noqa: E402  (Skill odoo-lesen, gleiche Ablage)

    url, db, benutzer, schluessel = odoo_lesen.hole_zugang()
    uid = odoo_lesen.anmelden(url, db, benutzer, schluessel)

    def lesen(modell, domain, felder, kontext=None):
        kwargs = {"fields": felder}
        if kontext:
            kwargs["context"] = kontext
        return odoo_lesen.json_rpc(url, {
            "jsonrpc": "2.0", "method": "call", "id": 2,
            "params": {"service": "object", "method": "execute_kw",
                       "args": [db, uid, schluessel, modell, "search_read", [domain], kwargs]},
        })
    return lesen


def daten_holen(lesen):
    stufen = lesen("crm.stage", [], ["id", "name", "sequence", "is_won"])
    chancen = lesen("crm.lead", [("type", "=", "opportunity")], FELDER, {"active_test": False})
    return stufen, chancen


# ---------- Rechnen ----------

def _datum(wert):
    if not wert:
        return None
    return datetime.strptime(str(wert)[:10], "%Y-%m-%d").date()


def _name(m2o, ersatz="-"):
    return m2o[1] if m2o else ersatz


def organisation(chance):
    """Schlüssel der Organisation: Kunde, sonst Teil des Titels vor dem Doppelpunkt, ohne Rechtsform."""
    text = _name(chance["partner_id"], "") or chance.get("partner_name") or chance["name"].split(":")[0]
    woerter = [w for w in re.findall(r"[a-zäöüé]+", text.lower()) if w not in ORGANISATIONS_WOERTER]
    return " ".join(woerter)


def fakten(stufen, chancen, stichtag):
    gewonnen_ids = {s["id"] for s in stufen if s["is_won"]}
    reihenfolge = {s["name"]: s["sequence"] for s in stufen}
    offen = [c for c in chancen if c["active"] and (c["stage_id"] and c["stage_id"][0] not in gewonnen_ids)]
    gewonnen = [c for c in chancen if c["active"] and c["stage_id"] and c["stage_id"][0] in gewonnen_ids]
    verloren = [c for c in chancen if not c["active"] and c["lost_reason_id"] or (not c["active"] and c["probability"] == 0)]

    def summe(liste, feld="expected_revenue"):
        return round(sum(c[feld] or 0 for c in liste), 2)

    # Überblick nach Stufe und nach Person
    nach_stufe = defaultdict(list)
    nach_person = defaultdict(list)
    for c in offen:
        nach_stufe[_name(c["stage_id"])].append(c)
        nach_person[_name(c["user_id"], "ohne Zuständige")].append(c)

    def zeile(liste):
        return {"anzahl": len(liste), "wert": summe(liste), "gewichtet": summe(liste, "prorated_revenue")}

    stufen_tabelle = [{"stufe": s, **zeile(nach_stufe[s])}
                      for s in sorted(nach_stufe, key=lambda s: reihenfolge.get(s, 99))]
    total_offen = summe(offen)
    personen_tabelle = []
    for p in sorted(nach_person, key=lambda p: -summe(nach_person[p])):
        z = zeile(nach_person[p])
        z["anteil_offen"] = round(z["wert"] / total_offen, 3) if total_offen else 0
        personen_tabelle.append({"person": p, **z})

    # Gewonnen, verloren, Quoten
    gruende = defaultdict(list)
    for c in verloren:
        gruende[_name(c["lost_reason_id"], "ohne Grund")].append(c)
    quote_person = []
    personen = sorted({_name(c["user_id"], "ohne Zuständige") for c in gewonnen + verloren})
    for p in personen:
        g = [c for c in gewonnen if _name(c["user_id"], "ohne Zuständige") == p]
        v = [c for c in verloren if _name(c["user_id"], "ohne Zuständige") == p]
        n, w = len(g) + len(v), summe(g) + summe(v)
        quote_person.append({"person": p, "gewonnen": len(g), "verloren": len(v),
                             "quote_anzahl": round(len(g) / n, 3) if n else None,
                             "quote_wert": round(summe(g) / w, 3) if w else None})
    n_ab = len(gewonnen) + len(verloren)
    w_ab = summe(gewonnen) + summe(verloren)

    woche_ab = stichtag - timedelta(days=WOCHE_TAGE)
    def in_woche(c):
        d = _datum(c["date_closed"])
        return d is not None and woche_ab < d <= stichtag

    # Feste Regeln
    def kurz(c):
        return {"id": c["id"], "chance": c["name"], "stufe": _name(c["stage_id"]),
                "zustaendig": _name(c["user_id"], "ohne Zuständige"), "wert": c["expected_revenue"],
                "gewichtet": c["prorated_revenue"], "kunde": _name(c["partner_id"], "nicht verknüpft")}

    ohne_aktivitaet = []
    ueberfaellige_aktivitaet = []
    abschluss_ueberschritten = []
    for c in offen:
        letzte_stufe = _datum(c["date_last_stage_update"])
        tage_in_stufe = (stichtag - letzte_stufe).days if letzte_stufe else None
        naechste = _datum(c["activity_date_deadline"])
        frist = _datum(c["date_deadline"])
        if naechste is None:
            ohne_aktivitaet.append({**kurz(c), "tage_in_stufe": tage_in_stufe,
                                    "letzte_stufenaenderung": str(letzte_stufe)})
        elif naechste < stichtag:
            ueberfaellige_aktivitaet.append({**kurz(c), "aktivitaet_faellig": str(naechste),
                                             "tage_ueberfaellig": (stichtag - naechste).days})
        if frist and frist < stichtag:
            abschluss_ueberschritten.append({**kurz(c), "erwarteter_abschluss": str(frist),
                                             "tage_ueberschritten": (stichtag - frist).days,
                                             "wahrscheinlichkeit": c["probability"]})

    nach_org = defaultdict(list)
    for c in offen:
        nach_org[organisation(c)].append(c)
    dubletten = []
    for org, liste in nach_org.items():
        if len(liste) < 2 or not org:
            continue
        unverknuepft = any(not c["partner_id"] for c in liste)
        personen_org = {_name(c["user_id"], "") for c in liste}
        if unverknuepft or len(personen_org) > 1:
            grund = []
            if unverknuepft:
                grund.append("eine Chance nicht mit dem Kunden verknüpft")
            if len(personen_org) > 1:
                grund.append("verschiedene Zuständige")
            dubletten.append({"organisation": org, "grund": ", ".join(grund), "chancen": [kurz(c) for c in liste]})

    klumpen = [p for p in personen_tabelle if p["anteil_offen"] > SCHWELLE_KLUMPEN]

    def nach_gewicht(liste):
        return sorted(liste, key=lambda x: -(x.get("gewichtet") or 0))

    return {
        "stichtag": str(stichtag),
        "regelversion": "1.0.0",
        "offen": {"anzahl": len(offen), "wert": total_offen, "gewichtet": summe(offen, "prorated_revenue")},
        "nach_stufe": stufen_tabelle,
        "nach_person": personen_tabelle,
        "groesste_offene": [kurz(c) for c in sorted(offen, key=lambda c: -c["expected_revenue"])[:5]],
        "gewonnen": {"anzahl": len(gewonnen), "wert": summe(gewonnen),
                     "diese_woche": [kurz(c) for c in gewonnen if in_woche(c)]},
        "verloren": {"anzahl": len(verloren), "wert": summe(verloren),
                     "nach_grund": [{"grund": g, "anzahl": len(l), "wert": summe(l)}
                                    for g, l in sorted(gruende.items(), key=lambda x: -summe(x[1]))],
                     "diese_woche": [kurz(c) for c in verloren if in_woche(c)]},
        "gewinnquote": {"abgeschlossen": n_ab,
                        "nach_anzahl": round(len(gewonnen) / n_ab, 3) if n_ab else None,
                        "nach_wert": round(summe(gewonnen) / w_ab, 3) if w_ab else None,
                        "nach_person": quote_person},
        "regeln": {
            "ohne_geplante_aktivitaet": nach_gewicht(ohne_aktivitaet),
            "ueberfaellige_aktivitaet": nach_gewicht(ueberfaellige_aktivitaet),
            "abschluss_ueberschritten": nach_gewicht(abschluss_ueberschritten),
            "moegliche_dubletten": dubletten,
            "klumpenrisiko": klumpen,
        },
        "ohne_kundenverknuepfung": {"anzahl": sum(1 for c in offen if not c["partner_id"]),
                                    "hinweis": "Bei neuen Anfragen normal, der Kunde wird erst beim Qualifizieren verknüpft."},
    }


# ---------- Ausgabe ----------

def chf(x):
    return f"CHF {x:,.2f}".replace(",", "'")


def pct(x):
    return "-" if x is None else f"{x * 100:.0f} %"


def markdown(f):
    z = []
    z.append(f"# Pipeline-Fakten, Stichtag {f['stichtag']} (Regeln {f['regelversion']})\n")
    o = f["offen"]
    z.append(f"Offen: {o['anzahl']} Chancen, {chf(o['wert'])}, gewichtet {chf(o['gewichtet'])}\n")
    z.append("## Nach Stufe\n\n| Stufe | Anzahl | Wert | gewichtet |\n| --- | ---: | ---: | ---: |")
    z += [f"| {s['stufe']} | {s['anzahl']} | {chf(s['wert'])} | {chf(s['gewichtet'])} |" for s in f["nach_stufe"]]
    z.append("\n## Nach Person (offen)\n\n| Person | Anzahl | Wert | gewichtet | Anteil am offenen Wert |\n| --- | ---: | ---: | ---: | ---: |")
    z += [f"| {p['person']} | {p['anzahl']} | {chf(p['wert'])} | {chf(p['gewichtet'])} | {pct(p['anteil_offen'])} |" for p in f["nach_person"]]
    z.append("\n## Grösste offene Chancen\n\n| Chance | Stufe | Zuständig | Wert |\n| --- | --- | --- | ---: |")
    z += [f"| {c['chance']} | {c['stufe']} | {c['zustaendig']} | {chf(c['wert'])} |" for c in f["groesste_offene"]]
    g, v, q = f["gewonnen"], f["verloren"], f["gewinnquote"]
    z.append(f"\n## Abgeschlossen\n\nGewonnen: {g['anzahl']}, {chf(g['wert'])}. Verloren: {v['anzahl']}, {chf(v['wert'])}. "
             f"Gewinnquote {pct(q['nach_anzahl'])} nach Anzahl, {pct(q['nach_wert'])} nach Wert ({q['abgeschlossen']} abgeschlossen).\n")
    z.append("| Verlustgrund | Anzahl | Wert |\n| --- | ---: | ---: |")
    z += [f"| {r['grund']} | {r['anzahl']} | {chf(r['wert'])} |" for r in v["nach_grund"]]
    z.append("\n| Person | gewonnen | verloren | Quote Anzahl | Quote Wert |\n| --- | ---: | ---: | ---: | ---: |")
    z += [f"| {p['person']} | {p['gewonnen']} | {p['verloren']} | {pct(p['quote_anzahl'])} | {pct(p['quote_wert'])} |" for p in q["nach_person"]]
    z.append(f"\nDiese Woche gewonnen: {len(g['diese_woche'])}, verloren: {len(v['diese_woche'])}.")
    for c in g["diese_woche"] + v["diese_woche"]:
        z.append(f"- {c['chance']} ({c['zustaendig']}, {chf(c['wert'])})")

    r = f["regeln"]
    z.append("\n## Befunde nach festen Regeln\n")
    z.append(f"### Ohne geplante Aktivität ({len(r['ohne_geplante_aktivitaet'])})")
    z += [f"- {c['chance']}: {c['stufe']}, {c['zustaendig']}, {chf(c['wert'])}, seit {c['tage_in_stufe']} Tagen in der Stufe (seit {c['letzte_stufenaenderung']})" for c in r["ohne_geplante_aktivitaet"]] or ["- keine"]
    z.append(f"\n### Erwarteter Abschluss überschritten ({len(r['abschluss_ueberschritten'])})")
    z += [f"- {c['chance']}: {c['zustaendig']}, {chf(c['wert'])}, Abschluss {c['erwarteter_abschluss']}, {c['tage_ueberschritten']} {'Tag' if c['tage_ueberschritten'] == 1 else 'Tage'} vorbei, noch {c['wahrscheinlichkeit']:.0f} %" for c in r["abschluss_ueberschritten"]] or ["- keine"]
    z.append(f"\n### Mögliche Dubletten ({len(r['moegliche_dubletten'])})")
    for d in r["moegliche_dubletten"] or []:
        z.append(f"- Organisation «{d['organisation']}» ({d['grund']}):")
        z += [f"  - {c['chance']}: {c['stufe']}, {c['zustaendig']}, {chf(c['wert'])}, Kunde {c['kunde']}" for c in d["chancen"]]
    if not r["moegliche_dubletten"]:
        z.append("- keine")
    z.append(f"\n### Klumpenrisiko (über {SCHWELLE_KLUMPEN * 100:.0f} % des offenen Werts bei einer Person)")
    z += [f"- {p['person']}: {pct(p['anteil_offen'])} des offenen Werts ({chf(p['wert'])})" for p in r["klumpenrisiko"]] or ["- keines"]
    z.append(f"\n### Überfällige Aktivitäten ({len(r['ueberfaellige_aktivitaet'])})")
    z += [f"- {c['chance']}: {c['zustaendig']}, fällig {c['aktivitaet_faellig']}, {c['tage_ueberfaellig']} {'Tag' if c['tage_ueberfaellig'] == 1 else 'Tage'} überfällig" for c in r["ueberfaellige_aktivitaet"]] or ["- keine"]
    k = f["ohne_kundenverknuepfung"]
    z.append(f"\nOhne Kundenverknüpfung: {k['anzahl']} offene Chancen. {k['hinweis']}")
    return "\n".join(z)


def main():
    parser = argparse.ArgumentParser(description="Fakten für den Pipeline-Bericht (nur lesen).")
    parser.add_argument("--stichtag", help="JJJJ-MM-TT, Standard heute")
    parser.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    args = parser.parse_args()
    stichtag = date.fromisoformat(args.stichtag) if args.stichtag else date.today()
    try:
        stufen, chancen = daten_holen(leser_aus_odoo_lesen())
    except Exception as fehler:  # Meldung von odoo-lesen weitergeben, nichts umgehen
        print(f"Fehler beim Lesen aus Odoo: {fehler}", file=sys.stderr)
        return 2
    f = fakten(stufen, chancen, stichtag)
    print(json.dumps(f, indent=2, ensure_ascii=False) if args.json else markdown(f))
    return 0


if __name__ == "__main__":
    sys.exit(main())
