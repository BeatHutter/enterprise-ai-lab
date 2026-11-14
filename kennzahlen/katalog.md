# Kennzahlen-Katalog der Muster AG

**Version 1.0, freigegeben am 3.11.2026 durch Beat Hutter.** Änderungen nur durch Beat. Jede Änderung einer Regel erhöht die Version der Kennzahl.

Dieser Katalog sagt, was jede Kennzahl bei der Muster AG bedeutet und wie sie gerechnet wird. Für jede Kennzahl gibt es genau einen Rechenweg. Wer eine Kennzahl braucht, ruft den Rechenweg auf und zählt nicht selbst zusammen. So erscheint immer dieselbe Zahl.

Begriffe nach Obligationenrecht (Art. 959b OR, Gliederung der Erfolgsrechnung nach dem Gesamtkostenverfahren) und Schweizer KMU-Kontenrahmen. Massgebend für die Konten ist der Kontenplan in Odoo (Schweiz - Buchhaltung, `l10n_ch`), gelesen am 3.11.2026.

## Grundregeln

Sie gelten für alle Kennzahlen, ausser eine Kennzahl sagt ausdrücklich etwas anderes.

| Regel | Festlegung |
| --- | --- |
| Quelle | Buchungszeilen in Odoo (`account.move.line`). Nicht die Rechnungsköpfe, nicht die Verkaufsaufträge |
| Nur gebuchte Belege | Nur Zeilen aus Belegen mit Status «Gebucht» (`parent_state = posted`). Entwürfe und stornierte Belege zählen nicht. Eine gebuchte Stornobuchung zählt und hebt den ursprünglichen Beleg auf |
| Alle Journale | Kundenrechnungen, Lieferantenrechnungen, Bank, Sonstige Vorgänge und Kursdifferenzen zählen gleich. Massgebend ist das Konto, nicht das Journal |
| Datum | Buchungsdatum der Zeile (`date`). Ein Zeitraum «von bis» schliesst beide Tage ein. Bestände gelten per Stichtag, Ende des Tages |
| Konten | Nach Kontonummer aus dem Odoo-Kontenplan, nicht nach Kontoart. Die Kontoarten der Lokalisierung sind teilweise falsch (Anhang B) |
| Ohne MWST | Erfolgskonten sind netto. Die MWST liegt auf eigenen Konten (1170, 1171, 2200) und zählt nirgends mit. Ausnahme: Debitorenbestände enthalten die MWST, weil der Kunde sie schuldet |
| In CHF | Betrag in Hauswährung CHF (`balance`). Belege in EUR rechnet Odoo mit dem Kurs am Buchungsdatum um. Kursdifferenzen bei der Zahlung sind eine eigene Grösse (Baustein B2) |
| Gutschriften | Eine Gutschrift mindert die Kennzahl im Monat ihres Buchungsdatums. Sie wird nicht auf den Monat der ursprünglichen Rechnung zurückgerechnet |
| Teil- und Anzahlungsrechnungen | Jede gebuchte Kundenrechnung zählt mit ihrem Buchungsdatum, auch Teil- und Anzahlungsrechnungen |
| Vorzeichen | Ertrag und Aufwand werden positiv ausgewiesen. Ergebnisse sind positiv bei Gewinn, negativ bei Verlust. Odoo speichert Soll minus Haben, Ertragskonten werden darum mit −1 multipliziert |
| Stammdaten | Zuordnungen aus Stammdaten (z. B. das Kundensegment) gelten nach heutigem Stand. Odoo führt keine Geschichte dieser Felder |
| Darstellung | Gerechnet auf den Rappen. Beträge als CHF 1'234.50, Quoten in Prozent mit einer Nachkommastelle (40.5 %), Tage ganzzahlig, Datum als 31.10.2026 |

## Übersicht

| Nr | Kennzahl | Kennung | Art | Kurzformel |
| --- | --- | --- | --- | --- |
| K1 | Nettoerlös | `nettoerloes` | Zeitraum | Konten 3000–3899 ohne 3806 |
| K2 | Nettoerlös nach Kundensegment | `nettoerloes_nach_segment` | Zeitraum | K1, aufgeteilt nach Branche des Kunden |
| K3 | Materialaufwand | `materialaufwand` | Zeitraum | Konten 4000–4999 ohne 4906 |
| K4 | Materialquote | `materialquote` | Zeitraum | K3 ÷ K1 |
| K5 | Bruttogewinn | `bruttogewinn` | Zeitraum | K1 + B1 − K3 |
| K6 | Bruttogewinnmarge | `bruttogewinnmarge` | Zeitraum | K5 ÷ K1 |
| K7 | Personalaufwand | `personalaufwand` | Zeitraum | Konten 5000–5999 ohne 5790 |
| K8 | Betriebsergebnis vor Abschreibungen (EBITDA) | `ebitda` | Zeitraum | K5 + B2 − K7 − B3 |
| K9 | Betriebsergebnis (EBIT) | `ebit` | Zeitraum | K8 − B4 |
| K10 | Offene Debitoren mit Altersstruktur | `debitoren_altersstruktur` | Stichtag | offene Posten Konto 1100 nach Tagen seit Fälligkeit |
| K11 | Debitorenfrist (DSO) | `debitorenfrist` | Zeitraum | durchschnittlicher Debitorenbestand ÷ Kundenumsatz inkl. MWST × Tage |

Bausteine, die in mehreren Kennzahlen vorkommen:

| Nr | Baustein | Kennung | Konten |
| --- | --- | --- | --- |
| B1 | Bestandesänderungen | `bestandesaenderungen` | 3900–3999 |
| B2 | Kursdifferenzen (netto) | `kursdifferenzen` | 3806 und 4906 |
| B3 | Übriger betrieblicher Aufwand | `uebriger_betrieblicher_aufwand` | 6000–6799 |
| B4 | Abschreibungen | `abschreibungen` | 6800–6899 |

## Aufbau der Erfolgsrechnung

So greifen Kennzahlen und Bausteine ineinander. Jede Zeile ist eine eigene Grösse mit eigenem Rechenweg.

| Stufe | Konten | Kennung |
| --- | --- | --- |
| Nettoerlöse aus Lieferungen und Leistungen | 3000–3899 ohne 3806 | K1 |
| + Bestandesänderungen | 3900–3999 | B1 |
| − Materialaufwand | 4000–4999 ohne 4906 | K3 |
| **= Bruttogewinn** | | K5 |
| − Personalaufwand | 5000–5999 ohne 5790 | K7 |
| − Übriger betrieblicher Aufwand | 6000–6799 | B3 |
| ± Kursdifferenzen (netto) | 3806, 4906 | B2 |
| **= Betriebsergebnis vor Abschreibungen (EBITDA)** | | K8 |
| − Abschreibungen | 6800–6899 | B4 |
| **= Betriebsergebnis (EBIT)** | | K9 |

Kurz gesagt: EBITDA = alle Konten 3000–6799 (Ertrag minus Aufwand), ohne 5790. Unter dem EBIT folgen Finanzerfolg (6900–6999), betriebliche Nebenerfolge (Klasse 7), betriebsfremder und ausserordentlicher Erfolg (Klasse 8) und direkte Steuern (8900). Sie gehören in dieser ersten Runde zu keiner Kennzahl.

---

## K1 Nettoerlös

**Bedeutung:** Was die Muster AG ihren Kunden für Produkte und Dienstleistungen in Rechnung gestellt hat, ohne MWST und nach Abzug von Rabatten, Gutschriften und Debitorenverlusten.

**Regel**

- Konten 3000 bis 3899, ohne 3806.
- Darin enthalten: Produktionserlöse (3000), Handelserlöse (3200), Dienstleistungserlöse (3400), übrige Erlöse (3600), Eigenleistungen und Eigenverbrauch (3700) und die Erlösminderungen 3800 bis 3899 ohne 3806 (Rabatte, Skonti, Debitorenverluste, Inkasso, Versand).
- Ohne 3806 Kursdifferenzen, weil Odoo dort alle Kursgewinne bucht, auch die aus Lieferantenrechnungen (Anhang B). Sie stehen im Baustein B2.
- Ohne Bestandesänderungen 3900 bis 3999 (Baustein B1).
- Nur gebuchte Belege, Buchungsdatum, ohne MWST, in CHF, Gutschriften mindern im Monat ihrer Buchung (Grundregeln).
- Vorzeichen: Ertrag positiv. Wert = −(Summe `balance`).

**Umsetzung in Odoo**

- Modell `account.move.line`
- Filter: `parent_state = posted`, `date` im Zeitraum, `account_id.code` von 3000 bis 3899, `account_id.code != 3806`
- Summe: `balance`, mal −1
- Ausgabe zusätzlich pro Konto, damit der Wert nachvollziehbar ist

**Abgleich:** OCA-Saldenliste (Trial Balance) für denselben Zeitraum, nur gebuchte Belege: Summe der Konten 3000 bis 3899 ohne 3806 muss auf den Rappen gleich sein. Die MIS-Vorlage «Profit & Loss» zeigt Ertrag und Aufwand nach Kontoart, nicht nach Kontenbereich. Ihr Ertragstotal enthält auch 3806, 3900 bis 3999 und Konten der Klassen 7 und 8. Abgleich dort nur über die Einzelkonten.

**Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

---

## K2 Nettoerlös nach Kundensegment

**Bedeutung:** Der Nettoerlös aufgeteilt auf die Kundengruppen der Muster AG, damit man sieht, welche Gruppe wie viel beiträgt.

**Regel**

- Gleiche Konten und Regeln wie K1.
- Segment = Branche des Kunden in Odoo. Massgebend ist die Firma, nicht die Kontaktperson: bei einer Kontaktperson die Branche ihrer Firma.
- Segmente der Muster AG: Gemeinden und Städte, Immobilienverwaltungen und Genossenschaften, Garten- und Landschaftsbau, Schulgemeinden, Hotels und Bergbahnen.
- Zeilen ohne Kunde oder mit einem Kunden ohne Branche kommen in «ohne Segment». Sie werden nie weggelassen.
- Die Summe aller Segmente ist gleich K1.
- Zuordnung nach heutigem Stand der Stammdaten. Wechselt ein Kunde die Branche, wandert sein ganzer Erlös mit, auch der vergangene.
- Anteil eines Segments = Nettoerlös des Segments ÷ K1.

**Umsetzung in Odoo**

- Modell `account.move.line`, gleicher Filter wie K1
- Gruppiert nach `partner_id`, danach Branche über `res.partner`: `commercial_partner_id.industry_id`
- Branche ist `res.partner.industry`

**Abgleich:** Kein Odoo-Bericht gruppiert nach Branche. Prüfung in zwei Schritten: (1) Summe der Segmente = K1 auf den Rappen. (2) Stichprobe: Rechnungsanalyse (Buchhaltung › Berichte), gefiltert auf die Kunden eines Segments, Total ohne MWST = Wert des Segments, solange alle Erlöse über Kundenrechnungen gebucht sind.

**Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

---

## K3 Materialaufwand

**Bedeutung:** Was die Muster AG für Material, Fremdleistungen und eingekaufte Dienstleistungen ausgegeben hat, die direkt in ihre Produkte und Aufträge eingehen, ohne MWST.

**Regel**

- Konten 4000 bis 4999, ohne 4906.
- Darin enthalten: Materialaufwand (4000), Bezugskosten wie Fracht und Zoll (4070 bis 4072), Handelswaren (4200), bezogene Dienstleistungen und Fremdleistungen (4400), Energie für die Produktion (4500 bis 4540), Bestandesänderungen Material (4800, 4801), Aufwandminderungen wie Einkaufsrabatte und Skonti (4900 bis 4999 ohne 4906).
- Ohne 4906 Kursdifferenzen, weil Odoo dort alle Kursverluste bucht, auch die aus Kundenrechnungen (Anhang B). Sie stehen im Baustein B2.
- Zeitpunkt: Buchungsdatum der Lieferantenrechnung. Die Muster AG führt keine Lagerbewertung. Material wird beim Einkauf zu Aufwand, eine Abgrenzung gibt es nicht.
- Belege in EUR: Betrag in CHF zum Kurs am Buchungsdatum.
- Gutschriften von Lieferanten mindern den Materialaufwand im Monat ihrer Buchung.
- Vorzeichen: Aufwand positiv. Wert = Summe `balance`.

**Umsetzung in Odoo**

- Modell `account.move.line`
- Filter: `parent_state = posted`, `date` im Zeitraum, `account_id.code` von 4000 bis 4999, `account_id.code != 4906`
- Summe: `balance`
- Ausgabe zusätzlich pro Konto

**Abgleich:** OCA-Saldenliste, Summe der Konten 4000 bis 4999 ohne 4906.

**Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

---

## K4 Materialquote

**Bedeutung:** Welcher Anteil des Nettoerlöses für Material und Fremdleistungen draufgeht.

**Regel**

- Materialquote = K3 Materialaufwand ÷ K1 Nettoerlös, in Prozent.
- Beide Werte für denselben Zeitraum und nach denselben Grundregeln.
- Ist der Nettoerlös null oder negativ, ist die Quote «nicht berechenbar». Das Skript gibt dann keinen Wert aus, sondern den Grund.

**Umsetzung in Odoo:** keine eigene Abfrage. Das Skript ruft die Rechenwege von K1 und K3 auf und teilt.

**Abgleich:** über K1 und K3. Kein Odoo-Bericht zeigt die Quote direkt.

**Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

---

## K5 Bruttogewinn

**Bedeutung:** Was vom Nettoerlös nach Abzug des Materialaufwands übrig bleibt, um Löhne, Miete und alle übrigen Kosten zu decken.

**Regel**

- Bruttogewinn = K1 Nettoerlös + B1 Bestandesänderungen − K3 Materialaufwand.
- Bei der Muster AG sind die Bestandesänderungen null, weil sie keine Lagerbewertung führt. Der Baustein bleibt in der Formel, damit sie auch mit Lager stimmt.
- Kursdifferenzen gehören nicht zum Bruttogewinn (Baustein B2, zwischen Bruttogewinn und EBITDA).
- Gemeint ist der Bruttogewinn nach Materialaufwand (oft «Bruttogewinn I» genannt). Der Bruttogewinn nach Personalaufwand («Bruttogewinn II») ist nicht Teil dieser Runde.

**Umsetzung in Odoo:** Summe der Rechenwege K1, B1 und K3.

**Abgleich:** OCA-Saldenliste: Konten 3000 bis 4999 ohne 3806 und 4906, Ertrag minus Aufwand.

**Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

---

## K6 Bruttogewinnmarge

**Bedeutung:** Wie viele Rappen von jedem Franken Nettoerlös nach dem Materialaufwand übrig bleiben.

**Regel**

- Bruttogewinnmarge = K5 Bruttogewinn ÷ K1 Nettoerlös, in Prozent.
- Ohne Bestandesänderungen gilt: Bruttogewinnmarge = 100 % − Materialquote.
- Nettoerlös null oder negativ: «nicht berechenbar», mit Grund.

**Umsetzung in Odoo:** keine eigene Abfrage, aus K5 und K1.

**Abgleich:** über K5 und K1.

**Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

---

## K7 Personalaufwand

**Bedeutung:** Was die Muster AG ihre Mitarbeitenden kostet: Löhne, Sozialleistungen und übrige Personalkosten.

**Regel**

- Konten 5000 bis 5999, ohne 5790.
- Darin enthalten: Lohnaufwand (5000 bis 5099), Honorare des Verwaltungsrats (5601), Sozialversicherungsaufwand (5700 bis 5799 ohne 5790), übriger Personalaufwand wie Ausbildung und Spesen (5800 bis 5899), Leistungen Dritter wie Temporärpersonal (5900).
- Ohne 5790 «IS-Quellensteuer». Die Lokalisierung führt es als Verbindlichkeit, also als Bilanzkonto, obwohl die Nummer in Klasse 5 liegt (Anhang B).
- Vorzeichen: Aufwand positiv.

**Nicht verfügbar**

- Aufteilung nach Bereich, Person oder Lohnart: nicht verfügbar. Die Muster AG führt keine Lohnbuchhaltung in Odoo. Die Löhne kommen als eine Sammelbuchung pro Monat.
- Personalaufwand pro Kopf und Anzahl Mitarbeitende: nicht verfügbar. Odoo enthält keine Personaldaten.
- Verfügbar ist die Aufteilung nach Konto, z. B. Löhne (5000) und Sozialleistungen (5700).

**Umsetzung in Odoo**

- Modell `account.move.line`
- Filter: `parent_state = posted`, `date` im Zeitraum, `account_id.code` von 5000 bis 5999, `account_id.code != 5790`
- Summe: `balance`, Ausgabe pro Konto

**Abgleich:** OCA-Saldenliste, Summe der Konten 5000 bis 5999 ohne 5790.

**Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

---

## K8 Betriebsergebnis vor Abschreibungen (EBITDA)

**Bedeutung:** Was die Muster AG mit ihrem Betrieb verdient, bevor Abschreibungen, Finanzerfolg, Nebenerfolge, ausserordentliche Posten und Steuern abgezogen sind.

**Regel**

- EBITDA = K5 Bruttogewinn − K7 Personalaufwand − B3 übriger betrieblicher Aufwand + B2 Kursdifferenzen (netto).
- Gleichbedeutend: alle Konten 3000 bis 6799 (Ertrag minus Aufwand), ohne 5790.
- Nicht enthalten: Abschreibungen (6800 bis 6899), Finanzaufwand und Finanzertrag (6900 bis 6999), Klasse 7, Klasse 8 und direkte Steuern.
- Vorzeichen: positiv = Gewinn.
- EBITDA-Marge = EBITDA ÷ K1 Nettoerlös, in Prozent. Das Skript gibt sie mit aus.

**Umsetzung in Odoo:** Summe der Rechenwege K5, K7, B3 und B2. Zur Kontrolle rechnet das Skript zusätzlich direkt über die Konten 3000 bis 6799 ohne 5790. Weichen die zwei Wege ab, meldet es einen Fehler statt einer Zahl.

**Abgleich:** OCA-Saldenliste, Konten 3000 bis 6799 ohne 5790.

**Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

---

## K9 Betriebsergebnis (EBIT)

**Bedeutung:** Was die Muster AG mit ihrem Betrieb verdient, nachdem auch die Abnützung von Maschinen, Fahrzeugen und Einrichtungen (Abschreibungen) abgezogen ist.

**Regel**

- EBIT = K8 EBITDA − B4 Abschreibungen.
- Gleichbedeutend: alle Konten 3000 bis 6899 (Ertrag minus Aufwand), ohne 5790.
- Abschreibungen bucht die Muster AG einmal im Jahr, im Dezember. Für einen Zeitraum ohne Dezember enthält das EBIT darum keine Abschreibungen. Das Skript rechnet keinen Anteil hoch und vermerkt das in der Ausgabe.
- EBIT-Marge = EBIT ÷ K1, in Prozent, wird mit ausgegeben.

**Umsetzung in Odoo:** K8 minus B4.

**Abgleich:** OCA-Saldenliste, Konten 3000 bis 6899 ohne 5790.

**Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

---

## K10 Offene Debitoren mit Altersstruktur

**Bedeutung:** Wie viel Geld Kunden der Muster AG an einem Stichtag noch schulden, und wie lange diese Beträge schon fällig sind.

**Regel**

- Stichtag frei wählbar, Ende des Tages.
- Konto 1100 Debitoren. Andere Konten der Kontoart «Forderung» (1101 Kassensystem, 1176 Quellensteuer) zählen nicht.
- Offener Posten = Betrag einer gebuchten Rechnungszeile auf 1100 (inkl. MWST) minus alle Zahlungen und Gutschriften, die bis zum Stichtag mit ihr verrechnet sind. Verrechnungen nach dem Stichtag zählen nicht. So gilt die Zahl auch für einen Stichtag in der Vergangenheit.
- Nur Posten, deren Buchungsdatum am oder vor dem Stichtag liegt.
- Alter = Stichtag minus Fälligkeitsdatum des Postens, in Kalendertagen. Massgebend ist das Fälligkeitsdatum, nicht das Rechnungsdatum.

| Stufe | Alter |
| --- | --- |
| nicht fällig | 0 Tage oder weniger (Fälligkeit am oder nach dem Stichtag) |
| 1–30 Tage | 1 bis 30 |
| 31–60 Tage | 31 bis 60 |
| 61–90 Tage | 61 bis 90 |
| über 90 Tage | 91 und mehr |

- Haben-Posten auf 1100, die am Stichtag mit keiner Rechnung verrechnet sind (Vorauszahlungen, nicht zugeordnete Gutschriften), stehen in einer eigenen Zeile «nicht zugeordnet» und mindern das Total.
- Total = Summe aller Stufen und der Zeile «nicht zugeordnet» = Saldo von Konto 1100 per Stichtag.
- Ausgabe pro Stufe: Betrag in CHF, Anzahl Posten, Anteil am Total. Wahlweise zusätzlich pro Kunde (Firma).
- Alle Kundenrechnungen der Muster AG sind in CHF. Käme eine Rechnung in Fremdwährung dazu, zählt der offene Betrag in CHF (`amount_residual` in Hauswährung).

**Umsetzung in Odoo**

- Modell `account.move.line`
- Filter: `parent_state = posted`, `account_id.code = 1100`, `date <= Stichtag`
- Offener Betrag per Stichtag: `balance` minus Verrechnungen aus `account.partial.reconcile` (Soll- und Habenseite) mit `max_date <= Stichtag`
- Fälligkeit: `date_maturity`
- Kunde: `partner_id.commercial_partner_id`

**Abgleich:** OCA-Altersliste (Aged Partner Balance), Stichtag, Konto 1100, nur gebuchte Belege. Ihre Spalten «Nicht fällig», «1–30», «31–60», «61–90» stimmen mit unseren überein. «91–120» und «älter» zusammen sind unser «über 90 Tage». Das Total muss gleich sein wie in der OCA-Liste «Offene Posten» (Open Items) und wie der Saldo von 1100 in der OCA-Saldenliste per Stichtag.

**Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

---

## K11 Debitorenfrist (DSO)

**Bedeutung:** Wie viele Tage es im Durchschnitt dauert, bis Kunden ihre Rechnungen bezahlen.

**Regel**

- Debitorenfrist = durchschnittlicher Debitorenbestand ÷ Kundenumsatz inkl. MWST im Zeitraum × Anzahl Tage im Zeitraum.
- Debitorenbestand = Saldo von Konto 1100, inkl. MWST.
- Durchschnitt = Mittelwert aus dem Bestand am Vortag des Zeitraumbeginns und den Beständen an jedem Monatsende im Zeitraum. Beispiel Januar bis Oktober: 31.12. des Vorjahres und die zehn Monatsenden, zusammen elf Werte.
- Kundenumsatz inkl. MWST = Total der gebuchten Kundenrechnungen minus Total der gebuchten Kundengutschriften, nach Buchungsdatum im Zeitraum. Inkl. MWST, weil auch der Debitorenbestand die MWST enthält.
- Endet der Zeitraum nicht an einem Monatsende, zählt zusätzlich der Bestand am letzten Tag des Zeitraums.
- Tage = Kalendertage im Zeitraum, beide Grenzen eingeschlossen (Januar bis Oktober 2026: 304 Tage).
- Ergebnis in ganzen Tagen. Zum Vergleich gibt das Skript die vereinbarte Zahlungsfrist mit aus (30 Tage netto).
- Kundenumsatz null: «nicht berechenbar», mit Grund.

**Umsetzung in Odoo**

- Bestände: `account.move.line`, `parent_state = posted`, `account_id.code = 1100`, `date <= Monatsende`, Summe `balance`
- Kundenumsatz: `account.move`, `state = posted`, `move_type in (out_invoice, out_refund)`, `date` im Zeitraum, Summe `amount_total_signed`

**Abgleich:** Kein Odoo-Bericht zeigt die Debitorenfrist. Die Bausteine werden einzeln geprüft: Bestände mit der OCA-Saldenliste (Saldo 1100 per Monatsende), Kundenumsatz mit dem Journal «Kundenrechnungen» bzw. der Rechnungsanalyse (Total inkl. MWST).

**Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

---

## Bausteine

### B1 Bestandesänderungen

- Konten 3900 bis 3999, Ertrag positiv.
- Bestandesänderungen an unfertigen und fertigen Erzeugnissen und an nicht fakturierten Dienstleistungen (Art. 959b Abs. 2 Ziff. 2 OR).
- Bei der Muster AG nicht geführt (keine Lagerbewertung), der Wert ist null.
- **Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

### B2 Kursdifferenzen (netto)

- Konten 3806 (Kursgewinne) und 4906 (Kursverluste). Wert = Gewinne minus Verluste, positiv = Gewinn.
- Entstehen, wenn eine Rechnung in Fremdwährung zu einem anderen Kurs bezahlt wird als gebucht.
- Odoo bucht jeden Kursgewinn auf 3806 und jeden Kursverlust auf 4906, egal ob er aus einer Kunden- oder einer Lieferantenrechnung stammt. Darum stehen sie weder im Nettoerlös noch im Materialaufwand.
- **Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

### B3 Übriger betrieblicher Aufwand

- Konten 6000 bis 6799, Aufwand positiv.
- Raumaufwand, Unterhalt und Reparaturen, Fahrzeuge und Leasing, Versicherungen, Energie und Entsorgung, Verwaltung und Informatik, Werbung, sonstiger betrieblicher Aufwand.
- **Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

### B4 Abschreibungen

- Konten 6800 bis 6899, Aufwand positiv.
- Abschreibungen und Wertberichtigungen auf Positionen des Anlagevermögens (Art. 959b Abs. 2 Ziff. 6 OR).
- **Version:** 1.0, freigegeben am 3.11.2026 (Beat Hutter).

---

## Anhang A: bebuchte Konten und ihre Kennzahl

Konten mit Buchungen in 2025 oder 2026, Name wie in Odoo. Alle übrigen Konten der Bereiche zählen nach denselben Regeln, sobald sie bebucht werden.

| Konto | Name in Odoo | gehört zu |
| --- | --- | --- |
| 1100 | Forderungen aus Lieferungen und Leistungen (Debitoren) | K10, K11 |
| 3000 | Verkauf von Produkten (Herstellung) | K1 |
| 3400 | Erlöse aus Dienstleistungen | K1 |
| 3806 | Wechselkursdifferenzen | B2 |
| 4000 | Materialaufwand Produktion | K3 |
| 4400 | Aufwand für bezogene Dienstleistungen | K3 |
| 4906 | Wechselkursdifferenzen | B2 |
| 5000 | Löhne und Gehälter | K7 |
| 5700 | Sozialleistungen | K7 |
| 6000 | Miete | B3 |
| 6100 | Kosten für Wartung und Reparatur | B3 |
| 6260 | Fahrzeugleasing und -vermietung | B3 |
| 6300 | Versicherungsprämien | B3 |
| 6400 | Energie- und Entsorgungsaufwand | B3 |
| 6500 | Verwaltungskosten | B3 |
| 6570 | IT Leasing | B3 |
| 6600 | Werbeaufwand | B3 |
| 6800 | Abschreibung | B4 |
| 8900 | Direkte Steuern | keine (unter dem EBIT) |

## Anhang B: Abweichungen des Odoo-Kontenplans vom KMU-Kontenrahmen

Gelesen aus Odoo am 3.11.2026. Die Bezeichnungen des KMU-Kontenrahmens sind sinngemäss wiedergegeben.

**Kontoarten, die nicht zur Nummer passen** (darum rechnet der Katalog nach Kontonummer)

| Konto | Odoo | Richtig wäre |
| --- | --- | --- |
| 5790 IS-Quellensteuer | Verbindlichkeit (Bilanz) | Die Nummer liegt im Personalaufwand. Der Katalog schliesst das Konto aus |
| 6950 Finanzerträge | Aufwand | Ertrag. Liegt unter dem EBIT, betrifft keine Kennzahl dieser Runde |
| 8510 «Außerordentliche Ausgaben» | Ertrag | Name falsch, gemeint ist ausserordentlicher Ertrag. Liegt unter dem EBIT |
| 1400–1489, 1510–1609, 1700–1779, 1850 | Umlaufvermögen | Anlagevermögen bzw. nicht einbezahltes Kapital. Betrifft keine Kennzahl dieser Runde |

1500, 1509 und 6800 sind seit dem 1.11.2026 korrigiert.

**Konten, die Odoo nach Vorzeichen statt nach Herkunft bebucht**

| Konto | Odoo bucht dort | KMU-Kontenrahmen |
| --- | --- | --- |
| 3806 Wechselkursdifferenzen | jeden Kursgewinn, auch aus Lieferantenrechnungen | Kursdifferenzen auf Debitoren |
| 4906 Wechselkursdifferenzen | jeden Kursverlust, auch aus Kundenrechnungen | Kursdifferenzen auf Kreditoren |
| 3801 Rabatte und Preisnachlässe | Skonto, den Lieferanten gewähren (Einstellung der Firma) | Erlösminderung gegenüber Kunden |
| 4901 Rabatte und Preisnachlässe | Skonto, den Kunden abziehen (Einstellung der Firma) | Aufwandminderung gegenüber Lieferanten |

3801 und 4901 sind bisher nicht bebucht. Werden Skonti gebucht, muss der Katalog diese zwei Konten neu zuordnen.

**Bezeichnungen** (Auswahl der Konten, die Kennzahlen betreffen)

| Konto | Name in Odoo | KMU-Kontenrahmen |
| --- | --- | --- |
| 1100 | Forderungen aus Lieferungen und Leistungen (Debitoren) | Forderungen aus Lieferungen und Leistungen, im Alltag Debitoren |
| 2000 | Verbindlichkeiten aus Lieferungen und Leistungen (Gläubiger) | Verbindlichkeiten aus Lieferungen und Leistungen, im Alltag Kreditoren |
| 2200 | Geschuldete MwSt. (Umsatzsteuer) | Geschuldete MWST |
| 3000 | Verkauf von Produkten (Herstellung) | Produktionserlöse |
| 3400 | Erlöse aus Dienstleistungen | Dienstleistungserlöse |
| 3800 | Erlösminderung | Erlösminderungen |
| 3805 | Verluste aus Forderungsausfällen | Debitorenverluste |
| 3806, 4906 | Wechselkursdifferenzen | Kursdifferenzen |
| 4000 | Materialaufwand Produktion | Materialaufwand |
| 4900 | Finanzielle Ermäßigungen | Aufwandminderungen |
| 5000 | Löhne und Gehälter | Lohnaufwand |
| 5700 | Sozialleistungen | Sozialversicherungsaufwand |
| 6800 | Abschreibung | Abschreibungen und Wertberichtigungen auf Positionen des Anlagevermögens |
| 8500, 8510 | Außerordentliche Ausgaben | ausserordentlicher Aufwand bzw. Ertrag |

Die Namen in Odoo bleiben, wie sie sind. In Berichten und Antworten gelten die Begriffe dieses Katalogs.
