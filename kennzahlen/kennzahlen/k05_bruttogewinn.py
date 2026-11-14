"""K5 Bruttogewinn = Nettoerlös + Bestandesänderungen − Materialaufwand (Katalog, K5)."""

from .basis import ergebnis

NR = "K5"
KENNUNG = "bruttogewinn"
NAME = "Bruttogewinn"
ART = "zeitraum"
EINHEIT = "CHF"
KATALOGVERSION = "1.0"


def berechne(ctx, von, bis):
    erloes = ctx.kennzahl("nettoerloes", von, bis)["wert"]
    bestand = ctx.kennzahl("bestandesaenderungen", von, bis)["wert"]
    material = ctx.kennzahl("materialaufwand", von, bis)["wert"]
    return ergebnis(erloes + bestand - material, [
        {"kennung": "nettoerloes", "name": "Nettoerlös", "wert": erloes},
        {"kennung": "bestandesaenderungen", "name": "Bestandesänderungen", "wert": bestand},
        {"kennung": "materialaufwand", "name": "Materialaufwand", "wert": -material},
    ])
