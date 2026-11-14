"""Prüffälle P1 bis P5 als Schichten auf dem Grundgeschäft (tests/prueffaelle.md).

Die Schichten greifen nur ab September 2025 ein. Bereits geschriebene Belege bis 31.8.2025
bleiben unverändert; der Trockenlauf prüft das mit einem Vergleich gegen den Plan ohne Schichten.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import plan as P

# P1: Stahlcenter +25 % ab April 2026, eigene Stahlartikel +6 % ab Juli 2026
STEEL_SUPPLIER = "Stahlcenter Limmat AG"
STEEL_PURCHASE_FROM = date(2026, 4, 1)
STEEL_PURCHASE_FACTOR = Decimal("1.25")
STEEL_SALE_FROM = date(2026, 7, 1)
STEEL_SALE_FACTOR = Decimal("1.06")

# P2: Rietli zahlt immer später. Zahlungsdauer nach Rechnungsmonat, None = bleibt offen
RIETLI = "Rietli Immobilien AG"
RIETLI_DELAY = [
    ((2025, 9), (2025, 10), 45),
    ((2025, 11), (2025, 12), 52),
    ((2026, 1), (2026, 2), 60),
    ((2026, 3), (2026, 3), 95),
    ((2026, 4), (2026, 4), 110),
    ((2026, 5), (2026, 12), None),
]
# Rietli-Rechnungen 2026, Bruttobetrag in CHF (ersetzen die zufälligen Rietli-Aufträge 2026)
RIETLI_2026 = {1: 11_000, 2: 10_000, 3: 9_000, 4: 8_000, 5: 14_000, 6: 13_000,
               7: 5_000, 8: 3_500, 9: 3_000, 10: 2_500}

# P3: Grossprojekt Bahnhofplatz der Stadt Seefeld, netto CHF 186'000
SEEFELD = "Stadt Seefeld"
SEEFELD_WEIGHT_2026 = 1.5       # Budget der Stadt fliesst 2026 ins Projekt, normales Geschäft wie im Vorjahr
PROJECT_KEY = "P3-SEEFELD"
PROJECT_REF = "Projekt Bahnhofplatz, Submission 2026-01"
PROJECT_LINES = [("VE-200", 3), ("VE-100", 2), ("BA-200", 14), ("AB-300", 6), ("AB-110", 10), ("PO-020", 24),
                 ("GR-200", 6), ("VE-010", 20), ("DL-030", 33), ("DL-020", 8), ("DL-010", 100), ("DL-100", 16)]
PROJECT_OFFER = date(2026, 2, 12)
PROJECT_ORDER = date(2026, 4, 21)
PROJECT_DOWNPAYMENT = (date(2026, 6, 15), Decimal("40"))
PROJECT_FINAL = date(2026, 9, 18)
# Material nach Baufortschritt: Anteil am Projektmaterial pro Monat
PROJECT_MATERIAL = {(2026, 5): Decimal("0.20"), (2026, 6): Decimal("0.20"),
                    (2026, 7): Decimal("0.25"), (2026, 8): Decimal("0.35")}

# P4: Schulen sparen 2026, Hinterberg am stärksten
SCHOOLS = "Schulgemeinden"
SCHOOLS_FACTOR_2026 = 0.4
HINTERBERG = "Schulgemeinde Hinterberg"
HINTERBERG_WEIGHT_2026 = 0.25

# P5: doppelt erfasste und bezahlte Rechnung der Pulverbeschichtung Glatttal
POWDER = "Pulverbeschichtung Glatttal AG"
DUPLICATE_GROSS = Decimal("8640.00")
DUPLICATE_QTY = Decimal("231")          # m² Sonderfarbe à 34.60 = 7'992.60 netto + 647.40 MWST = 8'640.00
DUPLICATE_PRICE = Decimal("34.60")
DUPLICATE_REPLACES = Decimal("307")     # m² der normalen Juni-Lieferung, die der Sonderauftrag ersetzt
DUPLICATE_DATE = date(2026, 6, 12)
DUPLICATE_REFS = ("PB-2026-0613", "PB 2026 613")
DUPLICATE_PAY = (date(2026, 7, 10), date(2026, 7, 14))


@dataclass
class PriceChange:
    key: str
    date: date
    kind: str               # "supplier_price" oder "list_price"
    prices: dict            # Artikelcode: neuer Preis


class Layers:
    def __init__(self, planner):
        self.pl = planner
        self.price_changes = []

    # --- Hooks während der Auftragsplanung -----------------------------

    def segment_factor(self, year, month, segment):
        return SCHOOLS_FACTOR_2026 if segment == SCHOOLS and year == 2026 else 1.0

    def customers(self, year, month, segment, customers):
        if year < 2026:
            return customers
        result = []
        for c in customers:
            if c["name"] == RIETLI:
                continue        # 2026: Rietli nur noch über P2
            if c["name"] == HINTERBERG:
                c = {**c, "gewicht": HINTERBERG_WEIGHT_2026}
            if c["name"] == SEEFELD:
                c = {**c, "gewicht": SEEFELD_WEIGHT_2026}
            result.append(c)
        return result

    def scripted_orders(self, year, month, segment):
        if year != 2026 or segment != "Immobilienverwaltungen und Genossenschaften" or month not in RIETLI_2026:
            return []
        r = P.rng("p2", year, month)
        customer = self.pl.customer(RIETLI)
        net = (Decimal(RIETLI_2026[month]) / (1 + P.VAT_RATE)).quantize(P.CENT)
        last = 26 if month == 6 else 28           # Juni-Rechnung muss per 31.10. über 90 Tage überfällig sein
        day = r.choice(P.workdays(year, month, 5, last))
        order = self.pl.make_order(r, f"{year % 100:02d}{month:02d}-RIETLI", segment, customer, net, day,
                                   lines=self.rietli_lines(net))
        return [float(order.net)]

    def rietli_lines(self, net):
        """Velo- und Abfallartikel für eine Siedlung, nahe am Zielbetrag (keine Zufallsmengen)."""
        lines, rest = [], net
        for code, share in (("VE-050", Decimal("0.5")), ("AB-110", Decimal("0.6")), ("VE-010", Decimal("0.9"))):
            qty = int(rest * share / self.pl.articles[code]["verkaufspreis"])
            if qty:
                lines.append(self.pl.sale_line(code, qty))
                rest -= lines[-1].net
        lines.append(self.pl.sale_line("DL-020", 1))
        rest -= lines[-1].net
        hours = max(1, int((rest / Decimal("118")).to_integral_value()))
        lines.append(self.pl.sale_line("DL-010", hours))
        return lines

    # --- Nach der Auftragsplanung --------------------------------------

    def after_orders(self):
        self.price_changes.append(PriceChange(
            "P1-EK", STEEL_PURCHASE_FROM, "supplier_price",
            {c: (self.pl.articles[c]["einkaufspreis"] * STEEL_PURCHASE_FACTOR).quantize(P.CENT)
             for c in P.SUPPLIER_PRODUCTS[STEEL_SUPPLIER]}))
        self.steel_sale_prices()
        self.seefeld_project()
        self.rietli_payments()

    def steel_sale_prices(self):
        steel = {c: a for c, a in self.pl.articles.items() if a["stahlartikel"]}
        new = {c: (a["verkaufspreis"] * STEEL_SALE_FACTOR).quantize(P.CENT) for c, a in steel.items()}
        self.price_changes.append(PriceChange("P1-VK", STEEL_SALE_FROM, "list_price", new))
        for order in self.pl.plan.orders:
            if order.offer_date >= STEEL_SALE_FROM and order.key != PROJECT_KEY:
                for line in order.lines:
                    if line.code in new:
                        line.price = new[line.code]

    def seefeld_project(self):
        customer = self.pl.customer(SEEFELD)
        lines = [self.pl.sale_line(code, qty) for code, qty in PROJECT_LINES]
        order = P.Order(PROJECT_KEY, customer, PROJECT_REF, PROJECT_OFFER, True, lines,
                        order_date=PROJECT_ORDER, invoice_date=PROJECT_FINAL)
        self.pl.plan.orders.append(order)

        day, percent = PROJECT_DOWNPAYMENT
        dp_lines = []
        for account in ("3000", "3400"):
            base = sum((l.net for l in lines if l.account == account), Decimal("0"))
            dp_lines.append(P.Line("ANZ", Decimal("1"), (base * percent / 100).quantize(P.CENT), account=account,
                                   tax="ust", label=f"Anzahlung {percent:.0f} %"))
        downpayment = P.Invoice(f"R-{PROJECT_KEY}-ANZ", customer, day, dp_lines, order_key=PROJECT_KEY)
        downpayment.kind, downpayment.percent = "downpayment", percent
        final_lines = list(lines) + [P.Line("ANZ", Decimal("1"), -l.price, account=l.account, tax="ust",
                                            label=l.label) for l in dp_lines]
        final = P.Invoice(f"R-{PROJECT_KEY}-SCHLUSS", customer, PROJECT_FINAL, final_lines, order_key=PROJECT_KEY)
        final.kind = "final"
        for inv in (downpayment, final):
            inv.pay_date = P.next_workday(inv.date + timedelta(days=customer["zahlt_nach_tagen"]))
            self.pl.plan.invoices.append(inv)

    def rietli_payments(self):
        for inv in self.pl.plan.invoices:
            if inv.customer["name"] != RIETLI or inv.date < P.CUTOFF + timedelta(days=1):
                continue
            for start, end, days in RIETLI_DELAY:
                if start <= (inv.date.year, inv.date.month) <= end:
                    if days is None:
                        inv.pay_date = None
                    else:
                        jitter = P.rng("p2-pay", inv.key).randint(-3, 3)
                        inv.pay_date = P.next_workday(inv.date + timedelta(days=days + jitter))

    # --- Einkauf --------------------------------------------------------

    def purchase_price_factor(self, supplier, po_day):
        if supplier["name"] == STEEL_SUPPLIER and po_day >= STEEL_PURCHASE_FROM:
            return STEEL_PURCHASE_FACTOR
        return Decimal("1")

    def is_project_invoice(self, inv):
        return inv.order_key == PROJECT_KEY

    def project_material_total(self):
        order = next(o for o in self.pl.plan.orders if o.key == PROJECT_KEY)
        return sum((l.qty * self.pl.articles[l.code]["materialkosten"] for l in order.lines),
                   Decimal("0")) * P.MATERIAL_FACTOR

    def after_purchases(self, year, month):
        if (year, month) in PROJECT_MATERIAL:
            self.project_purchases(year, month)
        if (year, month) == (DUPLICATE_DATE.year, DUPLICATE_DATE.month):
            self.duplicate_bill()

    def project_purchases(self, year, month):
        r = P.rng("p3-material", year, month)
        amount = self.project_material_total() * PROJECT_MATERIAL[(year, month)]
        material = {n: s for n, s in self.pl.suppliers.items() if s["rolle"] == "material"}
        scale = sum(s["anteil_einkauf"] for s in material.values())
        for name, supplier in material.items():
            po_day = r.choice(P.workdays(year, month, 3, 14))
            bill_day = P.next_workday(po_day + timedelta(days=r.randint(4, 10)))
            self.pl.add_purchase_bill(r, supplier, amount * supplier["anteil_einkauf"] / scale, po_day, bill_day,
                                      origin=f"Projekt Bahnhofplatz {po_day:%y%m%d}")

    def finalize(self):
        self.renumber_powder_2026()

    def renumber_powder_2026(self):
        """Rechnungsnummern der Pulverbeschichtung 2026 laufen so, dass PB-2026-0613 auf den 12. Juni fällt."""
        anchor = DUPLICATE_DATE.timetuple().tm_yday
        number = int(DUPLICATE_REFS[0].split("-")[-1])
        last = 0
        for b in sorted((b for b in self.pl.plan.bills if b.supplier["name"] == POWDER and b.date.year == 2026
                         and b.ref not in DUPLICATE_REFS), key=lambda b: (b.date, b.key)):
            n = max(last + 1, round(b.date.timetuple().tm_yday * number / anchor))
            if n == number:
                n += 1
            b.ref, last = f"PB-2026-{n:04d}", n

    def duplicate_bill(self):
        supplier = self.pl.suppliers[POWDER]
        # Die echte Rechnung ersetzt einen Teil der normalen Juni-Lieferung, der Materialaufwand bleibt gleich
        regular = next(b for b in self.pl.plan.bills if b.supplier["name"] == POWDER and b.po_date
                       and (b.date.year, b.date.month) == (2026, 6) and not b.origin)
        regular.lines[0].qty -= DUPLICATE_REPLACES
        for i, (ref, pay) in enumerate(zip(DUPLICATE_REFS, DUPLICATE_PAY)):
            line = P.Line("EK-PULVER", DUPLICATE_QTY, DUPLICATE_PRICE, account="4400", tax="vst_material",
                          label="Pulverbeschichtung RAL 7016, Sonderauftrag")
            po_day = P.prev_workday(DUPLICATE_DATE - timedelta(days=7)) if i == 0 else None
            bill = P.Bill(f"E-P5-{i + 1}", supplier, DUPLICATE_DATE, ref, [line], po_date=po_day)
            bill.origin = f"Disposition {po_day:%y%m%d}" if po_day else None
            bill.due = DUPLICATE_DATE + timedelta(days=30)
            bill.pay_date = pay
            bill.observe_duplicate = i == 1
            self.pl.plan.bills.append(bill)
