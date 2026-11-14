"""Etappe 2: Einstellungen und Stammdaten.

Ohne Argument: Trockenlauf, zeigt nur, was geschrieben würde.
Mit --schreiben: schreibt in Odoo. Bereits Vorhandenes wird übersprungen.
"""

import re
import sys

from master_data import (RESELLER_SEGMENT, SEGMENTS, load_articles, load_customers,
                         load_eur_rates, load_suppliers)
from odoo_client import OdooClient

OPENING_DATE = "2025-01-01"
# Fehler der Lokalisierung, nur bei Konten, die der Generator braucht
ACCOUNT_TYPE_FIXES = {
    "1500": "asset_fixed",
    "1509": "asset_fixed",
    "6800": "expense_depreciation",
}
BANK_ACCOUNT = "1021"
RESELLER_PRICELIST = "Wiederverkäufer 10 %"

SALE_CATEGORIES = ["Bänke", "Abfall", "Velo", "Grün", "Absperrungen", "Ersatzteile", "Dienstleistungen"]
PURCHASE_CATEGORIES = ["Material", "Fremdleistungen"]
CATEGORY_ACCOUNTS = {
    # Kategorie: (Ertragskonto, Aufwandkonto)
    **{name: ("3000", "4000") for name in SALE_CATEGORIES},
    "Dienstleistungen": ("3400", "4400"),
    "Material": ("3000", "4000"),
    "Fremdleistungen": ("3000", "4400"),
}

SETTINGS = {
    "group_discount_per_so_line": True,
    "group_product_pricelist": True,
    "group_uom": True,
    "default_invoice_policy": "order",
    "default_purchase_method": "purchase",
}


def slug(text):
    text = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("é", "e"), ("&", "und")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


class Stage2:
    def __init__(self, client, write):
        self.c = client
        self.write = write
        self.counts = {}

    # --- Hilfen ---------------------------------------------------------

    def log(self, group, text):
        self.counts[group] = self.counts.get(group, 0) + 1
        prefix = "schreibe" if self.write else "würde"
        print(f"  [{prefix}] {text}")

    def skip(self, text):
        print(f"  [vorhanden] {text}")

    def one_id(self, model, domain):
        ids = self.c.call(model, "search", domain, limit=1)
        return ids[0] if ids else None

    def account(self, code):
        acc = self.one_id("account.account", [("code", "=", code)])
        if not acc:
            raise SystemExit(f"Konto {code} fehlt im Kontenplan")
        return acc

    def tax(self, name, use):
        tax = self.one_id("account.tax", [("name", "=", name), ("type_tax_use", "=", use)])
        if not tax:
            raise SystemExit(f"Steuer {name} ({use}) fehlt")
        return tax

    def lookup(self, model, field, value):
        rec = self.one_id(model, [(field, "=", value)])
        if not rec:
            raise SystemExit(f"{model} mit {field}={value} fehlt")
        return rec

    def create(self, model, values):
        return self.c.call(model, "create", values) if self.write else None

    # --- Schritte -------------------------------------------------------

    def company_settings(self):
        print("\nFirma")
        company = self.c.search_read("res.company", [], ["account_opening_date"])[0]
        self.company_id = company["id"]
        if company["account_opening_date"] == OPENING_DATE:
            self.skip(f"Eröffnungsdatum {OPENING_DATE}")
        else:
            self.log("Einstellungen", f"Eröffnungsdatum {company['account_opening_date']} → {OPENING_DATE}")
            if self.write:
                self.c.call("res.company", "write", [company["id"]], {"account_opening_date": OPENING_DATE})

    def account_types(self):
        print("\nKontoarten korrigieren")
        for acc in self.c.search_read("account.account", [("code", "in", list(ACCOUNT_TYPE_FIXES))],
                                      ["code", "name", "account_type"]):
            target = ACCOUNT_TYPE_FIXES[acc["code"]]
            if acc["account_type"] == target:
                self.skip(f"{acc['code']} {acc['name']} ist {target}")
                continue
            self.log("Einstellungen", f"{acc['code']} {acc['name']}: {acc['account_type']} → {target}")
            if self.write:
                self.c.call("account.account", "write", [acc["id"]], {"account_type": target})

    def exchange_accounts(self):
        print("\nKonten für Kursdifferenzen")
        company = self.c.search_read("res.company", [], ["currency_exchange_journal_id",
                                                        "income_currency_exchange_account_id",
                                                        "expense_currency_exchange_account_id"])[0]
        journal = company["currency_exchange_journal_id"]
        print(f"  Journal: {journal[1] if journal else 'keins'}")
        for field, label, allowed, target in (
            ("income_currency_exchange_account_id", "Kursgewinne", ("income", "income_other"), "income_other"),
            ("expense_currency_exchange_account_id", "Kursverluste", ("expense",), "expense"),
        ):
            if not company[field]:
                raise SystemExit(f"Firma hat kein Konto für {label}")
            acc = self.c.search_read("account.account", [("id", "=", company[field][0])],
                                     ["code", "name", "account_type"])[0]
            if acc["account_type"] in allowed:
                self.skip(f"{label}: {acc['code']} {acc['name']} ({acc['account_type']})")
                continue
            self.log("Einstellungen", f"{label}: {acc['code']} {acc['name']}: {acc['account_type']} → {target}")
            if self.write:
                self.c.call("account.account", "write", [acc["id"]], {"account_type": target})

    def general_settings(self):
        print("\nEinstellungen Verkauf und Einkauf")
        current = self.current_settings()
        changes = {k: v for k, v in SETTINGS.items() if current.get(k) != v}
        for key in SETTINGS:
            if key in changes:
                self.log("Einstellungen", f"{key}: {current.get(key)} → {SETTINGS[key]}")
            else:
                self.skip(f"{key} = {SETTINGS[key]}")
        if changes and self.write:
            wizard = self.c.call("res.config.settings", "create", changes)
            self.c.call("res.config.settings", "execute", [wizard])

    def current_settings(self):
        # default_get liefert leere Auswahlfelder als None, das kann XML-RPC nicht übertragen
        groups = {
            "group_discount_per_so_line": ("sale", "group_discount_per_so_line"),
            "group_product_pricelist": ("product", "group_product_pricelist"),
            "group_uom": ("uom", "group_uom"),
        }
        current = {}
        for key, (module, name) in groups.items():
            group = self.c.search_read("ir.model.data", [("module", "=", module), ("name", "=", name)], ["res_id"])
            current[key] = bool(group) and bool(self.c.search_count(
                "res.users", [("id", "=", self.c.uid), ("groups_id", "in", group[0]["res_id"])]))
        defaults = {
            "default_invoice_policy": "invoice_policy",
            "default_purchase_method": "purchase_method",
        }
        for key, field in defaults.items():
            rec = self.c.search_read("ir.default", [("field_id.model", "=", "product.template"),
                                                    ("field_id.name", "=", field)], ["json_value"])
            current[key] = rec[0]["json_value"].strip('"') if rec else None
        # Odoo 18 berechnet «order» selbst und speichert dafür keinen Vorgabewert
        current["default_invoice_policy"] = current["default_invoice_policy"] or "order"
        return current

    def bank_payment_accounts(self):
        print(f"\nZahlungsarten Bank: direkt auf {BANK_ACCOUNT}")
        bank_account = self.account(BANK_ACCOUNT)
        lines = self.c.search_read("account.payment.method.line", [("journal_id.type", "=", "bank")],
                                   ["name", "journal_id", "payment_type", "payment_account_id"])
        for line in lines:
            label = f"{line['journal_id'][1]} {line['payment_type']} {line['name']}"
            if line["payment_account_id"] and line["payment_account_id"][0] == bank_account:
                self.skip(label)
                continue
            self.log("Einstellungen", f"{label}: Zwischenkonto → {BANK_ACCOUNT}")
            if self.write:
                self.c.call("account.payment.method.line", "write", [line["id"]],
                            {"payment_account_id": bank_account})

    def euro(self):
        print("\nEuro und Kurse")
        eur = self.c.search_read("res.currency", [("name", "=", "EUR"), ("active", "in", [True, False])],
                                 ["active"])[0]
        self.eur_id = eur["id"]
        if eur["active"]:
            self.skip("EUR aktiv")
        else:
            self.log("Einstellungen", "EUR aktivieren")
            if self.write:
                self.c.call("res.currency", "write", [eur["id"]], {"active": True})

        existing = {r["name"] for r in self.c.search_read("res.currency.rate", [("currency_id", "=", eur["id"])],
                                                           ["name"])}
        for rate in load_eur_rates():
            day = rate["gueltig_ab"]
            if day in existing:
                self.skip(f"Kurs {day}")
                continue
            # CSV: CHF pro EUR. Odoo speichert EUR pro CHF, das Feld inverse_company_rate nimmt CHF pro EUR.
            self.log("Kurse", f"Kurs ab {day}: 1 EUR = {rate['chf_pro_eur']} CHF "
                              f"(Odoo intern {1 / float(rate['chf_pro_eur']):.6f} EUR pro CHF)")
            self.create("res.currency.rate", {"name": day, "currency_id": eur["id"], "company_id": self.company_id,
                                              "inverse_company_rate": float(rate["chf_pro_eur"])})

    def industries(self):
        print("\nKundensegmente (Branche)")
        self.industry_ids = {}
        for name in SEGMENTS:
            rec = self.one_id("res.partner.industry", [("name", "=", name)])
            if rec:
                self.skip(name)
            else:
                self.log("Segmente", name)
                rec = self.create("res.partner.industry", {"name": name, "full_name": name})
            self.industry_ids[name] = rec

    def categories(self):
        print("\nArtikelkategorien")
        self.category_ids = {}
        for parent, children in (("Verkauf", SALE_CATEGORIES), ("Einkauf", PURCHASE_CATEGORIES)):
            parent_id = self.one_id("product.category", [("name", "=", parent), ("parent_id", "=", False)])
            if parent_id:
                self.skip(parent)
            else:
                self.log("Kategorien", parent)
                parent_id = self.create("product.category", {"name": parent})
            for name in children:
                income, expense = CATEGORY_ACCOUNTS[name]
                rec = self.one_id("product.category", [("name", "=", name), ("parent_id.name", "=", parent)])
                if rec:
                    self.skip(f"{parent} / {name}")
                else:
                    # Anzahlungskonto bleibt leer: Anzahlungen gehen so auf das Ertragskonto
                    self.log("Kategorien", f"{parent} / {name} (Ertrag {income}, Aufwand {expense})")
                    rec = self.create("product.category", {
                        "name": name, "parent_id": parent_id,
                        "property_account_income_categ_id": self.account(income),
                        "property_account_expense_categ_id": self.account(expense),
                    })
                self.category_ids[name] = rec

    def pricelist(self):
        print("\nPreisliste")
        self.pricelist_id = self.one_id("product.pricelist", [("name", "=", RESELLER_PRICELIST)])
        if self.pricelist_id:
            self.skip(RESELLER_PRICELIST)
            return
        self.log("Preislisten", f"{RESELLER_PRICELIST} für Segment {RESELLER_SEGMENT}")
        self.pricelist_id = self.create("product.pricelist", {
            "name": RESELLER_PRICELIST,
            "item_ids": [(0, 0, {"applied_on": "3_global", "compute_price": "percentage", "percent_price": 10})],
        })

    def customers(self):
        print("\nKunden")
        term = self.lookup("account.payment.term", "name", "30 Tage")
        country = self.lookup("res.country", "code", "CH")
        for row in load_customers():
            if self.one_id("res.partner", [("ref", "=", row["nummer"])]):
                self.skip(f"{row['nummer']} {row['name']}")
                continue
            extra = " (Preisliste Wiederverkäufer)" if row["segment"] == RESELLER_SEGMENT else ""
            self.log("Kunden", f"{row['nummer']} {row['name']}, {row['segment']}{extra}")
            values = {
                "name": row["name"], "ref": row["nummer"], "is_company": True, "lang": "de_CH",
                "street": row["strasse"], "zip": row["plz"], "city": row["ort"], "country_id": country,
                "email": f"info@{slug(row['name'])}.example",
                "industry_id": self.industry_ids[row["segment"]],
                "property_payment_term_id": term, "customer_rank": 1,
            }
            if row["segment"] == RESELLER_SEGMENT:
                values["property_product_pricelist"] = self.pricelist_id
            self.create("res.partner", values)

    def suppliers(self):
        print("\nLieferanten")
        self.supplier_ids = {}
        for row in load_suppliers():
            rec = self.one_id("res.partner", [("ref", "=", row["nummer"])])
            if rec:
                self.skip(f"{row['nummer']} {row['name']}")
                self.supplier_ids[row["name"]] = rec
                continue
            self.log("Lieferanten", f"{row['nummer']} {row['name']}, {row['liefert']}, {row['waehrung']}, {row['land']}")
            values = {
                "name": row["name"], "ref": row["nummer"], "is_company": True, "lang": "de_CH",
                "street": row["strasse"], "zip": row["plz"], "city": row["ort"],
                "country_id": self.lookup("res.country", "code", row["land"]),
                "email": f"buchhaltung@{slug(row['name'])}.example",
                "property_supplier_payment_term_id": self.lookup("account.payment.term", "name", row["zahlungsfrist"]),
                "supplier_rank": 1,
            }
            if row["waehrung"] == "EUR":
                values["property_purchase_currency_id"] = self.eur_id
            self.supplier_ids[row["name"]] = self.create("res.partner", values)

    def products(self):
        print("\nArtikel")
        sale_tax = self.tax("8.1%", "sale")
        purchase_tax = self.tax("8.1%", "purchase")
        for row in load_articles():
            if self.one_id("product.template", [("default_code", "=", row["code"])]):
                self.skip(f"{row['code']} {row['name']}")
                continue
            uom = self.lookup("uom.uom", "name", row["einheit"])
            values = {
                "name": row["name"], "default_code": row["code"],
                "categ_id": self.category_ids[row["kategorie"]],
                "uom_id": uom, "uom_po_id": uom,
                "standard_price": float(row["materialkosten"]),
            }
            if row["art"] == "einkauf":
                eur = row["einkaufswaehrung"] == "EUR"
                values.update({
                    "type": "consu", "sale_ok": False, "purchase_ok": True, "purchase_method": "purchase",
                    "list_price": 0, "taxes_id": [(6, 0, [])],
                    # EUR-Lieferanten ohne MWST, Einfuhrsteuer weggelassen (Plan)
                    "supplier_taxes_id": [(6, 0, [] if eur else [purchase_tax])],
                    "seller_ids": [(0, 0, {
                        "partner_id": self.supplier_ids[row["lieferant"]],
                        "price": float(row["einkaufspreis"]),
                        "currency_id": self.eur_id if eur else self.c.search_read(
                            "res.currency", [("name", "=", "CHF")], ["id"])[0]["id"],
                    })],
                })
                text = (f"{row['code']} {row['name']}, Einkauf {row['einkaufspreis']} {row['einkaufswaehrung']}"
                        f"/{row['einheit']} bei {row['lieferant']}")
            else:
                values.update({
                    "type": "service" if row["art"] == "dienst" else "consu",
                    "sale_ok": True, "purchase_ok": False, "invoice_policy": "order",
                    "list_price": float(row["verkaufspreis"]),
                    "taxes_id": [(6, 0, [sale_tax])], "supplier_taxes_id": [(6, 0, [])],
                })
                steel = ", Stahlartikel" if row["stahlartikel"] else ""
                text = (f"{row['code']} {row['name']}, {row['verkaufspreis']} CHF, "
                        f"Kosten {row['materialkosten']}{steel}")
            self.log("Artikel", text)
            self.create("product.template", values)

    def run(self):
        self.company_settings()
        self.account_types()
        self.exchange_accounts()
        self.general_settings()
        self.bank_payment_accounts()
        self.euro()
        self.industries()
        self.categories()
        self.pricelist()
        self.customers()
        self.suppliers()
        self.products()
        print("\nZusammenfassung" + ("" if self.write else " (Trockenlauf, nichts geschrieben)"))
        for group, count in self.counts.items():
            print(f"  {group}: {count}")


def main():
    write = "--schreiben" in sys.argv
    client = OdooClient()
    client.login()
    print("SCHREIBEN in Odoo" if write else "TROCKENLAUF, es wird nichts geschrieben")
    Stage2(client, write).run()


if __name__ == "__main__":
    main()
