"""Alle Kennzahlen und Bausteine, in der Reihenfolge des Katalogs."""

from . import (b1_bestandesaenderungen, b2_kursdifferenzen, b3_uebriger_betrieblicher_aufwand,
               b4_abschreibungen, k01_nettoerloes, k02_nettoerloes_nach_segment, k03_materialaufwand,
               k04_materialquote, k05_bruttogewinn, k06_bruttogewinnmarge, k07_personalaufwand, k08_ebitda,
               k09_ebit, k10_debitoren_altersstruktur, k11_debitorenfrist)

_ALLE = (k01_nettoerloes, k02_nettoerloes_nach_segment, k03_materialaufwand, k04_materialquote,
         k05_bruttogewinn, k06_bruttogewinnmarge, k07_personalaufwand, k08_ebitda, k09_ebit,
         k10_debitoren_altersstruktur, k11_debitorenfrist,
         b1_bestandesaenderungen, b2_kursdifferenzen, b3_uebriger_betrieblicher_aufwand, b4_abschreibungen)

MODULE = {m.KENNUNG: m for m in _ALLE}
