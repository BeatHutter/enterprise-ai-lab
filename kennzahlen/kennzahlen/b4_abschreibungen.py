"""B4 Abschreibungen: Abschreibungen und Wertberichtigungen auf dem Anlagevermögen

Regel im Katalog, Abschnitt B4. Konten 6800–6899.
"""

from .basis import summe_konten

NR = "B4"
KENNUNG = "abschreibungen"
NAME = "Abschreibungen"
ART = "zeitraum"
EINHEIT = "CHF"
KATALOGVERSION = "1.0"


def berechne(ctx, von, bis):
    konten = ctx.kontenbereich(6800, 6899, ohne=())
    # Vorzeichen 1: Aufwand positiv
    return summe_konten(ctx, konten, von, bis, vorzeichen=1)
