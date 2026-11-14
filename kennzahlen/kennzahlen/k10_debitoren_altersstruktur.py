"""K10 Offene Debitoren mit Altersstruktur per Stichtag (Katalog, K10).

Offener Posten = Zeile auf 1100 minus Verrechnungen (account.partial.reconcile) bis zum Stichtag.
Alter = Stichtag minus Fälligkeitsdatum. Total = Saldo 1100 per Stichtag.
"""

from .basis import GEBUCHT, KONTO_DEBITOREN, datum, ergebnis

NR = "K10"
KENNUNG = "debitoren_altersstruktur"
NAME = "Offene Debitoren mit Altersstruktur"
ART = "stichtag"
EINHEIT = "CHF"
KATALOGVERSION = "1.0"

STUFEN = (("nicht fällig", 0), ("1–30 Tage", 30), ("31–60 Tage", 60), ("61–90 Tage", 90), ("über 90 Tage", None))
NICHT_ZUGEORDNET = "nicht zugeordnet"
RAPPEN = 0.005


def stufe(alter):
    for name, grenze in STUFEN:
        if grenze is None or alter <= grenze:
            return name


def offene_posten(ctx, stichtag):
    """Liste der offenen Posten per Stichtag: Betrag, Fälligkeit, Kunde, Beleg."""
    konto = [k for k in ctx.konten() if k["code"] == str(KONTO_DEBITOREN)]
    zeilen = ctx.odoo.search_read(
        "account.move.line", [GEBUCHT, ("account_id", "in", [k["id"] for k in konto]), ("date", "<=", stichtag)],
        ["balance", "date_maturity", "date", "partner_id", "move_name"])
    ids = [z["id"] for z in zeilen]
    rest = {z["id"]: z["balance"] for z in zeilen}
    if ids:
        verrechnungen = ctx.odoo.search_read(
            "account.partial.reconcile",
            [("max_date", "<=", stichtag), "|", ("debit_move_id", "in", ids), ("credit_move_id", "in", ids)],
            ["debit_move_id", "credit_move_id", "amount"])
        for v in verrechnungen:
            if v["debit_move_id"][0] in rest:
                rest[v["debit_move_id"][0]] -= v["amount"]
            if v["credit_move_id"][0] in rest:
                rest[v["credit_move_id"][0]] += v["amount"]
    posten = []
    for z in zeilen:
        betrag = rest[z["id"]]
        if abs(betrag) < RAPPEN:
            continue
        faellig = z["date_maturity"] or z["date"]
        posten.append({"beleg": z["move_name"], "betrag": betrag, "faellig": faellig,
                       "partner_id": z["partner_id"][0] if z["partner_id"] else None,
                       "partner": z["partner_id"][1] if z["partner_id"] else "ohne Kunde"})
    return posten, konto


def berechne(ctx, stichtag, nach=None):
    tag = datum(stichtag)
    posten, konto = offene_posten(ctx, stichtag)

    # Kunde = Firma (commercial partner)
    firma = {}
    pids = sorted({p["partner_id"] for p in posten if p["partner_id"]})
    if pids:
        for r in ctx.odoo.read("res.partner", pids, ["commercial_partner_id"]):
            firma[r["id"]] = r["commercial_partner_id"][1]

    leer = {name: {"betrag": 0.0, "anzahl": 0} for name, _ in STUFEN}
    leer[NICHT_ZUGEORDNET] = {"betrag": 0.0, "anzahl": 0}
    summen = {k: dict(v) for k, v in leer.items()}
    kunden = {}
    for p in posten:
        name = stufe((tag - datum(p["faellig"])).days) if p["betrag"] > 0 else NICHT_ZUGEORDNET
        summen[name]["betrag"] += p["betrag"]
        summen[name]["anzahl"] += 1
        kunde = firma.get(p["partner_id"], p["partner"])
        eintrag = kunden.setdefault(kunde, {k: dict(v) for k, v in leer.items()})
        eintrag[name]["betrag"] += p["betrag"]
        eintrag[name]["anzahl"] += 1

    total = sum(s["betrag"] for s in summen.values())
    saldo = sum(z["saldo"] for z in ctx.saldo_per(konto, stichtag))
    if abs(total - saldo) > RAPPEN:
        raise RuntimeError(f"Offene Posten ({total:.2f}) weichen vom Saldo 1100 ({saldo:.2f}) ab")

    def zeilen(s, bezug):
        namen = [n for n, _ in STUFEN] + ([NICHT_ZUGEORDNET] if s[NICHT_ZUGEORDNET]["anzahl"] else [])
        return [{"stufe": n, "betrag": s[n]["betrag"], "anzahl": s[n]["anzahl"],
                 "anteil": s[n]["betrag"] / bezug * 100 if bezug > 0 else None} for n in namen]

    zusatz = {"stufen": zeilen(summen, total), "anzahl_posten": len(posten)}
    if nach == "kunde":
        liste = []
        for kunde, s in kunden.items():
            kt = sum(x["betrag"] for x in s.values())
            liste.append({"kunde": kunde, "total": kt, "stufen": zeilen(s, kt)})
        zusatz["kunden"] = sorted(liste, key=lambda k: -k["total"])
    return ergebnis(total, [{"konto": konto[0]["code"], "name": konto[0]["name"], "wert": saldo}], [], **zusatz)
