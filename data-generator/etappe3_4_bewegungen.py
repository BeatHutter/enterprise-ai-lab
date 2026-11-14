"""Etappe 3 und 4: Bewegungen nach Datum schreiben.

  --bis 2025-08-31   Etappe 3: alles bis und mit diesem Tag
  --ab 2025-09-01    Etappe 4: alles ab diesem Tag (noch nicht gebaut)
  ohne --schreiben   Trockenlauf: nur Bericht aus dem Plan, Odoo wird nicht angefasst
  --schreiben        schreibt in Odoo, Vorhandenes wird übersprungen
  --kontrolle        vergleicht Odoo mit dem Plan, liest nur
"""

import argparse
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

import plan as P

MONTH_NAMES = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
DREHBUCH_PAYMENT_DAYS = {
    "Gemeinden und Städte": 28, "Immobilienverwaltungen und Genossenschaften": 40,
    "Garten- und Landschaftsbau": 45, "Schulgemeinden": 30, "Hotels und Bergbahnen": 35,
}


def chf(value, width=12):
    text = f"{Decimal(value):,.0f}".replace(",", "'")
    return text.rjust(width)


def pct(value, width=7):
    return f"{value * 100:.1f} %".rjust(width)


class Report:
    def __init__(self, plan, planner, start, end):
        self.p = plan
        self.pl = planner
        self.start = start
        self.end = end

    def within(self, day):
        return day is not None and self.start <= day <= self.end

    def months(self):
        return [(y, m) for y, m in P.months((self.start.year, self.start.month), (self.end.year, self.end.month))
                if (y, m) >= (2025, 1)]

    def month_sum(self, accounts, y, m):
        first, last = date(y, m, 1), P.month_end(y, m)
        return -self.pl.balance(accounts, last, first)

    def revenue_and_material(self):
        print("\nUmsatz und Materialquote pro Monat (CHF ohne MWST)")
        print(f"  {'Monat':<9}{'Plan':>12}{'Drehbuch':>12}{'Abw.':>8}{'Material':>12}{'Quote':>8}")
        total = target = material = Decimal("0")
        for y, m in self.months():
            rev = self.month_sum({"3000", "3400"}, y, m)
            goal = self.pl.revenue_target(y, m)
            mat = -self.month_sum({"4000", "4400"}, y, m)
            total, target, material = total + rev, target + goal, material + mat
            print(f"  {MONTH_NAMES[m - 1]} {y}{chf(rev)}{chf(goal)}{pct(rev / goal - 1, 8)}{chf(mat)}{pct(mat / rev, 8)}")
        print(f"  {'Total':<9}{chf(total)}{chf(target)}{pct(total / target - 1, 8)}{chf(material)}{pct(material / total, 8)}")

    def mix(self):
        print("\nUmsatzmix nach Warengruppe und Segment (Rechnungen im Zeitraum)")
        by_cat, by_seg, total = defaultdict(Decimal), defaultdict(Decimal), Decimal("0")
        for inv in self.p.invoices:
            if inv.opening or not self.within(inv.date):
                continue
            for line in inv.lines:
                if line.code in self.pl.articles:      # Anzahlungszeilen haben keinen Artikel
                    by_cat[self.pl.articles[line.code]["kategorie"]] += line.net
                total += line.net
            by_seg[inv.customer["segment"]] += inv.net
        target_cat = {"Velo": 30, "Bänke": 25, "Abfall": 15, "Dienstleistungen": 13, "Grün": 10,
                      "Absperrungen": 5, "Ersatzteile": 2}
        for cat, goal in target_cat.items():
            print(f"  {cat:<45}{pct(by_cat[cat] / total)}  Drehbuch {goal} %")
        for seg, share in P.SEGMENT_SHARE.items():
            print(f"  {seg:<45}{pct(by_seg[seg] / total)}  Drehbuch {share * 100:.0f} %")

    def bank(self):
        print("\nBank 1021 am Monatsende")
        for y, m in [(2024, 12)] + self.months():
            day = P.month_end(y, m)
            if (y, m) == (2024, 12):
                day = P.OPENING_ENTRY_DATE
            label = "Eröffnung" if (y, m) == (2024, 12) else f"{MONTH_NAMES[m - 1]} {y}"
            print(f"  {label:<10}{chf(self.pl.balance({P.ACC_BANK}, day))}")
        days = sorted({d for d, acc, _, _ in self.p.ledger if acc == P.ACC_BANK and d <= self.end})
        low = min(((self.pl.balance({P.ACC_BANK}, d), d) for d in days))
        print(f"  Tiefster Stand: {chf(low[0], 0)} am {low[1]:%d.%m.%Y}" + ("  ← IM MINUS" if low[0] < 0 else ""))

    def transit(self):
        print("\nÜbergangskonto 1099")
        print(f"  am 31.12.2024 (offene Posten erfasst): {chf(self.pl.balance({P.ACC_TRANSIT}, date(2024, 12, 31)), 0)}")
        print(f"  nach der Eröffnungsbuchung {P.OPENING_ENTRY_DATE:%d.%m.%Y}: "
              f"{chf(self.pl.balance({P.ACC_TRANSIT}, P.OPENING_ENTRY_DATE), 0)}")
        print(f"  am {self.end:%d.%m.%Y}: {chf(self.pl.balance({P.ACC_TRANSIT}, self.end), 0)}")
        j = next(j for j in self.p.journals if j.kind == "eroeffnung")
        print("  Eröffnungsbuchung:")
        for account, amount in j.lines:
            side = "Soll" if amount > 0 else "Haben"
            print(f"    {account}  {side:<6}{chf(abs(amount))}")

    def vat(self):
        print("\nMWST-Zahlungen an die ESTV")
        for j in sorted((j for j in self.p.journals if j.kind == "mwst" and self.within(j.date)), key=lambda j: j.date):
            lines = dict(j.lines)
            print(f"  {j.date:%d.%m.%Y}  {j.ref:<32} Umsatzsteuer {chf(lines[P.ACC_VAT_DUE], 9)}"
                  f"  Vorsteuer {chf(-lines[P.ACC_VST_MAT] - lines[P.ACC_VST_OTHER], 8)}"
                  f"  Zahlung {chf(-lines[P.ACC_BANK], 9)}")
        for j in (j for j in self.p.journals if j.kind == "steuerzahlung" and self.within(j.date)):
            print(f"  {j.date:%d.%m.%Y}  {j.ref:<32} {chf(-dict(j.lines)[P.ACC_BANK], 9)}")

    def payment_days(self):
        print("\nZahlungsdauer pro Segment (Rechnungen bezahlt im Zeitraum, ohne offene Posten 2024)")
        days = defaultdict(list)
        for inv in self.p.invoices:
            if not inv.opening and self.within(inv.pay_date):
                days[inv.customer["segment"]].append((inv.pay_date - inv.date).days)
        for seg, goal in DREHBUCH_PAYMENT_DAYS.items():
            values = days[seg]
            avg = sum(values) / len(values) if values else 0
            print(f"  {seg:<45}{avg:6.1f} Tage  Drehbuch {goal}  ({len(values)} Rechnungen, max {max(values, default=0)})")

    def open_items(self):
        day = self.end
        print(f"\nOffene Posten per {day:%d.%m.%Y}")
        open_inv = [i for i in self.p.invoices if i.date <= day and (i.pay_date is None or i.pay_date > day)]
        open_bills = [b for b in self.p.bills if b.date <= day and (b.pay_date is None or b.pay_date > day)]
        for label, items, amount in (
            ("Debitoren", open_inv, lambda i: i.gross),
            ("Kreditoren", open_bills, lambda b: b.chf(b.gross)),
        ):
            total = sum((amount(i) for i in items), Decimal("0"))
            print(f"  {label}: {len(items)} Posten, {chf(total, 0)} CHF")
            if items:
                oldest = min(items, key=lambda i: i.date)
                name = oldest.customer["name"] if label == "Debitoren" else oldest.supplier["name"]
                overdue = (day - (oldest.due)).days
                print(f"    ältester: {oldest.date:%d.%m.%Y} {name}, {chf(amount(oldest), 0)} CHF, "
                      f"{(day - oldest.date).days} Tage alt, {max(0, overdue)} Tage überfällig")
        over90 = [i for i in open_inv if (day - i.date).days > 90]
        print(f"  Debitoren älter als 90 Tage: {len(over90)}")

    def counts(self):
        print("\nMengen im Zeitraum")
        o = self.p.orders
        rows = [
            ("Offerten erstellt", sum(1 for x in o if self.within(x.offer_date))),
            ("  davon direkt bestellt (Gartenbau)", sum(1 for x in o if self.within(x.offer_date)
                                                         and x.customer["segment"] == P.RESELLER_SEGMENT)),
            ("Aufträge bestätigt", sum(1 for x in o if self.within(x.order_date))),
            ("Offerten storniert (verloren)", sum(1 for x in o if self.within(x.cancel_date))),
            ("Kundenrechnungen", sum(1 for x in self.p.invoices if not x.opening and self.within(x.date))),
            ("Kundenrechnungen offene Posten 2024", sum(1 for x in self.p.invoices if x.opening and x.date <= self.end)),
            ("Bestellungen Einkauf", sum(1 for x in self.p.bills if self.within(x.po_date))),
            ("Lieferantenrechnungen aus Bestellungen", sum(1 for x in self.p.bills if x.po_date and self.within(x.date))),
            ("Lieferantenrechnungen Fixkosten", sum(1 for x in self.p.bills
                                                    if not x.po_date and not x.opening and self.within(x.date))),
            ("Lieferantenrechnungen offene Posten 2024", sum(1 for x in self.p.bills if x.opening and x.date <= self.end)),
            ("Zahlungseingänge", sum(1 for x in self.p.invoices if self.within(x.pay_date))),
            ("Zahlungsausgänge", sum(1 for x in self.p.bills if self.within(x.pay_date))),
            ("Journalbuchungen", sum(1 for x in self.p.journals if self.within(x.date))),
        ]
        for label, n in rows:
            print(f"  {label:<45}{n:>6}")
        won = sum(1 for x in o if self.within(x.offer_date) and x.won
                  and x.customer["segment"] != P.RESELLER_SEGMENT)
        offers = sum(1 for x in o if self.within(x.offer_date) and x.customer["segment"] != P.RESELLER_SEGMENT)
        print(f"  Erfolgsquote Offerten ohne Gartenbau: {pct(Decimal(won) / offers, 0)} (Drehbuch rund 40 %)")
        kinds = defaultdict(int)
        for j in self.p.journals:
            if self.within(j.date):
                kinds[j.kind] += 1
        print("  Journalbuchungen nach Art: " + ", ".join(f"{k} {v}" for k, v in kinds.items()))

    def run(self):
        print(f"TROCKENLAUF {self.start:%d.%m.%Y} bis {self.end:%d.%m.%Y}, Startwert {P.SEED}. Odoo wird nicht angefasst.")
        self.revenue_and_material()
        self.mix()
        self.bank()
        self.transit()
        self.vat()
        self.payment_days()
        self.open_items()
        self.counts()
        self.events()

    def events(self):
        from writer import build_events
        kinds = defaultdict(int)
        for event in build_events(self.p, self.start, self.end):
            kinds[event[3]] += 1
        print("\nSchreibschritte im Zeitraum (so würde --schreiben arbeiten)")
        for kind, n in kinds.items():
            print(f"  {kind:<18}{n:>6}")
        print(f"  {'total':<18}{sum(kinds.values()):>6}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bis", type=date.fromisoformat)
    parser.add_argument("--ab", type=date.fromisoformat)
    parser.add_argument("--schreiben", action="store_true")
    parser.add_argument("--kontrolle", action="store_true")
    args = parser.parse_args()
    start = args.ab or date(2024, 1, 1)   # erste Offerten entstehen im Herbst 2024
    end = args.bis or P.END
    planner = P.Planner()
    plan = planner.build()
    if not (args.schreiben or args.kontrolle):
        if args.ab and args.ab > P.CUTOFF:
            from bericht4 import Report4
            Report4(planner).run()
        else:
            Report(plan, planner, start, end).run()
        return

    from odoo_client import OdooClient
    client = OdooClient()
    client.login()
    if args.schreiben:
        from writer import Writer, build_events
        events = build_events(plan, start, end)
        print(f"SCHREIBEN {start:%d.%m.%Y} bis {end:%d.%m.%Y}: {len(events)} Schritte")
        Writer(client, plan, planner).run(events)
    from kontrolle import run_check
    run_check(client, planner, end)


if __name__ == "__main__":
    main()
