"""B3 Übriger betrieblicher Aufwand: Raum, Unterhalt, Fahrzeuge, Versicherungen, Energie, Verwaltung, Werbung

Regel im Katalog, Abschnitt B3. Konten 6000–6799.
"""

from .basis import summe_konten

NR = "B3"
KENNUNG = "uebriger_betrieblicher_aufwand"
NAME = "Übriger betrieblicher Aufwand"
ART = "zeitraum"
EINHEIT = "CHF"
KATALOGVERSION = "1.0"


def berechne(ctx, von, bis):
    konten = ctx.kontenbereich(6000, 6799, ohne=())
    # Vorzeichen 1: Aufwand positiv
    return summe_konten(ctx, konten, von, bis, vorzeichen=1)
