#!/usr/bin/env python3
"""Legt den Odoo-Benutzer «Werkzeug-Server» an (Bauschritt W0, Punkt 3). Nur mit Beats Ja und Sicherung davor.

Meldet sich als Admin an (Zugang aus data-generator/.env, wird nicht ausgegeben).
Setzt die Gruppen ausdrücklich, weil die Vorlage base.default_user sonst Administratorrechte mitgibt.
Ohne Passwort: Beat setzt es selbst, meldet sich an und erzeugt den API-Schlüssel.

Aufruf: python3 werkzeug-server/odoo-benutzer-anlegen.py [--nur-pruefen]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data-generator"))
from odoo_client import OdooClient  # noqa: E402

LOGIN = "werkzeug-server@muster-ag.local"
NAME = "Werkzeug-Server"
# Interner Benutzer und Rechnungsstellung «Fakturierung» (Lieferantenrechnungen anlegen)
GRUPPEN = [("base", "group_user"), ("account", "group_account_invoice")]


def gruppen_id(odoo, modul, name):
    treffer = odoo.search_read("ir.model.data", [("module", "=", modul), ("name", "=", name),
                                                 ("model", "=", "res.groups")], ["res_id"])
    if not treffer:
        raise SystemExit(f"Gruppe {modul}.{name} nicht gefunden")
    return treffer[0]["res_id"]


def zeige_gruppen(odoo, benutzer_id):
    benutzer = odoo.search_read("res.users", [("id", "=", benutzer_id)], ["groups_id", "share", "active"])[0]
    gruppen = odoo.search_read("res.groups", [("id", "in", benutzer["groups_id"])], ["full_name"])
    print(f"Benutzer id {benutzer_id}, aktiv {benutzer['active']}, {len(gruppen)} Gruppen:")
    verdaechtig = []
    for gruppe in sorted(gruppen, key=lambda g: g["full_name"]):
        print(f"  - {gruppe['full_name']}")
        if any(w in gruppe["full_name"].lower() for w in ("administrator", "settings", "einstellungen", "manager")):
            verdaechtig.append(gruppe["full_name"])
    if verdaechtig:
        print("ACHTUNG, Gruppen mit weitgehenden Rechten:", ", ".join(verdaechtig))
        return False
    print("Keine Administrator- oder Manager-Gruppe.")
    return True


def main():
    odoo = OdooClient()
    odoo.login()
    vorhanden = odoo.search_read("res.users", [("login", "=", LOGIN)], ["id"], context={"active_test": False})

    if "--nur-pruefen" in sys.argv:
        if not vorhanden:
            raise SystemExit("Benutzer gibt es noch nicht.")
        sys.exit(0 if zeige_gruppen(odoo, vorhanden[0]["id"]) else 1)

    if vorhanden:
        raise SystemExit(f"Benutzer {LOGIN} gibt es schon (id {vorhanden[0]['id']}). Nichts geändert.")

    ids = [gruppen_id(odoo, modul, name) for modul, name in GRUPPEN]
    benutzer_id = odoo.call("res.users", "create", {
        "name": NAME,
        "login": LOGIN,
        "groups_id": [(6, 0, ids)],
    })
    print(f"Angelegt: {NAME} ({LOGIN})")
    sys.exit(0 if zeige_gruppen(odoo, benutzer_id) else 1)


if __name__ == "__main__":
    main()
