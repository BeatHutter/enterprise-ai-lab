"""UC-001: Lieferantenrechnung als Entwurf anlegen (Schreibstufe 1, ohne Freigabe).

Manni liest den Beleg selbst und übergibt die Angaben. Dieses Modul prüft sie (Sperre 2)
und legt in Odoo nur einen Entwurf an. Gebucht wird nie, das macht ein Mensch in Odoo.
Plan: werkzeug-server/plan-werkzeug-server.md, Bauschritt W2.
"""

import re
from datetime import date

from pydantic import BaseModel, Field

from odoo import Odoo, OdooFehler

# Keine harte Grenze: Ein Entwurf ist unverbindlich (Entscheid Beat 10.11.2026). Über diesen Schwellen
# wird angelegt, aber mit Warnung am Beleg und in der Antwort. Eine Grenze gehört zum Buchen und Zahlen
WARNSCHWELLE = 50_000.00  # in Belegwährung
WARNFAKTOR = 3  # Total über dem Dreifachen der bisher grössten Rechnung dieses Lieferanten (gleiche Währung)
# Erlaubte Abweichung zwischen Total laut Beleg und Total laut Odoo (Rundung)
TOLERANZ = 0.05
# Erlaubte Aufwandkonten: Material und Dienstleistungen (4xxx), übriger Betriebsaufwand (6xxx)
KONTO_MUSTER = re.compile(r"^[46]\d{3}$")
ODOO_LINK = "http://lab-host:8069/odoo/action-account.action_move_in_invoice_type/{id}"


class Position(BaseModel):
    text: str = Field(description="Positionstext wie auf dem Beleg")
    konto: str = Field(description="Aufwandkonto, vierstellig, z. B. 4000 Material, 4400 Dienstleistungen, 6xxx übriger Aufwand")
    mwst: str = Field(default="", description="Name des Vorsteuer-Codes in Odoo, z. B. «8.1%» (Material/DL) oder «8.1% I OE» "
                                              "(Investitionen/übriger Aufwand). Leer, wenn der Beleg keine MWST enthält")
    betrag_netto: float = Field(description="Betrag der Position ohne MWST, in Belegwährung")


class Ablehnung(Exception):
    """Prüfregel verletzt: Es wird nichts angelegt, der Grund geht an den Aufrufer."""


def _datum(wert: str, feld: str) -> str:
    try:
        return date.fromisoformat(wert).isoformat()
    except (TypeError, ValueError):
        raise Ablehnung(f"{feld} «{wert}» ist kein Datum im Format JJJJ-MM-TT.")


def _pruefen_und_aufloesen(odoo: Odoo, lieferant_id, rechnungsnummer, rechnungsdatum, faelligkeit,
                           waehrung, positionen, total_brutto, bestellung):
    """Alle Prüfregeln vor dem Anlegen. Gibt aufgelöste IDs zurück oder wirft Ablehnung."""
    if not rechnungsnummer.strip():
        raise Ablehnung("Rechnungsnummer des Lieferanten fehlt.")
    rechnungsdatum = _datum(rechnungsdatum, "Rechnungsdatum")
    faelligkeit = _datum(faelligkeit, "Fälligkeit") if faelligkeit else None
    if faelligkeit and faelligkeit < rechnungsdatum:
        raise Ablehnung(f"Fälligkeit {faelligkeit} liegt vor dem Rechnungsdatum {rechnungsdatum}.")
    if not positionen:
        raise Ablehnung("Der Beleg hat keine Positionen.")
    if total_brutto <= 0 or any(p.betrag_netto <= 0 for p in positionen):
        raise Ablehnung("Beträge müssen positiv sein. Gutschriften erfasst dieses Werkzeug nicht.")

    # Regel: Lieferant existiert und ist als Lieferant geführt
    lieferant = odoo.search_read("res.partner", [("id", "=", lieferant_id)], ["name", "supplier_rank", "active"])
    if not lieferant or not lieferant[0]["active"]:
        raise Ablehnung(f"Kein aktiver Kontakt mit der ID {lieferant_id}.")
    if lieferant[0]["supplier_rank"] <= 0:
        raise Ablehnung(f"{lieferant[0]['name']} ist in Odoo nicht als Lieferant geführt.")
    lieferant_name = lieferant[0]["name"]

    # Regel: keine Doppelerfassung (gleiche Nummer beim gleichen Lieferanten, auch als Entwurf)
    doppelt = odoo.search_read("account.move", [("move_type", "=", "in_invoice"), ("partner_id", "=", lieferant_id),
                                                ("ref", "=ilike", rechnungsnummer.strip()), ("state", "!=", "cancel")],
                               ["name", "state"])
    if doppelt:
        d = doppelt[0]
        raise Ablehnung(f"Rechnung {rechnungsnummer} von {lieferant_name} ist schon erfasst "
                        f"({d['name'] or 'Entwurf'}, Status {d['state']}, id {d['id']}). Nichts angelegt.")

    # Regel: Währung aktiv
    waehrungen = odoo.search_read("res.currency", [("name", "=", waehrung.upper())], ["id"])
    if not waehrungen:
        raise Ablehnung(f"Währung {waehrung} ist in Odoo nicht aktiv.")

    # Regel: nur Aufwandkonten aus der erlaubten Liste
    codes = {p.konto.strip() for p in positionen}
    falsch = sorted(c for c in codes if not KONTO_MUSTER.match(c))
    if falsch:
        raise Ablehnung(f"Konto {', '.join(falsch)} ist nicht erlaubt. Erlaubt sind Aufwandkonten 4xxx und 6xxx.")
    konten = {a["code"]: a for a in odoo.search_read("account.account", [("code", "in", sorted(codes))],
                                                     ["code", "account_type"])}
    fehlend = sorted(codes - konten.keys())
    if fehlend:
        raise Ablehnung(f"Konto {', '.join(fehlend)} gibt es im Kontenplan nicht.")
    kein_aufwand = sorted(c for c, a in konten.items() if not a["account_type"].startswith("expense"))
    if kein_aufwand:
        raise Ablehnung(f"Konto {', '.join(kein_aufwand)} ist kein Aufwandkonto.")

    # Regel: nur Vorsteuer-Codes (Einkauf, Prozentsatz unter 100 %)
    namen = {p.mwst.strip() for p in positionen if p.mwst.strip()}
    steuern = {}
    if namen:
        for s in odoo.search_read("account.tax", [("name", "in", sorted(namen)), ("type_tax_use", "=", "purchase"),
                                                  ("amount_type", "=", "percent"), ("amount", "<", 100)],
                                  ["name", "amount"]):
            steuern[s["name"]] = s
    unbekannt = sorted(namen - steuern.keys())
    if unbekannt:
        raise Ablehnung(f"MWST-Code {', '.join(unbekannt)} ist kein erlaubter Vorsteuer-Code in Odoo "
                        "(z. B. «8.1%», «8.1% I OE», «2.6%», «0% EX»).")

    # Bestellung (freiwillig): muss es geben und zum Lieferanten gehören
    if bestellung:
        po = odoo.search_read("purchase.order", [("name", "=", bestellung.strip())], ["partner_id"])
        if not po:
            raise Ablehnung(f"Bestellung {bestellung} gibt es nicht.")
        if po[0]["partner_id"][0] != lieferant_id:
            raise Ablehnung(f"Bestellung {bestellung} gehört zu {po[0]['partner_id'][1]}, nicht zu {lieferant_name}.")

    # Keine Ablehnung, nur Warnungen: aussergewöhnlich hoher Betrag
    warnungen = []
    if total_brutto > WARNSCHWELLE:
        warnungen.append(f"Total {total_brutto:,.2f} {waehrung} liegt über {WARNSCHWELLE:,.0f}.")
    bisher = odoo.search_read("account.move", [("move_type", "=", "in_invoice"), ("partner_id", "=", lieferant_id),
                                               ("state", "=", "posted"), ("currency_id", "=", waehrungen[0]["id"])],
                              ["amount_total"], order="amount_total desc", limit=1)
    if bisher and total_brutto > WARNFAKTOR * bisher[0]["amount_total"]:
        warnungen.append(f"Total ist mehr als {WARNFAKTOR}-mal so hoch wie die bisher grösste Rechnung von "
                         f"{lieferant_name} ({bisher[0]['amount_total']:,.2f} {waehrung}). Lesefehler oder Kommafehler?")
    elif not bisher:
        warnungen.append(f"Erste Rechnung von {lieferant_name} in {waehrung}, kein Vergleich möglich.")

    return {"lieferant_name": lieferant_name, "rechnungsdatum": rechnungsdatum, "faelligkeit": faelligkeit,
            "waehrung_id": waehrungen[0]["id"], "konten": konten, "steuern": steuern, "warnungen": warnungen}


def entwurf_anlegen(odoo: Odoo, aufrufer: str, lieferant_id: int, rechnungsnummer: str, rechnungsdatum: str,
                    waehrung: str, positionen: list[Position], total_brutto: float,
                    faelligkeit: str | None = None, zahlungsreferenz: str | None = None,
                    bestellung: str | None = None) -> str:
    try:
        a = _pruefen_und_aufloesen(odoo, lieferant_id, rechnungsnummer, rechnungsdatum, faelligkeit,
                                   waehrung, positionen, total_brutto, bestellung)
    except Ablehnung as grund:
        return f"ABGELEHNT: {grund}"

    werte = {
        "move_type": "in_invoice",
        "partner_id": lieferant_id,
        "ref": rechnungsnummer.strip(),
        "invoice_date": a["rechnungsdatum"],
        "currency_id": a["waehrung_id"],
        "invoice_line_ids": [(0, 0, {
            "name": p.text,
            "account_id": a["konten"][p.konto.strip()]["id"],
            "tax_ids": [(6, 0, [a["steuern"][p.mwst.strip()]["id"]] if p.mwst.strip() else [])],
            "quantity": 1,
            "price_unit": round(p.betrag_netto, 2),
        }) for p in positionen],
    }
    if a["faelligkeit"]:
        werte["invoice_date_due"] = a["faelligkeit"]
    if zahlungsreferenz:
        werte["payment_reference"] = zahlungsreferenz.strip()
    if bestellung:
        werte["invoice_origin"] = bestellung.strip()

    move_id = odoo.call("account.move", "create", werte, context={"default_move_type": "in_invoice"})
    beleg = odoo.search_read("account.move", [("id", "=", move_id)],
                             ["state", "amount_untaxed", "amount_tax", "amount_total", "invoice_date_due"])[0]

    # Regel: Total laut Odoo muss zum Total laut Beleg passen, sonst Entwurf wieder entfernen
    differenz = round(beleg["amount_total"] - total_brutto, 2)
    if abs(differenz) > TOLERANZ:
        odoo.call("account.move", "unlink", [move_id])
        return (f"ABGELEHNT: Total laut Beleg {total_brutto:,.2f} {waehrung}, aus den Positionen gerechnet "
                f"{beleg['amount_total']:,.2f} (netto {beleg['amount_untaxed']:,.2f} + MWST {beleg['amount_tax']:,.2f}), "
                f"Differenz {differenz:+,.2f}. Rechenfehler auf dem Beleg oder falsche MWST. Nichts angelegt.")

    # Regel: Ergebnis muss ein Entwurf sein
    if beleg["state"] != "draft":
        return (f"FEHLER: Beleg id {move_id} steht im Status {beleg['state']} statt Entwurf. Bitte sofort Beat melden.")

    hinweise = []
    warnungen = a["warnungen"]
    # Notiz als Spur im Beleg. Scheitert sie, bleibt der Entwurf gültig, sonst versuchte der Agent es nochmals
    notiz = f"Entwurf angelegt durch den Werkzeug-Server im Auftrag von {aufrufer}. Bitte prüfen und buchen."
    if warnungen:
        notiz += " WARNUNG: " + " ".join(warnungen) + " Vor dem Buchen besonders prüfen."
    try:
        odoo.call("account.move", "message_post", [move_id], body=notiz, subtype_xmlid="mail.mt_note")
    except OdooFehler as fehler:
        hinweise.append(f"Notiz am Beleg nicht möglich ({fehler}).")

    if not a["faelligkeit"]:
        hinweise.append(f"Keine Fälligkeit übergeben, Odoo setzt {beleg['invoice_date_due']}. Bitte prüfen.")
    if not zahlungsreferenz:
        hinweise.append("Keine Zahlungsreferenz übergeben.")
    if differenz:
        hinweise.append(f"Rundungsdifferenz {differenz:+.2f} zum Total laut Beleg.")
    return (f"ENTWURF ANGELEGT: Lieferantenrechnung {rechnungsnummer} von {a['lieferant_name']}, "
            f"Total {beleg['amount_total']:,.2f} {waehrung} (netto {beleg['amount_untaxed']:,.2f}, MWST {beleg['amount_tax']:,.2f}), "
            f"id {move_id}, Status Entwurf. Gebucht wird in Odoo durch einen Menschen. Link: {ODOO_LINK.format(id=move_id)}"
            + ("\nWARNUNG (steht auch als Notiz am Beleg): " + " ".join(warnungen) if warnungen else "")
            + ("\nHinweise: " + " ".join(hinweise) if hinweise else ""))
