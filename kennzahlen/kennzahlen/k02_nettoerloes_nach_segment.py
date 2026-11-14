"""K2 Nettoerlös nach Kundensegment.

Gleiche Konten wie K1, aufgeteilt nach der Branche (res.partner.industry) der Firma
des Kunden. Ohne Kunde oder ohne Branche: «ohne Segment». Summe = K1 (Katalog, K2).
"""

from .basis import GEBUCHT, ergebnis

NR = "K2"
KENNUNG = "nettoerloes_nach_segment"
NAME = "Nettoerlös nach Kundensegment"
ART = "zeitraum"
EINHEIT = "CHF"
KATALOGVERSION = "1.0"
OHNE_SEGMENT = "ohne Segment"


def berechne(ctx, von, bis):
    konten = ctx.kontenbereich(3000, 3899, ohne=(3806,))
    domain = [GEBUCHT, ("account_id", "in", [k["id"] for k in konten]),
              ("date", ">=", von), ("date", "<=", bis)]
    gruppen = ctx.odoo.read_group("account.move.line", domain, ["balance:sum"], ["partner_id"])

    partner_ids = [g["partner_id"][0] for g in gruppen if g["partner_id"]]
    firma_von = {}
    if partner_ids:
        for p in ctx.odoo.read("res.partner", partner_ids, ["commercial_partner_id"]):
            firma_von[p["id"]] = p["commercial_partner_id"][0]
    branche_von = {}
    firmen = sorted(set(firma_von.values()))
    if firmen:
        for f in ctx.odoo.read("res.partner", firmen, ["industry_id"]):
            branche_von[f["id"]] = f["industry_id"][1] if f["industry_id"] else OHNE_SEGMENT

    summen = {}
    for g in gruppen:
        segment = OHNE_SEGMENT
        if g["partner_id"]:
            segment = branche_von.get(firma_von.get(g["partner_id"][0]), OHNE_SEGMENT)
        summen[segment] = summen.get(segment, 0.0) - g["balance"]  # Ertrag positiv

    total = sum(summen.values())
    nettoerloes = ctx.kennzahl("nettoerloes", von, bis)["wert"]
    if abs(total - nettoerloes) > 0.005:
        raise RuntimeError(f"Summe der Segmente ({total:.2f}) weicht vom Nettoerlös ({nettoerloes:.2f}) ab")

    reihenfolge = sorted((s for s in summen if s != OHNE_SEGMENT), key=lambda s: -summen[s])
    if OHNE_SEGMENT in summen:
        reihenfolge.append(OHNE_SEGMENT)
    segmente = [{"segment": s, "wert": summen[s],
                 "anteil": summen[s] / total * 100 if total > 0 else None} for s in reihenfolge]
    return ergebnis(total, [{"kennung": "nettoerloes", "name": "Nettoerlös", "wert": nettoerloes}],
                    segmente=segmente)
