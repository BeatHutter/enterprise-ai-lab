# Use-Case-Katalog Muster AG

Dieser Katalog sammelt die KI-Use-Cases, die wir an der Muster AG prüfen. Jeder Use Case wird nach derselben Vorlage beschrieben. Ziel ist eine ehrliche Bestandesaufnahme: was belegt ist, was plausibel ist und was noch offen ist.

Master ist dieses Dokument im Repository.

## Leitlinie: drei Kernabläufe

1. Vom Kundenkontakt bis zum Geldeingang
2. Vom Einkauf bis zur Zahlung an den Lieferanten
3. Vom Beleg bis zum Abschluss

## Abgrenzung der Simulation

- **Abgedeckt:** ERP und Buchhaltung (Odoo), CRM, E-Mail, Dokumentablage und Firmenwissen (Word, Excel)
- **Vorerst ausserhalb:** Personal und Lohn, MWST-Abrechnung, Bankanbindung, Fertigung, Lager

Use Cases, die einen ausgeklammerten Bereich berühren, werden trotzdem erfasst. Die fehlende Abdeckung steht dann unter «Abdeckungslücken».

## Prozess-IDs

| ID | Prozess |
| --- | --- |
| K1 | Marketing |
| K2 | Verkauf (Anfrage, Offerte, Auftrag) |
| K3 | Leistungserbringung |
| K4 | Lager und Logistik |
| K5 | Fakturierung und Debitoren |
| K6 | Kundendienst |
| U1 | Einkauf und Bestellwesen |
| U2 | Finanzen und Buchhaltung |
| U3 | Personal |
| U4 | Administration und Wissen |
| U5 | IT und Datenschutz |
| F1 | Steuerung und Reporting |
| F2 | Qualität und Compliance |
| KA | Kanäle (E-Mail, Telefon, Website, Post) |

## Rollen (Human in the Loop)

| Rolle | Aufgabe im Ablauf |
| --- | --- |
| Sachbearbeitung | prüft und ergänzt, was der Agent vorbereitet |
| Vorgesetzte Stelle / Geschäftsleitung | gibt frei, typischerweise ab einer Schwelle |
| Buchhaltung | prüft Belege und Zahlungen |
| Agent | bereitet vor, arbeitet unter eigener Identität, nie unter fremdem Login |

Mehrere Rollen werden nur dort ausgearbeitet, wo der Ablauf sie verlangt.

## Vorlage

| Feld | Inhalt | Werte |
| --- | --- | --- |
| ID | UC-Nummer | UC-001, UC-002 … |
| Prozess | Prozess-ID gemäss Tabelle oben | z. B. K2 |
| Komplexitätsklasse | wie anspruchsvoll der Use Case ist | **Basis** (Standardwerkzeuge, kaum Anbindung) · **Integration** (Anbindung an ERP oder Buchhaltung) · **Autonomie** (Agent handelt über mehrere Systeme) |
| Schreibstufe | wie folgenreich das Schreiben im ERP ist (siehe «Schreibstufen» unten) | **1** · **2** · **3** · **–** (schreibt nicht) |
| Ausgangslage | Problem heute, in Alltagssprache | Freitext |
| Lösungsansatz | was die KI konkret tut | ein bis drei Sätze |
| Systemvoraussetzungen | was angebunden sein muss | Liste |
| Kontrollpunkte | welche Rolle an welcher Stelle prüft oder freigibt, mit welcher Befugnis | Liste |
| Abdeckungslücken | was in der Muster AG fehlt, um den Use Case zu prüfen | Liste |
| Validierungsstatus | pro Lücke bzw. pro Lösungsbaustein | **validiert** (getestet) · **plausibel** (gestützt auf Dokumentation, nicht getestet) · **offen** (Annahme) |
| Validierungsexperiment | was geprüft werden muss, um «plausibel» oder «offen» zu klären | Freitext oder «bewusst offen gelassen» |
| Umsetzungsgrad | wie weit der Use Case an der Muster AG geprüft ist | **Konzept** (beschrieben) · **Proof of Concept** (einmal gegen echte Daten durchgespielt) · **Umgesetzt** (läuft wiederholbar) |
| Aufwand / Nutzen | grobe Einschätzung | tief · mittel · hoch |
| Datenschutz und Compliance | nur wo nötig | Freitext |

## Schreibstufen

Ergänzt am 10.11.2026 für den Werkzeug-Server ([architecture.md](architecture.md)). Die Stufe sagt, wie folgenreich ein Schreibzugriff in Odoo ist, und damit, welche Freigabe ein Werkzeug braucht.

| Stufe | Bedeutung | Beispiele | Freigabe im Werkzeug-Server |
| --- | --- | --- | --- |
| **1** | harmlos, umkehrbar | Notiz, Aktivität, Entwurf anlegen | keine, der Mensch arbeitet den Entwurf in Odoo weiter |
| **2** | intern verbindlich | Beleg buchen (Nummer wird vergeben), Kontakt ändern | Freigabe per Knopf |
| **3** | Aussenwirkung oder Geld | versenden, Offerte bestätigen, Zahlung, Bankverbindung | Freigabe per Knopf, oder das Werkzeug gibt es gar nicht |

Grundhaltung: Der grösste Nutzen liegt meist in Stufe 1. Der Agent übernimmt die Tipparbeit, die Entscheidung bleibt beim Menschen in Odoo.

## Übersicht

Erfasst ab 10.11.2026, Umsetzungsgrad nachgeführt am 23.11.2026. UC-001 bis UC-014 schreiben in Odoo und beschränken sich auf die installierten Module (Rechnungsstellung, Verkauf, Einkauf, Kontakte). Erster Leitfall für den Werkzeug-Server war UC-001.

| ID | Titel | Prozess | Komplexität | Schreibstufe | Umsetzungsgrad | Offene Punkte |
| --- | --- | --- | --- | --- | --- | --- |
| UC-001 | Lieferantenrechnung als Entwurf erfassen | U2 | Integration | 1 | Proof of Concept (11.11.2026) | Anhang des PDFs und Rechnungen direkt aus dem Postfach noch offen, vor Stufe 2 Lücke bei der Freigabe schliessen |
| UC-002 | Lieferantenrechnung mit Bestellung abgleichen | U1 | Integration | 1 | Konzept | baut auf UC-001 |
| UC-003 | Bestellung als Entwurf | U1 | Integration | 1 | Konzept | |
| UC-004 | Zahlungen an Lieferanten vorbereiten | U2 | Integration | 1 (3 für die Zahlung) | Konzept | Fälligkeiten unbrauchbar, Bankanbindung ausserhalb |
| UC-005 | Offerte als Entwurf aus einer Anfrage | K2 | Integration | 1 | Proof of Concept (11.11.2026), per Mail getestet (13.11.2026) | Merkmal «braucht Fundament» fehlt |
| UC-006 | Offerten nachfassen | K2 | Integration | 1 | Konzept | |
| UC-007 | Rechnung aus Auftrag als Entwurf | K5 | Integration | 1 (2 fürs Buchen) | Konzept | |
| UC-008 | Mahnungen vorbereiten | K5 | Integration | 1 (3 fürs Versenden) | Konzept | kein Mahnwesen in Community, Altersstufen |
| UC-009 | Gutschrift als Entwurf bei Reklamation | K6 | Integration | 1 | Konzept | |
| UC-010 | Zahlungseingänge offenen Rechnungen zuordnen | K5 | Integration | 2 | Konzept | Bankanbindung ausserhalb |
| UC-011 | Abgrenzungen zum Monatsende als Buchungsentwurf | U2 | Integration | 1 | Konzept | |
| UC-012 | Umbuchung bei Fehlbuchung vorschlagen | U2 | Integration | 1 | Konzept | |
| UC-013 | Kunden und Lieferanten anlegen und nachführen | U4 | Integration | 2 | Umgesetzt für Neukunden (27.11.2026, `kunde_anlegen` mit Freigabe per Knopf) | Dubletten-Sperre, optional verknüpft mit Chance (`UC-029`), keine Lieferanten/Bankkonten |
| UC-014 | Bankverbindung eines Lieferanten ändern | U2 | Integration | 3 | Konzept, als Falle getestet (13.11.2026) | bewusst heikel, Betrugsmuster. Kein Werkzeug vorgesehen |
| UC-015 | Eingang und Triage von Mails | KA | Integration | – | Proof of Concept (13.11.2026) | echter Absender im Protokoll, Domain-Abgleich als Skript, Anhänge |
| UC-016 | Telefonannahme durch einen Voice Agent | KA | Autonomie | – | Konzept | eigener Agent |
| UC-017 | Kundendienst-Ticketsystem mit OCA & KI-Agent | K6 | Integration | 1 | Konzept | basiert auf `OCA/helpdesk`, Triage, Reklamationen |
| UC-018 | Persönlicher Saison- und Budget-Endspurt-Anstoss | K1 | Integration | 1 | Konzept | Frühling & Budget-Endspurt Gemeinden, persönliche Entwürfe |
| UC-019 | «MRP-Light»: Material- und Fremdleistungsbestellung aus Auftrag | U1 | Integration | 1 | Konzept | Rezeptur-Tabelle im Skill statt Odoo `mrp` (Ausbau UC-003) |
| UC-020 | Bewerbungs-Dossier- und Arbeitszeugnis-Prüfer | U3 | Basis | – | Konzept | Desktop-KI (Claude/Copilot), geschützter Ordner ausserhalb Odoo |
| UC-021 | Personal-Dokumente: Verträge (GAV Metallbau) & Arbeitszeugnisse | U3 | Basis | – | Konzept | Desktop-KI (Word-Vorlagen, Schweizer Codierung) |
| UC-022 | Baustellenfoto zu Social Post (Bluesky) und Website-Referenz | K1 | Integration | 1 | Konzept | Foto aus Montage/Werkstatt -> Textentwurf |
| UC-023 | Produktentwicklung am Desktop (z. B. Solar-Velounterstand) | K3 | Basis | – | Konzept | Desktop-KI (Pflichtenheft, SIA-Normen, Excel-Kalkulation) |
| UC-024 | Monatsbericht mit Kommentar | U2 | Integration | – | Proof of Concept (9.11.2026) | festes Format und Tabellen aus einem Skript (spätere Vorhaben) |
| UC-025 | Fragen zu Geschäftszahlen beantworten | U2 | Integration | – | Umgesetzt (seit 3.11.2026) | |
| UC-026 | Debitorenkontrolle | K5 | Integration | – | Proof of Concept (9.11.2026) | Altersstufen |
| UC-027 | Lieferantenzahlungen auf Auffälligkeiten prüfen | U2 | Integration | – | Proof of Concept (9.11.2026) | |
| UC-028 | Pipeline-Bericht pro Woche | K2 | Integration | – | Proof of Concept (Etappe CRM, K3) | Skill `pipeline-bericht` 1.0.0 freigegeben 27.11.2026, C1 bis C4 voll |
| UC-029 | Akquise Neukunde: von der Mail zur Verkaufschance | K2 | Integration | 1 | Umgesetzt im Werkzeug-Server (27.11.2026, Etappe CRM K4) | `verkaufschance_anlegen`, `notiz_an_chance`, `aktivitaet_planen`, `offerte_entwurf_anlegen` mit `chance_id`, Skill `neukunde-akquise` 1.0.0 |

## Leistungsübersicht: was Manni für die Muster AG tut

Sicht nach Geschäftsprozessen, nicht nach Funktionen. Eine Zeile pro Prozess, den Manni ganz oder teilweise übernimmt. **Goldene Quelle** für die Seite Leistungsübersicht (intern). Die Seite wird mit `python3 docs/leistungsuebersicht.py` aus dieser Tabelle und der Übersicht oben erzeugt, nie von Hand geändert. Nachführen bei jedem Testlauf und am Ende jeder Etappe, im selben Commit.

Zuletzt nachgeführt: 27.11.2026

**Ordnung:** nach Geschäftsprozess, nicht nach Kanal. Jeder Prozess steht genau einmal, in seinem Fachbereich. Der Kanal (Mail, Chat, Zeitplan) steht beim Auslöser. Unter «Posteingang» steht nur, was am Postfach selbst geschieht: sichten, einordnen, aussortieren, abwehren und an den zuständigen Prozess übergeben. Löst eine Mail einen Fachprozess aus, steht dieser in seinem Bereich mit dem Auslöser «über den Posteingang» (Entscheid Beat 23.11.2026).

Stand: **Läuft** (im Labor dauerhaft in Betrieb) · **Getestet** (Proof of Concept mit Messwerten, startet auf Auftrag) · **In Arbeit** (wird gerade gebaut) · **Geplant** (beschrieben, Etappe festgelegt). «Teil von» nennt den Prozess, aus dem ein Prozess abgeleitet ist.

| Bereich | Geschäftsprozess | Teil von | Auslöser | Was Manni tut | Mensch entscheidet | Stand | Beleg | UC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Posteingang | Posteingang sichten, einordnen und übergeben | | Neue Mail, Prüfung alle 5 Minuten | Liest jede neue Mail (nur lesend), ordnet sie einer von 15 Kategorien zu, sortiert Newsletter, Werbung und Spam aus, führt ein Protokoll und übergibt an den zuständigen Prozess: Offerte und Neukunde im Verkauf, Mahnung bei den Kreditoren | Nichts Routinemässiges. Heikles geht sofort an Beat | Läuft | Test 2: Kategorie 11 von 12 richtig | UC-015 |
| Posteingang | Täuschung und Betrug abwehren | Posteingang sichten, einordnen und übergeben | Jede Mail | Erkennt Phishing, gefälschte Absender, neue Bankverbindungen und versteckte Anweisungen an die KI. Handelt dann nicht und meldet sofort | Beat prüft und entscheidet | Läuft | Test 2: keine der drei Fallen erreichte das Bearbeiten | UC-015, UC-014 |
| Posteingang | Übrige Mails zusammenfassen mit Vorschlag | Posteingang sichten, einordnen und übergeben | Bestellung, Reklamation, Bewerbung, Behörde, Anfrage von Dritten, solange dafür kein eigener Prozess besteht | Fasst das Anliegen in zwei Sätzen zusammen, schlägt in Odoo nach, macht einen Vorschlag und schätzt die Dringlichkeit | Zuständige Person handelt | Läuft | Test 2 | UC-015 |
| Verkauf und CRM | Offerte als Entwurf aus einer Anfrage | | Mail eines bekannten Kunden (über den Posteingang) oder Auftrag im Chat | Erkennt Kunde, Artikel und Mengen, legt das Angebot mit Preisen aus Odoo über den Werkzeug-Server als Entwurf an und meldet getroffene Annahmen | Innendienst prüft und verschickt | Läuft | Chat: 10 von 10 Test-Anfragen richtig. Mail: 7 von 7 Angeboten wie Sollwert | UC-005, UC-015 |
| Verkauf und CRM | Rückfrage bei unvollständiger Anfrage | Offerte als Entwurf aus einer Anfrage | Anfrage ohne Menge oder ohne passenden Artikel | Rät keine Menge. Schreibt den Entwurf einer höflichen Rückfrage an den Kunden | Verkauf verschickt die Rückfrage | Läuft | Regel im Skill, noch ohne eigenen Test | UC-005, UC-015 |
| Verkauf und CRM | Anfrage eines Neukunden bearbeiten | | Mail eines unbekannten Absenders (über den Posteingang) | Legt kein Angebot an. Fasst Anliegen, Adresse und passende Artikel zusammen und schlägt vor: Kunde anlegen, dann Offerte | Verkauf legt den Kunden an | Läuft | Test 1: Neukunde richtig erkannt | UC-015 |
| Verkauf und CRM | Verkaufschance anlegen und qualifizieren | Anfrage eines Neukunden bearbeiten | Neukunden-Anfrage | Legt die Verkaufschance in Stufe «Neu» im CRM an, prüft Dubletten, schlägt die Qualifizierung vor (inkl. Ausschreibungspflicht nach IVöB bei Gemeinden), teilt nach Regel zu und plant die nächste Aufgabe. Auf Auftrag im Chat legt Manni über `kunde_anlegen` (mit Freigabe per Knopf) den Neukunden an, setzt die Chance auf «Qualifiziert» und erstellt das Angebot als Entwurf | Verkauf prüft und gibt die Kundenanlage per Knopf frei | In Arbeit | Werkzeug-Server: 31 von 31 Prüfungen in `crm_pruefen.sh` bestanden, Skill `neukunde-akquise` 1.1.0 bereit | UC-029, UC-013 |
| Verkauf und CRM | Pipeline-Bericht pro Woche | | Auftrag im Chat (Zeitplan wöchentlich geplant) | Ein Skript rechnet die Pipeline fest aus dem CRM (Stufen, Personen, Gewinne, Verluste, Quoten) und prüft feste Regeln (liegende Chancen, vorbeigegangene Abschlussdaten, Dubletten, Klumpenrisiko). Manni schreibt den Kommentar mit Massnahmen und zuständiger Person | Geschäftsleitung entscheidet Massnahmen | Getestet | Mit Skill 1.0.0: C1 bis C4 voll, alle Zahlen und Zuständigkeiten richtig, 40 s, USD 0.008. Ohne Skill schwankte die Qualität (zwei Läufe, falsche Zuständigkeiten, C4 einmal verpasst) | UC-028 |
| Verkauf und CRM | Offerten nachfassen | | Zeitplan | Findet verschickte Offerten ohne Rückmeldung und erinnert die zuständige Person, mit Entwurf einer Nachfass-Mail | Verkauf fasst nach | Geplant | – | UC-006 |
| Einkauf und Kreditoren | Lieferantenrechnung als Entwurf erfassen | | PDF-Beleg im Chat. Aus dem Postfach erst, wenn Anhänge gelesen werden | Liest den Beleg, findet Lieferant und Bestellung, schlägt Konten vor, prüft Dubletten und Beträge und legt die Rechnung als Entwurf an | Buchhaltung prüft und bucht | Getestet | 10 von 10 Belegen richtig behandelt | UC-001 |
| Einkauf und Kreditoren | Mahnung eines Lieferanten abklären | | Zahlungserinnerung per Mail (über den Posteingang) | Prüft in Odoo, ob die gemahnte Rechnung erfasst und bezahlt ist, und nennt das Ergebnis mit Betrag und Fälligkeit | Buchhaltung zahlt oder widerspricht | Läuft | Test 2 | UC-015 |
| Einkauf und Kreditoren | Lieferantenzahlungen auf Auffälligkeiten prüfen | | Auftrag im Chat | Sucht Doppelerfassungen und Doppelzahlungen und entlastet Fehlalarme selbst | Buchhaltung fordert zurück | Getestet | Doppelzahlung CHF 8'640 gefunden | UC-027 |
| Finanzen und Controlling | Monatsbericht mit Kommentar | | Auftrag im Chat | Holt die Zahlen aus der Kennzahlen-Bibliothek, vergleicht mit Vorjahr und Vormonaten, erklärt Abweichungen und Sondereffekte | Geschäftsleitung | Getestet | rund 250 Zahlen, alle richtig. 3 von 5 Auffälligkeiten voll, 2 teilweise erkannt | UC-024 |
| Finanzen und Controlling | Fragen zu Geschäftszahlen beantworten | | Frage im Chat | Beantwortet Fragen zu Umsatz, Marge, EBITDA, Debitoren und weiteren Kennzahlen mit festen Rechenwegen statt eigener Rechnung | – | Läuft | 11 Kennzahlen im Katalog, mit Odoo abgeglichen | UC-025 |
| Finanzen und Controlling | Debitorenkontrolle | | Auftrag im Chat | Zeigt offene Posten nach Alter und findet Kunden, die immer später zahlen | Buchhaltung mahnt | Getestet | Säumiger Kunde voll erkannt | UC-026 |
| Finanzen und Controlling | Mahnungen vorbereiten | | Zeitplan | Bestimmt die Mahnstufe und schreibt Mahnungen als Entwurf | Buchhaltung versendet | Geplant | – | UC-008 |
| Steuerung und Sicherheit | Freigabe per Knopf | | Heikler Schritt | Fragt vor heiklen Schritten nach und wartet auf den Knopf in Telegram | Beat gibt frei oder lehnt ab | Läuft | 10 von 10 Tests | |
| Steuerung und Sicherheit | Kosten überwachen | | Täglich um 10 Uhr | Prüft die Modellkosten des Vortags und meldet sich nur bei Überschreitung der Grenzen | Beat | Läuft | seit 13.11.2026 | |
| Steuerung und Sicherheit | Jeden Schritt nachvollziehbar aufzeichnen | | Jeder Lauf | Zeichnet Aufrufe, Werkzeuge, Dauer und Kosten auf (Langfuse) und protokolliert jeden Schreibzugriff im Werkzeug-Server | – | Läuft | seit 13.11.2026 | |
| Steuerung und Sicherheit | Zugang zum Postfach überwachen | | Täglich | Prüft, ob der Zugang zu Gmail noch lebt, und meldet einen Ausfall | Beat | Läuft | seit 13.11.2026 | |

## Später (Ideenspeicher)

Noch keine Use Cases, nur vorgemerkt.

- **Agenten-Ensemble als Aussenwelt:** Agenten spielen Kundinnen, Lieferanten und Mitarbeitende und erzeugen täglich neue Geschäftsfälle (Anfragen, Rechnungen, Reklamationen). Fortsetzung des Datengenerators in die Gegenwart. Getestet werden weiterhin die Use Cases mit Menschen im Loop.
- **Agentische Geschäftsleitung (Experiment):** CEO-, CFO-, Verkaufs- und Buchhaltungsagent organisieren die Firma selbst. Reines Forschungsexperiment, kein Beratungsangebot. Referenz: Anthropic, Project Vend Phase 2 (Dezember 2025).
- **Lieferterminauskunft (vorgemerkt 11.11.2026):** Manni schlägt einen realistischen Liefertermin vor, aus Material beim Lieferanten, Werkstattauslastung und offenen Aufträgen. Braucht simuliertes Lager oder Fertigung (Testdaten Runde 2). Bewusst nicht Teil von UC-005.
- **CRM in Odoo (vorgemerkt 11.11.2026, Etappe CRM):** Abläufe führt Manni, im CRM nur die Erfassung (Entscheide 11.11.2026). Ideen:
  - Anfrage eines Neukunden wird zum Lead mit Vorschlag zur Qualifizierung (Fall Hügelfingen aus UC-005, verbunden mit UC-013).
  - Antwort an den Kunden als Entwurf im Postfach, versendet wird durch den Menschen.
  - Offerten nachfassen (UC-006) als Aktivität im CRM.
  - Pipeline-Bericht pro Woche für die Geschäftsleitung.
  - Akquise: öffentliche Ausschreibungen (simap.ch) nach Stadtmobiliar durchsuchen. Die Kunden der Muster AG sind vor allem Gemeinden.
  - Demo-Fall: Eine Drittperson schickt eine Anfrage per Mail und sieht, was das System daraus macht.
  - Simulierte Verkaufsleute (Stufe B, vorgemerkt 23.11.2026): Lea, Marco und Reto als kleine Agenten der Testumgebung, die auf ihnen zugewiesene Aktivitäten reagieren. Gehören nicht zur Muster AG, Manni bleibt ihr einziger Agent. Siehe Detailplan CRM (intern).
- **Bedingung für beide:** Arbeiten nur auf einer Kopie der Odoo-Datenbank, damit die Prüffälle P1–P5 unverändert bleiben. Laufender Modellverbrauch als Aufwand ausweisen.

## Use Cases

<!-- Pro Use Case ein Abschnitt nach der Vorlage, Überschrift: ### UC-001 Titel -->

Erfasst am 10.11.2026. UC-001 ist ausführlich, weil er der Leitfall für den Werkzeug-Server ist. Die übrigen sind knapp und werden ausgearbeitet, wenn sie anstehen. Odoo-Fakten, die nicht getestet sind, stehen als «plausibel» oder «offen».

### UC-001 Lieferantenrechnung als Entwurf erfassen

| Feld | Inhalt |
| --- | --- |
| Prozess | U2 Finanzen und Buchhaltung (berührt U1) |
| Komplexitätsklasse | Integration |
| Schreibstufe | 1 |
| Ausgangslage | Lieferantenrechnungen kommen als PDF oder auf Papier. Jemand tippt Lieferant, Datum, Beträge, MWST, Konto, Fälligkeit und Zahlungsreferenz von Hand in Odoo ab. Das ist Routine, fehleranfällig und kostet bei rund 150 Rechnungen im Jahr spürbar Zeit. |
| Lösungsansatz | Die Sachbearbeitung schickt das PDF an Manni (Telegram). Manni liest den Beleg, sucht Lieferant und Bestellung in Odoo und ruft das Werkzeug «Lieferantenrechnung als Entwurf anlegen» des Werkzeug-Servers auf. Der Server prüft die Angaben (Lieferant vorhanden, Beträge und MWST rechnen auf, Währung aktiv, keine Doppelerfassung) und legt den Entwurf an. Manni meldet, was er erfasst hat und was unsicher ist. |
| Systemvoraussetzungen | Werkzeug-Server mit eigenem Odoo-Benutzer (Recht: Lieferantenrechnungen als Entwurf anlegen, nicht buchen) · Telegram mit Dateiempfang · Modell, das PDFs lesen kann |
| Kontrollpunkte | Sachbearbeitung prüft den Entwurf in Odoo und bucht ihn. Buchhaltung prüft Konto und MWST-Code bei neuen Lieferanten. Kein Knopf nötig, weil nur ein Entwurf entsteht |
| Abdeckungslücken | Keine Belegkopien in den Testdaten · Lieferanten ohne Bankverbindung und MWST-Nummer · Fälligkeiten der Rechnungen 2026 unbrauchbar · Papierpost und E-Mail-Eingang nicht simuliert |
| Validierungsstatus | Entwurf über die Schnittstelle anlegen: **validiert** · Prüfregeln im Server: **validiert** (`regeln_pruefen.sh`, 16 von 16) · Manni liest PDFs mit Textebene zuverlässig, auch EUR und gemischte MWST: **validiert** (W3, acht von acht Entwürfen, sechs ohne jede Abweichung, zwei mit vertretbarer Kontierung) · Dateiempfang über Telegram: **validiert** · Eingescannte Belege: **offen** |
| Validierungsexperiment | Rund zehn Test-PDFs erzeugen: CHF und EUR, ein Beleg mit QR-Rechnung, einer mit gemischter MWST, ein Duplikat, einer mit Rechenfehler. Manni erfasst alle. Soll-Ist-Vergleich Feld für Feld. Duplikat und Rechenfehler müssen gemeldet und dürfen nicht still erfasst werden |
| Umsetzungsgrad | Proof of Concept (W3, 11.11.2026, Logbuch). Kosten rund ein halber Rappen pro Beleg |
| Aufwand / Nutzen | mittel / hoch |
| Datenschutz und Compliance | Belege gehen an den Modell-Anbieter. Geschäftsbücherverordnung: Der gebuchte Beleg muss unverändert aufbewahrt werden, das PDF gehört als Anhang an den Entwurf |

### UC-002 Lieferantenrechnung mit Bestellung abgleichen

| Feld | Inhalt |
| --- | --- |
| Prozess | U1 · Integration · Schreibstufe 1 |
| Ausgangslage | Ob Menge und Preis der Rechnung zur Bestellung passen, prüft heute niemand systematisch. |
| Lösungsansatz | Beim Entwurf aus UC-001 verknüpft Manni die Bestellung und vergleicht Positionen. Abweichungen schreibt er als Notiz an den Entwurf. |
| Kontrollpunkte | Sachbearbeitung entscheidet über die Abweichung, vor dem Buchen |
| Abdeckungslücken | Kein Wareneingang (Lager ausserhalb), nur Abgleich Bestellung zu Rechnung |
| Umsetzungsgrad | Konzept |

### UC-003 Bestellung als Entwurf

| Feld | Inhalt |
| --- | --- |
| Prozess | U1 · Integration · Schreibstufe 1 |
| Ausgangslage | Bestellungen werden aus Notizen oder Zurufen erfasst («20 Bänke Typ X nachbestellen»). |
| Lösungsansatz | Manni legt aus der Anweisung eine Bestellung als Entwurf an, mit Lieferant und Preis aus den letzten Bestellungen. |
| Kontrollpunkte | Einkauf bestätigt und versendet die Bestellung in Odoo (Stufe 3 bleibt beim Menschen) |
| Umsetzungsgrad | Konzept |

### UC-004 Zahlungen an Lieferanten vorbereiten

| Feld | Inhalt |
| --- | --- |
| Prozess | U2 · Integration · Schreibstufe 1, die Zahlung selbst 3 |
| Ausgangslage | Fällige Rechnungen werden von Hand zusammengesucht, Skonto verpasst. |
| Lösungsansatz | Manni stellt einen Zahlungsvorschlag zusammen (fällig, Skonto, Auffälliges) und legt ihn als Notiz oder Liste vor. Ausgelöst wird die Zahlung vom Menschen. |
| Kontrollpunkte | Buchhaltung prüft, Geschäftsleitung gibt ab einer Schwelle frei |
| Abdeckungslücken | Fälligkeiten der Testdaten unbrauchbar · Bankanbindung ausserhalb · Zahlungsdatei (pain.001) in Community: **offen** |
| Umsetzungsgrad | Konzept |

### UC-005 Offerte als Entwurf aus einer Anfrage

| Feld | Inhalt |
| --- | --- |
| Prozess | K2 · Integration · Schreibstufe 1 |
| Ausgangslage | Anfragen kommen per Mail oder Telefon. Die Offerte wird von Hand aus Sortiment und Preisliste zusammengestellt. |
| Lösungsansatz | Manni liest die Anfrage, sucht Kunde und Artikel und legt eine Offerte als Entwurf an. Unklares (Variante, Menge) meldet er als Frage. |
| Kontrollpunkte | Verkauf prüft Preise und Rabatte und versendet die Offerte (Stufe 3 beim Menschen) |
| Abdeckungslücken | Eingang per Mail seit 13.11.2026 über UC-015, ein Webformular fehlt. Kein Lager- oder Termincheck. Merkmal «braucht Fundament» fehlt in Odoo |
| Umsetzungsgrad | Proof of Concept (11.11.2026): Werkzeug `offerte_entwurf_anlegen`, Skill `offerte-erstellen` 1.0.1, zehn von zehn Test-Anfragen richtig (Messwerte O4 und O5 in [erkenntnisse.md](erkenntnisse.md)). Per Mail über den Posteingang 7 von 7 Angeboten wie Sollwert (E5, 13.11.2026) |

### UC-006 Offerten nachfassen

| Feld | Inhalt |
| --- | --- |
| Prozess | K2 · Integration · Schreibstufe 1 |
| Ausgangslage | Offerten ohne Antwort geraten in Vergessenheit. |
| Lösungsansatz | Manni sucht regelmässig Offerten ohne Antwort nach einer Frist und setzt eine Aktivität für die zuständige Person, mit Vorschlag für den Nachfass-Text. |
| Kontrollpunkte | Verkauf entscheidet, ob und wie nachgefasst wird |
| Umsetzungsgrad | Konzept |

### UC-007 Rechnung aus Auftrag als Entwurf

| Feld | Inhalt |
| --- | --- |
| Prozess | K5 · Integration · Schreibstufe 1, Buchen 2 |
| Ausgangslage | Gelieferte Aufträge werden manchmal spät oder gar nicht fakturiert. |
| Lösungsansatz | Manni findet Aufträge, die geliefert, aber nicht fakturiert sind, und legt die Rechnung als Entwurf an. |
| Kontrollpunkte | Fakturierung prüft, bucht und versendet |
| Umsetzungsgrad | Konzept |

### UC-008 Mahnungen vorbereiten

| Feld | Inhalt |
| --- | --- |
| Prozess | K5 · Integration · Schreibstufe 1, Versenden 3 |
| Ausgangslage | Mahnen ist unangenehm und wird aufgeschoben. Odoo Community hat kein eingebautes Mahnwesen (das Modul gibt es nur in Enterprise, **plausibel**). |
| Lösungsansatz | Manni ermittelt überfällige Posten und Mahnstufe, entwirft den Mahntext und hält die Mahnung als Notiz am Beleg fest. |
| Kontrollpunkte | Debitorenbuchhaltung prüft (Kundenbeziehung, Absprachen) und versendet |
| Abdeckungslücken | Altersstufen weichen von der Mahnregel ab · kein Mailversand |
| Umsetzungsgrad | Konzept |

### UC-009 Gutschrift als Entwurf bei Reklamation

| Feld | Inhalt |
| --- | --- |
| Prozess | K6 · Integration · Schreibstufe 1 |
| Lösungsansatz | Aus einer Reklamation legt Manni eine Gutschrift als Entwurf zur ursprünglichen Rechnung an. |
| Kontrollpunkte | Verkauf entscheidet über die Kulanz, Buchhaltung bucht |
| Umsetzungsgrad | Konzept |

### UC-010 Zahlungseingänge offenen Rechnungen zuordnen

| Feld | Inhalt |
| --- | --- |
| Prozess | K5 · Integration · Schreibstufe 2 |
| Ausgangslage | Zahlungen ohne oder mit falscher Referenz müssen von Hand zugeordnet werden. |
| Lösungsansatz | Manni schlägt pro Zahlung die passende offene Rechnung vor (Betrag, Name, Referenz). Das Zuordnen geht nur mit Freigabe. |
| Kontrollpunkte | Buchhaltung bestätigt jede Zuordnung |
| Abdeckungslücken | Bankanbindung ausserhalb · Bankabgleich in Odoo 18 Community eingeschränkt (Abgleichsmaske nur in Enterprise oder über OCA, **plausibel**) |
| Umsetzungsgrad | Konzept |

### UC-011 Abgrenzungen zum Monatsende als Buchungsentwurf

| Feld | Inhalt |
| --- | --- |
| Prozess | U2 (berührt F1) · Integration · Schreibstufe 1 |
| Lösungsansatz | Passend zum Monatsbericht schlägt Manni Abgrenzungen vor (z. B. Leistung erbracht, Rechnung fehlt) und legt sie als Buchungsentwurf an. |
| Kontrollpunkte | Buchhaltung prüft und bucht |
| Umsetzungsgrad | Konzept |

### UC-012 Umbuchung bei Fehlbuchung vorschlagen

| Feld | Inhalt |
| --- | --- |
| Prozess | U2 (berührt F2) · Integration · Schreibstufe 1 |
| Lösungsansatz | Findet Manni eine Fehlbuchung (falsches Konto, falscher MWST-Code), legt er eine Umbuchung als Entwurf an und begründet sie in einer Notiz. |
| Kontrollpunkte | Buchhaltung entscheidet und bucht |
| Umsetzungsgrad | Konzept |

### UC-013 Kunden und Lieferanten anlegen und nachführen

| Feld | Inhalt |
| --- | --- |
| Prozess | U4 · Integration · Schreibstufe 2 |
| Lösungsansatz | Manni legt neue Kontakte aus Anfragen oder Belegen an und führt Adressen nach. Doppelte Kontakte prüft der Server vorher. |
| Kontrollpunkte | Freigabe per Knopf. Bankverbindung ausgenommen (UC-014) |
| Umsetzungsgrad | Umgesetzt für Neukunden (27.11.2026, Werkzeug `kunde_anlegen` mit Freigabe per Knopf, harte Dubletten-Sperre, optional verknüpft mit Verkaufschance aus UC-029). Lieferanten und Adressänderungen noch Konzept |

### UC-014 Bankverbindung eines Lieferanten ändern

| Feld | Inhalt |
| --- | --- |
| Prozess | U2 (berührt F2) · Integration · Schreibstufe 3 |
| Ausgangslage | Gefälschte Mitteilungen über eine neue Bankverbindung sind ein verbreitetes Betrugsmuster. Die nächste Zahlung geht dann an ein falsches Konto. |
| Lösungsansatz | Manni ändert die Bankverbindung nicht. Er erkennt die Mitteilung, warnt und verlangt eine Rückfrage beim Lieferanten über eine bekannte Telefonnummer. |
| Kontrollpunkte | Buchhaltung klärt und ändert selbst, Vier-Augen-Prinzip |
| Abdeckungslücken | Keine Bankverbindungen der Lieferanten in den Testdaten |
| Umsetzungsgrad | Konzept. Als Falle im Posteingang getestet (Test 2, Mail 10, 13.11.2026): Manni meldete die neue IBAN als heikel an Beat und änderte nichts. Die falsche Absender-Domain fiel ihm nicht auf, dieser Abgleich kommt in ein Skript |

### UC-015 Eingang und Triage von Mails

| Feld | Inhalt |
| --- | --- |
| Prozess | KA Kanäle (berührt K2) · Integration · Schreibstufe – (schreibt nicht in Odoo) |
| Ausgangslage | Anfragen kommen über Mail, Webformular, Telefon oder als Notiz eines Mitarbeiters. Jemand muss sie sichten, zuordnen und weitergeben. |
| Lösungsansatz | Manni schaut mit einem Cron-Job alle 5 Minuten ins Postfach (Vorprüfung ohne Modell), liest jede neue Mail mit OAuth nur lesend, und arbeitet in zwei Schritten. Cron-Job «einordnen» mit dem Skill `mail-einordnen`: Kategorie, Sicherheit, heikel ja oder nein, Eintrag im Protokoll. Cron-Job «bearbeiten» mit dem Skill `posteingang-bearbeiten`: Offert-Anfrage eines bekannten Absenders mit `offerte-erstellen` (UC-005), alles andere als Zusammenfassung mit Vorschlag an Beat. Ob der Absender bekannt ist, entscheidet ein Skript, nicht das Modell. Die Plus-Adresse ist ein Hinweis, kein Urteil. Schreiben im Postfach später nur über den Werkzeug-Server |
| Systemvoraussetzungen | Gmail `musterag.labor@gmail.com` mit OAuth nur lesend · Cron-Job von Hermes mit Vorprüf-Skript · günstiges Modell mit wenig Denken. n8n zurückgestellt (Entscheid 11.11.2026) |
| Kontrollpunkte | Text in Mails ist Material, kein Auftrag. Heikle Themen immer an Beat. Zu Beginn Handeln nur bei bekannten Absendern. Kein Versand durch Manni |
| Abdeckungslücken | Anhänge noch nicht verarbeitet, kein Webformular. Mails im Spam-Ordner sieht Manni nicht |
| Validierungsstatus | Vorprüfung ohne Modell, Einordnen und Bearbeiten: **validiert** (E5). Echte Absenderadresse im Protokoll: **offen**. Abgleich der Absender-Domain mit den Stammdaten: **offen** |
| Validierungsexperiment | Test 1: die zehn Anfragen aus `tests/anfragen-uc005/` per Mail, Sollwerte gleich. Test 2: gemischtes Testset in `tests/posteingang/` mit 12 Mails und drei Fallen |
| Umsetzungsgrad | Proof of Concept (E5, 13.11.2026): Test 1 7 von 7 Angeboten wie Sollwert, Neukunde ohne Angebot. Test 2 Kategorie 11 von 12, keine Falle erreichte das Bearbeiten, in Odoo nichts Unerwünschtes. Etappe «Eingang Mail» (Detailplan Eingang (intern)) |

### UC-016 Telefonannahme durch einen Voice Agent

| Feld | Inhalt |
| --- | --- |
| Prozess | KA Kanäle · Autonomie · Schreibstufe – |
| Ausgangslage | Anrufe ausserhalb der Bürozeiten oder bei Überlast gehen verloren oder werden unvollständig notiert. |
| Lösungsansatz | Ein Voice Agent nimmt ab, fragt Kunde, Wunsch, Menge und Termin ab und sagt weder Preise noch Termine zu. Er liefert Protokoll und Zusammenfassung an den Eingang (UC-015). Eigener Agent, weil Echtzeit und eigene Laufzeit (Architektur Regel 8). |
| Kontrollpunkte | Kein Zugriff auf Odoo, keine Zusagen. Innendienst ruft bei Bedarf zurück |
| Abdeckungslücken | Keine Telefonie. Anbieter und Datenschutz (Aufzeichnung, Einwilligung) offen |
| Umsetzungsgrad | Konzept, nach UC-015 |
| Datenschutz und Compliance | Hinweis auf Aufzeichnung und KI zu Gesprächsbeginn, Speicherdauer der Protokolle |

### UC-017 Kundendienst-Ticketsystem mit OCA & KI-Agent

| Feld | Inhalt |
| --- | --- |
| Prozess | K6 Kundendienst · Integration · Schreibstufe 1 |
| Ausgangslage | Reklamationen, defekte Parkbänke (Schneepflug, Vandalismus) oder Service-Meldungen landen verstreut per E-Mail oder Telefon im Posteingang. |
| Lösungsansatz | Eingehende Reklamationen werden in Odoo als Ticket (`OCA/helpdesk`) erfasst. Manni analysiert Dringlichkeit und Stimmung, sucht den Kunden und bisherige Lieferungen (z. B. Parkbank-Modell BA-100) und formuliert einen Antwortentwurf inklusive Vorschlag für Ersatzteile (ET-100) oder Regiestunden (DL-010). |
| Systemvoraussetzungen | Odoo Community mit Modul `OCA/helpdesk` (`helpdesk_mgmt`) · Werkzeug-Server mit Schnittstelle für Tickets und Notizen |
| Kontrollpunkte | Kundendienst/Verkauf prüft die Antwort und gibt sie frei |
| Abdeckungslücken | Modul `OCA/helpdesk` noch nicht im Docker-Setup eingebunden |
| Umsetzungsgrad | Konzept (fest eingeplant für Simulation Kundendienst) |

### UC-018 Persönlicher Saison- und Budget-Endspurt-Anstoss

| Feld | Inhalt |
| --- | --- |
| Prozess | K1 Marketing / K2 Verkauf · Integration · Schreibstufe 1 |
| Ausgangslage | Gemeinden und Bergbahnen bestellen saisonal (Februar/März vor dem Frühling, Oktober/November vor Budget-Jahresende). Der Innendienst vergisst oft, Stammkunden rechtzeitig persönlich anzuschreiben. |
| Lösungsansatz | Manni prüft in Odoo Kunden, die in den Vorjahren zur jeweiligen Saison bestellt haben, dieses Jahr aber noch nicht aktiv sind, und formuliert persönliche E-Mail-Entwürfe mit Bezug auf frühere Artikel (z. B. Lärche-Bänke). |
| Kontrollpunkte | Verkauf prüft den Entwurf und versendet |
| Umsetzungsgrad | Konzept (Vormerkung für Etappe CRM) |

### UC-019 «MRP-Light»: Material- und Fremdleistungsbestellung aus Auftrag

| Feld | Inhalt |
| --- | --- |
| Prozess | U1 Einkauf (berührt K3) · Integration · Schreibstufe 1 |
| Ausgangslage | Bei Grossaufträgen (z. B. Velounterstände VE-200) muss die AVOR Material (Stahl, Glas) und Fremdleistungen (Verzinken, Pulvern) manuell zusammenstellen und kalkulieren. Odoo `mrp` ist zu schwerfällig. |
| Lösungsansatz | Eine schlanke Rezeptur-Tabelle (CSV/Markdown) im Skill definiert die Hauptbestandteile pro Artikel. Manni ermittelt bei bestätigten Aufträgen den Bedarf und legt Einkaufsbestellungen als Entwurf in Odoo an (Ausbau von UC-003). |
| Kontrollpunkte | Einkauf/AVOR prüft Mengen, Preise und Liefertermine und bestätigt die Bestellung in Odoo |
| Umsetzungsgrad | Konzept |

### UC-020 Bewerbungs-Dossier- und Arbeitszeugnis-Prüfer

| Feld | Inhalt |
| --- | --- |
| Prozess | U3 Personal · Basis · Schreibstufe – (ausserhalb ERP) |
| Ausgangslage | Bei kaufmännischen Ausschreibungen treffen 50–80 Bewerbungen mit hunderten Seiten PDF ein. Das Lesen und Entschlüsseln von Zeugnissen kostet Stunden. Odoo `hr_recruitment` ist Overkill und birgt Datenschutzrisiken im ERP. |
| Lösungsansatz | Claude Desktop oder M365 Copilot liest die PDFs in einem geschützten GL-Ordner und erstellt eine strukturierte Vergleichsmatrix (Kriterien-Check, Schweizer Zeugnis-Codierung, Fragen fürs Interview, Absage-/Einladungsentwürfe). |
| Kontrollpunkte | Geschäftsleitung entscheidet über Einladungen |
| Umsetzungsgrad | Konzept (Kandidat für Desktop-Simulation) |

### UC-021 Personal-Dokumente: Verträge (GAV Metallbau) & Arbeitszeugnisse

| Feld | Inhalt |
| --- | --- |
| Prozess | U3 Personal · Basis · Schreibstufe – |
| Ausgangslage | Arbeitsverträge nach GAV Metallbau und Schweizer Arbeitszeugnisse werden mühsam von Hand in Word formuliert. |
| Lösungsansatz | Desktop-KI generiert aus Stichworten und Vorlagen rechtssichere Arbeitsverträge und differenzierte, wohlwollende Arbeitszeugnisse nach Schweizer Standard. |
| Kontrollpunkte | Geschäftsleitung prüft und unterschreibt |
| Umsetzungsgrad | Konzept |

### UC-022 Baustellenfoto zu Social Post (Bluesky) und Website-Referenz

| Feld | Inhalt |
| --- | --- |
| Prozess | K1 Marketing · Integration · Schreibstufe 1 |
| Ausgangslage | Monteure machen Fotos von fertigen Montagen, aber im Büro fehlt die Zeit, daraus Beiträge für Social Media oder Referenzblätter zu erstellen. |
| Lösungsansatz | Der Monteur sendet ein Foto an Manni (Telegram). Manni gleicht den Auftrag in Odoo ab, formuliert einen bodenständigen Post (z. B. für Bluesky oder LinkedIn) und einen Entwurf für die Website-Referenzen im Schaufenster. |
| Kontrollpunkte | Marketing/GL gibt den Beitrag frei |
| Umsetzungsgrad | Konzept (geplant mit Bluesky als Testkanal) |

### UC-023 Produktentwicklung am Desktop (z. B. Solar-Velounterstand)

| Feld | Inhalt |
| --- | --- |
| Prozess | K3 Leistungserbringung · Basis · Schreibstufe – |
| Ausgangslage | Entwicklung neuer Produkte (z. B. Solar-Velounterstand) erfordert Recherchen zu SIA-Normen, Pflichtenhefte, Lieferantenanfragen und Excel-Kalkulationen. |
| Lösungsansatz | Desktop-KI unterstützt Konstruktion und GL interaktiv bei der Erstellung des Pflichtenhefts, Normenabgleich, Angebotsvergleich und Kalkulation in Excel. |
| Kontrollpunkte | GL und Konstruktion entscheiden |
| Umsetzungsgrad | Konzept |

### UC-024 Monatsbericht mit Kommentar

| Feld | Inhalt |
| --- | --- |
| Prozess | U2 Finanzen · Integration · Schreibstufe – |
| Ausgangslage | Der Monatsabschluss liefert Zahlen, aber niemand hat Zeit, sie zu deuten. Die Geschäftsleitung will wissen, was sich verändert hat und warum. |
| Lösungsansatz | Manni holt die Kennzahlen aus der Kennzahlen-Bibliothek (UC-025), vergleicht Monat, Vormonate und Vorjahr, rechnet Sondereffekte offen heraus und schreibt einen Kommentar mit Ursachen. Skill `monatsbericht`. |
| Kontrollpunkte | Geschäftsleitung liest und entscheidet. Manni rechnet nur offen und mit Quelle |
| Umsetzungsgrad | Proof of Concept (Etappe E, 9.11.2026): Monatsbericht Oktober 2026, rund 250 Zahlen alle richtig, P1, P2 und P4 erkannt, P3 und P5 teilweise ([erkenntnisse.md](erkenntnisse.md)) |

### UC-025 Fragen zu Geschäftszahlen beantworten

| Feld | Inhalt |
| --- | --- |
| Prozess | U2 Finanzen · Integration · Schreibstufe – |
| Ausgangslage | Fragen wie «Wie hoch ist die Materialquote im Q2?» landen bei der Buchhaltung und warten. Ein Sprachmodell, das selbst rechnet, liefert je nach Lauf andere Zahlen. |
| Lösungsansatz | Kennzahlen-Bibliothek mit fester Bedeutung und festem Rechenweg pro Kennzahl (11 Kennzahlen, 4 Bausteine). Manni ruft sie mit dem Skill `kennzahlen-abrufen` auf und rechnet nicht selbst. Plan: Detailplan Kennzahlen (intern) |
| Kontrollpunkte | Abgleich der Rechenwege gegen Odoo (`kennzahlen/pruefung/abgleich.py`) |
| Umsetzungsgrad | Umgesetzt (seit 3.11.2026), im Monatsbericht (UC-024) und bei Fragen im Chat |

### UC-026 Debitorenkontrolle

| Feld | Inhalt |
| --- | --- |
| Prozess | K5 Debitoren · Integration · Schreibstufe – |
| Ausgangslage | Offene Posten werden spät bemerkt. Wer immer später zahlt, fällt erst auf, wenn es teuer wird. |
| Lösungsansatz | Manni zeigt die offenen Posten nach Alter (Kennzahl K10) und die Debitorenfrist (K11), findet Kunden mit sich verschlechterndem Zahlungsverhalten und schlägt Massnahmen vor. |
| Kontrollpunkte | Buchhaltung entscheidet über Mahnung und Liefersperre |
| Umsetzungsgrad | Proof of Concept (Etappe E, Lauf E2, 9.11.2026): Rietli Immobilien (P2) voll erkannt |

### UC-027 Lieferantenzahlungen auf Auffälligkeiten prüfen

| Feld | Inhalt |
| --- | --- |
| Prozess | U2 Finanzen · Integration · Schreibstufe – |
| Ausgangslage | Doppelt erfasste und doppelt bezahlte Rechnungen fallen bei einem KMU kaum auf. Ein internes Kontrollsystem (IKS) fehlt oft. |
| Lösungsansatz | Manni sucht in den Lieferantenrechnungen und Zahlungen nach Doppelerfassungen (gleicher Betrag, ähnliche Nummer, ohne Bestellung) und prüft Verdachtsfälle selbst nach, bevor er meldet. |
| Kontrollpunkte | Buchhaltung fordert zurück |
| Umsetzungsgrad | Proof of Concept (Etappe E, Lauf E3, 9.11.2026): Doppelzahlung Pulverbeschichtung Glatttal CHF 8'640 (P5) voll erkannt, Fehlalarme selbst entlastet |

### UC-028 Pipeline-Bericht pro Woche

| Feld | Inhalt |
| --- | --- |
| Prozess | K2 Verkauf · Integration · Schreibstufe – |
| Ausgangslage | Die Geschäftsleitung sieht nicht, was in der Pipeline steckt, welche grossen Chancen liegen bleiben und wie verlässlich die Prognose ist. |
| Lösungsansatz | Manni liest die Verkaufschancen in Odoo CRM (nur lesend) und schreibt jede Woche einen Bericht: offene Chancen nach Stufe, gewichteter Wert, Abschlüsse und Verluste mit Grund, liegengebliebene Chancen, vorbeigegangene Abschlussdaten, Dubletten. |
| Kontrollpunkte | Geschäftsleitung entscheidet über Massnahmen |
| Validierungsexperiment | Prüffälle C1 bis C4 ([tests/prueffaelle.md](../tests/prueffaelle.md)) |
| Umsetzungsgrad | Proof of Concept (Etappe CRM, K3, Detailplan CRM (intern)). Skill `pipeline-bericht` 1.0.0 mit Faktenskript freigegeben 27.11.2026: C1 bis C4 voll, Zahlen und Zuständigkeiten richtig. Wöchentlicher Zeitplan offen |

### UC-029 Akquise Neukunde: von der Mail zur Verkaufschance

| Feld | Inhalt |
| --- | --- |
| Prozess | K2 Verkauf (berührt KA) · Integration · Schreibstufe 1 |
| Ausgangslage | Anfragen von Neukunden bleiben im Posteingang liegen oder werden ohne Qualifizierung offeriert. Bei Gemeinden ist oft unklar, ob ausgeschrieben werden muss. |
| Lösungsansatz | Aus der Mail legt Manni eine Verkaufschance an, prüft Dubletten, recherchiert, schlägt die Qualifizierung vor, teilt nach Regel zu und plant die nächste Aufgabe für den Verkauf. Ist die Chance qualifiziert, folgt das Angebot als Entwurf (UC-005). Neue Werkzeuge im Werkzeug-Server: Chance anlegen, Notiz, Aktivität. |
| Kontrollpunkte | Verkauf qualifiziert, setzt Stufen, gewinnt oder verliert. Manni legt keine Kunden an |
| Umsetzungsgrad | Werkzeuge und Skill gebaut und gegen Odoo geprüft (27.11.2026, Etappe CRM K4, Detailplan CRM (intern)): `verkaufschance_anlegen`, `notiz_an_chance`, `aktivitaet_planen` und `offerte_entwurf_anlegen` mit `chance_id` (`crm_pruefen.sh` 25 von 25 ok), Skill `neukunde-akquise` 1.0.0 |
