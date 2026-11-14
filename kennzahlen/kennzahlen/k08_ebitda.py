"""K8 Betriebsergebnis vor Abschreibungen (EBITDA) (Katalog, K8).

EBITDA = Bruttogewinn − Personalaufwand − übriger betrieblicher Aufwand + Kursdifferenzen.
Kontrolle: gleich wie alle Konten 3000–6799 ohne 5790, Ertrag minus Aufwand.
"""

from .basis import ergebnis, quote

NR = "K8"
KENNUNG = "ebitda"
NAME = "Betriebsergebnis vor Abschreibungen (EBITDA)"
ART = "zeitraum"
EINHEIT = "CHF"
KATALOGVERSION = "1.0"


def berechne(ctx, von, bis):
    brutto = ctx.kennzahl("bruttogewinn", von, bis)["wert"]
    personal = ctx.kennzahl("personalaufwand", von, bis)["wert"]
    uebriger = ctx.kennzahl("uebriger_betrieblicher_aufwand", von, bis)["wert"]
    kurs = ctx.kennzahl("kursdifferenzen", von, bis)["wert"]
    wert = brutto - personal - uebriger + kurs

    # Zweiter Weg direkt über die Konten. Weichen sie ab, keine Zahl, sondern ein Fehler
    direkt = -sum(z["saldo"] for z in ctx.salden(ctx.kontenbereich(3000, 6799, ohne=(5790,)), von, bis))
    if abs(direkt - wert) > 0.005:
        raise RuntimeError(f"EBITDA widersprüchlich: Stufen {wert:.2f}, Konten 3000–6799 {direkt:.2f}")

    erloes = ctx.kennzahl("nettoerloes", von, bis)["wert"]
    marge, grund = quote(wert, erloes, "der Nettoerlös")
    return ergebnis(wert, [
        {"kennung": "bruttogewinn", "name": "Bruttogewinn", "wert": brutto},
        {"kennung": "personalaufwand", "name": "Personalaufwand", "wert": -personal},
        {"kennung": "uebriger_betrieblicher_aufwand", "name": "Übriger betrieblicher Aufwand", "wert": -uebriger},
        {"kennung": "kursdifferenzen", "name": "Kursdifferenzen (netto)", "wert": kurs},
    ], [grund] if grund else [], marge=marge)
