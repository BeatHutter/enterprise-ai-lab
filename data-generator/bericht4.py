"""Trockenlauf-Bericht für Etappe 4: Jahr 2025, Jahreswechsel, Prüffälle P1 bis P5."""

from collections import defaultdict
from datetime import date
from decimal import Decimal

import plan as P
import schichten as S
from writer import build_events

REV, MAT, PERS = {"3000", "3400"}, {"4000", "4400"}, {"5000", "5700"}
DREHBUCH_2025 = {"Umsatz": 4_200_000, "Material": 1_680_000, "Personal": 1_760_000, "Übriger Aufwand": 450_000,
                 "EBITDA": 310_000, "Abschreibungen": 80_000, "Steuern": 45_000, "Reingewinn": 185_000}
JAN_OCT = {2025: (date(2025, 1, 1), date(2025, 10, 31)), 2026: (date(2026, 1, 1), date(2026, 10, 31))}


def chf(value, width=12):
    return f"{Decimal(value):,.0f}".replace(",", "'").rjust(width)


def pct(value, width=8):
    return f"{value * 100:+.1f} %".rjust(width) if value is not None else "".rjust(width)


class Report4:
    def __init__(self, planner):
        self.pl = planner
        self.p = planner.plan

    def sum(self, accounts, since, until):
        return self.pl.balance(accounts, until, since)

    def other_accounts(self):
        return {a for _, a, _, _ in self.p.ledger if a[0] == "6" and a != "6800"} | {"3806", "4906"}

    def pnl(self, since, until):
        rev = -self.sum(REV, since, until)
        mat = self.sum(MAT, since, until)
        pers = self.sum(PERS, since, until)
        other = self.sum(self.other_accounts(), since, until)
        ebitda = rev - mat - pers - other
        dep = self.sum({"6800"}, since, until)
        tax = self.sum({"8900"}, since, until)
        return {"Umsatz": rev, "Material": mat, "Personal": pers, "Übriger Aufwand": other, "EBITDA": ebitda,
                "Abschreibungen": dep, "Steuern": tax, "Reingewinn": ebitda - dep - tax}

    # --- Stabilität ----------------------------------------------------

    def stability(self):
        base = P.Planner(layers=False)
        base_plan = base.build()

        def fp(plan):
            return [(d, k, key, str(getattr(o, "gross", None) or getattr(o, "net", None) or o.lines))
                    for d, _, key, k, o in build_events(plan, date(2024, 1, 1), P.CUTOFF)]
        same = fp(base_plan) == fp(self.p)
        print(f"\nStabilität: Plan bis {P.CUTOFF:%d.%m.%Y} mit Schichten gegenüber Etappe 3: "
              f"{'identisch' if same else 'UNTERSCHIED, nicht schreiben'}")

    # --- 2025 und Jahreswechsel -----------------------------------------

    def year_2025(self):
        print("\nErfolgsrechnung 2025, ganzes Jahr (CHF)")
        actual = self.pnl(date(2025, 1, 1), date(2025, 12, 31))
        print(f"  {'Position':<18}{'Plan':>12}{'Drehbuch':>12}{'Abw.':>9}{'Anteil':>9}")
        for key, goal in DREHBUCH_2025.items():
            share = actual[key] / actual["Umsatz"] * 100
            print(f"  {key:<18}{chf(actual[key])}{chf(goal)}{pct(actual[key] / goal - 1, 9)}{share:>8.1f}%")

    def year_end(self):
        end = date(2025, 12, 31)
        print("\nPrüfpunkte Jahreswechsel (aus dem Plan, nach 4a in Odoo zu prüfen)")
        for j in self.p.journals:
            if j.date.year == 2025 and j.date.month == 12 and j.kind in ("lohn", "abschreibung", "steuer"):
                amount = sum(v for _, v in j.lines if v > 0)
                print(f"  {j.date:%d.%m.%Y}  {j.ref:<36}{chf(amount)}")
        bs = defaultdict(Decimal)
        for d, acc, amount, _ in self.p.ledger:
            if d <= end and acc[0] in "12":
                bs[acc] += amount
        assets = sum((v for a, v in bs.items() if a[0] == "1"), Decimal("0"))
        liabilities = -sum((v for a, v in bs.items() if a[0] == "2" and not a.startswith(("28", "29"))), Decimal("0"))
        equity = -sum((v for a, v in bs.items() if a.startswith(("28", "29"))), Decimal("0"))
        profit = self.pnl(date(2025, 1, 1), end)["Reingewinn"]
        print(f"  Bilanz 31.12.2025: Aktiven {chf(assets, 0)} = Fremdkapital {chf(liabilities, 0)} + Eigenkapital "
              f"{chf(equity, 0)} + Gewinn 2025 {chf(profit, 0)} → Differenz {chf(assets - liabilities - equity - profit, 0)}")
        print("  Gewinn 2025: ohne Buchung. Odoo weist ihn ab 2026 als «Unverteilte Gewinne» im Eigenkapital aus.")
        last = max(i.date for i in self.p.invoices if i.date.year == 2025)
        print(f"  Letzte Kundenrechnung 2025 am {last:%d.%m.%Y}. In 4b muss die erste 2026er RE/2026/00001 heissen.")

    # --- Prüffälle -----------------------------------------------------

    def p1(self):
        print("\nP1 Stahlcenter +25 % ab 1.4.2026, eigene Stahlartikel +6 % ab 1.7.2026")
        for pc in self.p.price_changes:
            what = "Einkaufspreis (Lieferantenpreis im Artikel)" if pc.kind == "supplier_price" else \
                "Verkaufspreis (Artikelpreis, gilt für Offerten ab diesem Tag)"
            print(f"  {pc.date:%d.%m.%Y} {what}:")
            for code, price in pc.prices.items():
                old = self.pl.articles[code]["einkaufspreis" if pc.kind == "supplier_price" else "verkaufspreis"]
                print(f"    {code:<12}{self.pl.articles[code]['name']:<42}{old:>10} → {price}")
        print("  Stahlcenter-Einkauf und Materialquote pro Monat")
        print(f"  {'Monat':<9}{'Stahlcenter':>12}{'Material':>12}{'Umsatz':>12}{'Quote':>8}")
        quarters = defaultdict(lambda: [Decimal("0"), Decimal("0")])
        for y, m in list(P.months((2025, 1), (2025, 10))) + list(P.months((2026, 1), (2026, 10))):
            first, last = date(y, m, 1), P.month_end(y, m)
            rev, mat = -self.sum(REV, first, last), self.sum(MAT, first, last)
            quarters[(y, (m - 1) // 3 + 1)][0] += rev
            quarters[(y, (m - 1) // 3 + 1)][1] += mat
            if y == 2026:
                steel = sum((b.chf(b.net) for b in self.p.bills if b.supplier["name"] == S.STEEL_SUPPLIER
                             and first <= b.date <= last), Decimal("0"))
                print(f"  {y}-{m:02d}  {chf(steel)}{chf(mat)}{chf(rev)}{mat / rev * 100:>7.1f}%")
        for (y, q), (rev, mat) in sorted(quarters.items()):
            if q <= 3:
                print(f"  Q{q} {y}: Materialquote {mat / rev * 100:.1f} %")

    def p2(self):
        print("\nP2 Rietli Immobilien AG: Rechnungen ab September 2025")
        print(f"  {'Rechnung':<26}{'Datum':>12}{'brutto':>10}{'fällig':>12}{'bezahlt':>12}{'Tage':>6}")
        end = P.END
        for inv in sorted((i for i in self.p.invoices if i.customer["name"] == S.RIETLI
                           and i.date >= date(2025, 9, 1)), key=lambda i: i.date):
            paid = f"{inv.pay_date:%d.%m.%Y}" if inv.pay_date else "offen"
            days = (inv.pay_date - inv.date).days if inv.pay_date else (end - inv.date).days
            print(f"  {inv.key:<26}{inv.date:%d.%m.%Y}{chf(inv.gross, 10)}  {inv.due:%d.%m.%Y}  {paid:>10}{days:>6}")
        buckets = defaultdict(lambda: [0, Decimal("0")])
        others_over_90 = 0
        for inv in self.p.invoices:
            if inv.date <= end and inv.pay_date is None:
                overdue = (end - inv.due).days
                if inv.customer["name"] == S.RIETLI:
                    b = "nicht fällig" if overdue <= 0 else "1-30" if overdue <= 30 else "31-60" if overdue <= 60 \
                        else "61-90" if overdue <= 90 else "über 90"
                    buckets[b][0] += 1
                    buckets[b][1] += inv.gross
                elif overdue > 90:
                    others_over_90 += 1
        total = sum((v[1] for v in buckets.values()), Decimal("0"))
        print(f"  Offen per 31.10.2026 nach Tagen überfällig: " +
              ", ".join(f"{b} {buckets[b][0]} / {chf(buckets[b][1], 0)}"
                        for b in ("nicht fällig", "1-30", "31-60", "61-90", "über 90")) + f", total {chf(total, 0)}")
        print(f"  Andere Kunden mit Posten über 90 Tage überfällig: {others_over_90}")

    def p3(self):
        print("\nP3 Stadt Seefeld, Projekt Bahnhofplatz")
        order = next(o for o in self.p.orders if o.key == S.PROJECT_KEY)
        print(f"  Offerte {order.offer_date:%d.%m.%Y}, Zuschlag (Auftrag) {order.order_date:%d.%m.%Y}, "
              f"netto {chf(order.net, 0)}, Referenz «{order.ref}»")
        for code, qty in S.PROJECT_LINES:
            line = next(l for l in order.lines if l.code == code)
            print(f"    {qty:>4} × {code:<7}{self.pl.articles[code]['name']:<44}{chf(line.net)}")
        for inv in (i for i in self.p.invoices if i.order_key == S.PROJECT_KEY):
            print(f"  {inv.kind:<12} {inv.date:%d.%m.%Y}  netto {chf(inv.net, 0)}, brutto {chf(inv.gross, 0)}, "
                  f"bezahlt {inv.pay_date:%d.%m.%Y}")
        print(f"  Projektmaterial total {chf(self.layers().project_material_total(), 0)}, eingekauft:")
        for (y, m), share in S.PROJECT_MATERIAL.items():
            bills = [b for b in self.p.bills if b.origin and b.origin.startswith("Projekt")
                     and (b.date.year, b.date.month) == (y, m)]
            print(f"    {y}-{m:02d}: {len(bills)} Bestellungen, {chf(sum((b.chf(b.net) for b in bills), Decimal('0')), 0)}"
                  f" ({share * 100:.0f} %)")
        self.revenue_compare()

    def project_revenue(self, since, until):
        return sum((i.net for i in self.p.invoices if i.order_key == S.PROJECT_KEY and since <= i.date <= until),
                   Decimal("0"))

    def customer_revenue(self, name, since, until):
        return sum((i.net for i in self.p.invoices if i.customer["name"] == name and since <= i.date <= until
                    and not i.opening), Decimal("0"))

    def revenue_compare(self):
        r25, r26 = (-self.sum(REV, *JAN_OCT[y]) for y in (2025, 2026))
        proj = self.project_revenue(*JAN_OCT[2026])
        s25, s26 = (self.customer_revenue(S.SEEFELD, *JAN_OCT[y]) for y in (2025, 2026))
        print("  Umsatz Januar bis Oktober")
        print(f"    2025 {chf(r25, 0)}, 2026 {chf(r26, 0)} → {pct(r26 / r25 - 1, 0)}")
        print(f"    2026 ohne Projekt Bahnhofplatz {chf(r26 - proj, 0)} gegenüber 2025 gesamt → {pct((r26 - proj) / r25 - 1, 0)}")
        print(f"    ohne Kunde Seefeld in beiden Jahren: 2025 {chf(r25 - s25, 0)}, 2026 {chf(r26 - s26, 0)} "
              f"→ {pct((r26 - s26) / (r25 - s25) - 1, 0)}")
        for m in (6, 9):
            first, last = date(2026, m, 1), P.month_end(2026, m)
            print(f"    {MONTHS[m]} 2026: {chf(-self.sum(REV, first, last), 0)}, davon Projekt "
                  f"{chf(self.project_revenue(first, last), 0)}; Vorjahr {chf(-self.sum(REV, date(2025, m, 1), P.month_end(2025, m)), 0)}")

    def p4(self):
        print("\nP4 Schulgemeinden, Januar bis Oktober")
        for label, filt in (("Segment Schulen", lambda i: i.customer["segment"] == S.SCHOOLS),
                            ("davon Hinterberg", lambda i: i.customer["name"] == S.HINTERBERG)):
            v = [sum((i.net for i in self.p.invoices if filt(i) and not i.opening
                      and JAN_OCT[y][0] <= i.date <= JAN_OCT[y][1]), Decimal("0")) for y in (2025, 2026)]
            print(f"  {label:<18} 2025 {chf(v[0], 0)}, 2026 {chf(v[1], 0)} → {pct(v[1] / v[0] - 1 if v[0] else None, 0)}")

    def p5(self):
        print("\nP5 Pulverbeschichtung Glatttal, doppelt erfasst")
        for b in (b for b in self.p.bills if b.key.startswith("E-P5")):
            src = f"aus Bestellung ({b.origin})" if b.po_date else "ohne Bestellung, von Hand erfasst"
            print(f"  Referenz «{b.ref}», Rechnungsdatum {b.date:%d.%m.%Y}, brutto {b.gross}, {src}, "
                  f"bezahlt {b.pay_date:%d.%m.%Y}")
        print("  Erwartung Duplikatwarnung: keine. Odoo vergleicht nur exakt gleiche Referenzen im selben Jahr.")

    def overall(self):
        print("\nGesamtbild Januar bis Oktober (CHF)")
        proj_mat = sum((b.chf(b.net) for b in self.p.bills if b.origin and b.origin.startswith("Projekt")),
                       Decimal("0"))
        e25 = self.pnl(*JAN_OCT[2025])["EBITDA"]
        e26 = self.pnl(*JAN_OCT[2026])["EBITDA"]
        proj = self.project_revenue(*JAN_OCT[2026])
        print(f"  EBITDA 2025 {chf(e25, 0)}")
        print(f"  EBITDA 2026 {chf(e26, 0)} mit Seefeld, {chf(e26 - proj + proj_mat, 0)} ohne Projekt "
              f"(Umsatz {chf(proj, 0)} und Material {chf(proj_mat, 0)} herausgerechnet)")
        print(f"  Hochrechnung aufs Jahr (×12/10, grob): mit {chf(e26 * 12 / 10, 0)}, ohne {chf((e26 - proj + proj_mat) * 12 / 10, 0)}")

    def quarter_ratio(self, y, q):
        first, last = date(y, 3 * q - 2, 1), P.month_end(y, 3 * q)
        return self.sum(MAT, first, last) / -self.sum(REV, first, last)

    def targets(self):
        print("\nVorschlag Zielwerte für tests/prueffaelle.md (Januar bis Oktober, Toleranz)")
        r25, r26 = (-self.sum(REV, *JAN_OCT[y]) for y in (2025, 2026))
        proj = self.project_revenue(*JAN_OCT[2026])
        school = [sum((i.net for i in self.p.invoices if i.customer["segment"] == S.SCHOOLS and not i.opening
                       and JAN_OCT[y][0] <= i.date <= JAN_OCT[y][1]), Decimal("0")) for y in (2025, 2026)]
        open_r = [i for i in self.p.invoices if i.customer["name"] == S.RIETLI and i.pay_date is None and i.date <= P.END]
        over = sum((i.gross for i in open_r if (P.END - i.due).days > 90), Decimal("0"))
        print(f"  P1 Materialquote Q1 2026 {self.quarter_ratio(2026, 1) * 100:.1f} % ± 1.0, "
              f"Q2 2026 {self.quarter_ratio(2026, 2) * 100:.1f} % ± 1.0 (Q2 2025: {self.quarter_ratio(2025, 2) * 100:.1f} %)")
        print(f"  P2 Rietli offen {chf(sum((i.gross for i in open_r), Decimal('0')), 0)} ± 2'000, davon über 90 Tage "
              f"überfällig {chf(over, 0)} ± 2'000; einziger Kunde über 90 Tage")
        print(f"  P3 Projekt 186'000 netto exakt; Umsatz ohne Projekt {pct((r26 - proj) / r25 - 1, 0)} ± 1.5 Punkte")
        print(f"  P4 Segment Schulen {pct(school[1] / school[0] - 1, 0)} ± 5 Punkte")
        print("  P5 zwei Rechnungen à 8'640.00 brutto exakt, beide bezahlt")

    def counts(self):
        print("\nSchreibschritte")
        for label, start, end in (("4a", date(2025, 9, 1), date(2025, 12, 31)),
                                  ("4b", date(2026, 1, 1), date(2026, 10, 31))):
            kinds = defaultdict(int)
            for e in build_events(self.p, start, end):
                kinds[e[3]] += 1
            print(f"  {label} {start:%d.%m.%Y}–{end:%d.%m.%Y}: total {sum(kinds.values())}  ("
                  + ", ".join(f"{k} {v}" for k, v in kinds.items()) + ")")
        days = sorted({d for d, a, _, _ in self.p.ledger if a == P.ACC_BANK})
        low = min((self.pl.balance({P.ACC_BANK}, d), d) for d in days)
        print(f"  Bank: tiefster Stand {chf(low[0], 0)} am {low[1]:%d.%m.%Y}, "
              f"31.12.2025 {chf(self.pl.balance({P.ACC_BANK}, date(2025, 12, 31)), 0)}, "
              f"31.10.2026 {chf(self.pl.balance({P.ACC_BANK}, P.END), 0)}")

    def layers(self):
        return self.pl.layers

    def run(self):
        print(f"TROCKENLAUF ETAPPE 4, Startwert {P.SEED}. Odoo wird nicht angefasst.")
        self.stability()
        self.year_2025()
        self.year_end()
        self.p1()
        self.p2()
        self.p3()
        self.p4()
        self.p5()
        self.overall()
        self.targets()
        self.counts()


MONTHS = {6: "Juni", 9: "September"}
