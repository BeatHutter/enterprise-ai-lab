"""UC-005: Offerte (Angebot) als Entwurf anlegen (Schreibstufe 1, ohne Freigabe).

Manni liest die Anfrage und übergibt Kunde, Artikel und Mengen. Preise und Rabatte setzt Odoo
aus der Preisliste des Kunden. Es gibt bewusst keinen Parameter für Preis oder Rabatt (OE3).
Versenden und Bestätigen bleiben beim Menschen (Stufe 3).
Plan: werkzeug-server/plan-werkzeug-server.md, Etappe UC-005.
"""

from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from odoo import Odoo, OdooFehler

WARN_TOTAL = 100_000.00  # CHF netto
WARN_FAKTOR_MENGE = 5  # Menge über dem Fünffachen der bisher grössten Menge des Artikels
DOPPEL_TAGE = 14  # offene Angebote desselben Kunden mit denselben Artikeln
ODOO_LINK = "http://lab-host:8069/odoo/action-sale.action_quotations_with_onboarding/{id}"
STUECK_EINHEITEN = {"Einheit(en)", "Units", "Stk"}


class OffertPosition(BaseModel):
    artikel: str = Field(description="Artikelcode aus Odoo, z. B. BA-100, VE-010, DL-030")
    menge: float = Field(description="Menge in der Einheit des Artikels (Stück, Stunden oder Meter)")


class Ablehnung(Exception):
    pass


def _pruefen(odoo: Odoo, kunde_id: int, positionen: list[OffertPosition]):
    if not positionen:
        raise Ablehnung("Die Offerte hat keine Positionen.")

    kunde = odoo.search_read("res.partner", [("id", "=", kunde_id)], ["name", "customer_rank", "active"])
    if not kunde or not kunde[0]["active"]:
        raise Ablehnung(f"Kein aktiver Kontakt mit der ID {kunde_id}.")
    if kunde[0]["customer_rank"] <= 0:
        raise Ablehnung(f"{kunde[0]['name']} ist in Odoo nicht als Kunde geführt. Neukunden legt dieses Werkzeug "
                        "nicht an (UC-013). Bitte Beat melden.")

    codes = sorted({p.artikel.strip().upper() for p in positionen})
    artikel = {a["default_code"]: a for a in odoo.search_read(
        "product.product", [("default_code", "in", codes), ("sale_ok", "=", True)],
        ["default_code", "name", "uom_id", "list_price"])}
    unbekannt = [c for c in codes if c not in artikel]
    if unbekannt:
        gueltig = [a["default_code"] for a in odoo.search_read("product.product", [("sale_ok", "=", True)],
                                                                ["default_code"], order="default_code")]
        raise Ablehnung(f"Artikel {', '.join(unbekannt)} gibt es nicht oder er ist nicht verkäuflich. "
                        f"Gültige Codes: {', '.join(gueltig)}.")

    for p in positionen:
        a = artikel[p.artikel.strip().upper()]
        if p.menge <= 0:
            raise Ablehnung(f"Menge für {a['default_code']} muss grösser als 0 sein.")
        if a["uom_id"][1] in STUECK_EINHEITEN and p.menge != int(p.menge):
            raise Ablehnung(f"{a['default_code']} wird in ganzen Stück verkauft, nicht {p.menge}.")

    return kunde[0]["name"], artikel


def _warnungen(odoo: Odoo, kunde_id: int, kunde_name: str, positionen, artikel, order_id: int) -> list[str]:
    warnungen = []
    seit = (datetime.now() - timedelta(days=DOPPEL_TAGE)).strftime("%Y-%m-%d %H:%M:%S")
    ids = [artikel[p.artikel.strip().upper()]["id"] for p in positionen]
    offen = odoo.search_read("sale.order", [("partner_id", "=", kunde_id), ("state", "in", ["draft", "sent"]),
                                            ("date_order", ">=", seit), ("id", "!=", order_id),
                                            ("order_line.product_id", "in", ids)], ["name"])
    if offen:
        warnungen.append(f"{kunde_name} hat in den letzten {DOPPEL_TAGE} Tagen schon offene Angebote mit denselben "
                         f"Artikeln: {', '.join(o['name'] for o in offen)}. Möglicherweise doppelt.")
    for p in positionen:
        a = artikel[p.artikel.strip().upper()]
        bisher = odoo.search_read("sale.order.line", [("product_id", "=", a["id"]), ("state", "=", "sale")],
                                  ["product_uom_qty"], order="product_uom_qty desc", limit=1)
        if bisher and p.menge > WARN_FAKTOR_MENGE * bisher[0]["product_uom_qty"]:
            warnungen.append(f"Menge {p.menge:g} für {a['default_code']} ist mehr als {WARN_FAKTOR_MENGE}-mal so hoch "
                             f"wie die bisher grösste Bestellmenge ({bisher[0]['product_uom_qty']:g}). Lesefehler?")
    return warnungen


def angebot_anlegen(odoo: Odoo, aufrufer: str, kunde_id: int, positionen: list[OffertPosition],
                    kundenreferenz: str | None = None, hinweis: str | None = None) -> str:
    try:
        kunde_name, artikel = _pruefen(odoo, kunde_id, positionen)
    except Ablehnung as grund:
        return f"ABGELEHNT: {grund}"

    werte = {
        "partner_id": kunde_id,
        "order_line": [(0, 0, {"product_id": artikel[p.artikel.strip().upper()]["id"], "product_uom_qty": p.menge})
                       for p in positionen],
    }
    if kundenreferenz:
        werte["client_order_ref"] = kundenreferenz.strip()
    order_id = odoo.call("sale.order", "create", werte)
    order = odoo.search_read("sale.order", [("id", "=", order_id)],
                             ["name", "state", "amount_untaxed", "amount_total", "pricelist_id", "validity_date",
                              "user_id"])[0]
    if order["state"] != "draft":
        return f"FEHLER: Angebot {order['name']} steht im Status {order['state']} statt Entwurf. Bitte sofort Beat melden."

    zeilen = odoo.search_read("sale.order.line", [("order_id", "=", order_id), ("display_type", "=", False)],
                              ["product_id", "product_uom_qty", "price_unit", "discount", "price_subtotal"], order="id")
    warnungen = _warnungen(odoo, kunde_id, kunde_name, positionen, artikel, order_id)
    if order["amount_untaxed"] > WARN_TOTAL:
        warnungen.append(f"Total netto {order['amount_untaxed']:,.2f} liegt über {WARN_TOTAL:,.0f}.")

    hinweise = []
    notiz = f"Angebot als Entwurf angelegt durch den Werkzeug-Server im Auftrag von {aufrufer}. Bitte prüfen und versenden."
    if hinweis:
        notiz += f" Hinweis zur Anfrage: {hinweis.strip()}"
    if warnungen:
        notiz += " WARNUNG: " + " ".join(warnungen)
    try:
        # Interne Notiz (mt_note): geht an niemanden hinaus, auch nicht an den Kunden als Follower
        odoo.call("sale.order", "message_post", [order_id], body=notiz, subtype_xmlid="mail.mt_note")
    except OdooFehler as fehler:
        hinweise.append(f"Notiz am Angebot nicht möglich ({fehler}).")

    positionen_text = "; ".join(
        f"{z['product_id'][1]}: {z['product_uom_qty']:g} × {z['price_unit']:,.2f}"
        + (f" − {z['discount']:g} %" if z["discount"] else "") + f" = {z['price_subtotal']:,.2f}" for z in zeilen)
    return (f"ANGEBOT ALS ENTWURF ANGELEGT: {order['name']} für {kunde_name}, Preisliste {order['pricelist_id'][1]}, "
            f"Total netto {order['amount_untaxed']:,.2f} CHF, inkl. MWST {order['amount_total']:,.2f} CHF, "
            f"gültig bis {order['validity_date']}, Verkäufer {order['user_id'][1]}. Positionen: {positionen_text}. "
            f"Versendet und bestätigt wird durch einen Menschen. Link: {ODOO_LINK.format(id=order_id)}"
            + ("\nWARNUNG (steht auch als Notiz am Angebot): " + " ".join(warnungen) if warnungen else "")
            + ("\nHinweise: " + " ".join(hinweise) if hinweise else ""))
