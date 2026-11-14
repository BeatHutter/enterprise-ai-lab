"""K6 Bruttogewinnmarge = Bruttogewinn ÷ Nettoerlös, in Prozent (Katalog, K6)."""

from .basis import ergebnis, quote

NR = "K6"
KENNUNG = "bruttogewinnmarge"
NAME = "Bruttogewinnmarge"
ART = "zeitraum"
EINHEIT = "%"
KATALOGVERSION = "1.0"


def berechne(ctx, von, bis):
    brutto = ctx.kennzahl("bruttogewinn", von, bis)["wert"]
    erloes = ctx.kennzahl("nettoerloes", von, bis)["wert"]
    wert, grund = quote(brutto, erloes, "der Nettoerlös")
    return ergebnis(wert, [{"kennung": "bruttogewinn", "name": "Bruttogewinn", "wert": brutto},
                           {"kennung": "nettoerloes", "name": "Nettoerlös", "wert": erloes}],
                    [grund] if grund else [])
