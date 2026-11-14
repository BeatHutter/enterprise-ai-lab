"""Kontrolle nach einem Schreiblauf: Odoo gegen Plan. Liest nur."""

from collections import defaultdict
from datetime import date
from decimal import Decimal

import plan as P


def chf(value):
    return f"{Decimal(str(value)):,.2f}".replace(",", "'")


class Check:
    def __init__(self, client, planner):
        self.c = client
        self.pl = planner

    def lines(self, domain):
        return self.c.search_read("account.move.line", [("parent_state", "=", "posted")] + domain,
                                  ["account_id", "balance", "date"])

    def balances(self, until):
        result = defaultdict(Decimal)
        for line in self.lines([("date", "<=", str(until))]):
            code = line["account_id"][1].split(" ")[0]
            result[code] += Decimal(str(line["balance"]))
        return {k: round(v, 2) for k, v in result.items() if v}

    def first_eur_bill(self):
        print("\nErste EUR-Lieferantenrechnung")
        bill = self.c.search_read("account.move", [("move_type", "=", "in_invoice"), ("state", "=", "posted"),
                                                   ("currency_id.name", "=", "EUR")],
                                  ["name", "ref", "partner_id", "invoice_date", "amount_total", "amount_total_signed"],
                                  order="invoice_date, id", limit=1)
        if not bill:
            print("  keine")
            return
        b = bill[0]
        eur, chf_amount = Decimal(str(b["amount_total"])), abs(Decimal(str(b["amount_total_signed"])))
        rate = self.pl.rate(date.fromisoformat(b["invoice_date"]))
        print(f"  {b['name']} ({b['ref']}), {b['partner_id'][1]}, Rechnungsdatum {b['invoice_date']}")
        print(f"  EUR {chf(eur)} × Kurs {rate} (CSV, CHF pro EUR) = CHF {chf(eur * rate)} erwartet")
        print(f"  Odoo bucht CHF {chf(chf_amount)}, das sind {chf_amount / eur:.4f} CHF pro EUR")

    def paid_customer_invoice(self):
        print("\nBezahlte Kundenrechnung (Beispiel aus dem laufenden Geschäft)")
        inv = self.c.search_read("account.move", [("move_type", "=", "out_invoice"), ("payment_state", "=", "paid"),
                                                  ("invoice_origin", "!=", False)],
                                 ["name", "partner_id", "invoice_date", "invoice_date_due", "amount_total",
                                  "payment_state", "invoice_origin"], order="invoice_date, id", limit=1)
        if not inv:
            print("  keine")
            return
        i = inv[0]
        pay = [p for p in self.c.search_read("account.payment", [("partner_id", "=", i["partner_id"][0])],
                                             ["name", "date", "amount", "reconciled_invoice_ids"])
               if i["id"] in p["reconciled_invoice_ids"]]
        print(f"  {i['name']} zu Auftrag {i['invoice_origin']}, {i['partner_id'][1]}")
        print(f"  Datum {i['invoice_date']}, fällig {i['invoice_date_due']}, Betrag CHF {chf(i['amount_total'])}, "
              f"Status «{i['payment_state']}»")
        for p in pay:
            print(f"  Zahlung {p['name']} am {p['date']} über CHF {chf(p['amount'])}")
        counts = defaultdict(int)
        for m in self.c.search_read("account.move", [("move_type", "in", ["out_invoice", "in_invoice"]),
                                                     ("state", "=", "posted")], ["move_type", "payment_state"]):
            counts[(m["move_type"], m["payment_state"])] += 1
        print("  Zahlungsstatus aller Rechnungen: " + ", ".join(f"{k[0]} {k[1]}: {v}" for k, v in sorted(counts.items())))

    def transit_and_unaffected(self, until):
        print("\nÜbergangskonto und Ausgleichskonto")
        for label, domain in (("1099 Übergangskonto", [("account_id.code", "=", "1099")]),
                              ("999999 Unverteilte Gewinne/Verluste", [("account_id.account_type", "=", "equity_unaffected")])):
            lines = self.lines(domain)
            total = sum(Decimal(str(l["balance"])) for l in lines)
            at_ye = sum(Decimal(str(l["balance"])) for l in lines if l["date"] <= "2024-12-31")
            print(f"  {label}: {len(lines)} Buchungszeilen, Saldo per 31.12.2024 {chf(at_ye)}, per {until} {chf(total)}")
        opening = self.c.search_read("res.company", [], ["account_opening_move_id", "account_opening_date"])[0]
        print(f"  Eröffnungsbuchung der Firma: {opening['account_opening_move_id'] and opening['account_opening_move_id'][1]}, "
              f"Eröffnungsdatum {opening['account_opening_date']}")

    def balance_sheet(self, plan_balance):
        day = date(2024, 12, 31)
        print("\nBilanz per 31.12.2024: Odoo gegenüber Plan (Soll positiv)")
        odoo = self.balances(day)
        codes = sorted(set(odoo) | {c for c in plan_balance if plan_balance[c]})
        for code in codes:
            o, p = odoo.get(code, Decimal("0")), plan_balance.get(code, Decimal("0"))
            mark = "" if abs(o - p) < Decimal("0.01") else "  ← Abweichung"
            print(f"  {code:<7}{chf(o):>16}{chf(p):>16}{mark}")
        pl = {c: v for c, v in odoo.items() if c[0] in "345678"}
        print(f"  Erfolgsrechnung 2024: {len(pl)} Konten bebucht, Summe {chf(sum(pl.values(), Decimal('0')))}")

    def numbers(self):
        print("\nBelegnummern")
        for label, move_type in (("Kundenrechnungen", "out_invoice"), ("Lieferantenrechnungen", "in_invoice")):
            for year in (2024, 2025, 2026):
                moves = self.c.search_read("account.move", [("move_type", "=", move_type), ("state", "=", "posted"),
                                                            ("date", ">=", f"{year}-01-01"), ("date", "<=", f"{year}-12-31")],
                                           ["name", "date"], order="name")
                if moves:
                    print(f"  {label} {year}: {len(moves)}, erste {moves[0]['name']} ({moves[0]['date']}), "
                          f"letzte {moves[-1]['name']} ({moves[-1]['date']})")
        for model, label in (("sale.order", "Offerten/Aufträge"), ("purchase.order", "Bestellungen")):
            recs = self.c.search_read(model, [], ["name"], order="id")
            if recs:
                print(f"  {label}: {len(recs)}, erste {recs[0]['name']}, letzte {recs[-1]['name']}")

    def reconcile(self, day):
        """Saldo 1100 bzw. 2000 gegen die Summe der an diesem Tag offenen Rechnungen."""
        payments = self.c.search_read("account.payment", [("state", "not in", ["draft", "canceled"]),
                                                          ("date", "<=", str(day))],
                                      ["reconciled_invoice_ids", "reconciled_bill_ids"])
        paid = {i for p in payments for i in p["reconciled_invoice_ids"] + p["reconciled_bill_ids"]}
        print(f"\nAbstimmung per {day:%d.%m.%Y}")
        for code, move_type, label in (("1100", "out_invoice", "Debitoren"), ("2000", "in_invoice", "Kreditoren")):
            moves = self.c.search_read("account.move", [("move_type", "=", move_type), ("state", "=", "posted"),
                                                        ("date", "<=", str(day))],
                                       ["name", "partner_id", "amount_total_signed"])
            open_moves = [m for m in moves if m["id"] not in paid]
            # amount_total_signed ist bei Lieferantenrechnungen schon negativ, wie der Saldo auf 2000
            open_sum = sum(Decimal(str(m["amount_total_signed"])) for m in open_moves)
            ledger = defaultdict(Decimal)
            for line in self.c.search_read("account.move.line", [("account_id.code", "=", code),
                                                                 ("parent_state", "=", "posted"),
                                                                 ("date", "<=", str(day))], ["partner_id", "balance"]):
                ledger[line["partner_id"] and line["partner_id"][0]] += Decimal(str(line["balance"]))
            balance = sum(ledger.values(), Decimal("0"))
            diff = balance - open_sum
            status = "stimmt" if abs(diff) < Decimal("0.01") else f"DIFFERENZ {chf(diff)}"
            print(f"  {code} {label}: Saldo {chf(balance)}, offene Rechnungen {len(open_moves)} = {chf(open_sum)} → {status}")
            if abs(diff) >= Decimal("0.01"):
                per_partner = defaultdict(Decimal)
                for m in open_moves:
                    per_partner[m["partner_id"][0]] += Decimal(str(m["amount_total_signed"]))
                for partner in set(ledger) | set(per_partner):
                    d = ledger.get(partner, Decimal("0")) - per_partner.get(partner, Decimal("0"))
                    if abs(d) >= Decimal("0.01"):
                        docs = [m["name"] for m in moves if m["partner_id"][0] == partner]
                        print(f"    Partner {partner}: Differenz {chf(d)}, Belege {', '.join(docs)}")

    def open_moves(self, day, move_type):
        payments = self.c.search_read("account.payment", [("state", "not in", ["draft", "canceled"]),
                                                          ("date", "<=", str(day))],
                                      ["reconciled_invoice_ids", "reconciled_bill_ids"])
        paid = {i for p in payments for i in p["reconciled_invoice_ids"] + p["reconciled_bill_ids"]}
        moves = self.c.search_read("account.move", [("move_type", "=", move_type), ("state", "=", "posted"),
                                                    ("date", "<=", str(day))],
                                   ["name", "partner_id", "amount_total_signed", "invoice_date", "invoice_date_due"])
        return [m for m in moves if m["id"] not in paid]

    def aging(self, day):
        print(f"\nOffene Posten nach Alter per {day:%d.%m.%Y} (Tage nach Fälligkeit, CHF)")
        buckets = ["nicht fällig", "1-30", "31-60", "61-90", "über 90"]
        for move_type, label in (("out_invoice", "Debitoren"), ("in_invoice", "Kreditoren")):
            sums, counts = defaultdict(Decimal), defaultdict(int)
            for m in self.open_moves(day, move_type):
                overdue = (day - date.fromisoformat(m["invoice_date_due"])).days
                b = buckets[0] if overdue <= 0 else buckets[1] if overdue <= 30 else buckets[2] if overdue <= 60 \
                    else buckets[3] if overdue <= 90 else buckets[4]
                sums[b] += abs(Decimal(str(m["amount_total_signed"])))
                counts[b] += 1
            total = sum(sums.values(), Decimal("0"))
            print(f"  {label}: " + " | ".join(f"{b} {counts[b]} / {chf(sums[b])}" for b in buckets)
                  + f" | total {sum(counts.values())} / {chf(total)}")
            oldest = sorted(self.open_moves(day, move_type), key=lambda m: m["invoice_date_due"])[:3]
            for m in oldest:
                print(f"    {m['name']} {m['partner_id'][1]}, fällig {m['invoice_date_due']}, "
                      f"{chf(abs(m['amount_total_signed']))}")

    def monthly(self, start, until):
        print("\nUmsatz und Materialquote pro Monat: Odoo gegenüber Plan (CHF)")
        print(f"  {'Monat':<9}{'Umsatz Odoo':>14}{'Plan':>14}{'Material Odoo':>15}{'Plan':>14}{'Quote':>8}")
        lines = self.lines([("date", ">=", str(start)), ("date", "<=", str(until)),
                            ("account_id.code", "in", ["3000", "3400", "4000", "4400"])])
        odoo = defaultdict(Decimal)
        for l in lines:
            code = l["account_id"][1].split(" ")[0]
            odoo[(l["date"][:7], "rev" if code[0] == "3" else "mat")] += Decimal(str(l["balance"]))
        for y, m in P.months((start.year, start.month), (until.year, until.month)):
            key = f"{y}-{m:02d}"
            first, last = date(y, m, 1), P.month_end(y, m)
            rev, mat = -odoo[(key, "rev")], odoo[(key, "mat")]
            p_rev = -self.pl.balance({"3000", "3400"}, last, first)
            p_mat = self.pl.balance({"4000", "4400"}, last, first)
            mark = "" if abs(rev - p_rev) < 1 and abs(mat - p_mat) < 1 else "  ← Abweichung"
            print(f"  {key:<9}{chf(rev):>14}{chf(p_rev):>14}{chf(mat):>15}{chf(p_mat):>14}"
                  f"{(mat / rev * 100 if rev else 0):>7.1f}%{mark}")

    def vat_payments(self, until):
        print("\nMWST-Zahlungen an die ESTV in Odoo")
        moves = self.c.search_read("account.move", [("move_type", "=", "entry"), ("state", "=", "posted"),
                                                    ("ref", "like", "MWST-Abrechnung"), ("date", "<=", str(until))],
                                   ["name", "date", "ref", "line_ids"], order="date")
        plan = {j.ref: -dict(j.lines)[P.ACC_BANK] for j in self.pl.plan.journals if j.kind == "mwst"}
        for m in moves:
            bank = sum(Decimal(str(l["balance"])) for l in self.c.search_read(
                "account.move.line", [("move_id", "=", m["id"]), ("account_id.code", "=", "1021")], ["balance"]))
            print(f"  {m['date']}  {m['name']}  {m['ref']:<32} Zahlung {chf(-bank):>12}  Plan {chf(plan.get(m['ref'], 0)):>12}")

    def bank(self, until, plan_bank):
        odoo = sum(Decimal(str(l["balance"])) for l in self.lines([("account_id.code", "=", "1021"),
                                                                   ("date", "<=", str(until))]))
        print(f"\nBank 1021 per {until}: Odoo {chf(odoo)}, Plan {chf(plan_bank)}")


def run_check(client, planner, until):
    check = Check(client, planner)
    plan_ye = defaultdict(Decimal)
    for day, account, amount, _ in planner.plan.ledger:
        if day <= date(2024, 12, 31):
            plan_ye[account] += amount
    check.first_eur_bill()
    check.paid_customer_invoice()
    check.transit_and_unaffected(until)
    check.balance_sheet(plan_ye)
    check.reconcile(date(2024, 12, 31))
    if until > date(2024, 12, 31):
        check.reconcile(until)
    check.numbers()
    check.bank(until, planner.balance({P.ACC_BANK}, until))
    if until > date(2025, 1, 31):
        check.monthly(date(2025, 1, 1), until)
        check.vat_payments(until)
        check.aging(until)
