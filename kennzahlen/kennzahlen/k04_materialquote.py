"""K4 Materialquote = Materialaufwand ÷ Nettoerlös, in Prozent (Katalog, K4)."""

from .basis import ergebnis, quote

NR = "K4"
KENNUNG = "materialquote"
NAME = "Materialquote"
ART = "zeitraum"
EINHEIT = "%"
KATALOGVERSION = "1.0"


def berechne(ctx, von, bis):
    material = ctx.kennzahl("materialaufwand", von, bis)["wert"]
    erloes = ctx.kennzahl("nettoerloes", von, bis)["wert"]
    wert, grund = quote(material, erloes, "der Nettoerlös")
    return ergebnis(wert, [{"kennung": "materialaufwand", "name": "Materialaufwand", "wert": material},
                           {"kennung": "nettoerloes", "name": "Nettoerlös", "wert": erloes}],
                    [grund] if grund else [])
