"""K7 Personalaufwand: Löhne, Sozialleistungen, übriger Personalaufwand

Regel im Katalog, Abschnitt K7. Konten 5000–5999 ohne 5790.
"""

from .basis import summe_konten

NR = "K7"
KENNUNG = "personalaufwand"
NAME = "Personalaufwand"
ART = "zeitraum"
EINHEIT = "CHF"
KATALOGVERSION = "1.0"


def berechne(ctx, von, bis):
    konten = ctx.kontenbereich(5000, 5999, ohne=(5790,))
    # Vorzeichen 1: Aufwand positiv
    return summe_konten(ctx, konten, von, bis, vorzeichen=1)
