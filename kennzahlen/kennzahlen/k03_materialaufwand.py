"""K3 Materialaufwand: Material, Fremdleistungen und bezogene Dienstleistungen

Regel im Katalog, Abschnitt K3. Konten 4000–4999 ohne 4906.
"""

from .basis import summe_konten

NR = "K3"
KENNUNG = "materialaufwand"
NAME = "Materialaufwand"
ART = "zeitraum"
EINHEIT = "CHF"
KATALOGVERSION = "1.0"


def berechne(ctx, von, bis):
    konten = ctx.kontenbereich(4000, 4999, ohne=(4906,))
    # Vorzeichen 1: Aufwand positiv
    return summe_konten(ctx, konten, von, bis, vorzeichen=1)
