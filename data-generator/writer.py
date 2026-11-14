"""Schreibt den Plan in Odoo, streng nach Datum.

Jeder Schritt prüft zuerst, ob es den Beleg schon gibt, und überspringt ihn dann.
Ein abgebrochener Lauf kann deshalb mit denselben Argumenten fortgesetzt werden.
"""

import time
from collections import Counter
from datetime import timedelta
from decimal import Decimal

import plan as P

# Reihenfolge innerhalb eines Tages
PRIORITY = {"opening_invoice": 0, "opening_bill": 0, "opening_entry": 1, "price_change": 1, "offer": 2, "confirm": 3, "po": 4,
            "bill": 5, "fixed_bill": 5, "invoice": 6, "cancel": 7, "customer_payment": 8,
            "vendor_payment": 8, "journal": 9}
TAX_NAMES = {"ust": ("8.1%", "sale"), "vst_material": ("8.1%", "purchase"), "vst_uebrig": ("8.1% I OE", "purchase")}
OPENING_LABEL = "Übernahme 2024 Nr. {:02d}"


def build_events(plan, start, end):
    events = []

    def add(kind, day, obj):
        if day is not None and start <= day <= end:
            events.append((day, PRIORITY[kind], obj.key, kind, obj))

    for o in plan.orders:
        add("offer", o.offer_date, o)
        if o.won:
            add("confirm", o.order_date, o)
        add("cancel", o.cancel_date, o)
    for inv in plan.invoices:
        add("opening_invoice" if inv.opening else "invoice", inv.date, inv)
        add("customer_payment", inv.pay_date, inv)
    for b in plan.bills:
        if b.opening:
            add("opening_bill", b.date, b)
        elif b.po_date:
            add("po", b.po_date, b)
            add("bill", b.date, b)
        else:
            add("fixed_bill", b.date, b)
        add("vendor_payment", b.pay_date, b)
    for j in plan.journals:
        add("opening_entry" if j.kind == "eroeffnung" else "journal", j.date, j)
    for pc in plan.price_changes:
        add("price_change", pc.date, pc)
    events.sort(key=lambda e: e[:3])
    return events


class Writer:
    def __init__(self, client, plan, planner):
        self.c = client
        self.plan = plan
        self.planner = planner
        self.stats = Counter()
        self.warnings = []
        self.notes = []
        self.move_ids = {}
        self.orders = {o.key: o for o in plan.orders}
        self.opening_numbers = {inv.key: i + 1 for i, inv in enumerate(i for i in plan.invoices if i.opening)}
        self.load_ids()

    # --- Stammdaten-IDs -------------------------------------------------

    def ids(self, model, field, values):
        records = self.c.search_read(model, [(field, "in", list(values))], [field])
        found = {r[field]: r["id"] for r in records}
        missing = set(values) - set(found)
        if missing:
            raise SystemExit(f"{model}: fehlt {sorted(missing)}")
        return found

    def load_ids(self):
        codes = {l.account for i in self.plan.invoices for l in i.lines} | \
                {l.account for b in self.plan.bills for l in b.lines} | \
                {a for j in self.plan.journals for a, _ in j.lines} | {P.ACC_VAT_DUE, P.ACC_VST_MAT, P.ACC_VST_OTHER}
        self.account = self.ids("account.account", "code", codes)
        self.partner = self.ids("res.partner", "ref",
                                {c["nummer"] for c in self.planner.customers} |
                                {s["nummer"] for s in self.planner.suppliers.values()})
        self.product = self.ids("product.product", "default_code", set(self.planner.articles))
        self.tax = {}
        for key, (name, use) in TAX_NAMES.items():
            found = self.c.search_read("account.tax", [("name", "=", name), ("type_tax_use", "=", use)], ["id"])
            self.tax[key] = found[0]["id"]
        self.journal = self.ids("account.journal", "code", {"BNK1", "SONST"})
        self.currency = self.ids("res.currency", "name", {"CHF", "EUR"})
        self.company_id = self.c.search_read("res.company", [], ["id"])[0]["id"]

    def tax_ids(self, key):
        return [(6, 0, [self.tax[key]] if key else [])]

    # --- Hilfen ---------------------------------------------------------

    def find(self, model, domain, fields=("id",)):
        found = self.c.search_read(model, domain, list(fields), limit=1)
        return found[0] if found else None

    def check_amount(self, label, odoo_value, plan_value):
        if abs(Decimal(str(odoo_value)) - plan_value) > Decimal("0.05"):
            self.warnings.append(f"{label}: Odoo {odoo_value} statt Plan {plan_value}")

    def post(self, move_id):
        self.c.call("account.move", "action_post", [move_id])

    def register_payment(self, move_id, day):
        ctx = {"active_model": "account.move", "active_ids": [move_id]}
        wizard = self.c.call("account.payment.register", "create",
                             {"payment_date": str(day), "journal_id": self.journal["BNK1"]}, context=ctx)
        self.c.call("account.payment.register", "action_create_payments", [wizard], context=ctx)
        state = self.c.search_read("account.move", [("id", "=", move_id)], ["payment_state"])[0]["payment_state"]
        if state != "paid":
            raise SystemExit(f"Zahlung erfasst, aber Rechnung {move_id} steht auf «{state}» statt «paid». Abbruch.")

    # --- Verkauf --------------------------------------------------------

    def order(self, o):
        return self.find("sale.order", [("partner_id", "=", self.partner[o.customer["nummer"]]),
                                        ("client_order_ref", "=", o.ref)], ("id", "state", "invoice_ids"))

    def do_offer(self, o):
        if self.order(o):
            return "vorhanden"
        so_id = self.c.call("sale.order", "create", {
            "partner_id": self.partner[o.customer["nummer"]],
            "client_order_ref": o.ref,
            "date_order": f"{o.offer_date} 08:00:00",
            "validity_date": str(o.offer_date + timedelta(days=30)),
            "order_line": [(0, 0, {"product_id": self.product[l.code], "product_uom_qty": float(l.qty),
                                   "price_unit": float(l.price), "discount": float(l.discount)})
                           for l in o.lines],
        })
        amount = self.c.search_read("sale.order", [("id", "=", so_id)], ["amount_untaxed"])[0]["amount_untaxed"]
        self.check_amount(f"Offerte {o.key}", amount, o.net)
        if o.customer["segment"] != P.RESELLER_SEGMENT:
            self.c.call("sale.order", "action_quotation_sent", [so_id])

    def do_confirm(self, o):
        so = self.order(o)
        if so["state"] == "sale":
            return "vorhanden"
        self.c.call("sale.order", "action_confirm", [so["id"]])
        # Odoo setzt beim Bestätigen das Datum auf jetzt
        self.c.call("sale.order", "write", [so["id"]], {"date_order": f"{o.order_date} 08:00:00"})

    def do_cancel(self, o):
        so = self.order(o)
        if so["state"] == "cancel":
            return "vorhanden"
        self.c.call("sale.order", "action_cancel", [so["id"]], context={"disable_cancel_warning": True})

    def posted_invoices(self, so):
        return self.c.search_read("account.move", [("id", "in", so["invoice_ids"]), ("state", "=", "posted")],
                                  ["id"], order="id")

    def do_invoice(self, inv):
        o = self.orders[inv.order_key]
        so = self.order(o)
        kind = getattr(inv, "kind", None)
        posted = self.posted_invoices(so)
        # Projekt Seefeld: erst Anzahlung, dann Schlussrechnung (P3)
        needed = 2 if kind == "final" else 1
        if len(posted) >= needed:
            self.move_ids[inv.key] = posted[needed - 1]["id"]
            return "vorhanden"
        ctx = {"active_model": "sale.order", "active_ids": [so["id"]]}
        values = {"advance_payment_method": "delivered", "sale_order_ids": [(6, 0, [so["id"]])]}
        if kind == "downpayment":
            values.update({"advance_payment_method": "percentage", "amount": float(inv.percent)})
        elif kind == "final":
            values["deduct_down_payments"] = True
        wizard = self.c.call("sale.advance.payment.inv", "create", values, context=ctx)
        self.c.call("sale.advance.payment.inv", "create_invoices", [wizard], context=ctx)
        draft = self.c.search_read("account.move", [("line_ids.sale_line_ids.order_id", "=", so["id"]),
                                                    ("state", "=", "draft")], ["id"])
        move_id = draft[0]["id"]
        self.c.call("account.move", "write", [move_id], {"invoice_date": str(inv.date), "date": str(inv.date)})
        self.post(move_id)
        self.move_ids[inv.key] = move_id
        total = self.c.search_read("account.move", [("id", "=", move_id)], ["amount_total"])[0]["amount_total"]
        self.check_amount(f"Rechnung {inv.key}", total, inv.gross)

    def opening_invoice_domain(self, inv):
        return [("move_type", "=", "out_invoice"), ("partner_id", "=", self.partner[inv.customer["nummer"]]),
                ("ref", "=", OPENING_LABEL.format(self.opening_numbers[inv.key]))]

    def do_opening_invoice(self, inv):
        existing = self.find("account.move", self.opening_invoice_domain(inv))
        if existing:
            self.move_ids[inv.key] = existing["id"]
            return "vorhanden"
        line = inv.lines[0]
        move_id = self.c.call("account.move", "create", {
            "move_type": "out_invoice", "partner_id": self.partner[inv.customer["nummer"]],
            "invoice_date": str(inv.date), "date": str(inv.date),
            "ref": OPENING_LABEL.format(self.opening_numbers[inv.key]),
            "invoice_line_ids": [(0, 0, {"name": line.label, "quantity": 1, "price_unit": float(line.price),
                                         "account_id": self.account[line.account], "tax_ids": [(6, 0, [])]})],
        })
        self.post(move_id)
        self.move_ids[inv.key] = move_id

    def customer_invoice_id(self, inv):
        if inv.key not in self.move_ids:
            if inv.opening:
                self.move_ids[inv.key] = self.find("account.move", self.opening_invoice_domain(inv))["id"]
            else:
                posted = self.posted_invoices(self.order(self.orders[inv.order_key]))
                self.move_ids[inv.key] = posted[-1 if getattr(inv, "kind", None) == "final" else 0]["id"]
        return self.move_ids[inv.key]

    def do_customer_payment(self, inv):
        move_id = self.customer_invoice_id(inv)
        state = self.c.search_read("account.move", [("id", "=", move_id)], ["payment_state"])[0]["payment_state"]
        if state in ("paid", "in_payment"):
            return "vorhanden"
        self.register_payment(move_id, inv.pay_date)

    # --- Einkauf --------------------------------------------------------

    def purchase_order(self, b):
        return self.find("purchase.order", [("partner_id", "=", self.partner[b.supplier["nummer"]]),
                                            ("origin", "=", self.po_origin(b))],
                         ("id", "state", "invoice_ids"))

    def do_po(self, b):
        if self.purchase_order(b):
            return "vorhanden"
        po_id = self.c.call("purchase.order", "create", {
            "partner_id": self.partner[b.supplier["nummer"]],
            "currency_id": self.currency[b.currency],
            "date_order": f"{b.po_date} 08:00:00",
            "origin": self.po_origin(b),
            "order_line": [(0, 0, {"product_id": self.product[l.code], "product_qty": float(l.qty),
                                   "price_unit": float(l.price), "date_planned": f"{b.date} 08:00:00",
                                   "taxes_id": self.tax_ids(l.tax)}) for l in b.lines],
        })
        self.c.call("purchase.order", "button_confirm", [po_id])
        self.c.call("purchase.order", "write", [po_id], {"date_approve": f"{b.po_date} 08:00:00"})

    def po_origin(self, b):
        return b.origin or f"Disposition {b.po_date:%y%m%d}"

    def bill_domain(self, b):
        return [("move_type", "=", "in_invoice"), ("partner_id", "=", self.partner[b.supplier["nummer"]]),
                ("ref", "=", b.ref)]

    def do_bill(self, b):
        existing = self.find("account.move", self.bill_domain(b))
        if existing:
            self.move_ids[b.key] = existing["id"]
            return "vorhanden"
        po = self.purchase_order(b)
        self.c.call("purchase.order", "action_create_invoice", [po["id"]])
        po = self.purchase_order(b)
        draft = self.c.search_read("account.move", [("id", "in", po["invoice_ids"]), ("state", "=", "draft")], ["id"])
        move_id = draft[0]["id"]
        self.c.call("account.move", "write", [move_id], {"invoice_date": str(b.date), "date": str(b.date), "ref": b.ref})
        self.post(move_id)
        self.move_ids[b.key] = move_id
        total = self.c.search_read("account.move", [("id", "=", move_id)], ["amount_total"])[0]["amount_total"]
        self.check_amount(f"Lieferantenrechnung {b.key}", total, b.gross)

    def do_fixed_bill(self, b):
        existing = self.find("account.move", self.bill_domain(b))
        if existing:
            self.move_ids[b.key] = existing["id"]
            return "vorhanden"
        move_id = self.c.call("account.move", "create", {
            "move_type": "in_invoice", "partner_id": self.partner[b.supplier["nummer"]],
            "invoice_date": str(b.date), "date": str(b.date), "ref": b.ref,
            "currency_id": self.currency[b.currency],
            "invoice_line_ids": [(0, 0, {"name": l.label, "quantity": float(l.qty), "price_unit": float(l.price),
                                         "account_id": self.account[l.account], "tax_ids": self.tax_ids(l.tax),
                                         **({"product_id": self.product[l.code]} if l.code in self.product else {})})
                                 for l in b.lines],
        })
        if getattr(b, "observe_duplicate", False):
            # P5: nur beobachten, ob Odoo eine Duplikatwarnung zeigt, nichts umgehen
            dup = self.c.search_read("account.move", [("id", "=", move_id)], ["duplicated_ref_ids"])[0]
            self.notes.append(f"P5 {b.ref}: Duplikatwarnung von Odoo: "
                              f"{'ja, ' + str(dup['duplicated_ref_ids']) if dup['duplicated_ref_ids'] else 'keine'}")
        self.post(move_id)
        self.move_ids[b.key] = move_id
        total = self.c.search_read("account.move", [("id", "=", move_id)], ["amount_total"])[0]["amount_total"]
        self.check_amount(f"Lieferantenrechnung {b.key}", total, b.gross)

    do_opening_bill = do_fixed_bill

    def do_vendor_payment(self, b):
        if b.key not in self.move_ids:
            self.move_ids[b.key] = self.find("account.move", self.bill_domain(b))["id"]
        move_id = self.move_ids[b.key]
        state = self.c.search_read("account.move", [("id", "=", move_id)], ["payment_state"])[0]["payment_state"]
        if state in ("paid", "in_payment"):
            return "vorhanden"
        self.register_payment(move_id, b.pay_date)

    # --- Journalbuchungen -----------------------------------------------

    def balance(self, code, day):
        lines = self.c.search_read("account.move.line", [("account_id", "=", self.account[code]),
                                                         ("parent_state", "=", "posted"),
                                                         ("date", "<=", str(day))], ["balance"])
        return Decimal(str(round(sum(l["balance"] for l in lines), 2)))

    def vat_lines(self, j):
        """MWST-Saldo aus den tatsächlichen Odoo-Buchungen, nicht aus dem Plan."""
        quarter = int(j.key[-1])
        year = int(j.key.split("-")[2])
        end = P.month_end(year, quarter * 3)
        due, mat, other = -self.balance(P.ACC_VAT_DUE, end), self.balance(P.ACC_VST_MAT, end), \
            self.balance(P.ACC_VST_OTHER, end)
        lines = [(P.ACC_VAT_DUE, due), (P.ACC_VST_MAT, -mat), (P.ACC_VST_OTHER, -other),
                 (P.ACC_BANK, -(due - mat - other))]
        self.check_amount(f"MWST-Zahlung {j.key}", due - mat - other, -dict(j.lines)[P.ACC_BANK])
        return lines

    def do_journal(self, j):
        if self.find("account.move", [("move_type", "=", "entry"), ("ref", "=", j.ref)]):
            return "vorhanden"
        lines = self.vat_lines(j) if j.kind == "mwst" else j.lines
        move_id = self.c.call("account.move", "create", {
            "move_type": "entry", "journal_id": self.journal["SONST"], "date": str(j.date), "ref": j.ref,
            "line_ids": [(0, 0, {"account_id": self.account[a], "name": j.ref,
                                 "debit": float(v) if v > 0 else 0.0, "credit": float(-v) if v < 0 else 0.0})
                         for a, v in lines if v],
        })
        self.post(move_id)
        return move_id

    def do_opening_entry(self, j):
        move_id = self.do_journal(j)
        if move_id == "vorhanden":
            return move_id
        self.c.call("res.company", "write", [self.company_id], {"account_opening_move_id": move_id})

    # --- Preisänderungen (P1) -------------------------------------------

    def do_price_change(self, pc):
        changed = 0
        for code, price in pc.prices.items():
            if pc.kind == "list_price":
                tmpl = self.find("product.template", [("default_code", "=", code)], ("id", "list_price"))
                if abs(Decimal(str(tmpl["list_price"])) - price) >= Decimal("0.01"):
                    self.c.call("product.template", "write", [tmpl["id"]], {"list_price": float(price)})
                    changed += 1
            else:
                info = self.find("product.supplierinfo", [("product_tmpl_id.default_code", "=", code)], ("id", "price"))
                if abs(Decimal(str(info["price"])) - price) >= Decimal("0.01"):
                    self.c.call("product.supplierinfo", "write", [info["id"]], {"price": float(price)})
                    changed += 1
        return None if changed else "vorhanden"

    # --- Lauf -----------------------------------------------------------

    def run(self, events):
        started = time.time()
        for n, (day, _, key, kind, obj) in enumerate(events, 1):
            try:
                result = getattr(self, f"do_{kind}")(obj)
            except Exception as error:
                print(f"\nFEHLER bei {kind} {key} am {day}: {error}")
                print("Abbruch. Ein neuer Lauf mit denselben Argumenten setzt hier fort.")
                raise SystemExit(1)
            self.stats[(kind, "übersprungen" if result == "vorhanden" else "geschrieben")] += 1
            if n % 50 == 0 or n == len(events):
                print(f"  {n}/{len(events)} bis {day:%d.%m.%Y}, {time.time() - started:.0f} s", flush=True)
        print("\nErgebnis")
        for kind in PRIORITY:
            written, skipped = self.stats[(kind, "geschrieben")], self.stats[(kind, "übersprungen")]
            if written or skipped:
                print(f"  {kind:<18} geschrieben {written:>4}, schon vorhanden {skipped:>4}")
        for note in self.notes:
            print(f"\n{note}")
        if self.warnings:
            print(f"\nAbweichungen Odoo gegenüber Plan ({len(self.warnings)}):")
            for w in self.warnings[:30]:
                print(f"  {w}")
