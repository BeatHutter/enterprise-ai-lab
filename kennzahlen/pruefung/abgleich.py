#!/usr/bin/env python3
"""Abgleich der Kennzahlen-Bibliothek gegen Odoo-Berichte. Nur für operator, wird nicht eingespielt.

Vergleicht jede Kennzahl mit einem Bericht, den Odoo selbst rechnet:
- Erfolgsrechnung: MIS-Vorlage «Profit & Loss» pro Konto (OCA mis_builder, compute()).
- Debitorenbestände: MIS-Vorlage «Balance Sheet», Konto 1100 pro Stichtag.
- Segmente und Kundenumsatz inkl. MWST: Rechnungsanalyse (account.invoice.report).
- Altersstruktur: Gegenrechnung pro Rechnung aus Odoos Zahlungsangaben (invoice_payments_widget),
  per heute zusätzlich aus amount_residual.

Schreibt nur vorübergehende MIS-Berichte (temporary=True) und löscht sie am Ende wieder.
Benutzt den Odoo-Zugang des Datengenerators (Admin). Aufruf: python3 -B kennzahlen/pruefung/abgleich.py
"""

import datetime as dt
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "data-generator"))
sys.path.insert(0, str(REPO / "kennzahlen"))
sys.dont_write_bytecode = True

from config import load_config  # noqa: E402
from odoo_client import OdooClient  # noqa: E402

os.environ.update({k: v for k, v in load_config().items() if k.startswith("ODOO_")})

from kennzahlen.basis import Kontext, monatsende  # noqa: E402
from kennzahlen.k10_debitoren_altersstruktur import stufe  # noqa: E402
from kennzahlen.k11_debitorenfrist import stichtage  # noqa: E402
from kennzahlen.register import MODULE  # noqa: E402

ZEITRAEUME = [("Jan–Okt 2026", "2026-01-01", "2026-10-31"), ("2025", "2025-01-01", "2025-12-31")]
STICHTAGE = ["2026-10-31", "2025-10-31", "2025-12-31"]
RAPPEN = 0.005

admin = OdooClient()
admin.login()
ctx = Kontext()
zeilen = []          # Ergebnisse für die Tabelle
angelegt = []        # vorübergehende MIS-Berichte


def melde(was, zeitraum, bibliothek, odoo, quelle, einheit="CHF"):
    diff = None if bibliothek is None or odoo is None else bibliothek - odoo
    toleranz = RAPPEN if einheit == "CHF" else 0.05
    ok = diff is not None and abs(diff) <= toleranz
    zeilen.append((was, zeitraum, bibliothek, odoo, diff, ok, quelle, einheit))


def mis_instanz(report_name, perioden):
    """Legt einen vorübergehenden MIS-Bericht an, rechnet ihn und gibt {Spalte: {Kontonummer: Wert, Abschnitt}} zurück."""
    report_id = admin.search_read("mis.report", [("name", "=", report_name)], ["id"])[0]["id"]
    werte = {
        "name": f"Abgleich Kennzahlen (vorübergehend) {dt.datetime.now():%Y-%m-%d %H:%M}",
        "report_id": report_id, "temporary": True, "target_move": "posted", "comparison_mode": True,
        "period_ids": [(0, 0, {"name": name, "mode": "fix", "source": "actuals", "sequence": i,
                               "manual_date_from": von, "manual_date_to": bis})
                       for i, (name, von, bis) in enumerate(perioden)],
    }
    inst = admin.call("mis.report.instance", "create", [werte])
    inst = inst[0] if isinstance(inst, list) else inst
    angelegt.append(inst)
    matrix = admin.call("mis.report.instance", "compute", [inst])
    spalten = [c["label"] for c in matrix["header"][0]["cols"]]
    ergebnis = {s: {} for s in spalten}
    abschnitt = None
    for row in matrix["body"]:
        label = row["label"] or ""
        nummer = label.split(" ", 1)[0]
        if not nummer.isdigit():
            abschnitt = label
            continue
        for s, cell in zip(spalten, row["cells"]):
            ergebnis[s][nummer] = (cell.get("val") or 0.0, abschnitt)
    return ergebnis


def balance_aus_pl(werte, nummer):
    """MIS P&L: Abschnitt «Profit» = −balance (Ertrag), «Loss» = balance (Aufwand)."""
    if nummer not in werte:
        return 0.0
    val, abschnitt = werte[nummer]
    return -val if abschnitt == "Profit" else val


def summe(werte, von, bis, ohne=(), nur=None):
    nummern = [n for n in werte if (nur and int(n) in nur) or (not nur and von <= int(n) <= bis and int(n) not in ohne)]
    return sum(balance_aus_pl(werte, n) for n in nummern)


def kz(kennung, *args):
    return ctx.kennzahl(kennung, *args)["wert"]


def erfolgsrechnung():
    mis = mis_instanz("Profit & Loss", ZEITRAEUME)
    for name, von, bis in ZEITRAEUME:
        w = mis[name]
        quelle = "MIS «Profit & Loss», Einzelkonten"
        erloes = -summe(w, 3000, 3899, ohne=(3806,))
        material = summe(w, 4000, 4999, ohne=(4906,))
        bestand = -summe(w, 3900, 3999)
        kurs = -summe(w, 0, 0, nur=(3806, 4906))
        personal = summe(w, 5000, 5999, ohne=(5790,))
        uebriger = summe(w, 6000, 6799)
        abschr = summe(w, 6800, 6899)
        brutto = erloes + bestand - material
        ebitda = -summe(w, 3000, 6799, ohne=(5790,))
        ebit = -summe(w, 3000, 6899, ohne=(5790,))
        for kennung, wert in [("nettoerloes", erloes), ("materialaufwand", material),
                              ("bestandesaenderungen", bestand), ("kursdifferenzen", kurs),
                              ("personalaufwand", personal), ("uebriger_betrieblicher_aufwand", uebriger),
                              ("abschreibungen", abschr), ("bruttogewinn", brutto), ("ebitda", ebitda),
                              ("ebit", ebit)]:
            melde(kennung, name, kz(kennung, von, bis), wert, quelle)
        melde("materialquote", name, kz("materialquote", von, bis), material / erloes * 100, quelle, "%")
        melde("bruttogewinnmarge", name, kz("bruttogewinnmarge", von, bis), brutto / erloes * 100, quelle, "%")
        # Kontrolle: jedes Konto der MIS-Vorlage einzeln gegen die Salden der Bibliothek
        konten = [k for k in ctx.konten() if k["code"] in w]
        bib = {z["konto"]: z["saldo"] for z in ctx.salden(konten, von, bis)}
        for nummer in sorted(w):
            melde(f"Konto {nummer}", name, bib.get(nummer, 0.0), balance_aus_pl(w, nummer),
                  "MIS «Profit & Loss», Konto (Saldo Soll minus Haben)")


def segmente():
    for name, von, bis in ZEITRAEUME:
        gruppen = admin.call("account.invoice.report", "read_group",
                             [("state", "=", "posted"), ("move_type", "in", ["out_invoice", "out_refund"]),
                              ("invoice_date", ">=", von), ("invoice_date", "<=", bis)],
                             ["price_subtotal:sum"], ["commercial_partner_id"], lazy=False)
        ids = [g["commercial_partner_id"][0] for g in gruppen if g["commercial_partner_id"]]
        branche = {p["id"]: (p["industry_id"][1] if p["industry_id"] else "ohne Segment")
                   for p in admin.call("res.partner", "read", ids, fields=["industry_id"])}
        odoo = {}
        for g in gruppen:
            seg = branche.get(g["commercial_partner_id"][0], "ohne Segment") if g["commercial_partner_id"] else "ohne Segment"
            odoo[seg] = odoo.get(seg, 0.0) + g["price_subtotal"]
        bib = {s["segment"]: s["wert"] for s in ctx.kennzahl("nettoerloes_nach_segment", von, bis)["segmente"]}
        for seg in sorted(set(odoo) | set(bib)):
            melde(f"nettoerloes_nach_segment: {seg}", name, bib.get(seg, 0.0), odoo.get(seg, 0.0),
                  "Rechnungsanalyse, ohne MWST")


def debitoren():
    perioden = [(t, f"{t[:4]}-01-01", t) for t in STICHTAGE]
    dso_tage = sorted({d.isoformat() for _, von, bis in ZEITRAEUME
                       for d in stichtage(dt.date.fromisoformat(von), dt.date.fromisoformat(bis))})
    perioden += [(f"DSO {t}", f"{t[:4]}-01-01", t) for t in dso_tage]
    mis = mis_instanz("Balance Sheet", perioden)

    for t in STICHTAGE:
        ergebnis = ctx.kennzahl("debitoren_altersstruktur", t, None)
        melde("debitoren_altersstruktur: Total", t, ergebnis["wert"], mis[t]["1100"][0], "MIS «Balance Sheet», Konto 1100")
        # Gegenrechnung pro Rechnung: Betrag minus Zahlungen bis Stichtag laut Odoo
        rechnungen = admin.search_read("account.move", [("state", "=", "posted"),
                                                         ("move_type", "in", ["out_invoice", "out_refund"]),
                                                         ("date", "<=", t)],
                                       ["amount_total_signed", "invoice_date_due", "invoice_payments_widget"])
        odoo = {}
        for r in rechnungen:
            bezahlt = sum(p["amount"] for p in ((r["invoice_payments_widget"] or {}).get("content") or [])
                          if p["date"] <= t)
            offen = r["amount_total_signed"] - bezahlt
            if abs(offen) < RAPPEN:
                continue
            s = stufe((dt.date.fromisoformat(t) - dt.date.fromisoformat(r["invoice_date_due"])).days)
            odoo[s] = odoo.get(s, 0.0) + offen
        for s in ergebnis["stufen"]:
            melde(f"debitoren_altersstruktur: {s['stufe']}", t, s["betrag"], odoo.get(s["stufe"], 0.0),
                  "Rechnungen minus Zahlungen bis Stichtag (Odoo)")

    # Per heute (keine Buchungen nach dem 31.10.2026): Odoos eigener Restbetrag
    offen = admin.search_read("account.move.line", [("parent_state", "=", "posted"), ("account_id.code", "=", "1100"),
                                                    ("reconciled", "=", False)], ["amount_residual"])
    melde("debitoren_altersstruktur: Total", "2026-10-31", ctx.kennzahl("debitoren_altersstruktur", "2026-10-31", None)["wert"],
          sum(o["amount_residual"] for o in offen), "Odoo amount_residual (Stand heute)")

    for name, von, bis in ZEITRAEUME:
        tage = stichtage(dt.date.fromisoformat(von), dt.date.fromisoformat(bis))
        bestaende = []
        for d in tage:
            spalte = f"DSO {d.isoformat()}"
            bestaende.append(mis[spalte].get("1100", (0.0, None))[0])
        gruppen = admin.call("account.invoice.report", "read_group",
                             [("state", "=", "posted"), ("move_type", "in", ["out_invoice", "out_refund"]),
                              ("invoice_date", ">=", von), ("invoice_date", "<=", bis)],
                             ["price_total:sum"], ["move_type"], lazy=False)
        umsatz = sum(g["price_total"] for g in gruppen)
        anzahl = (dt.date.fromisoformat(bis) - dt.date.fromisoformat(von)).days + 1
        dso = sum(bestaende) / len(bestaende) / umsatz * anzahl
        roh = ctx.kennzahl("debitorenfrist", von, bis)
        melde("debitorenfrist: Kundenumsatz inkl. MWST", name, roh["bestandteile"][1]["wert"], umsatz,
              "Rechnungsanalyse, inkl. MWST")
        melde("debitorenfrist: Ø Bestand", name, roh["bestandteile"][0]["wert"], sum(bestaende) / len(bestaende),
              "MIS «Balance Sheet», 1100 pro Monatsende")
        melde("debitorenfrist", name, roh["wert"], dso, "aus den Odoo-Werten gerechnet", "Tage")


def main():
    try:
        erfolgsrechnung()
        segmente()
        debitoren()
    finally:
        if angelegt:
            admin.call("mis.report.instance", "unlink", angelegt)
            rest = admin.search_count("mis.report.instance", [("id", "in", angelegt)])
            print(f"Vorübergehende MIS-Berichte gelöscht: {len(angelegt)}, übrig: {rest}")
    print()
    print("| Kennzahl | Zeitraum / Stichtag | Bibliothek | Odoo | Differenz | ok | Odoo-Quelle |")
    print("| --- | --- | ---: | ---: | ---: | --- | --- |")
    for was, zeit, bib, odoo, diff, ok, quelle, einheit in zeilen:
        f = (lambda x: f"{x:,.2f}".replace(",", "'")) if einheit == "CHF" else (lambda x: f"{x:.2f}")
        print(f"| {was} | {zeit} | {f(bib)} | {f(odoo)} | {f(diff)} | {'ja' if ok else '**nein**'} | {quelle} |")
    fehler = sum(1 for z in zeilen if not z[5])
    print(f"\n{len(zeilen)} Vergleiche, {fehler} Abweichungen.")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
