"""Etappe 1: Verbindungstest und Bestandsaufnahme. Liest nur, schreibt nichts."""

from odoo_client import OdooClient

# Konten, die der Generator voraussichtlich braucht (Schweizer KMU-Kontenrahmen)
NEEDED_ACCOUNTS = [
    "1021", "1099", "1100", "1170", "1171", "1200", "1500", "1509",
    "2000", "2030", "2200", "2208", "2800", "2950", "2970",
    "3000", "3400",
    "4000", "4400",
    "5000", "5700",
    "6000", "6100", "6260", "6300", "6400", "6500", "6570", "6600", "6800",
    "8900",
]

RELEVANT_MODULES = [
    "account", "l10n_ch", "sale_management", "purchase", "contacts", "stock",
    "currency_rate_live", "account_financial_report", "mis_builder",
    "mis_template_financial_report", "mis_builder_budget",
]


def header(title):
    print(f"\n== {title} ==")


def pick(client, model, wanted):
    """Nur Felder abfragen, die es in dieser Odoo-Version gibt."""
    available = client.fields(model)
    return [f for f in wanted if f in available]


def show_company(client):
    header("Firma")
    fields = pick(client, "res.company", [
        "name", "street", "zip", "city", "country_id", "currency_id", "vat",
        "account_fiscal_country_id", "chart_template", "fiscalyear_last_month",
        "fiscalyear_last_day", "fiscalyear_lock_date", "tax_lock_date",
        "hard_lock_date", "sale_lock_date", "purchase_lock_date",
        "account_opening_date", "account_opening_move_id",
        "currency_exchange_journal_id", "income_currency_exchange_account_id",
        "expense_currency_exchange_account_id", "transfer_account_id",
        "downpayment_account_id",
    ])
    for company in client.search_read("res.company", [], fields):
        for key in fields:
            value = company.get(key)
            if isinstance(value, list) and len(value) == 2:
                value = value[1]
            print(f"  {key}: {value}")


def show_modules(client):
    header("Module")
    installed = client.search_read("ir.module.module", [("state", "=", "installed")], ["name"])
    names = sorted(m["name"] for m in installed)
    print(f"  installiert: {len(names)} Module")
    for name in RELEVANT_MODULES:
        print(f"  {name}: {'ja' if name in names else 'nein'}")
    others = [n for n in names if n.startswith(("l10n_", "mis_", "account_", "sale", "purchase", "currency"))]
    print(f"  weitere relevante: {', '.join(others)}")


def show_user(client):
    header("Benutzer")
    user = client.search_read("res.users", [("id", "=", client.uid)], ["name", "login", "lang", "tz"])[0]
    print(f"  {user['name']} ({user['login']}), Sprache {user['lang']}, Zeitzone {user['tz']}")
    for xmlid, label in [
        ("account.group_account_manager", "Buchhaltung Administrator"),
        ("account.group_account_user", "Zeige vollständige Finanzbuchhaltung"),
        ("base.group_multi_currency", "Mehrere Währungen"),
        ("sale.group_auto_done_setting", "Aufträge sperren"),
        ("sale.group_discount_per_so_line", "Rabatte auf Positionen"),
    ]:
        module, name = xmlid.split(".")
        ref = client.search_read("ir.model.data", [("module", "=", module), ("name", "=", name)], ["res_id"])
        if not ref:
            print(f"  {label}: Gruppe nicht gefunden")
            continue
        member = client.search_count("res.users", [("id", "=", client.uid), ("groups_id", "in", ref[0]["res_id"])])
        print(f"  {label}: {'ja' if member else 'nein'}")


def show_currencies(client):
    header("Währungen")
    for cur in client.search_read("res.currency", [("name", "in", ["CHF", "EUR"]), ("active", "in", [True, False])],
                                  ["name", "active", "rate", "rounding"]):
        rates = client.search_count("res.currency.rate", [("currency_id.name", "=", cur["name"])])
        print(f"  {cur['name']}: aktiv {cur['active']}, Kurs {cur['rate']}, Rundung {cur['rounding']}, Kurseinträge {rates}")
    rate_fields = client.fields("res.currency.rate")
    print(f"  Kursfelder: {', '.join(f for f in ('rate', 'company_rate', 'inverse_company_rate') if f in rate_fields)}")


def show_taxes(client):
    header("Steuern (aktiv)")
    fields = pick(client, "account.tax", ["name", "description", "invoice_label", "type_tax_use", "amount",
                                         "amount_type", "price_include", "tax_group_id", "tax_scope"])
    taxes = client.search_read("account.tax", [], fields, order="type_tax_use, amount, name")
    for tax in taxes:
        label = tax.get("invoice_label") or ""
        group = tax["tax_group_id"][1] if tax.get("tax_group_id") else ""
        scope = tax.get("tax_scope") or ""
        print(f"  [{tax['id']:>3}] {tax['type_tax_use']:<8} {tax['amount']:>5} %  {tax['name']}  | {label} | {group} | {scope}")
    print(f"  total {len(taxes)}")


def show_accounts(client):
    header("Konten")
    total = client.search_count("account.account", [])
    print(f"  Kontenplan: {total} Konten")
    accounts = client.search_read("account.account", [("code", "in", NEEDED_ACCOUNTS)],
                                  ["code", "name", "account_type", "reconcile"])
    by_code = {a["code"]: a for a in accounts}
    for code in NEEDED_ACCOUNTS:
        acc = by_code.get(code)
        if acc:
            print(f"  {code} {acc['name']}  ({acc['account_type']}{', abgleichbar' if acc['reconcile'] else ''})")
        else:
            print(f"  {code} fehlt")
    unaffected = client.search_read("account.account", [("account_type", "=", "equity_unaffected")], ["code", "name"])
    for acc in unaffected:
        print(f"  Gewinn laufendes Jahr: {acc['code']} {acc['name']}")


def show_journals(client):
    header("Journale")
    fields = pick(client, "account.journal", ["name", "code", "type", "default_account_id", "currency_id",
                                             "suspense_account_id"])
    for j in client.search_read("account.journal", [], fields, order="type, code"):
        acc = j["default_account_id"][1] if j.get("default_account_id") else "-"
        cur = j["currency_id"][1] if j.get("currency_id") else "Firmenwährung"
        print(f"  [{j['id']}] {j['code']:<6} {j['type']:<9} {j['name']}  Konto {acc}, {cur}")

    header("Zahlungsarten der Bank- und Kassenjournale")
    lines = client.search_read("account.payment.method.line", [("journal_id.type", "in", ["bank", "cash"])],
                               ["name", "journal_id", "payment_type", "payment_account_id"])
    for line in lines:
        acc = line["payment_account_id"][1] if line["payment_account_id"] else "keins (Zahlung ohne Buchung)"
        print(f"  {line['journal_id'][1]}: {line['payment_type']:<8} {line['name']}  Zwischenkonto {acc}")
    company_fields = client.fields("res.company")
    extra = [f for f in ("account_journal_payment_debit_account_id", "account_journal_payment_credit_account_id")
             if f in company_fields]
    if extra:
        company = client.search_read("res.company", [], extra)[0]
        for key in extra:
            print(f"  Firma {key}: {company[key][1] if company[key] else '-'}")


def show_terms_and_settings(client):
    header("Zahlungsbedingungen")
    for term in client.search_read("account.payment.term", [], ["name"]):
        print(f"  [{term['id']}] {term['name']}")

    header("Einstellungen (Systemparameter)")
    params = client.search_read("ir.config_parameter",
                                [("key", "ilike", "sale."), ("key", "not ilike", "mail")], ["key", "value"])
    for p in params:
        print(f"  {p['key']} = {p['value']}")

    deposit = client.search_read("product.product", [("name", "ilike", "anzahlung")], ["name", "property_account_income_id"])
    deposit += client.search_read("product.product", [("name", "ilike", "down payment")], ["name", "property_account_income_id"])
    for prod in deposit:
        acc = prod["property_account_income_id"][1] if prod["property_account_income_id"] else "-"
        print(f"  Anzahlungsartikel: {prod['name']}, Ertragskonto {acc}")


def show_existing_data(client):
    header("Vorhandene Daten (sollte leer sein)")
    checks = [
        ("res.partner Firmen", "res.partner", [("is_company", "=", True)]),
        ("res.partner Personen ohne Benutzer", "res.partner", [("is_company", "=", False), ("user_ids", "=", False)]),
        ("res.partner.industry", "res.partner.industry", []),
        ("product.template", "product.template", []),
        ("sale.order", "sale.order", []),
        ("purchase.order", "purchase.order", []),
        ("account.move gebucht", "account.move", [("state", "=", "posted")]),
        ("account.move Entwurf", "account.move", [("state", "=", "draft")]),
        ("account.payment", "account.payment", []),
    ]
    for label, model, domain in checks:
        print(f"  {label}: {client.search_count(model, domain)}")
    for prod in client.search_read("product.template", [], ["name", "type", "default_code"]):
        print(f"    Artikel vorhanden: {prod['default_code'] or ''} {prod['name']} ({prod['type']})")
    for partner in client.search_read("res.partner", [("is_company", "=", True)], ["name"]):
        print(f"    Firma vorhanden: {partner['name']}")


def main():
    client = OdooClient()
    version = client.version()
    print(f"Odoo-Server: {version.get('server_version')} ({version.get('server_serie')})")
    print(f"Adresse: {client.url}, Datenbank: {client.db}")
    uid = client.login()
    print(f"Anmeldung mit API-Schlüssel ok, Benutzer-ID {uid}")

    show_user(client)
    show_company(client)
    show_modules(client)
    show_currencies(client)
    show_taxes(client)
    show_accounts(client)
    show_journals(client)
    show_terms_and_settings(client)
    show_existing_data(client)


if __name__ == "__main__":
    main()
