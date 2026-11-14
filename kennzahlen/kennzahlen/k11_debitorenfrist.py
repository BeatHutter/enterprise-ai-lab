"""K11 Debitorenfrist (DSO) (Katalog, K11).

Durchschnittlicher Debitorenbestand ÷ Kundenumsatz inkl. MWST × Tage im Zeitraum.
Bestände: Vortag des Beginns, jedes Monatsende im Zeitraum, dazu der letzte Tag,
wenn der Zeitraum nicht an einem Monatsende endet.
"""

import datetime as dt

from .basis import KONTO_DEBITOREN, datum, ergebnis, monatsende

NR = "K11"
KENNUNG = "debitorenfrist"
NAME = "Debitorenfrist (DSO)"
ART = "zeitraum"
EINHEIT = "Tage"
KATALOGVERSION = "1.0"
ZAHLUNGSFRIST_TAGE = 30  # vereinbart: 30 Tage netto


def stichtage(von, bis):
    tage = [von - dt.timedelta(days=1)]
    tag = monatsende(von)
    while tag <= bis:
        tage.append(tag)
        tag = monatsende(tag + dt.timedelta(days=1))
    if tage[-1] != bis:
        tage.append(bis)
    return tage


def berechne(ctx, von, bis):
    beginn, ende = datum(von), datum(bis)
    konto = [k for k in ctx.konten() if k["code"] == str(KONTO_DEBITOREN)]
    bestaende = [{"datum": t.isoformat(),
                  "betrag": sum(z["saldo"] for z in ctx.saldo_per(konto, t.isoformat()))}
                 for t in stichtage(beginn, ende)]
    durchschnitt = sum(b["betrag"] for b in bestaende) / len(bestaende)

    gruppen = ctx.odoo.read_group(
        "account.move", [("state", "=", "posted"), ("move_type", "in", ["out_invoice", "out_refund"]),
                         ("date", ">=", von), ("date", "<=", bis)],
        ["amount_total_signed:sum"], ["move_type"])
    umsatz = sum(g["amount_total_signed"] for g in gruppen)
    anzahl_tage = (ende - beginn).days + 1

    hinweise = []
    if umsatz <= 0:
        wert = None
        hinweise.append("nicht berechenbar: der Kundenumsatz inkl. MWST ist null oder negativ")
    else:
        wert = durchschnitt / umsatz * anzahl_tage
    return ergebnis(wert, [
        {"name": "durchschnittlicher Debitorenbestand", "wert": durchschnitt},
        {"name": "Kundenumsatz inkl. MWST", "wert": umsatz},
    ], hinweise, bestaende=bestaende, tage_im_zeitraum=anzahl_tage, zahlungsfrist_tage=ZAHLUNGSFRIST_TAGE)
