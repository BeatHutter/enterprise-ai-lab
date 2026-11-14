"""K1 Nettoerlös: Erlöse ohne MWST nach Erlösminderungen

Regel im Katalog, Abschnitt K1. Konten 3000–3899 ohne 3806.
"""

from .basis import summe_konten

NR = "K1"
KENNUNG = "nettoerloes"
NAME = "Nettoerlös"
ART = "zeitraum"
EINHEIT = "CHF"
KATALOGVERSION = "1.0"


def berechne(ctx, von, bis):
    konten = ctx.kontenbereich(3000, 3899, ohne=(3806,))
    # Vorzeichen -1: Ertrag positiv (Odoo speichert Soll minus Haben)
    return summe_konten(ctx, konten, von, bis, vorzeichen=-1)
