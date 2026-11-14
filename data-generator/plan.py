"""Plant die Geschichte der Muster AG, ohne Odoo.

Alles hängt nur vom Startwert SEED und den CSV-Dateien ab. Jeder Zufall kommt aus einem
eigenen Strom pro Zweck und Monat (rng("orders", 2025, 3) usw.). Spätere Änderungen, etwa
die Prüffälle in Etappe 4, verschieben deshalb nichts in früheren Monaten.

Vorzeichen im Hauptbuch: positiv = Soll, negativ = Haben.
"""

import calendar
import math
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from master_data import RESELLER_SEGMENT, load_articles, load_customers, load_eur_rates, load_suppliers

SEED = 20250101
CUTOFF = date(2025, 8, 31)          # Etappe 3 schreibt bis hier, Etappe 4 ab dem Folgetag
END = date(2026, 10, 31)            # letzter Tag der Geschichte
OPENING_ENTRY_DATE = date(2024, 12, 31)   # wie Odoo: Tag vor dem Eröffnungsdatum 1.1.2025

CENT = Decimal("0.01")
VAT_RATE = Decimal("0.081")

# Umsatz 2025 in CHF ohne MWST (Drehbuch), 2026 mit 3 % Wachstum
REVENUE_2025 = {1: 168_000, 2: 210_000, 3: 336_000, 4: 420_000, 5: 462_000, 6: 462_000,
                7: 294_000, 8: 252_000, 9: 378_000, 10: 378_000, 11: 336_000, 12: 504_000}
GROWTH_2026 = Decimal("1.03")

SEGMENT_SHARE = {
    "Gemeinden und Städte": Decimal("0.45"),
    "Immobilienverwaltungen und Genossenschaften": Decimal("0.20"),
    "Garten- und Landschaftsbau": Decimal("0.17"),
    "Schulgemeinden": Decimal("0.10"),
    "Hotels und Bergbahnen": Decimal("0.08"),
}
# Auftragsgrösse netto in CHF (Drehbuch), Gartenbau: Standardartikel
ORDER_SIZE = {
    "Gemeinden und Städte": (5_000, 60_000),
    "Immobilienverwaltungen und Genossenschaften": (2_000, 30_000),
    "Garten- und Landschaftsbau": (1_200, 9_000),
    "Schulgemeinden": (3_000, 25_000),
    "Hotels und Bergbahnen": (2_000, 15_000),
}
# Tage vom Auftrag bis zur Rechnung (Fertigung und Montage)
LEAD_DAYS = {
    "Gemeinden und Städte": (21, 56),
    "Immobilienverwaltungen und Genossenschaften": (21, 49),
    "Garten- und Landschaftsbau": (5, 20),
    "Schulgemeinden": (21, 49),
    "Hotels und Bergbahnen": (21, 42),
}
REF_PREFIX = {
    "Gemeinden und Städte": "Bauamt",
    "Immobilienverwaltungen und Genossenschaften": "Auftrag",
    "Garten- und Landschaftsbau": "Bestellung",
    "Schulgemeinden": "Schulpflege",
    "Hotels und Bergbahnen": "Bestellung",
}
OFFER_DAYS = (7, 35)                # Offerte bis Auftrag
LOST_CANCEL_DAYS = 60               # verlorene Offerten werden danach storniert
WIN_RATE = Decimal("0.4")           # nur zur Kontrolle im Bericht

# Warengruppen-Gewichte pro Segment, abgestimmt auf den Umsatzmix im Drehbuch
CATEGORY_WEIGHTS = {
    "Gemeinden und Städte": {"Velo": 30, "Bänke": 35, "Abfall": 15, "Grün": 10, "Absperrungen": 8, "Ersatzteile": 2},
    "Immobilienverwaltungen und Genossenschaften": {"Velo": 55, "Bänke": 20, "Abfall": 15, "Grün": 8, "Absperrungen": 2},
    "Garten- und Landschaftsbau": {"Velo": 15, "Bänke": 35, "Abfall": 10, "Grün": 30, "Absperrungen": 5, "Ersatzteile": 5},
    "Schulgemeinden": {"Velo": 45, "Bänke": 40, "Abfall": 5, "Grün": 5, "Absperrungen": 3, "Ersatzteile": 2},
    "Hotels und Bergbahnen": {"Velo": 10, "Bänke": 50, "Abfall": 20, "Grün": 15, "Absperrungen": 3, "Ersatzteile": 2},
}
PRODUCT_WEIGHTS = {
    "BA-100": 35, "BA-110": 20, "BA-120": 20, "BA-200": 15, "BA-300": 10,
    "AB-060": 30, "AB-110": 35, "AB-300": 15, "AB-400": 20,
    "VE-010": 25, "VE-050": 30, "VE-100": 30, "VE-200": 15,
    "GR-080": 35, "GR-120": 35, "GR-200": 30,
    "PO-010": 35, "PO-020": 35, "PO-100": 30,
    "ET-100": 50, "ET-200": 50,
}
# Fundamente pro Stück (DL-030)
FOUNDATIONS = {"VE-100": 2, "VE-200": 3, "BA-200": 1, "AB-300": 1}
MONTAGE_SHARE = Decimal("0.11")     # Montagestunden als Anteil am Warenwert

# Kleinmaterial, Verschnitt und Fremdleistungen über den Standardkosten der Artikel
MATERIAL_FACTOR = Decimal("1.125")
# Aufteilung innerhalb eines Lieferanten auf seine Einkaufsartikel
SUPPLIER_PRODUCTS = {
    "Stahlcenter Limmat AG": {"EK-ST-ROHR": Decimal("0.6"), "EK-ST-BLECH": Decimal("0.4")},
    "Beton Fertig AG": {"EK-BETON": Decimal("0.7"), "EK-FUNDAMENT": Decimal("0.3")},
}
SUPPLIER_REF = {
    "Stahlcenter Limmat AG": "SCL", "Holzwerk Tirol GmbH": "HT", "Pulverbeschichtung Glatttal AG": "PB",
    "Corten Metall GmbH": "CM", "Verzinkerei Furttal AG": "VF", "Glas Wyss AG": "GW",
    "Beton Fertig AG": "BF", "Befestigungstechnik Huber AG": "BH", "Transporte Keller AG": "TK",
    "Kunststoffwerk Aare AG": "KA", "Werkhof Immobilien AG": "WI", "Elektrizitätswerk Talbach": "EWT",
    "Fahrzeugleasing Limmattal AG": "FL", "Datenwerk Informatik GmbH": "DW",
    "Securia Versicherungen AG": "SV", "Treuhand und Revision Kalt AG": "TRK",
    "Kommunalmesse Schweiz GmbH": "KM", "Werkstattbedarf Brändli AG": "WB",
}

# Fixkosten (Drehbuch)
WAGES = Decimal("114000")
SOCIAL = Decimal("21000")
RENT = Decimal("14500")
LEASING = Decimal("2400")
IT = Decimal("1800")
ENERGY = {1: 4500, 2: 4300, 3: 3800, 4: 3200, 5: 2800, 6: 2500, 7: 2500, 8: 2500, 9: 2800, 10: 3300, 11: 4000, 12: 4400}
MAINTENANCE = (9_000, 11_000)
INSURANCE = Decimal("18000")        # Januar
AUDIT = Decimal("9000")             # März
FAIR = (date(2025, 6, 1), Decimal("25000"))
DEPRECIATION = Decimal("80000")     # Dezember
INCOME_TAX = Decimal("45000")       # Rückstellung im Dezember, Zahlung im Juni des Folgejahres

# Eröffnungsbilanz (mit Beat abgestimmt)
OPENING = {
    "bank": Decimal("420000"), "stock": Decimal("150000"), "machines": Decimal("480000"),
    "receivables": Decimal("520000"), "payables": Decimal("160000"),
    "vat": Decimal("60000"), "tax_provision": Decimal("45000"),
    "share_capital": Decimal("200000"), "reserves": Decimal("100000"),
}

ACC_BANK, ACC_TRANSIT, ACC_RECEIVABLE, ACC_PAYABLE = "1021", "1099", "1100", "2000"
ACC_VAT_DUE, ACC_VST_MAT, ACC_VST_OTHER = "2200", "1170", "1171"
ACC_FX_GAIN, ACC_FX_LOSS = "3806", "4906"


# --- Hilfen -------------------------------------------------------------

def rng(*parts):
    return random.Random("|".join(str(p) for p in (SEED,) + parts))


def money(value):
    return Decimal(value).quantize(CENT, ROUND_HALF_UP)


# Feiertage Kanton Zürich
HOLIDAYS = {date(y, m, d) for y in (2024, 2025, 2026) for m, d in ((1, 1), (1, 2), (5, 1), (8, 1), (12, 25), (12, 26))} | {
    date(2025, 4, 18), date(2025, 4, 21), date(2025, 5, 29), date(2025, 6, 9),
    date(2026, 4, 3), date(2026, 4, 6), date(2026, 5, 14), date(2026, 5, 25),
}


def is_workday(day):
    return day.weekday() < 5 and day not in HOLIDAYS


def next_workday(day):
    while not is_workday(day):
        day += timedelta(days=1)
    return day


def prev_workday(day):
    while not is_workday(day):
        day -= timedelta(days=1)
    return day


def month_end(year, month):
    return date(year, month, calendar.monthrange(year, month)[1])


def workdays(year, month, first=1, last=31):
    last = min(last, calendar.monthrange(year, month)[1])
    return [date(year, month, d) for d in range(first, last + 1) if is_workday(date(year, month, d))]


def months(start, end):
    y, m = start
    while (y, m) <= end:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def weighted(r, weights):
    keys = list(weights)
    return r.choices(keys, weights=[float(weights[k]) for k in keys])[0]


def loguniform(r, low, high):
    return math.exp(r.uniform(math.log(low), math.log(high)))


# --- Datensätze ---------------------------------------------------------

@dataclass
class Line:
    code: str
    qty: Decimal
    price: Decimal
    discount: Decimal = Decimal("0")
    account: str = ""
    tax: str = ""                   # "ust", "vst_material", "vst_uebrig" oder ""
    label: str = ""

    @property
    def net(self):
        return money(self.qty * self.price * (1 - self.discount / 100))


@dataclass
class Order:
    key: str
    customer: dict
    ref: str
    offer_date: date
    won: bool
    lines: list
    order_date: date = None
    invoice_date: date = None
    cancel_date: date = None

    @property
    def net(self):
        return sum((l.net for l in self.lines), Decimal("0"))


@dataclass
class Invoice:
    key: str
    customer: dict
    date: date
    lines: list
    order_key: str = None
    opening: bool = False
    pay_date: date = None

    @property
    def net(self):
        return sum((l.net for l in self.lines), Decimal("0"))

    @property
    def tax(self):
        return sum((money(l.net * VAT_RATE) for l in self.lines if l.tax), Decimal("0"))

    @property
    def gross(self):
        return self.net + self.tax

    @property
    def due(self):
        return self.date + timedelta(days=30)


@dataclass
class Bill:
    key: str
    supplier: dict
    date: date
    ref: str
    lines: list
    currency: str = "CHF"
    rate: Decimal = Decimal("1")    # CHF pro EUR am Rechnungsdatum
    po_date: date = None            # gesetzt bei Bestellungen
    origin: str = None              # Quelldokument der Bestellung, Vorgabe «Disposition JJMMTT»
    opening: bool = False
    due: date = None
    pay_date: date = None

    @property
    def net(self):
        return sum((l.net for l in self.lines), Decimal("0"))

    @property
    def tax(self):
        return sum((money(l.net * VAT_RATE) for l in self.lines if l.tax), Decimal("0"))

    @property
    def gross(self):
        return self.net + self.tax

    def chf(self, amount, rate=None):
        return money(amount * (rate or self.rate)) if self.currency == "EUR" else amount


@dataclass
class Journal:
    key: str
    date: date
    ref: str
    lines: list                     # [(Konto, Betrag)], positiv = Soll
    kind: str = ""


@dataclass
class Plan:
    orders: list = field(default_factory=list)
    invoices: list = field(default_factory=list)
    bills: list = field(default_factory=list)
    journals: list = field(default_factory=list)
    price_changes: list = field(default_factory=list)
    ledger: list = field(default_factory=list)  # (Datum, Konto, Betrag, Quelle)


# --- Planer -------------------------------------------------------------

class Planner:
    def __init__(self, layers=True):
        self.articles = {a["code"]: a for a in load_articles()}
        self.customers = load_customers()
        self.suppliers = {s["name"]: s for s in load_suppliers()}
        self.rates = sorted((date.fromisoformat(r["gueltig_ab"]), r["chf_pro_eur"]) for r in load_eur_rates())
        self.by_segment = {}
        for c in self.customers:
            self.by_segment.setdefault(c["segment"], []).append(c)
        self.by_category = {}
        for a in self.articles.values():
            if a["art"] != "einkauf":
                self.by_category.setdefault(a["kategorie"], []).append(a)
        self.plan = Plan()
        self.ref_counter = {}
        self.layers = None
        if layers:
            from schichten import Layers
            self.layers = Layers(self)

    def rate(self, day):
        current = None
        for start, value in self.rates:
            if start <= day:
                current = value
        if current is None:
            raise ValueError(f"Kein EUR-Kurs für {day}")
        return current

    def customer(self, name):
        return next(c for c in self.customers if c["name"] == name)

    # Umsatzziel ---------------------------------------------------------

    def revenue_target(self, year, month):
        base = Decimal(REVENUE_2025[month])
        return base * GROWTH_2026 if year == 2026 else base

    # Aufträge -----------------------------------------------------------

    def build_lines(self, r, segment, target, customer):
        """Positionen für einen Auftrag mit Netto-Zielwert target."""
        discount = Decimal("10") if segment == RESELLER_SEGMENT else Decimal("0")
        list_target = float(target) / (0.9 if discount else 1.0)
        services = segment != RESELLER_SEGMENT
        goods_target = list_target * (0.86 if services else 0.95)

        weights = dict(CATEGORY_WEIGHTS[segment])
        if customer["name"] == "Wohnbaugenossenschaft Sonnhalde":
            weights = {"Velo": 80, "Abfall": 10, "Bänke": 10}
        count = 1 if goods_target < 3_000 else 2 if goods_target < 10_000 else r.randint(2, 4)
        shares = [r.uniform(0.5, 1.5) for _ in range(count)]
        lines, used = [], set()
        for share in shares:
            alloc = goods_target * share / sum(shares)
            category = weighted(r, weights)
            options = [a for a in self.by_category[category] if a["code"] not in used]
            fitting = [a for a in options if float(a["verkaufspreis"]) <= alloc * 1.2] or \
                sorted(options, key=lambda a: a["verkaufspreis"])[:1]
            if not fitting:
                continue
            article = self.articles[weighted(r, {a["code"]: PRODUCT_WEIGHTS[a["code"]] for a in fitting})]
            used.add(article["code"])
            qty = max(1, round(alloc / float(article["verkaufspreis"])))
            lines.append(self.sale_line(article["code"], qty, discount))

        goods = sum((l.qty * l.price for l in lines), Decimal("0"))
        transport = 1 + int(goods // 25_000)
        lines.append(self.sale_line("DL-020", transport, discount))
        if services:
            hours = max(2, round(goods * MONTAGE_SHARE / Decimal("118")))
            lines.append(self.sale_line("DL-010", hours, discount))
            foundations = sum(FOUNDATIONS.get(l.code, 0) * l.qty for l in lines)
            if foundations:
                lines.append(self.sale_line("DL-030", foundations, discount))
            if goods > 30_000:
                lines.append(self.sale_line("DL-100", r.randint(6, 20), discount))
        return lines

    def sale_line(self, code, qty, discount=Decimal("0")):
        article = self.articles[code]
        account = "3400" if article["kategorie"] == "Dienstleistungen" else "3000"
        return Line(code, Decimal(qty), article["verkaufspreis"], discount, account, "ust")

    def next_ref(self, segment, day):
        key = (segment, day.year)
        self.ref_counter[key] = self.ref_counter.get(key, 0) + 1
        return f"{REF_PREFIX[segment]} {day:%y}-{self.ref_counter[key]:03d}"

    def plan_orders(self, year, month):
        r = rng("orders", year, month)
        target = self.revenue_target(year, month)
        days = workdays(year, month)
        n = 0
        for segment, share in SEGMENT_SHARE.items():
            budget = float(target * share) * r.uniform(0.97, 1.03)
            if self.layers:
                budget *= self.layers.segment_factor(year, month, segment)
            low, high = ORDER_SIZE[segment]
            for scripted in self.scripted_orders(year, month, segment):
                budget -= scripted
            customers = self.by_segment[segment]
            if self.layers:
                customers = self.layers.customers(year, month, segment, customers)
            while budget > low * 0.5:
                size = min(loguniform(r, low, high), budget)
                if budget - size < low * 0.5:
                    size = budget
                customer = r.choices(customers, weights=[c["gewicht"] for c in customers])[0]
                n += 1
                order = self.make_order(r, f"{year % 100:02d}{month:02d}-{n:03d}", segment, customer,
                                        Decimal(str(round(size, 2))), r.choice(days))
                budget -= float(order.net)
                self.lost_offers(r, order, segment, f"{year % 100:02d}{month:02d}-{n:03d}")

    def scripted_orders(self, year, month, segment):
        """Wiederkehrende Bestellungen aus dem Drehbuch, gibt die Nettobeträge zurück."""
        r = rng("scripted", year, month, segment)
        amounts = []
        if segment == "Hotels und Bergbahnen" and month == 4:
            # Bergbahnen Hochmatt bestellt jeden März, Rechnung im April vor der Sommersaison
            customer = self.customer("Bergbahnen Hochmatt AG")
            invoice_day = r.choice(workdays(year, 4, 14, 30))
            order = self.make_order(r, f"{year % 100:02d}04-H", segment, customer,
                                    Decimal(r.randint(9_000, 14_000)), invoice_day,
                                    order_day=r.choice(workdays(year, 3, 2, 20)))
            amounts.append(float(order.net))
        if segment == "Gemeinden und Städte" and month == 12:
            # Budget-Endspurt: Talbach und Bachenrain bestellen im Dezember
            for name, size in (("Gemeinde Talbach", (28_000, 40_000)), ("Gemeinde Bachenrain", (22_000, 32_000))):
                customer = self.customer(name)
                invoice_day = r.choice(workdays(year, 12, 15, 22))
                order = self.make_order(r, f"{year % 100:02d}12-{customer['nummer']}", segment, customer,
                                        Decimal(r.randint(*size)), invoice_day,
                                        order_day=r.choice(workdays(year, 12, 1, 5)))
                amounts.append(float(order.net))
        if self.layers:
            amounts += self.layers.scripted_orders(year, month, segment)
        return amounts

    def make_order(self, r, key, segment, customer, target, invoice_day, order_day=None, lines=None):
        lines = lines or self.build_lines(r, segment, target, customer)
        if order_day is None:
            order_day = prev_workday(invoice_day - timedelta(days=r.randint(*LEAD_DAYS[segment])))
        offer_day = order_day if segment == RESELLER_SEGMENT else \
            prev_workday(order_day - timedelta(days=r.randint(*OFFER_DAYS)))
        order = Order(key, customer, self.next_ref(segment, offer_day), offer_day, True, lines,
                      order_date=order_day, invoice_date=invoice_day)
        self.plan.orders.append(order)
        self.add_invoice(r, order)
        return order

    def lost_offers(self, r, won, segment, key):
        if segment == RESELLER_SEGMENT:
            return                          # Wiederverkäufer bestellen direkt
        low, high = ORDER_SIZE[segment]
        for i in range(2 if r.random() < 0.5 else 1):
            customer = r.choices(self.by_segment[segment], weights=[c["gewicht"] for c in self.by_segment[segment]])[0]
            offer_day = next_workday(won.offer_date + timedelta(days=r.randint(-20, 20)))
            lines = self.build_lines(r, segment, Decimal(str(round(loguniform(r, low, high), 2))), customer)
            self.plan.orders.append(Order(f"{key}-V{i + 1}", customer, self.next_ref(segment, offer_day),
                                          offer_day, False, lines,
                                          cancel_date=next_workday(offer_day + timedelta(days=LOST_CANCEL_DAYS))))

    # Rechnungen und Zahlungen ------------------------------------------

    def payment_delay(self, r, customer, invoice_day):
        days = r.gauss(customer["zahlt_nach_tagen"], 6)
        return int(min(75, max(8, round(days))))

    def add_invoice(self, r, order):
        inv = Invoice(f"R-{order.key}", order.customer, order.invoice_date, order.lines, order_key=order.key)
        inv.pay_date = next_workday(inv.date + timedelta(days=self.payment_delay(r, order.customer, inv.date)))
        self.plan.invoices.append(inv)

    # Einkauf ------------------------------------------------------------

    def supplier_ref(self, supplier, day):
        prefix = SUPPLIER_REF[supplier["name"]]
        key = ("ref", supplier["name"], day.year)
        r = rng("supplier-ref", supplier["name"], day.year, day.month)
        self.ref_counter[key] = self.ref_counter.get(key, r.randint(10, 80)) + r.randint(20, 60)
        return f"{prefix}-{day.year}-{self.ref_counter[key]:04d}"

    def material_cost(self, invoices):
        total = Decimal("0")
        for inv in invoices:
            for line in inv.lines:
                total += line.qty * self.articles[line.code]["materialkosten"]
        return money(total * MATERIAL_FACTOR)

    def plan_purchases(self, year, month):
        r = rng("purchases", year, month)
        invoices = [i for i in self.plan.invoices
                    if not i.opening and (i.date.year, i.date.month) == (year, month)
                    and not (self.layers and self.layers.is_project_invoice(i))]
        total = self.material_cost(invoices)
        material = {n: s for n, s in self.suppliers.items() if s["rolle"] == "material"}
        raw = {n: float(s["anteil_einkauf"]) * r.uniform(0.9, 1.1) for n, s in material.items()}
        scale = sum(raw.values())
        last_day = workdays(year, month)[-1]
        for name, weight in raw.items():
            supplier = material[name]
            amount = total * Decimal(str(weight / scale))
            parts = 2 if name == "Stahlcenter Limmat AG" else 1
            for p in range(parts):
                po_day = r.choice(workdays(year, month, 1 + p * 12, 12 + p * 12))
                bill_day = min(next_workday(po_day + timedelta(days=r.randint(4, 12))), last_day)
                self.add_purchase_bill(r, supplier, amount / parts, po_day, bill_day)

    def add_purchase_bill(self, r, supplier, amount_chf, po_day, bill_day, origin=None):
        eur = supplier["waehrung"] == "EUR"
        rate = self.rate(bill_day) if eur else Decimal("1")
        products = SUPPLIER_PRODUCTS.get(supplier["name"]) or {
            a["code"]: Decimal("1") for a in self.articles.values() if a["lieferant"] == supplier["name"]}
        lines = []
        for code, share in products.items():
            article = self.articles[code]
            account = "4400" if article["kategorie"] == "Fremdleistungen" else "4000"
            price = article["einkaufspreis"]
            qty = max(1, round(amount_chf * share / rate / price))
            if self.layers:
                # Menge nach altem Preis, Preiserhöhung des Lieferanten erhöht den Aufwand (P1)
                price = price * self.layers.purchase_price_factor(supplier, po_day)
            lines.append(Line(code, Decimal(qty), price, account=account, tax="" if eur else "vst_material"))
        key = f"E-{supplier['nummer']}-{po_day:%y%m%d}" + ("-P" if origin else "")
        bill = Bill(key, supplier, bill_day, self.supplier_ref(supplier, bill_day), lines, supplier["waehrung"],
                    rate, po_date=po_day, origin=origin)
        bill.due = bill.date + timedelta(days=30)
        bill.pay_date = prev_workday(bill.due)
        self.plan.bills.append(bill)

    def fixed_bill(self, r, name, day, net, label, terms_days=30):
        supplier = self.suppliers[name]
        tax = {"keine": ""}.get(supplier["steuer"], supplier["steuer"])
        line = Line(label, Decimal("1"), money(net), account=supplier["aufwandkonto"], tax=tax, label=label)
        bill = Bill(f"F-{supplier['nummer']}-{day:%y%m%d}", supplier, day, self.supplier_ref(supplier, day), [line])
        bill.due = day + timedelta(days=terms_days)
        bill.pay_date = prev_workday(bill.due) if terms_days else day
        self.plan.bills.append(bill)

    def plan_fixed_costs(self, year, month):
        r = rng("fixed", year, month)
        first = workdays(year, month)[0]
        self.fixed_bill(r, "Werkhof Immobilien AG", first, RENT, f"Miete {month:02d}/{year}", 0)
        self.fixed_bill(r, "Fahrzeugleasing Limmattal AG", first, LEASING, f"Leasing Lieferwagen {month:02d}/{year}", 0)
        self.fixed_bill(r, "Datenwerk Informatik GmbH", r.choice(workdays(year, month, 3, 7)), IT,
                        f"IT, Software, Telefonie {month:02d}/{year}")
        energy = Decimal(ENERGY[month]) * Decimal(str(round(r.uniform(0.95, 1.05), 3)))
        self.fixed_bill(r, "Elektrizitätswerk Talbach", r.choice(workdays(year, month, 6, 12)), energy,
                        f"Strom und Wärme {month:02d}/{year}")
        maintenance = Decimal(r.randint(*MAINTENANCE))
        split = Decimal(str(round(r.uniform(0.35, 0.65), 2)))
        self.fixed_bill(r, "Werkstattbedarf Brändli AG", r.choice(workdays(year, month, 5, 14)),
                        maintenance * split, "Werkzeug und Verbrauchsmaterial")
        self.fixed_bill(r, "Werkstattbedarf Brändli AG", r.choice(workdays(year, month, 18, 28)),
                        maintenance * (1 - split), "Unterhalt und Reparaturen")
        if month == 1:
            self.fixed_bill(r, "Securia Versicherungen AG", r.choice(workdays(year, 1, 8, 15)), INSURANCE,
                            f"Versicherungsprämien {year}")
        if month == 3:
            self.fixed_bill(r, "Treuhand und Revision Kalt AG", r.choice(workdays(year, 3, 10, 20)), AUDIT,
                            f"Revision Jahresrechnung {year - 1}")
        if (year, month) == (FAIR[0].year, FAIR[0].month):
            self.fixed_bill(r, "Kommunalmesse Schweiz GmbH", r.choice(workdays(year, month, 2, 10)), FAIR[1],
                            "Standmiete und Auftritt Fachmesse für Gemeinden")

    # Journalbuchungen ---------------------------------------------------

    def plan_journals(self, year, month):
        factor = 2 if month == 12 else 1
        pay_day = prev_workday(date(year, month, 20 if month == 12 else 25))
        self.plan.journals.append(Journal(
            f"J-LOHN-{year}-{month:02d}", pay_day, f"Löhne {month:02d}/{year}",
            [("5000", WAGES * factor), ("5700", SOCIAL * factor), (ACC_BANK, -(WAGES + SOCIAL) * factor)], "lohn"))
        if month == 12:
            end = date(year, 12, 31)
            self.plan.journals.append(Journal(f"J-ABSCHR-{year}", end, f"Abschreibungen {year}",
                                              [("6800", DEPRECIATION), ("1509", -DEPRECIATION)], "abschreibung"))
            self.plan.journals.append(Journal(f"J-STEUER-{year}", end, f"Rückstellung Gewinnsteuern {year}",
                                              [("8900", INCOME_TAX), ("2208", -INCOME_TAX)], "steuer"))
        if month == 6:
            day = prev_workday(month_end(year, 6))
            self.plan.journals.append(Journal(f"J-STEUERZ-{year}", day, f"Zahlung Gewinnsteuern {year - 1}",
                                              [("2208", INCOME_TAX), (ACC_BANK, -INCOME_TAX)], "steuerzahlung"))

    # Eröffnung ----------------------------------------------------------

    def plan_opening(self):
        r = rng("opening")
        label = "Übernahme offener Posten 2024"
        counts = {"Gemeinden und Städte": 12, "Immobilienverwaltungen und Genossenschaften": 6,
                  "Garten- und Landschaftsbau": 6, "Schulgemeinden": 3, "Hotels und Bergbahnen": 3}
        drafts = [(self.customer("Gemeinde Talbach"), 36_000.0, date(2024, 12, 18)),
                  (self.customer("Gemeinde Bachenrain"), 29_000.0, date(2024, 12, 19))]
        for segment, count in counts.items():
            low, high = ORDER_SIZE[segment]
            for _ in range(count - (2 if segment == "Gemeinden und Städte" else 0)):
                customer = r.choices(self.by_segment[segment], weights=[c["gewicht"] for c in self.by_segment[segment]])[0]
                first = 20 if segment in ("Garten- und Landschaftsbau", "Immobilienverwaltungen und Genossenschaften") else 2
                days = workdays(2024, 11, first) + workdays(2024, 12, 1, 20) if first == 20 else workdays(2024, 12, 2, 20)
                drafts.append((customer, loguniform(r, low, high) * 1.081, r.choice(days)))
        scale = float(OPENING["receivables"]) / sum(d[1] for d in drafts)
        amounts = [money(Decimal(str(d[1] * scale))) for d in drafts]
        amounts[-1] += OPENING["receivables"] - sum(amounts)
        for i, ((customer, _, day), amount) in enumerate(sorted(zip(drafts, amounts), key=lambda x: x[0][2])):
            line = Line("", Decimal("1"), amount, account=ACC_TRANSIT, label=label)
            inv = Invoice(f"R-2024-{i + 1:02d}", customer, day, [line], opening=True)
            earliest = date(2025, 1, 6)
            inv.pay_date = next_workday(max(earliest, day + timedelta(days=self.payment_delay(r, customer, day))))
            self.plan.invoices.append(inv)

        # Lieferanten: 20 Rechnungen, davon 2 in EUR
        bill_counts = {"Stahlcenter Limmat AG": 5, "Holzwerk Tirol GmbH": 1, "Pulverbeschichtung Glatttal AG": 3,
                       "Corten Metall GmbH": 1, "Verzinkerei Furttal AG": 1, "Glas Wyss AG": 1, "Beton Fertig AG": 1,
                       "Befestigungstechnik Huber AG": 1, "Transporte Keller AG": 1, "Kunststoffwerk Aare AG": 1}
        fixed = [("Elektrizitätswerk Talbach", Decimal("4756.40")), ("Datenwerk Informatik GmbH", Decimal("1945.80")),
                 ("Werkstattbedarf Brändli AG", Decimal("4310.25")), ("Werkstattbedarf Brändli AG", Decimal("3986.70"))]
        material_total = OPENING["payables"] - sum(a for _, a in fixed)
        share_total = sum(self.suppliers[n]["anteil_einkauf"] for n in bill_counts)
        drafts = []
        for name, count in bill_counts.items():
            part = material_total * self.suppliers[name]["anteil_einkauf"] / share_total / count
            for _ in range(count):
                drafts.append((self.suppliers[name], money(part * Decimal(str(r.uniform(0.85, 1.15))))))
        drafts[0] = (drafts[0][0], drafts[0][1] + material_total - sum(a for _, a in drafts))
        drafts += [(self.suppliers[n], a) for n, a in fixed]
        for i, (supplier, amount_chf) in enumerate(drafts):
            day = r.choice(workdays(2024, 12, 2, 20))
            eur = supplier["waehrung"] == "EUR"
            rate = self.rate(day) if eur else Decimal("1")
            amount = money(amount_chf / rate) if eur else amount_chf
            line = Line("", Decimal("1"), amount, account=ACC_TRANSIT, label=label)
            bill = Bill(f"E-2024-{i + 1:02d}", supplier, day, self.supplier_ref(supplier, day), [line],
                        supplier["waehrung"], rate, opening=True)
            bill.due = day + timedelta(days=30)
            bill.pay_date = max(prev_workday(bill.due), date(2025, 1, 6))
            self.plan.bills.append(bill)

    def opening_journal(self):
        receivables = sum((i.gross for i in self.plan.invoices if i.opening), Decimal("0"))
        payables = sum((b.chf(b.gross) for b in self.plan.bills if b.opening), Decimal("0"))
        o = OPENING
        lines = [(ACC_BANK, o["bank"]), ("1200", o["stock"]), ("1500", o["machines"]),
                 (ACC_TRANSIT, receivables), (ACC_TRANSIT, -payables),
                 (ACC_VAT_DUE, -o["vat"]), ("2208", -o["tax_provision"]),
                 ("2800", -o["share_capital"]), ("2950", -o["reserves"])]
        lines.append(("2970", -sum(a for _, a in lines)))
        self.plan.journals.append(Journal("J-EROEFFNUNG", OPENING_ENTRY_DATE, "Eröffnungsbilanz 2025",
                                          lines, "eroeffnung"))

    # Hauptbuch ----------------------------------------------------------

    def post(self, day, account, amount, source):
        if amount:
            self.plan.ledger.append((day, account, amount, source))

    def build_ledger(self):
        for inv in self.plan.invoices:
            for line in inv.lines:
                self.post(inv.date, line.account, -line.net, inv.key)
                if line.tax:
                    self.post(inv.date, ACC_VAT_DUE, -money(line.net * VAT_RATE), inv.key)
            self.post(inv.date, ACC_RECEIVABLE, inv.gross, inv.key)
            if inv.pay_date:
                self.post(inv.pay_date, ACC_BANK, inv.gross, f"Z-{inv.key}")
                self.post(inv.pay_date, ACC_RECEIVABLE, -inv.gross, f"Z-{inv.key}")
        for bill in self.plan.bills:
            booked = Decimal("0")
            for line in bill.lines:
                chf = bill.chf(line.net)
                booked += chf
                self.post(bill.date, line.account, chf, bill.key)
                if line.tax:
                    tax = money(line.net * VAT_RATE)
                    booked += tax
                    self.post(bill.date, ACC_VST_MAT if line.tax == "vst_material" else ACC_VST_OTHER, tax, bill.key)
            self.post(bill.date, ACC_PAYABLE, -booked, bill.key)
            if not bill.pay_date:
                continue
            paid = bill.chf(bill.gross, self.rate(bill.pay_date)) if bill.currency == "EUR" else booked
            self.post(bill.pay_date, ACC_PAYABLE, booked, f"Z-{bill.key}")
            self.post(bill.pay_date, ACC_BANK, -paid, f"Z-{bill.key}")
            if paid != booked:
                self.post(bill.pay_date, ACC_FX_LOSS if paid > booked else ACC_FX_GAIN, paid - booked, f"Z-{bill.key}")
        for j in self.plan.journals:
            for account, amount in j.lines:
                self.post(j.date, account, amount, j.key)

    def balance(self, accounts, until, since=None):
        return sum((a for d, acc, a, _ in self.plan.ledger
                    if acc in accounts and d <= until and (since is None or d >= since)), Decimal("0"))

    def plan_vat_payments(self):
        """MWST-Saldo pro Quartal, bezahlt am letzten Werktag des zweiten Monats nach Quartalsende."""
        quarters = [(2024, 12)] + [(y, m) for y, m in months((2025, 3), (2026, 9)) if m % 3 == 0]
        for year, month in quarters:
            end = month_end(year, month)
            py, pm = (year + 1, month - 10) if month > 10 else (year, month + 2)
            pay_day = prev_workday(month_end(py, pm))
            if pay_day > END:
                continue
            if end < OPENING_ENTRY_DATE:
                # Q4 2024: nur die MWST-Schuld aus der Eröffnungsbilanz
                due, mat, other = OPENING["vat"], Decimal("0"), Decimal("0")
            else:
                due = -self.balance({ACC_VAT_DUE}, end)
                mat = self.balance({ACC_VST_MAT}, end)
                other = self.balance({ACC_VST_OTHER}, end)
            q = (month - 1) // 3 + 1
            j = Journal(f"J-MWST-{year}-Q{q}", pay_day, f"MWST-Abrechnung Q{q}/{year} ESTV",
                        [(ACC_VAT_DUE, due), (ACC_VST_MAT, -mat), (ACC_VST_OTHER, -other),
                         (ACC_BANK, -(due - mat - other))], "mwst")
            self.plan.journals.append(j)
            for account, amount in j.lines:
                self.post(j.date, account, amount, j.key)

    # Gesamtlauf ---------------------------------------------------------

    def build(self):
        self.plan_opening()
        self.opening_journal()
        # Rechnungsmonate bis Dezember 2026, damit Ende Oktober ein Auftragsbestand offen ist
        for year, month in months((2025, 1), (2026, 12)):
            self.plan_orders(year, month)
        if self.layers:
            self.layers.after_orders()
        for year, month in months((2025, 1), (2026, 10)):
            self.plan_purchases(year, month)
            if self.layers:
                self.layers.after_purchases(year, month)
            self.plan_fixed_costs(year, month)
            self.plan_journals(year, month)
        if self.layers:
            self.layers.finalize()
            self.plan.price_changes = self.layers.price_changes
        self.trim()
        self.build_ledger()
        self.plan_vat_payments()
        return self.plan

    def trim(self):
        """Alles nach END fällt weg. Was danach bezahlt würde, bleibt offen."""
        p = self.plan
        p.orders = [o for o in p.orders if o.offer_date <= END]
        for o in p.orders:
            if o.order_date and o.order_date > END:
                o.won, o.order_date, o.invoice_date = False, None, None
            if o.cancel_date and o.cancel_date > END:
                o.cancel_date = None
        p.invoices = [i for i in p.invoices if i.date <= END]
        for i in p.invoices:
            if i.pay_date and i.pay_date > END:
                i.pay_date = None
        p.bills = [b for b in p.bills if b.date <= END]
        for b in p.bills:
            if b.pay_date and b.pay_date > END:
                b.pay_date = None
        p.journals = [j for j in p.journals if j.date <= END]


def build_plan():
    return Planner().build()
