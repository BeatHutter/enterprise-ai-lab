"""Gemeinsame Grundlagen der Rechenwege: Kontext, Konten, Salden, Zeiträume, Darstellung.

Die Grundregeln stehen im Katalog (katalog.md, Abschnitt «Grundregeln»):
nur gebuchte Belege, Buchungsdatum, Konten nach Nummer, Betrag in CHF (balance).
"""

import datetime as dt

from .odoo import Odoo

GEBUCHT = ("parent_state", "=", "posted")
KONTO_DEBITOREN = 1100


class Kontext:
    """Eine Odoo-Verbindung pro Aufruf. Merkt sich Konten und schon gerechnete Werte."""

    def __init__(self, odoo=None):
        self.odoo = odoo or Odoo.aus_umgebung()
        self._konten = None
        self._merker = {}

    def konten(self):
        if self._konten is None:
            rows = self.odoo.search_read("account.account", [], ["code", "name"])
            # Nur rein numerische Kontonummern (999999 ist ein technisches Konto)
            self._konten = sorted((r for r in rows if r["code"] and r["code"].isdigit() and len(r["code"]) == 4),
                                  key=lambda r: r["code"])
        return self._konten

    def kontenbereich(self, von, bis, ohne=()):
        return [k for k in self.konten() if von <= int(k["code"]) <= bis and int(k["code"]) not in ohne]

    def merke(self, schluessel, rechne):
        if schluessel not in self._merker:
            self._merker[schluessel] = rechne()
        return self._merker[schluessel]

    def kennzahl(self, kennung, *args):
        """Ergebnis einer anderen Kennzahl, einmal pro Aufruf gerechnet."""
        from .register import MODULE  # spät importieren, sonst Kreisbezug
        return self.merke((kennung, *args), lambda: MODULE[kennung].berechne(self, *args))

    def salden(self, konten, von, bis):
        """Summe balance pro Konto für gebuchte Zeilen mit Buchungsdatum von bis bis (beide eingeschlossen)."""
        domain = [GEBUCHT, ("account_id", "in", [k["id"] for k in konten])]
        if von:
            domain.append(("date", ">=", von))
        domain.append(("date", "<=", bis))
        return self._salden_pro_konto(konten, domain)

    def saldo_per(self, konten, stichtag):
        """Bestand per Stichtag: alle gebuchten Zeilen bis und mit Stichtag."""
        return self.salden(konten, None, stichtag)

    def _salden_pro_konto(self, konten, domain):
        if not konten:
            return []
        gruppen = self.odoo.read_group("account.move.line", domain, ["balance:sum"], ["account_id"])
        nach_id = {g["account_id"][0]: g["balance"] for g in gruppen if g["account_id"]}
        return [{"konto": k["code"], "name": k["name"], "saldo": nach_id[k["id"]]}
                for k in konten if k["id"] in nach_id]


# --- Ergebnisse --------------------------------------------------------------

def ergebnis(wert, bestandteile=None, hinweise=None, **zusatz):
    """Rohes Ergebnis eines Rechenwegs, ungerundet. Gerundet wird erst bei der Ausgabe."""
    return {"wert": wert, "bestandteile": bestandteile or [], "hinweise": hinweise or [], **zusatz}


def summe_konten(ctx, konten, von, bis, vorzeichen):
    """Summe über Konten; vorzeichen -1 für Ertrag (Odoo speichert Soll minus Haben)."""
    zeilen = ctx.salden(konten, von, bis)
    bestandteile = [{"konto": z["konto"], "name": z["name"], "wert": vorzeichen * z["saldo"]} for z in zeilen]
    return ergebnis(sum(b["wert"] for b in bestandteile), bestandteile)


def quote(zaehler, nenner, name_nenner):
    """Quote in Prozent oder None mit Grund, wenn der Nenner null oder negativ ist."""
    if nenner is None or nenner <= 0:
        return None, f"nicht berechenbar: {name_nenner} ist null oder negativ"
    return zaehler / nenner * 100, None


# --- Zeiträume ----------------------------------------------------------------

def datum(text):
    try:
        return dt.date.fromisoformat(text)
    except (TypeError, ValueError):
        raise ValueError(f"Datum ungültig: {text!r}, erwartet JJJJ-MM-TT") from None


def monatsende(tag):
    naechster = (tag.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return naechster - dt.timedelta(days=1)


def vorjahr(tag):
    try:
        return tag.replace(year=tag.year - 1)
    except ValueError:  # 29. Februar
        return tag.replace(year=tag.year - 1, day=28)


def teilzeitraeume(von, bis, art):
    """Monate oder Quartale im Zeitraum, an den Rändern abgeschnitten."""
    teile = []
    start = von
    while start <= bis:
        if art == "monat":
            ende = monatsende(start)
            label = f"{start.month:02d}.{start.year}"
        elif art == "quartal":
            q = (start.month - 1) // 3 + 1
            ende = monatsende(dt.date(start.year, q * 3, 1))
            label = f"Q{q} {start.year}"
        else:
            raise ValueError(f"Aufteilung unbekannt: {art}")
        ende = min(ende, bis)
        teile.append((start, ende, label))
        start = ende + dt.timedelta(days=1)
    return teile


# --- Darstellung (Schweizer Schreibweise) -----------------------------------

def chf(wert):
    if wert is None:
        return "nicht verfügbar"
    text = f"{abs(wert):,.2f}".replace(",", "'")
    return f"CHF {'-' if wert < -0.004 else ''}{text}"


def prozent(wert):
    return "nicht berechenbar" if wert is None else f"{wert:.1f} %"


def tage(wert):
    return "nicht berechenbar" if wert is None else f"{round(wert):d} Tage"


def ch_datum(tag):
    tag = datum(tag) if isinstance(tag, str) else tag
    return tag.strftime("%d.%m.%Y")


FORMATE = {"CHF": chf, "%": prozent, "Tage": tage}


def runde(wert, einheit):
    if wert is None:
        return None
    if einheit == "CHF":
        return round(wert, 2)
    if einheit == "%":
        return round(wert, 1)
    if einheit == "Tage":
        return round(wert)
    return wert
