"""Prüfskript Etappe 5: rechnet die Prüffälle P1 bis P5 nur aus Odoo-Daten nach.

Liest nur. Importiert nichts aus dem Datengenerator und liest weder dessen CSV-Dateien
noch dessen Plan. Die Zielwerte stehen in tests/prueffaelle.md (Abschnitt «Zielwerte»).
Die Auffälligkeiten werden allgemein gesucht (Aufträge über CHF 100'000, Preissprünge,
Posten mit hohem Alter, Doppelerfassungen) und erst dann mit den erwarteten Namen verglichen.

Aufruf:  python3 tests/pruefskript.py
Zugang:  Datei .env mit ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY. Standard
         data-generator/.env, mit PRUEF_ENV auf eine andere Datei umstellbar.
         Werte werden nie ausgegeben.
"""

import json
import os
import re
import statistics
import sys
import urllib.request
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal as D

STICHTAG = date(2026, 10, 31)
GEGENTEST_STICHTAG = date(2025, 10, 31)
GROSSAUFTRAG = D("100000")     # ab diesem Nettobetrag gilt ein Auftrag als Einzelprojekt
# Namen aus tests/prueffaelle.md. Sie werden nur zum Vergleichen benutzt, nicht zum Suchen.
ERWARTET = {"p1_lieferant": "Stahlcenter", "p2_kunde": "Rietli", "p3_kunde": "Seefeld",
            "p4_segment": "Schulgemeinden", "p4_kunde": "Hinterberg", "p5_lieferant": "Pulverbeschichtung"}


# --- Verbindung ----------------------------------------------------------

def lade_env():
    pfad = os.environ.get("PRUEF_ENV") or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                       "..", "data-generator", ".env")
    werte = {}
    with open(pfad, encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if zeile and not zeile.startswith("#") and "=" in zeile:
                k, v = zeile.split("=", 1)
                werte[k.strip()] = v.strip().strip('"').strip("'")
    return werte


class Odoo:
    def __init__(self):
        env = lade_env()
        self.url, self.db, self.user, self._key = (env["ODOO_URL"].rstrip("/"), env["ODOO_DB"],
                                                   env["ODOO_USER"], env["ODOO_API_KEY"])
        self._n = 0
        self.uid = self._rpc("common", "authenticate", self.db, self.user, self._key, {})
        if not self.uid:
            raise SystemExit("Anmeldung an Odoo fehlgeschlagen.")

    def _rpc(self, service, method, *args):
        self._n += 1
        daten = {"jsonrpc": "2.0", "method": "call", "id": self._n,
                 "params": {"service": service, "method": method, "args": list(args)}}
        req = urllib.request.Request(self.url + "/jsonrpc", data=json.dumps(daten).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as antwort:
            res = json.loads(antwort.read())
        if res.get("error"):
            raise RuntimeError(res["error"].get("data", {}).get("message") or res["error"].get("message"))
        return res.get("result")

    def lesen(self, modell, domain, felder, **kw):
        return self._rpc("object", "execute_kw", self.db, self.uid, self._key, modell, "search_read",
                         [domain], {"fields": felder, "context": {"lang": "de_CH"}, **kw})


# --- Hilfen --------------------------------------------------------------

def d(wert):
    return D(str(wert))


def monatsende(j, m):
    return (date(j + (m == 12), m % 12 + 1, 1)) - timedelta(days=1)


def chf(w, nk=0):
    return f"{w:,.{nk}f}".replace(",", "'")


def prozent(w):
    return f"{w * 100:+.1f} %"


class Tabelle:
    def __init__(self, titel, kopf):
        self.titel, self.kopf, self.zeilen = titel, kopf, []

    def zeile(self, *zellen, ok):
        self.zeilen.append((zellen, ok))

    def drucken(self):
        breiten = [max(len(str(z[0][i])) for z in self.zeilen + [((self.kopf), True)]) for i in range(len(self.kopf))]
        print(f"\n{self.titel}")
        print("  " + "  ".join(str(k).ljust(b) for k, b in zip(self.kopf, breiten)) + "  Ergebnis")
        print("  " + "  ".join("-" * b for b in breiten) + "  --------")
        for zellen, ok in self.zeilen:
            print("  " + "  ".join(str(z).ljust(b) for z, b in zip(zellen, breiten)) + "  " + ("ok" if ok else "NICHT OK"))
        return all(ok for _, ok in self.zeilen)


def nahe(ist, soll, tol):
    return abs(ist - soll) <= tol


# --- Daten holen -----------------------------------------------------------

class Daten:
    def __init__(self, o):
        print("Lese Daten aus Odoo (nur lesen) ...")
        self.partner = {p["id"]: p for p in o.lesen("res.partner", [], ["name", "industry_id"])}
        kunden = o.lesen("account.move", [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
                         ["name", "commercial_partner_id", "invoice_date", "invoice_date_due", "amount_untaxed",
                          "amount_total", "ref", "invoice_origin"])
        self.rechnungen = kunden
        self.lieferanten_rechnungen = o.lesen(
            "account.move", [("move_type", "=", "in_invoice"), ("state", "=", "posted")],
            ["name", "commercial_partner_id", "invoice_date", "amount_total", "amount_untaxed_signed", "ref",
             "invoice_origin", "currency_id", "payment_state"])
        zahlungen = o.lesen("account.payment", [("state", "not in", ["draft", "canceled"])],
                            ["date", "reconciled_invoice_ids"])
        self.bezahlt_am = {}
        for z in zahlungen:
            for i in z["reconciled_invoice_ids"]:
                self.bezahlt_am[i] = max(self.bezahlt_am.get(i, z["date"]), z["date"])
        zeilen = o.lesen("account.move.line", [("parent_state", "=", "posted"), ("date", ">=", "2025-01-01")],
                         ["account_id", "balance", "date"])
        self.konto = defaultdict(lambda: defaultdict(D))      # Konto -> Monat "YYYY-MM" -> Saldo
        for z in zeilen:
            if not z["account_id"]:       # Abschnitts- und Notizzeilen haben kein Konto
                continue
            code = z["account_id"][1].split(" ")[0]
            if code[0] in "3456":
                self.konto[code][z["date"][:7]] += d(z["balance"])
        self.auftraege = o.lesen("sale.order", [("state", "in", ["sale", "done"])],
                                 ["name", "date_order", "amount_untaxed", "client_order_ref", "partner_id"])
        self.bestellungen = o.lesen("purchase.order", [("state", "in", ["purchase", "done"])],
                                    ["name", "origin", "invoice_ids"])
        self.einkaufszeilen = o.lesen(
            "account.move.line", [("move_id.move_type", "=", "in_invoice"), ("parent_state", "=", "posted"),
                                  ("product_id", "!=", False), ("date", ">=", "2025-01-01")],
            ["move_id", "product_id", "price_unit", "date", "partner_id"])

    def name(self, pid):
        return self.partner[pid]["name"]

    def segment(self, pid):
        ind = self.partner[pid]["industry_id"]
        return ind[1] if ind else "(ohne Branche)"

    # Konten ----------------------------------------------------------------
    def summe(self, konten, von, bis):
        """Summe der Salden der Konten über die Monate von..bis (je als date, nur Monate zählen)."""
        a, b = von.strftime("%Y-%m"), bis.strftime("%Y-%m")
        return sum((s for k in konten for m, s in self.konto.get(k, {}).items() if a <= m <= b), D(0))

    def umsatz(self, von, bis):
        return -self.summe(("3000", "3400"), von, bis)

    def material(self, von, bis):
        return self.summe(("4000", "4400"), von, bis)

    def quote(self, von, bis):
        return self.material(von, bis) / self.umsatz(von, bis)

    def ebitda(self, von, bis):
        alle = [k for k in self.konto if k != "6800"]
        return -self.summe(alle, von, bis)

    # Kundenrechnungen --------------------------------------------------------
    def netto(self, von, bis, filt=lambda r: True):
        return sum((d(r["amount_untaxed"]) for r in self.rechnungen
                    if von.isoformat() <= r["invoice_date"] <= bis.isoformat() and filt(r)), D(0))

    def offen(self, stichtag):
        s = stichtag.isoformat()
        return [r for r in self.rechnungen if r["invoice_date"] <= s
                and not (r["id"] in self.bezahlt_am and self.bezahlt_am[r["id"]] <= s)]


def stufe(alter):
    return 3 if alter >= 90 else 2 if alter >= 60 else 1 if alter >= 30 else 0


# --- Prüffälle ---------------------------------------------------------------

def p1(dt):
    """Materialquote und Preissprung eines Lieferanten."""
    q = lambda j, n: dt.quote(date(j, 3 * n - 2, 1), monatsende(j, 3 * n))
    q2, q1, q2v = q(2026, 2), q(2026, 1), q(2025, 2)
    sprung = preissprung(dt, [(2026, 1), (2026, 2)])
    return q2, q1, q2v, sprung


def quartal_preise(dt, quartale):
    """(Lieferant, Artikel) -> Quartal -> Durchschnittspreis der Einkaufszeilen."""
    mv = {r["id"]: r["commercial_partner_id"][0] for r in dt.lieferanten_rechnungen}
    preise = defaultdict(lambda: defaultdict(list))
    for z in dt.einkaufszeilen:
        j, m = int(z["date"][:4]), int(z["date"][5:7])
        qu = (j, (m - 1) // 3 + 1)
        if qu in quartale and z["move_id"][0] in mv:
            preise[(mv[z["move_id"][0]], z["product_id"][0])][qu].append(d(z["price_unit"]))
    return {k: {qu: sum(v) / len(v) for qu, v in qs.items()} for k, qs in preise.items()}


def preissprung(dt, quartale):
    """Grösster Preissprung eines Lieferanten zwischen aufeinanderfolgenden Quartalen (Median seiner Artikel)."""
    preise = quartal_preise(dt, set(quartale))
    je_lieferant = defaultdict(list)
    for (lief, _), qs in preise.items():
        for a, b in zip(quartale, quartale[1:]):
            if a in qs and b in qs:
                je_lieferant[lief].append(qs[b] / qs[a] - 1)
    if not je_lieferant:
        return None
    lief, werte = max(je_lieferant.items(), key=lambda kv: statistics.median(kv[1]))
    return dt.name(lief), statistics.median(werte)


def p2(dt, stichtag):
    """Offene Posten nach Alter (Tage nach Fälligkeit) und Mahnstufe."""
    posten = []
    for r in dt.offen(stichtag):
        alter = (stichtag - date.fromisoformat(r["invoice_date_due"])).days
        posten.append((r["commercial_partner_id"][0], alter, d(r["amount_total"])))
    ueber90 = defaultdict(D)
    gesamt = defaultdict(D)
    stufen = defaultdict(lambda: defaultdict(int))
    for pid, alter, betrag in posten:
        gesamt[pid] += betrag
        if alter >= 90:
            ueber90[pid] += betrag
        if stufe(alter):
            stufen[pid][stufe(alter)] += 1
    return posten, ueber90, gesamt, stufen


def p3(dt, jahr):
    """Aufträge ab CHF 100'000 netto im Jahr, mit ihren Rechnungen und dem Projektmaterial."""
    gross = [a for a in dt.auftraege if d(a["amount_untaxed"]) >= GROSSAUFTRAG and a["date_order"][:4] == str(jahr)]
    projekte = []
    for a in gross:
        rechnungen = [r for r in dt.rechnungen if r["invoice_origin"] == a["name"]]
        kern = (a["client_order_ref"] or "").split(",")[0].strip()
        material = D(0)
        if kern:
            ids = {i for b in dt.bestellungen if b["origin"] and kern.lower() in b["origin"].lower() for i in b["invoice_ids"]}
            material = sum((abs(d(r["amount_untaxed_signed"])) for r in dt.lieferanten_rechnungen if r["id"] in ids), D(0))
        projekte.append((a, rechnungen, material))
    return projekte


def p4(dt):
    """Umsatz je Branche und je Kunde, Januar bis Oktober 2026 gegen 2025."""
    zeit = {2025: (date(2025, 1, 1), date(2025, 10, 31)), 2026: (date(2026, 1, 1), date(2026, 10, 31))}
    seg, kd = defaultdict(lambda: defaultdict(D)), defaultdict(lambda: defaultdict(D))
    for j, (von, bis) in zeit.items():
        for r in dt.rechnungen:
            if von.isoformat() <= r["invoice_date"] <= bis.isoformat():
                pid = r["commercial_partner_id"][0]
                seg[dt.segment(pid)][j] += d(r["amount_untaxed"])
                kd[pid][j] += d(r["amount_untaxed"])
    return seg, kd


def normref(ref):
    teile = re.split(r"[^0-9a-zA-Z]+", (ref or "").lower())
    return tuple(t.lstrip("0") if t.isdigit() else t for t in teile if t)


def p5(dt, von, bis):
    """Doppelerfassung: gleicher Lieferant, Währung, Betrag, höchstens 7 Tage, mindestens eine ohne Bestellung."""
    gruppen = defaultdict(list)
    for r in dt.lieferanten_rechnungen:
        if von.isoformat() <= r["invoice_date"] <= bis.isoformat():
            gruppen[(r["commercial_partner_id"][0], r["currency_id"][0], round(r["amount_total"], 2))].append(r)
    paare = []
    for rs in gruppen.values():
        rs.sort(key=lambda r: r["invoice_date"])
        for a, b in zip(rs, rs[1:]):
            tage = (date.fromisoformat(b["invoice_date"]) - date.fromisoformat(a["invoice_date"])).days
            if tage <= 7 and not (a["invoice_origin"] and b["invoice_origin"]):
                paare.append((a, b))
    return paare


# --- Hauptteil ---------------------------------------------------------------

def main():
    dt = Daten(Odoo())
    jan, okt26, okt25 = date(2026, 1, 1), STICHTAG, GEGENTEST_STICHTAG
    ziel = Tabelle("Prüffälle Odoo gegen Zielwerte (Stichtag 31.10.2026)", ("Fall", "Zielwert", "Ist", "Toleranz"))
    gegen = Tabelle("Gegentest 2025 (muss «nicht gefunden» melden)", ("Fall", "Erwartung", "Ist"))

    # P1
    q2, q1, q2v, sprung = p1(dt)
    ziel.zeile("P1 Materialquote Q2 2026", "44.6 %", f"{q2 * 100:.1f} % (Q1 {q1 * 100:.1f} %, Q2 2025 {q2v * 100:.1f} %)",
               "± 1.0 Punkt", ok=nahe(q2 * 100, D("44.6"), D("1.0")))
    name, wert = sprung if sprung else ("-", D(0))
    ziel.zeile("P1 Preissprung Lieferant Q1→Q2", "Stahlcenter +25 %", f"{name} {prozent(wert)}", "± 1 Punkt",
               ok=ERWARTET["p1_lieferant"] in name and nahe(wert * 100, D(25), D(1)))

    # P2
    posten, ueber90, gesamt, stufen = p2(dt, STICHTAG)
    top = max(ueber90, key=ueber90.get) if ueber90 else None
    kunde = dt.name(top) if top else "-"
    ziel.zeile("P2 Kunde mit Alter ≥ 90 Tage", "Rietli, einziger", f"{kunde}, mit Stufe 3: {sorted(dt.name(p) for p in ueber90)}",
               "-", ok=top is not None and ERWARTET["p2_kunde"] in kunde and len(ueber90) == 1)
    ziel.zeile("P2 Rietli offen total", "41'736", chf(gesamt[top]) if top else "-", "± 2'000",
               ok=top is not None and nahe(gesamt[top], D(41736), D(2000)))
    ziel.zeile("P2 Rietli davon ≥ 90 Tage", "26'954", chf(ueber90[top]) if top else "-", "± 2'000",
               ok=top is not None and nahe(ueber90[top], D(26954), D(2000)))
    anzahl = defaultdict(int)
    for pid, st in stufen.items():
        for s, n in st.items():
            anzahl[s] += n
    ziel.zeile("P2 Mahnstufen 3 / 2 / 1", "2 / 1 / 1", f"{anzahl[3]} / {anzahl[2]} / {anzahl[1]}", "exakt",
               ok=(anzahl[3], anzahl[2], anzahl[1]) == (2, 1, 1))
    andere = [dt.name(p) for p in stufen if p != top]
    ziel.zeile("P2 andere Kunden mit Mahnstufe", "keine", str(andere) if andere else "keine", "exakt", ok=not andere)

    # P3
    proj = p3(dt, 2026)
    if proj:
        a, rechnungen, material = proj[0]
        netto = d(a["amount_untaxed"])
        je_monat = defaultdict(D)
        for r in rechnungen:
            je_monat[r["invoice_date"][:7]] += d(r["amount_untaxed"])
        ziel.zeile("P3 Projekt gefunden", "1 Auftrag, Seefeld",
                   f"{len(proj)} Auftrag/Aufträge, {a['name']} {dt.name(a['partner_id'][0])}, "
                   f"«{a['client_order_ref']}»", "-", ok=len(proj) == 1 and ERWARTET["p3_kunde"] in dt.name(a["partner_id"][0]))
        ziel.zeile("P3 Projekt netto", "186'000", chf(netto, 2), "exakt", ok=netto == 186000)
        ziel.zeile("P3 Rechnung Juni / September", "74'400 / 111'600",
                   f"{chf(je_monat['2026-06'], 2)} / {chf(je_monat['2026-09'], 2)}", "exakt",
                   ok=je_monat["2026-06"] == 74400 and je_monat["2026-09"] == 111600)
        proj_umsatz = sum((d(r["amount_untaxed"]) for r in rechnungen if r["invoice_date"] <= okt26.isoformat()), D(0))
    else:
        proj_umsatz = material = D(0)
        ziel.zeile("P3 Projekt gefunden", "1 Auftrag, Seefeld", "keiner", "-", ok=False)
    u25 = dt.netto(date(2025, 1, 1), date(2025, 10, 31))
    u26 = dt.netto(jan, okt26)
    ziel.zeile("P3 Umsatz Jan–Okt gegen Vorjahr", "+3.0 %", prozent(u26 / u25 - 1), "± 1.5 Punkte",
               ok=nahe((u26 / u25 - 1) * 100, D(3.0), D("1.5")))
    ziel.zeile("P3 ohne Projekt", "−2.6 %", prozent((u26 - proj_umsatz) / u25 - 1), "± 1.5 Punkte",
               ok=nahe(((u26 - proj_umsatz) / u25 - 1) * 100, D("-2.6"), D("1.5")))
    for monat, soll in ((7, 51), (8, 54), (9, 33)):
        qm = dt.quote(date(2026, monat, 1), monatsende(2026, monat))
        ziel.zeile(f"P3 Materialquote Monat {monat}/2026", f"{soll} %", f"{qm * 100:.1f} %", "± 2 Punkte",
                   ok=nahe(qm * 100, D(soll), D(2)))

    # P4
    seg, kd = p4(dt)
    aend = {s: (v[2026] / v[2025] - 1) for s, v in seg.items() if v[2025]}
    schlecht = min(aend, key=aend.get)
    ziel.zeile("P4 Segment mit stärkstem Rückgang", "Schulgemeinden −58.8 %", f"{schlecht} {prozent(aend[schlecht])}",
               "± 5 Punkte", ok=ERWARTET["p4_segment"] in schlecht and nahe(aend[schlecht] * 100, D("-58.8"), D(5)))
    im_seg = {p: v for p, v in kd.items() if dt.segment(p) == schlecht and v[2025]}
    verlust = min(im_seg, key=lambda p: im_seg[p][2026] - im_seg[p][2025])
    vw = im_seg[verlust][2026] / im_seg[verlust][2025] - 1
    ziel.zeile("P4 Kunde mit grösstem Verlust darin", "Hinterberg −71 %", f"{dt.name(verlust)} {prozent(vw)}",
               "± 5 Punkte", ok=ERWARTET["p4_kunde"] in dt.name(verlust) and nahe(vw * 100, D(-71), D(5)))

    # P5
    paare = p5(dt, date(2026, 1, 1), okt26)
    if len(paare) == 1:
        a, b = paare[0]
        ohne = a if not a["invoice_origin"] else b
        beide_bezahlt = a["payment_state"] == "paid" and b["payment_state"] == "paid"
        gleiche_ref = normref(a["ref"]) == normref(b["ref"])
        ziel.zeile("P5 Doppelerfassung gefunden", "1 Paar, Pulverbeschichtung",
                   f"{dt.name(a['commercial_partner_id'][0])}, «{a['ref']}» und «{b['ref']}», gleiche bereinigte Referenz: "
                   f"{'ja' if gleiche_ref else 'nein'}", "-",
                   ok=ERWARTET["p5_lieferant"] in dt.name(a["commercial_partner_id"][0]) and gleiche_ref)
        ziel.zeile("P5 Betrag, bezahlt, Rückforderung", "8'640.00 je, beide bezahlt, 8'640.00",
                   f"{chf(d(a['amount_total']), 2)} / {chf(d(b['amount_total']), 2)}, bezahlt: {'ja' if beide_bezahlt else 'nein'}, "
                   f"zurückzufordern {chf(d(ohne['amount_total']), 2)} ({ohne['name']}, ohne Bestellung)", "exakt",
                   ok=d(a["amount_total"]) == 8640 and d(b["amount_total"]) == 8640 and beide_bezahlt)
    else:
        ziel.zeile("P5 Doppelerfassung gefunden", "1 Paar", f"{len(paare)} Paare", "exakt", ok=False)

    # Gesamt
    e26 = dt.ebitda(jan, okt26)
    ziel.zeile("Gesamt EBITDA Jan–Okt 2026", "263'000", chf(e26), "± 15'000", ok=nahe(e26, D(263000), D(15000)))
    ohne_proj = e26 - proj_umsatz + material
    ziel.zeile("Gesamt EBITDA ohne Projekt", "165'000",
               f"{chf(ohne_proj)} (Projektumsatz {chf(proj_umsatz)}, Projektmaterial {chf(material)})", "± 15'000",
               ok=nahe(ohne_proj, D(165000), D(15000)))
    ziel.zeile("Gesamt EBITDA Jan–Okt 2025", "290'000", chf(dt.ebitda(date(2025, 1, 1), date(2025, 10, 31))), "± 15'000",
               ok=nahe(dt.ebitda(date(2025, 1, 1), date(2025, 10, 31)), D(290000), D(15000)))

    # Gegentest 2025
    monatsquoten = [(dt.quote(date(2025, m, 1), monatsende(2025, m)), m) for m in range(1, 13)]
    hoechste = max(monatsquoten)
    gegen.zeile("P1 höchste Monatsquote 2025", "unter 42 %", f"{hoechste[0] * 100:.1f} % (Monat {hoechste[1]})",
                ok=hoechste[0] * 100 < 42)
    s25 = preissprung(dt, [(2025, 1), (2025, 2), (2025, 3), (2025, 4)])
    gegen.zeile("P1 Preissprung Lieferant 2025", "keiner über 10 %",
                f"grösster: {s25[0]} {prozent(s25[1])}" if s25 else "keiner", ok=s25 is None or s25[1] < D("0.10"))
    _, ueber90_25, _, stufen25 = p2(dt, GEGENTEST_STICHTAG)
    gegen.zeile("P2 Kunden mit Alter ≥ 90 per 31.10.2025", "keine", (str([dt.name(p) for p in ueber90_25]) if ueber90_25 else "keine"),
                ok=not ueber90_25)
    gegen.zeile("P2 Mahnstufe 3 per 31.10.2025", "keine", str(sum(s.get(3, 0) for s in stufen25.values())) + " Rechnungen",
                ok=sum(s.get(3, 0) for s in stufen25.values()) == 0)
    proj25 = p3(dt, 2025)
    gegen.zeile("P3 Aufträge ab 100'000 netto 2025", "keiner", f"{len(proj25)}", ok=not proj25)
    uebrige = {s: v for s, v in aend.items() if s != schlecht}
    schwach = min(uebrige, key=uebrige.get)
    gegen.zeile("P4 übrige Segmente 2026 gegen 2025", "keines unter −20 %",
                f"schwächstes: {schwach} {prozent(uebrige[schwach])} (Segmente: " +
                ", ".join(f"{s} {prozent(v)}" for s, v in sorted(uebrige.items())) + ")", ok=uebrige[schwach] > D("-0.20"))
    paare25 = p5(dt, date(2025, 1, 1), date(2025, 12, 31))
    gegen.zeile("P5 Doppelerfassungen 2025", "kein Paar", f"{len(paare25)}", ok=not paare25)

    gut1 = ziel.drucken()
    gut2 = gegen.drucken()
    print("\nGesamtergebnis: " + ("alles ok" if gut1 and gut2 else "ES GIBT ABWEICHUNGEN"))
    sys.exit(0 if gut1 and gut2 else 1)


if __name__ == "__main__":
    main()
