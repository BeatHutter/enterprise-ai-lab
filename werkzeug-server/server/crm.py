"""UC-029 (CRM K4) und UC-013: Werkzeuge für den Akquiseprozess Neukunde und die Kundenanlage.

1. verkaufschance_anlegen (Stufe 1): Legt eine Verkaufschance (crm.lead) in der Stufe «Neu» an.
2. notiz_an_chance (Stufe 1): Hängt eine interne Notiz unter dem Namen «Manni (KI-Assistent)»
   an eine bestehende Verkaufschance.
3. aktivitaet_planen (Stufe 1): Plant eine Aufgabe für den Verkauf an einer Verkaufschance.
4. kunde_anlegen (Stufe 2, mit Freigabe per Knopf): Legt nach menschlicher Freigabe einen Neukunden
   (res.partner) an und setzt eine optional verknüpfte Verkaufschance gleich auf «Qualifiziert».

Plan: crm/plan-crm.md (Bauschritt K4) und docs/use-cases.md (UC-013, UC-029).
"""

import html
import re
from datetime import date

from odoo import Odoo, OdooFehler

TEAM_ID = 1  # Verkaufsteam «Verkauf»
STUFE_NEU = "Neu"
STUFE_QUALIFIZIERT = "Qualifiziert"
WAHRSCHEINLICHKEIT_NEU = 10
WAHRSCHEINLICHKEIT_QUALIFIZIERT = 30
WARN_SCHAETZWERT = 100_000.00  # CHF netto
MANNI_LOGIN = "hermes@muster-ag.local"
ODOO_CRM_LINK = "http://lab-host:8069/odoo/crm/{id}"
ODOO_KUNDE_LINK = "http://lab-host:8069/odoo/customers/{id}"

PREISLISTEN_ZUORDNUNG = {
    "standard": "Standard",
    "wiederverkäufer": "Wiederverkäufer 10 %",
    "wiederverkaeufer": "Wiederverkäufer 10 %",
    "wiederverkäufer 10 %": "Wiederverkäufer 10 %",
    "wiederverkaeufer 10 %": "Wiederverkäufer 10 %",
}

FREEMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "gmx.net", "gmx.de",
    "bluewin.ch", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "proton.me", "protonmail.ch",
}

VERKAUF_ZUORDNUNG = {
    "lea": "lea.brunner@muster-ag.local",
    "lea brunner": "lea.brunner@muster-ag.local",
    "lea.brunner@muster-ag.local": "lea.brunner@muster-ag.local",
    "marco": "marco.steiner@muster-ag.local",
    "marco steiner": "marco.steiner@muster-ag.local",
    "marco.steiner@muster-ag.local": "marco.steiner@muster-ag.local",
    "reto": "reto.kaelin@muster-ag.local",
    "reto kälin": "reto.kaelin@muster-ag.local",
    "reto kaelin": "reto.kaelin@muster-ag.local",
    "reto.kaelin@muster-ag.local": "reto.kaelin@muster-ag.local",
}

AKTIVITAET_ARTEN = {
    "call": ("mail.mail_activity_data_call", "Anruf"),
    "anruf": ("mail.mail_activity_data_call", "Anruf"),
    "email": ("mail.mail_activity_data_email", "E-Mail"),
    "e-mail": ("mail.mail_activity_data_email", "E-Mail"),
    "mail": ("mail.mail_activity_data_email", "E-Mail"),
    "todo": ("mail.mail_activity_data_todo", "Aufgabe"),
    "aufgabe": ("mail.mail_activity_data_todo", "Aufgabe"),
    "meeting": ("mail.mail_activity_data_meeting", "Sitzung"),
    "sitzung": ("mail.mail_activity_data_meeting", "Sitzung"),
    "termin": ("mail.mail_activity_data_meeting", "Sitzung"),
}


class Ablehnung(Exception):
    pass


def manni_autor_id(odoo: Odoo) -> int | None:
    """Gibt die res.partner-ID von «Manni (KI-Assistent)» zurück, damit Notizen unter seinem Namen erscheinen."""
    treffer = odoo.search_read("res.users", [("login", "=", MANNI_LOGIN)], ["partner_id"])
    if treffer and treffer[0].get("partner_id"):
        return treffer[0]["partner_id"][0]
    return None


def _text_zu_html(text: str) -> str:
    """Wandelt einfachen Text mit Absätzen in sicheres HTML für den Odoo-Chatter um."""
    bloecke = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    if not bloecke:
        return "<p></p>"
    teile = []
    for block in bloecke:
        escaped = html.escape(block).replace("\n", "<br/>")
        teile.append(f"<p>{escaped}</p>")
    return "".join(teile)


def _verkaufsperson_aufloesen(odoo: Odoo, angabe: str) -> tuple[int, str]:
    login = VERKAUF_ZUORDNUNG.get(angabe.strip().lower())
    if not login:
        raise Ablehnung(
            f"Unbekannte Verkaufsperson «{angabe}». Erlaubt: Lea Brunner, Marco Steiner, Reto Kälin."
        )
    nutzer = odoo.search_read("res.users", [("login", "=", login)], ["id", "name"])
    if not nutzer:
        raise Ablehnung(f"Verkaufsperson «{angabe}» ({login}) ist in Odoo nicht eingerichtet.")
    return nutzer[0]["id"], nutzer[0]["name"]


def _zuteilung_ableiten(firma: str | None, titel: str, merkmale: list[str] | None) -> str:
    """Leitet die zuständige Verkaufsperson nach der Zuteilungsregel der Muster AG ab."""
    text = f"{firma or ''} {titel} {' '.join(merkmale or [])}"
    if re.search(r"schul|hotel|kurhaus|genossenschaft", text, re.I):
        return "Marco Steiner"
    if re.search(r"gemeinde|stadt|bergbahn|sesselbahn|ausschreibung", text, re.I):
        return "Reto Kälin"
    return "Lea Brunner"


def _datum_pruefen(wert: str, feldname: str) -> date:
    try:
        return date.fromisoformat(wert.strip())
    except ValueError:
        raise Ablehnung(f"{feldname} «{wert}» ist kein gültiges Datum im Format JJJJ-MM-TT.")


def _domain_aus_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    dom = email.strip().rsplit("@", 1)[-1].lower().strip("> ")
    if not dom or dom in FREEMAIL_DOMAINS or dom.startswith("gmx."):
        return None
    return dom


def _aktive_chance_laden(odoo: Odoo, chance_id: int) -> dict:
    chancen = odoo.search_read(
        "crm.lead",
        [("id", "=", chance_id), ("type", "=", "opportunity")],
        ["id", "name", "stage_id", "user_id", "partner_id", "partner_name", "active"],
        context={"active_test": False},
    )
    if not chancen:
        raise Ablehnung(f"Keine Verkaufschance mit der ID {chance_id} gefunden.")
    chance = chancen[0]
    if not chance["active"]:
        raise Ablehnung(
            f"Verkaufschance ID {chance_id} («{chance['name']}») ist archiviert/verloren und kann nicht geändert werden."
        )
    return chance


def _dubletten_und_warnungen(
    odoo: Odoo,
    firma: str | None,
    email: str | None,
    geschaetzter_wert: float,
    neue_id: int,
) -> list[str]:
    warnungen = []
    domain = _domain_aus_email(email)
    firma_norm = (firma or "").strip()

    # 1. Prüfen, ob schon ein aktiver Kunde in res.partner existiert
    partner_filter = []
    if firma_norm:
        partner_filter.append(("name", "ilike", firma_norm))
    if domain:
        partner_filter.append(("email", "ilike", f"%@{domain}"))
    if partner_filter:
        oder_domain = [("customer_rank", ">", 0), ("active", "=", True)]
        if len(partner_filter) == 2:
            oder_domain += ["|", partner_filter[0], partner_filter[1]]
        else:
            oder_domain += [partner_filter[0]]
        kunden = odoo.search_read("res.partner", oder_domain, ["id", "name"], limit=5)
        if kunden:
            liste = ", ".join(f"{k['name']} (ID {k['id']})" for k in kunden)
            warnungen.append(
                f"Kontakt oder Domain existiert in Odoo bereits als Kunde: {liste}. "
                "Falls es ein bestehender Kunde ist, direkt ein Angebot erstellen."
            )

    # 2. Prüfen, ob schon eine offene Verkaufschance existiert
    offene_stufen = [
        s["id"] for s in odoo.search_read("crm.stage", [("is_won", "=", False)], ["id"])
    ]
    chance_filter = []
    if firma_norm:
        chance_filter.append(("partner_name", "ilike", firma_norm))
        chance_filter.append(("partner_id.name", "ilike", firma_norm))
    if email and email.strip():
        chance_filter.append(("email_from", "ilike", email.strip()))
    if domain:
        chance_filter.append(("email_from", "ilike", f"%@{domain}"))

    if chance_filter and offene_stufen:
        oder = ["|"] * (len(chance_filter) - 1) + chance_filter
        such_domain = [
            ("id", "!=", neue_id),
            ("type", "=", "opportunity"),
            ("active", "=", True),
            ("stage_id", "in", offene_stufen),
        ] + oder
        offene = odoo.search_read("crm.lead", such_domain, ["id", "name", "stage_id", "user_id"], limit=5)
        if offene:
            liste = "; ".join(
                f"ID {c['id']} «{c['name']}» (Stufe {c['stage_id'][1]}, "
                f"{c['user_id'][1] if c['user_id'] else 'ohne Zuständige'})"
                for c in offene
            )
            warnungen.append(
                f"Es gibt bereits offene Verkaufschance(n) für diesen Kontakt oder diese Organisation: {liste}. "
                "Möglicherweise doppelt."
            )

    # 3. Hoher Schätzwert
    if geschaetzter_wert > WARN_SCHAETZWERT:
        warnungen.append(
            f"Geschätzter Wert {geschaetzter_wert:,.2f} CHF liegt über {WARN_SCHAETZWERT:,.0f} CHF "
            "(bei öffentlicher Hand Schwellenwerte für Ausschreibungen nach IVöB beachten)."
        )

    return warnungen


def chance_anlegen(
    odoo: Odoo,
    aufrufer: str,
    titel: str,
    firma: str | None = None,
    kontaktperson: str | None = None,
    funktion: str | None = None,
    email: str | None = None,
    telefon: str | None = None,
    strasse: str | None = None,
    plz: str | None = None,
    ort: str | None = None,
    geschaetzter_wert: float = 0.0,
    zustaendig: str | None = None,
    merkmale: list[str] | None = None,
    quelle: str = "E-Mail",
    frist: str | None = None,
    beschreibung: str | None = None,
) -> str:
    try:
        titel_sauber = (titel or "").strip()
        if not titel_sauber:
            raise Ablehnung("Der Titel der Verkaufschance darf nicht leer sein.")

        firma_sauber = (firma or "").strip()
        email_sauber = (email or "").strip()
        if not firma_sauber and not email_sauber:
            raise Ablehnung("Mindestens Firma/Organisation oder E-Mail-Adresse muss angegeben sein.")

        if email_sauber and ("@" not in email_sauber or "." not in email_sauber.rsplit("@", 1)[-1]):
            raise Ablehnung(f"Ungültige E-Mail-Adresse «{email_sauber}».")

        if geschaetzter_wert < 0:
            raise Ablehnung(f"Geschätzter Wert darf nicht negativ sein ({geschaetzter_wert}).")

        if frist:
            _datum_pruefen(frist, "Frist")

        zustaendig_angabe = zustaendig.strip() if zustaendig and zustaendig.strip() else _zuteilung_ableiten(
            firma_sauber, titel_sauber, merkmale
        )
        user_id, user_name = _verkaufsperson_aufloesen(odoo, zustaendig_angabe)

        stufen = odoo.search_read("crm.stage", [("name", "=", STUFE_NEU)], ["id"])
        if not stufen:
            raise Ablehnung(f"CRM-Stufe «{STUFE_NEU}» nicht in Odoo gefunden.")
        stufe_neu_id = stufen[0]["id"]

        tag_ids = []
        tag_namen = []
        if merkmale:
            alle_tags = {t["name"].lower(): t for t in odoo.search_read("crm.tag", [], ["id", "name"])}
            unbekannt = [m for m in merkmale if m.strip().lower() not in alle_tags]
            if unbekannt:
                erlaubt = ", ".join(sorted(t["name"] for t in alle_tags.values()))
                raise Ablehnung(f"Unbekannte Merkmale: {', '.join(unbekannt)}. Erlaubt: {erlaubt}.")
            for m in merkmale:
                t = alle_tags[m.strip().lower()]
                if t["id"] not in tag_ids:
                    tag_ids.append(t["id"])
                    tag_namen.append(t["name"])

        quelle_id = None
        if quelle and quelle.strip():
            alle_quellen = {q["name"].lower(): q for q in odoo.search_read("utm.source", [], ["id", "name"])}
            q_treffer = alle_quellen.get(quelle.strip().lower())
            if not q_treffer:
                erlaubt_q = ", ".join(sorted(q["name"] for q in alle_quellen.values()))
                raise Ablehnung(f"Unbekannte Quelle «{quelle}». Erlaubt: {erlaubt_q}.")
            quelle_id = q_treffer["id"]
    except Ablehnung as grund:
        return f"ABGELEHNT: {grund}"

    werte = {
        "name": titel_sauber,
        "type": "opportunity",
        "team_id": TEAM_ID,
        "user_id": user_id,
        "stage_id": stufe_neu_id,
        "probability": WAHRSCHEINLICHKEIT_NEU,
        "expected_revenue": float(geschaetzter_wert),
    }
    if firma_sauber:
        werte["partner_name"] = firma_sauber
    if kontaktperson and kontaktperson.strip():
        werte["contact_name"] = kontaktperson.strip()
    if funktion and funktion.strip():
        werte["function"] = funktion.strip()
    if email_sauber:
        werte["email_from"] = email_sauber
    if telefon and telefon.strip():
        werte["phone"] = telefon.strip()
    if strasse and strasse.strip():
        werte["street"] = strasse.strip()
    if plz and plz.strip():
        werte["zip"] = plz.strip()
    if ort and ort.strip():
        werte["city"] = ort.strip()
    if frist and frist.strip():
        werte["date_deadline"] = frist.strip()
    if tag_ids:
        werte["tag_ids"] = [(6, 0, tag_ids)]
    if quelle_id:
        werte["source_id"] = quelle_id
    if beschreibung and beschreibung.strip():
        werte["description"] = _text_zu_html(beschreibung)

    lead_id = odoo.call("crm.lead", "create", werte)
    angelegt = odoo.search_read("crm.lead", [("id", "=", lead_id)], ["name", "stage_id", "user_id", "expected_revenue"])[0]
    if angelegt["stage_id"][1] != STUFE_NEU:
        return (
            f"FEHLER: Verkaufschance ID {lead_id} steht in Stufe «{angelegt['stage_id'][1]}» statt «{STUFE_NEU}». "
            "Bitte sofort Beat melden."
        )

    warnungen = _dubletten_und_warnungen(odoo, firma_sauber, email_sauber, float(geschaetzter_wert), lead_id)

    notiz = (
        f"Verkaufschance angelegt durch Manni (KI-Assistent) über den Werkzeug-Server "
        f"(Aufrufer: {aufrufer}). Stufe «{STUFE_NEU}», zuständig: {user_name}."
    )
    if warnungen:
        notiz += "\n\nWARNUNG: " + " ".join(warnungen)

    hinweise = []
    try:
        post_kwargs = {"body": _text_zu_html(notiz), "message_type": "comment", "subtype_xmlid": "mail.mt_note"}
        autor_id = manni_autor_id(odoo)
        if autor_id:
            post_kwargs["author_id"] = autor_id
        odoo.call("crm.lead", "message_post", [lead_id], **post_kwargs)
    except OdooFehler as fehler:
        hinweise.append(f"Eröffnungsnotiz an der Chance nicht möglich ({fehler}).")

    merkmale_text = f", Merkmale: {', '.join(tag_namen)}" if tag_namen else ""
    return (
        f"VERKAUFSCHANCE ANGELEGT: ID {lead_id}, «{angelegt['name']}», Stufe {angelegt['stage_id'][1]}, "
        f"zuständig {user_name}, geschätzter Wert {angelegt['expected_revenue']:,.2f} CHF{merkmale_text}. "
        f"Die Qualifizierung und Umwandlung in einen Kunden erfolgt durch den Verkauf. "
        f"Link: {ODOO_CRM_LINK.format(id=lead_id)}"
        + ("\nWARNUNG (steht auch als Notiz an der Chance): " + " ".join(warnungen) if warnungen else "")
        + ("\nHinweise: " + " ".join(hinweise) if hinweise else "")
    )


def notiz_anhaengen(odoo: Odoo, aufrufer: str, chance_id: int, notiz: str) -> str:
    try:
        text_sauber = (notiz or "").strip()
        if not text_sauber:
            raise Ablehnung("Der Notiztext darf nicht leer sein.")
        chance = _aktive_chance_laden(odoo, chance_id)
    except Ablehnung as grund:
        return f"ABGELEHNT: {grund}"

    fusszeile = f"\n\n(Erstellt durch Manni (KI-Assistent) über den Werkzeug-Server, Aufrufer: {aufrufer})"
    post_kwargs = {
        "body": _text_zu_html(text_sauber + fusszeile),
        "message_type": "comment",
        "subtype_xmlid": "mail.mt_note",
    }
    autor_id = manni_autor_id(odoo)
    if autor_id:
        post_kwargs["author_id"] = autor_id

    odoo.call("crm.lead", "message_post", [chance_id], **post_kwargs)
    return (
        f"NOTIZ AN CHANCE ANGEHÄNGT: Chance ID {chance_id} («{chance['name']}»), "
        f"Autor Manni (KI-Assistent). Link: {ODOO_CRM_LINK.format(id=chance_id)}"
    )


def aktivitaet_anlegen(
    odoo: Odoo,
    aufrufer: str,
    chance_id: int,
    zusammenfassung: str,
    faellig_am: str,
    art: str = "call",
    zustaendig: str | None = None,
    notiz: str | None = None,
) -> str:
    try:
        titel_sauber = (zusammenfassung or "").strip()
        if not titel_sauber:
            raise Ablehnung("Die Zusammenfassung der Aktivität darf nicht leer sein.")
        _datum_pruefen(faellig_am, "Fälligkeitsdatum")
        art_schluessel = (art or "").strip().lower()
        if art_schluessel not in AKTIVITAET_ARTEN:
            raise Ablehnung(
                f"Unbekannte Aktivitätsart «{art}». Erlaubt: call (Anruf), email (E-Mail), todo (Aufgabe), meeting (Sitzung)."
            )
        xmlid_ref, art_name = AKTIVITAET_ARTEN[art_schluessel]
        chance = _aktive_chance_laden(odoo, chance_id)

        if zustaendig and zustaendig.strip():
            user_id, user_name = _verkaufsperson_aufloesen(odoo, zustaendig)
        elif chance.get("user_id"):
            user_id, user_name = chance["user_id"][0], chance["user_id"][1]
        else:
            raise Ablehnung("An der Chance ist niemand zuständig; bitte zustaendig angeben.")
    except Ablehnung as grund:
        return f"ABGELEHNT: {grund}"

    notiz_text = (notiz.strip() + "\n\n") if (notiz and notiz.strip()) else ""
    notiz_text += f"Geplant durch Manni (KI-Assistent) über den Werkzeug-Server ({aufrufer})."

    act_res = odoo.call(
        "crm.lead",
        "activity_schedule",
        [chance_id],
        act_type_xmlid=xmlid_ref,
        summary=titel_sauber,
        date_deadline=faellig_am.strip(),
        user_id=user_id,
        note=_text_zu_html(notiz_text),
    )
    m = re.search(r"\d+", str(act_res))
    act_id = m.group(0) if m else act_res
    return (
        f"AKTIVITÄT GEPLANT: ID {act_id}, {art_name} «{titel_sauber}» an Chance ID {chance_id} "
        f"(«{chance['name']}») für {user_name}, fällig am {faellig_am.strip()}. "
        f"Link: {ODOO_CRM_LINK.format(id=chance_id)}"
    )


def _branche_ableiten(odoo: Odoo, firma: str) -> tuple[int | None, str]:
    """Ordnet der Firma anhand des Namens eine Branche (res.partner.industry) der Muster AG zu."""
    if re.search(r"schul", firma, re.I):
        ziel = "Schulgemeinden"
    elif re.search(r"bergbahn|sesselbahn|hotel|kurhaus", firma, re.I):
        ziel = "Hotels und Bergbahnen"
    elif re.search(r"gemeinde|stadt", firma, re.I):
        ziel = "Gemeinden und Städte"
    elif re.search(r"garten|grün|landschaft", firma, re.I):
        ziel = "Garten- und Landschaftsbau"
    else:
        ziel = "Immobilienverwaltungen und Genossenschaften"
    treffer = odoo.search_read("res.partner.industry", [("name", "=", ziel)], ["id", "name"])
    if treffer:
        return treffer[0]["id"], treffer[0]["name"]
    return None, ziel


def _naechste_kundennummer(odoo: Odoo) -> str:
    """Ermittelt die nächste freie Kundennummer (z. B. K-026 oder KD-026)."""
    kunden = odoo.search_read("res.partner", [("customer_rank", ">", 0), ("ref", "!=", False)], ["ref"])
    praefix = "K-"
    max_nr = 0
    for k in kunden:
        m = re.match(r"^([A-Z]+-)(\d+)$", str(k.get("ref") or "").strip())
        if m:
            praefix = m.group(1)
            max_nr = max(max_nr, int(m.group(2)))
    return f"{praefix}{max_nr + 1:03d}"


def kunde_vorbereiten(
    odoo: Odoo,
    firma: str | None = None,
    kontaktperson: str | None = None,
    funktion: str | None = None,
    email: str | None = None,
    telefon: str | None = None,
    strasse: str | None = None,
    plz: str | None = None,
    ort: str | None = None,
    preisliste: str = "Standard",
    chance_id: int | None = None,
) -> tuple[dict | None, str]:
    """Prüft alle Angaben für kunde_anlegen vor der Freigabe.

    Gibt (daten_dict, freigabe_text) zurück oder (None, 'ABGELEHNT: ...').
    """
    try:
        chance = None
        if chance_id is not None:
            chancen = odoo.search_read(
                "crm.lead",
                [("id", "=", chance_id), ("type", "=", "opportunity")],
                [
                    "id", "name", "stage_id", "partner_id", "partner_name",
                    "contact_name", "function", "email_from", "phone",
                    "street", "zip", "city", "active",
                ],
                context={"active_test": False},
            )
            if not chancen:
                raise Ablehnung(f"Keine Verkaufschance mit der ID {chance_id} gefunden.")
            chance = chancen[0]
            if not chance["active"]:
                raise Ablehnung(f"Verkaufschance ID {chance_id} («{chance['name']}») ist archiviert/verloren.")
            if chance.get("partner_id"):
                raise Ablehnung(
                    f"Verkaufschance ID {chance_id} ist bereits mit dem Kunden "
                    f"«{chance['partner_id'][1]}» (ID {chance['partner_id'][0]}) verknüpft."
                )
            firma = firma or chance.get("partner_name") or ""
            kontaktperson = kontaktperson or chance.get("contact_name") or ""
            funktion = funktion or chance.get("function") or ""
            email = email or chance.get("email_from") or ""
            telefon = telefon or chance.get("phone") or ""
            strasse = strasse or chance.get("street") or ""
            plz = plz or chance.get("zip") or ""
            ort = ort or chance.get("city") or ""

        firma_sauber = (firma or "").strip()
        if not firma_sauber:
            raise Ablehnung("Der Firmen- oder Organisationsname darf nicht leer sein.")

        ort_sauber = (ort or "").strip()
        if not ort_sauber:
            raise Ablehnung("Der Ort des Kunden muss angegeben sein.")

        email_sauber = (email or "").strip()
        if not email_sauber or "@" not in email_sauber or "." not in email_sauber.rsplit("@", 1)[-1]:
            raise Ablehnung(f"Eine gültige E-Mail-Adresse ist erforderlich (erhalten: «{email_sauber}»).")

        pl_key = (preisliste or "Standard").strip().lower()
        if pl_key not in PREISLISTEN_ZUORDNUNG:
            raise Ablehnung(
                f"Unbekannte Preisliste «{preisliste}». Erlaubt: Standard, Wiederverkäufer 10 %."
            )
        pl_name = PREISLISTEN_ZUORDNUNG[pl_key]
        pl_treffer = odoo.search_read("product.pricelist", [("name", "=", pl_name)], ["id", "name"])
        if not pl_treffer:
            raise Ablehnung(f"Preisliste «{pl_name}» nicht in Odoo gefunden.")
        pl_id = pl_treffer[0]["id"]

        # Harte Dubletten-Sperre gegen res.partner
        domain = _domain_aus_email(email_sauber)
        oder_teile = [
            ("name", "=ilike", firma_sauber),
            ("email", "=ilike", email_sauber),
        ]
        if domain:
            oder_teile.append(("email", "ilike", f"%@{domain}"))
        such_domain = [("active", "=", True), ("parent_id", "=", False)] + ["|"] * (len(oder_teile) - 1) + oder_teile
        vorhanden = odoo.search_read(
            "res.partner", such_domain, ["id", "name", "email", "customer_rank"], limit=5
        )
        if vorhanden:
            liste = ", ".join(f"{k['name']} (ID {k['id']}, {k.get('email') or '-'})" for k in vorhanden)
            raise Ablehnung(
                f"Kontakt oder E-Mail-Domain existiert in Odoo bereits: {liste}. "
                "Dubletten sind gesperrt."
            )

        branche_id, branche_name = _branche_ableiten(odoo, firma_sauber)
        daten = {
            "firma": firma_sauber,
            "kontaktperson": (kontaktperson or "").strip(),
            "funktion": (funktion or "").strip(),
            "email": email_sauber,
            "telefon": (telefon or "").strip(),
            "strasse": (strasse or "").strip(),
            "plz": (plz or "").strip(),
            "ort": ort_sauber,
            "preisliste_id": pl_id,
            "preisliste_name": pl_name,
            "branche_id": branche_id,
            "branche_name": branche_name,
            "chance_id": chance["id"] if chance else None,
            "chance_name": chance["name"] if chance else None,
            "chance_stufe": chance["stage_id"][1] if chance else None,
        }

        zeilen = [
            "NEUKUNDE IN ODOO ANLEGEN (Freigabe erforderlich)",
            "",
            f"Firma / Organisation: {daten['firma']}",
        ]
        if daten["kontaktperson"]:
            kp = daten["kontaktperson"] + (f" ({daten['funktion']})" if daten["funktion"] else "")
            zeilen.append(f"Kontaktperson: {kp}")
        adr = ", ".join(p for p in [daten["strasse"], f"{daten['plz']} {daten['ort']}".strip()] if p)
        zeilen.append(f"Adresse: {adr} (Schweiz)")
        zeilen.append(f"E-Mail: {daten['email']}" + (f" · Telefon: {daten['telefon']}" if daten["telefon"] else ""))
        zeilen.append(f"Branche: {daten['branche_name']}")
        zeilen.append(f"Preisliste: {daten['preisliste_name']} · Zahlungsfrist: 30 Tage")
        if daten["preisliste_name"] != "Standard":
            zeilen.append(f"ACHTUNG: Rabatt-Preisliste «{daten['preisliste_name']}» ausgewählt!")
        if daten["chance_id"]:
            zeilen.append(
                f"Verkaufschance: ID {daten['chance_id']} «{daten['chance_name']}» "
                f"wird verknüpft und auf Stufe «{STUFE_QUALIFIZIERT}» gesetzt."
            )
        return daten, "\n".join(zeilen)
    except Ablehnung as grund:
        return None, f"ABGELEHNT: {grund}"


def kunde_schreiben(odoo: Odoo, aufrufer: str, daten: dict) -> str:
    """Legt den geprüften und per Knopf freigegebenen Kunden in Odoo an und aktualisiert ggf. die Chance."""
    land = odoo.search_read("res.country", [("code", "=", "CH")], ["id"])
    frist = odoo.search_read("account.payment.term", [("name", "=", "30 Tage")], ["id"])
    ref = _naechste_kundennummer(odoo)

    werte = {
        "name": daten["firma"],
        "ref": ref,
        "is_company": True,
        "lang": "de_CH",
        "city": daten["ort"],
        "email": daten["email"],
        "customer_rank": 1,
        "supplier_rank": 0,
        "property_product_pricelist": daten["preisliste_id"],
    }
    if daten["strasse"]:
        werte["street"] = daten["strasse"]
    if daten["plz"]:
        werte["zip"] = daten["plz"]
    if daten["telefon"]:
        werte["phone"] = daten["telefon"]
    if land:
        werte["country_id"] = land[0]["id"]
    if frist:
        werte["property_payment_term_id"] = frist[0]["id"]
    if daten["branche_id"]:
        werte["industry_id"] = daten["branche_id"]

    partner_id = odoo.call("res.partner", "create", werte)

    kontakt_id = None
    if daten["kontaktperson"]:
        kp_werte = {
            "name": daten["kontaktperson"],
            "parent_id": partner_id,
            "is_company": False,
            "type": "contact",
            "lang": "de_CH",
            "email": daten["email"],
        }
        if daten["funktion"]:
            kp_werte["function"] = daten["funktion"]
        if daten["telefon"]:
            kp_werte["phone"] = daten["telefon"]
        kontakt_id = odoo.call("res.partner", "create", kp_werte)

    autor_id = manni_autor_id(odoo)
    notiz_kunde = (
        f"Neukunde ({ref}) nach Freigabe per Knopf angelegt durch Manni (KI-Assistent) "
        f"über den Werkzeug-Server (Aufrufer: {aufrufer}). Preisliste: {daten['preisliste_name']}."
    )
    try:
        post_kwargs = {"body": _text_zu_html(notiz_kunde), "message_type": "comment", "subtype_xmlid": "mail.mt_note"}
        if autor_id:
            post_kwargs["author_id"] = autor_id
        odoo.call("res.partner", "message_post", [partner_id], **post_kwargs)
    except OdooFehler:
        pass

    chance_text = ""
    if daten["chance_id"]:
        cid = daten["chance_id"]
        lead_update = {"partner_id": partner_id}
        if daten["chance_stufe"] == STUFE_NEU:
            stufen = odoo.search_read("crm.stage", [("name", "=", STUFE_QUALIFIZIERT)], ["id"])
            if stufen:
                lead_update["stage_id"] = stufen[0]["id"]
                lead_update["probability"] = WAHRSCHEINLICHKEIT_QUALIFIZIERT
        odoo.call("crm.lead", "write", [cid], lead_update)
        notiz_lead = (
            f"Neukunde «{daten['firma']}» (ID {partner_id}, {ref}) nach Freigabe per Knopf angelegt, "
            f"mit dieser Verkaufschance verknüpft und Stufe auf «{STUFE_QUALIFIZIERT}» gesetzt "
            f"(Aufrufer: {aufrufer})."
        )
        try:
            post_kwargs = {"body": _text_zu_html(notiz_lead), "message_type": "comment", "subtype_xmlid": "mail.mt_note"}
            if autor_id:
                post_kwargs["author_id"] = autor_id
            odoo.call("crm.lead", "message_post", [cid], **post_kwargs)
        except OdooFehler:
            pass
        chance_text = (
            f", verknüpft mit Verkaufschance ID {cid} («{daten['chance_name']}», "
            f"Stufe jetzt «{STUFE_QUALIFIZIERT}»)"
        )

    kp_text = f", Kontaktperson {daten['kontaktperson']} (ID {kontakt_id})" if kontakt_id else ""
    return (
        f"KUNDE ANGELEGT (MIT FREIGABE): ID {partner_id}, «{daten['firma']}» ({ref}), "
        f"{daten['plz']} {daten['ort']}".replace("  ", " ")
        + f", Preisliste {daten['preisliste_name']}{kp_text}{chance_text}. "
        f"Link: {ODOO_KUNDE_LINK.format(id=partner_id)}"
    )
