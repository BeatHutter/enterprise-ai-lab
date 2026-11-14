"""B1 Bestandesänderungen: Bestandesänderungen an Erzeugnissen und nicht fakturierten Dienstleistungen

Regel im Katalog, Abschnitt B1. Konten 3900–3999.
"""

from .basis import summe_konten

NR = "B1"
KENNUNG = "bestandesaenderungen"
NAME = "Bestandesänderungen"
ART = "zeitraum"
EINHEIT = "CHF"
KATALOGVERSION = "1.0"


def berechne(ctx, von, bis):
    konten = ctx.kontenbereich(3900, 3999, ohne=())
    # Vorzeichen -1: Ertrag positiv (Odoo speichert Soll minus Haben)
    return summe_konten(ctx, konten, von, bis, vorzeichen=-1)
