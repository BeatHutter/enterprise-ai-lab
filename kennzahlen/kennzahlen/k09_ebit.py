"""K9 Betriebsergebnis (EBIT) = EBITDA − Abschreibungen (Katalog, K9)."""

from .basis import ergebnis, quote

NR = "K9"
KENNUNG = "ebit"
NAME = "Betriebsergebnis (EBIT)"
ART = "zeitraum"
EINHEIT = "CHF"
KATALOGVERSION = "1.0"


def berechne(ctx, von, bis):
    ebitda = ctx.kennzahl("ebitda", von, bis)["wert"]
    abschreibungen = ctx.kennzahl("abschreibungen", von, bis)
    wert = ebitda - abschreibungen["wert"]
    hinweise = []
    if not abschreibungen["bestandteile"]:
        hinweise.append("Im Zeitraum sind keine Abschreibungen gebucht. Die Muster AG bucht sie einmal "
                        "im Jahr im Dezember. Es wird kein Anteil hochgerechnet.")
    erloes = ctx.kennzahl("nettoerloes", von, bis)["wert"]
    marge, grund = quote(wert, erloes, "der Nettoerlös")
    if grund:
        hinweise.append(grund)
    return ergebnis(wert, [
        {"kennung": "ebitda", "name": "Betriebsergebnis vor Abschreibungen (EBITDA)", "wert": ebitda},
        {"kennung": "abschreibungen", "name": "Abschreibungen", "wert": -abschreibungen["wert"]},
    ], hinweise, marge=marge)
