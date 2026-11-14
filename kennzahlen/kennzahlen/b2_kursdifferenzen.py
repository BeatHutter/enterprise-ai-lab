"""B2 Kursdifferenzen (netto): Kursgewinne 3806 minus Kursverluste 4906.

Odoo bucht jeden Kursgewinn auf 3806 und jeden Kursverlust auf 4906, egal ob aus
Kunden- oder Lieferantenrechnungen. Darum ein eigener Baustein (Katalog, B2).
"""

from .basis import summe_konten

NR = "B2"
KENNUNG = "kursdifferenzen"
NAME = "Kursdifferenzen (netto)"
ART = "zeitraum"
EINHEIT = "CHF"
KATALOGVERSION = "1.0"


def berechne(ctx, von, bis):
    konten = [k for k in ctx.konten() if k["code"] in ("3806", "4906")]
    # Vorzeichen -1: Gewinn positiv, Verlust negativ
    return summe_konten(ctx, konten, von, bis, vorzeichen=-1)
