# Architektur der Agenten: Werkzeuge statt Fachagenten

Stand: 6. November 2026, abends. Entscheid von Beat, besprochen in claude.ai (Projekt «KI im KMU»). Geändert am 9. November 2026: Manni liest direkt, nur das Schreiben geht über den Werkzeug-Server (Variante B, siehe «Nachtrag 9.11.2026» unten).

**Dieses Dokument ist massgebend** für die Frage, wie Agenten auf der Kiste auf Systeme zugreifen und wie ihre Rechte begrenzt werden. Wo ältere Aussagen abweichen, sind sie überholt. Das gilt vor allem für den Grundsatz vom 6.11.2026 («eigener Agent pro Zugriffsbereich») und für die Profile Buchhaltung, Verkauf und Reporting im alten Hermes-Plan (seit 9.11.2026 im Logbuch (intern), Etappe D).

## Der Entscheid in einem Satz

Manni ist der einzige Agent. Lesen darf er direkt in Odoo, mit einem eigenen Benutzer, der nur lesen kann. Schreiben geht nur über die Werkzeuge eines eigenen Werkzeug-Servers. Die Schreibrechte sitzen in diesem Server, nicht in getrennten Agenten.

## Das Bild

```
Beat (Telegram, Desktop-App)
   │  Auftrag. Freigabe für Unumkehrbares per Knopf im Chat
   ▼
Manni (Hermes, Profil «Hauptagent», Linux-Benutzer hermes)
   │  Fachwissen aus Skills (z. B. Monatsbericht, Kreditoren prüfen)
   │
   ├── lesen: direkt, Skills odoo-lesen und kennzahlen-abrufen,
   │          eigener Odoo-Benutzer «Hermes», nur lesen
   │
   └── schreiben: Werkzeuge, mit Mannis eigenem Schlüssel für den Server
        ▼
     Werkzeug-Server (MCP, in Docker, nur 127.0.0.1)
        │  prüft: Darf dieser Schlüssel dieses Werkzeug? Stimmen die Prüfregeln?
        │  hält die Schlüssel zum Schreiben in Odoo (später M365). hermes kommt nicht an sie heran
        ▼
Odoo (später M365)
      Rechte im System als letzte Sperre: Benutzer «Hermes» nur lesen,
      Benutzer des Servers nur, was seine Werkzeuge brauchen
```

## Die Regeln

### 1. Ein Agent, Fachwissen aus Skills

- Manni ist der einzige Agent.
- Fachwissen holt er aus Skills, zum Beispiel «Monatsbericht erstellen» oder «Kreditoren prüfen». Ein Skill gibt ihm Wissen und Ablauf, aber keine zusätzlichen Rechte.
- Es gibt vorerst keine Profile Buchhaltung, Verkauf und Reporting und kein Kanban zwischen Agenten. Etappe D3 ist zurückgestellt.

### 2. Der Werkzeug-Server

- Ein eigener MCP-Server. Er läuft in Docker wie Odoo und hört nur auf `127.0.0.1`.
- Er hält die Schlüssel zu den Zielsystemen. Der Benutzer `hermes` ist nicht in der Gruppe `docker` und hat keinen Zugriff auf `/Docker`. Er kommt nicht an diese Schlüssel heran.
- Jeder Agent meldet sich mit einem eigenen Schlüssel beim Server an. Der Server führt eine Liste: welcher Schlüssel welche Werkzeuge darf. Heute steht nur Manni auf der Liste. Die Liste ist für weitere Agenten und später für Menschen vorbereitet.
- Manni behält seinen eigenen Odoo-Benutzer «Hermes», der nur lesen kann, mit dem Schlüssel in seiner `.env`. Er liest direkt. Der Server ist nur für das zuständig, was in Odoo schreibt (Nachtrag 9.11.2026).
- Die Skills zum Lesen (`odoo-lesen`, `kennzahlen-abrufen`) bleiben, wie sie sind. Fach-Skills nennen die Werkzeuge des Servers beim Namen, sobald es Anwendungsfälle gibt, die schreiben. Ein Skill gibt Wissen und Ablauf, das Werkzeug führt aus und trägt die Rechte.
- Er ist der «eigene Werkzeug-Dienst» aus dem Entscheid zu OP-10 vom 3.11.2026.

### 3. Arten von Werkzeugen

| Art | Beispiel | Wo |
| --- | --- | --- |
| lesen | allgemeine Abfrage, nur Lesemethoden, alle Bereiche, die der Benutzer «Hermes» lesen darf | direkt, Skill `odoo-lesen` (Nachtrag 9.11.2026) |
| Kennzahlen | Kennzahlen-Bibliothek aus `/opt/muster-kennzahlen` | direkt, Skill `kennzahlen-abrufen` (Nachtrag 9.11.2026) |
| Entwurf anlegen | `rechnungsentwurf_anlegen`, `mailentwurf_anlegen` | Werkzeug-Server |
| beantragen | `senden_beantragen`, `buchen_beantragen`, nur mit Freigabe (Regel 5) | Werkzeug-Server |

Rechnen und Ablegen bleiben bei Manni selbst (Terminal und `~/arbeit`, Regel 7).

Werkzeuge für Aktionen, die wir nicht brauchen, gibt es im Server gar nicht, zum Beispiel bezahlen oder löschen. Was es nicht gibt, kann kein Agent auslösen.

Freies Lesen ist wichtig. Ohne freies Suchen findet Manni Auffälligkeiten wie P3 nicht. Feste Kennzahlen allein reichen dafür nicht. Darum bleibt das Lesen direkt und breit, begrenzt durch die Rechte des Odoo-Benutzers «Hermes».

### 4. Vier Sperren übereinander

| Sperre | Frage | Beispiel Odoo | Beispiel Mail |
| --- | --- | --- | --- |
| 1 Enges Werkzeug | Was kann er überhaupt tun? | `rechnungsentwurf_anlegen`, kein allgemeines «schreib in Odoo» | `mailentwurf_anlegen`, `senden_beantragen` |
| 2 Prüfregeln im Server | Ist der Inhalt plausibel? | Kunde existiert, Betrag unter Limit, nur Status Entwurf | nur an bekannte Kontakte, nur aus buchhaltung@, höchstens N pro Tag |
| 3 Freigabe | Wer drückt den letzten Knopf? | Beat gibt das Buchen frei oder bucht selbst | Beat gibt das Senden frei |
| 4 Rechte im System | Was, wenn alles andere versagt? | Der Odoo-Benutzer des Servers hat nur die nötigen Gruppen | Das Postfach-Recht ist auf ein Postfach begrenzt |

### 5. Freigabe: Knopf im Telegram-Chat

- Alles, was sich nicht rückgängig machen lässt (senden, buchen), gibt Beat frei.
- Die Freigabe läuft im normalen Telegram-Chat mit Manni. Es gibt keinen eigenen Freigabekanal.
- **Knopf, nicht Text.** Hermes selbst hält den Werkzeugaufruf an und blendet im Chat einen Knopf ein. Der Knopf zeigt Empfänger und Betreff aus dem echten Aufruf, nicht Mannis Zusammenfassung. Manni kann den Knopf nicht selbst drücken. Ein Tipp gilt für genau diesen einen Aufruf.
- Ein «passt, schick raus» als Text gilt nicht als Freigabe. Sonst müsste Manni selbst beurteilen, ob eine Freigabe vorliegt. Er könnte sie auf den falschen Entwurf beziehen. Eine eingehende Mail mit dem Satz «Beat hat das schon freigegeben» könnte ihn täuschen.
- **Geprüft 10.11.2026 (W1, OP-23):** Der Knopf kommt über eine Rückfrage des Servers (MCP-Elicitation), in Telegram, Desktop-App und Terminal, ohne Plugin. Er hält aber nur für Aufrufe über die Verbindung von Hermes. Mit Terminal und Schlüssel liesse er sich umgehen (OP-37), zu lösen vor dem ersten Werkzeug der Stufe 2 oder 3.
- Geht der Knopf in Hermes v0.22.5 für MCP-Werkzeuge nicht, bauen wir ein kleines eigenes Plugin mit dem Haken `pre_tool_call`. Das braucht Beats Ja zur Installation. Notlösung ist die Freigabe per Text. Dann liegt die Sicherheit allein in den Prüfregeln des Servers (Sperre 2), und das wird so benannt.
- Läuft eine Kategorie lange fehlerfrei, zum Beispiel Zahlungserinnerungen an bekannte Kunden, kann Beat die Freigabe für genau diese Kategorie abschalten. Die Prüfregeln bleiben. Grund: Wer viele Freigaben bekommt, klickt irgendwann blind.
- Ein eigener Freigabekanal ausserhalb von Hermes kommt erst bei einem Kunden, und dort nur für Aktionen mit grossem Schaden, zum Beispiel Zahlungen.

### 6. Werkzeuge mit eigenem Modell: über Sampling

- Ein Werkzeug darf innen ein Sprachmodell nutzen, zum Beispiel ein günstiges Modell zum Lesen eines Belegs. Es bleibt trotzdem ein Werkzeug: ein Schritt, keine eigenen Entscheidungen.
- Das Modell holt sich der Server über MCP-Sampling bei Hermes. Welches Modell, stellt man in Hermes pro Server ein (`mcp_servers.<name>.sampling`).
- Grund (Beat): Im Container liegen keine zusätzlichen Modell-Schlüssel. Die Modell-Schlüssel bleiben an einem Ort.
- Zu prüfen (OP-23): wie Sampling in v0.22.5 genau arbeitet, und ob andere Clients wie Claude Desktop und Claude Code Sampling unterstützen. Das zählt, sobald Menschen denselben Server nutzen. Wenn nicht, braucht das Werkzeug für diese Clients einen Ersatzweg.

### 7. Manni behält Terminal und Dateiwerkzeuge

- Manni behält Terminal, Dateiwerkzeuge und Code-Ausführung.
- Damit kann er theoretisch seinen eigenen Server-Schlüssel, seinen Odoo-Schlüssel (nur lesen) und andere Dateien unter `hermes` lesen. An die Schlüssel im Container kommt er nicht.
- Begründung und Restrisiko stehen unten.

### 8. Wann es doch einen Fachagenten gibt

Ein Fachagent ist ein eigener Agent mit eigener SOUL.md, der selbst plant und mehrere Schritte macht. Er lohnt sich nur, wenn einer dieser Gründe zutrifft:

- Manni braucht in einem Bereich regelmässig lange Ketten von Schritten mit eigenem Urteil.
- Das Fachwissen eines Bereichs überlädt Mannis Kontext.
- Ein Bereich braucht eine eigene Arbeitskette auf einem anderen Modell oder mit eigenem Budget.

Keine Gründe für einen Fachagenten:

- **Rechte.** Die regelt der Werkzeug-Server.
- **Ein anderes Modell für einen Einzelschritt.** Das macht ein Werkzeug mit Sampling (Regel 6).

Später als Versuch: ein einzelner Fachagent, zum Beispiel für die Kreditorenprüfung (P5), im Vergleich zu Manni mit dem passenden Skill. So beantworten wir die Frage mit einem Test statt am Reissbrett.

## Begründung

### Warum Fachagenten keine Sicherheitsgrenze sind

- Alle Hermes-Profile laufen unter demselben Linux-Benutzer `hermes` und liegen unter `~/.hermes/profiles/`.
- Ein Agent mit Terminal kann die `.env` jedes Profils lesen. Getrennte Profile trennen die Rechte also nur auf dem Papier. Das stand schon in OP-22, Punkt 3.
- Der Grundsatz vom 6.11.2026 wollte Fachagenten als Sicherheitsgrenze. Diese Grenze hätte nicht gehalten.

### Warum keine eigenen Linux-Benutzer und keine weiteren Hermes-Installationen

- Eine echte Trennung der Agenten bräuchte pro Fachagent einen eigenen Linux-Benutzer mit eigener Hermes-Installation.
- Verworfen: Das ist aufwendig, schwer zu betreiben und nicht das, was man einem KMU anbietet. Es ist auch nicht der übliche Weg.
- Der übliche Weg: Die Rechte sitzen am Werkzeug, nicht am Agenten. Das ist das Prinzip eines MCP-Gateways: ein Server pro Zugang, abgeschottet im Container, eine Liste erlaubter Werkzeuge pro Agent, und jeder Aufruf trägt die Identität dessen, der ihn macht.

### Warum die Sicherheit im Werkzeug-Server liegt

- Massgebend ist nicht, welcher Agent einen Schlüssel hat. Massgebend ist, was man mit dem Schlüssel anrichten kann.
- Der Server bietet nur Entwürfe und Anträge. Unumkehrbares geht nur mit Beats Freigabe. Gefährliche Werkzeuge gibt es gar nicht. Lesen braucht den Server nicht, das begrenzt der Odoo-Benutzer «Hermes» (Nachtrag 9.11.2026).
- Wer einen Schlüssel des Servers stiehlt, kann im schlimmsten Fall einen Entwurf anlegen oder eine Freigabe beantragen. Ohne Beats Tipp geht nichts hinaus und nichts wird gebucht.

### Warum Manni das Terminal behält

- Ohne Terminal verlöre Manni freies Suchen, Rechnen mit Python und das Ablegen von Dateien. Ein Teil davon liesse sich mit Werkzeugen ersetzen, aber Etappe E würde dann einen anderen Manni messen.
- Das Terminal gefährdet die Sicherheit im Werkzeug-Server nicht (siehe oben).
- **Restrisiko, offen benannt:** Diese Ordnung schützt gegen Irrtümer und gegen Täuschung, zum Beispiel durch eine manipulierte Mail. Sie schützt nicht gegen einen Manni, der gezielt Schlüssel sucht und missbraucht. Für Testdaten, bei denen nur Entwürfe und freigegebene Aktionen möglich sind, ist das vertretbar. Beim Kunden gehört es in die Risikobeurteilung.
- **Auslöser zum Überdenken:** Sobald ein Agent ein Recht bekommt, dessen Missbrauch ohne Freigabe echten Schaden anrichtet oder vertrauliche Daten zeigt (zum Beispiel Löhne, Personaldaten, Zahlungen), verlieren Agenten im selben Linux-Benutzer das Terminal, oder das Terminal läuft in einer Sandbox.

### Vergleich mit den zwei Quellen

**AI-First, KI-Betriebssystem 2.0** (https://ai-first.ai/insights/ai-first-ki-betriebssystem-2-0)

- Gleich: Rechte nur im Tool, nie im Agenten. Der Agent liest und legt Entwürfe an, ein Mensch schickt ab. Technisch gesperrt ist nur, was echten Schaden anrichten kann. Regeln und Sperren ändert nur ein Mensch.
- Gleich: ein einziger Agent mit Skills. AI-First hat die Skills von rund 100 auf 19 zusammengestrichen.
- Anders: Dort hat jede Person ihren eigenen Agenten (Claude Code, mit Shell) und meldet sich mit dem eigenen Konto an. Die Shell sieht nur die Schlüssel dieser Person. Bei uns teilen sich Hintergrund-Agenten eine Maschine. Darum sitzt die Sicherheit bei uns im Werkzeug-Server.
- Ihre technische Sperre ist ein Prüfprogramm bei jedem Werkzeugaufruf, vermutlich ein Hook in Claude Code. Es arbeitet mit einer schwarzen Liste: gesperrt sind einzelne Aktionen, alles andere bleibt frei. Bei Hermes entspricht dem `approvals.deny` und der Haken `pre_tool_call`.

**Snowflake Forum Zürich, 5.11.2026** (Grundlage `KMU_Agentenarchitektur_Grundlage_20261106.docx` bei Beat)

- Der Semantic Layer der Vorträge ist bei uns die Kennzahlen-Bibliothek (Katalog, fester Rechenweg, gegen MIS abgeglichen).
- Die Faustregel der Grundlage gilt: mit Werkzeugen und Skills starten, einen Bereich erst zum Sub-Agenten machen, wenn er lange Ketten braucht und den Kontext überlädt. Jede Agentenschicht kostet Tokens und Zeit und macht die Fehlersuche schwerer («stille Post»).
- Die Grundlage nahm das Claude Agent SDK als Agenten an. Auf der Kiste ist es Hermes. Am Prinzip ändert das nichts.

## Übertragbarkeit auf ein KMU

- **Mitarbeitende** haben ihren eigenen Agenten auf dem Desktop (zum Beispiel Claude) und melden sich mit dem eigenen Konto am Werkzeug-Server an, später zum Beispiel über M365. Sie arbeiten mit ihren eigenen Rechten. Das entspricht AI-First.
- **Hintergrund-Agenten** wie Manni haben einen eigenen Agenten-Schlüssel am Werkzeug-Server und einen eigenen Benutzer im Zielsystem, der nur lesen kann.
- Beide nutzen denselben Server mit denselben Werkzeugen, Prüfregeln und Freigaben. Wir bauen nichts doppelt. Nur die Quelle der Identität ändert sich.
- Verkaufsargument: Ruhe beim Inhaber entsteht durch Leitplanken (enge Werkzeuge, Grenzen, Freigaben), nicht durch getrennte Agenten.

## Reihenfolge

1. **Etappe E** (Monatsbericht Oktober 2026) mit Manni und den heutigen Skills. Vorher wird nichts umgebaut.
2. **Prüfpunkte OP-23** klären.
3. **Werkzeug-Server bauen**, spätestens vor dem ersten Anwendungsfall, der schreibt (OP-10). Er enthält nur Werkzeuge, die schreiben. Hermes behält seinen Odoo-Schlüssel zum Lesen.
4. **Später, als Versuch:** ein Fachagent im Vergleich zu Manni mit Skill (Regel 8).

## Was sich an früheren Entscheiden ändert

| Früherer Entscheid | Neu |
| --- | --- |
| 06.11.2026: eigener Agent pro Zugriffsbereich mit eigenem Odoo-Benutzer, Manni ohne diese Rechte | ersetzt durch dieses Dokument |
| 02.11.2026: Kanban mit drei Profilen Buchhaltung, Verkauf, Reporting | zurückgestellt (Regel 1 und 8) |
| 03.11.2026: Schreiben in Odoo in Stufen, Entwürfe über einen eigenen Werkzeug-Dienst (OP-10) | bleibt. Der Werkzeug-Dienst ist der Werkzeug-Server dieses Dokuments |
| 03.11.2026: Kennzahlen-Bibliothek, späterer MCP-Server ersetzt nur den Skill | bleibt als Skill, kommt nicht in den Werkzeug-Server (Nachtrag 9.11.2026) |
| 02.11.2026: Odoo zuerst über einen Skill mit JSON-RPC | bleibt dauerhaft für das Lesen (Nachtrag 9.11.2026) |

## Nachtrag 9.11.2026: Lesen direkt, Schreiben über den Server (Variante B)

Entscheid von Beat am 9.11.2026, nach der Vorbereitung von OP-23. Bis dahin sah dieses Dokument vor, dass auch das Lesen über den Werkzeug-Server läuft und Hermes seinen Odoo-Schlüssel verliert (Variante A).

### Die Frage

Beat: «Ich kann mir nicht vorstellen, dass wir unseren Agenten derart beschneiden, dass er nicht mehr über das native Leserecht in Odoo verfügt und sich überall in Odoo seine Infos suchen kann.» Müsste dann jeder Anwendungsfall einzeln freigeschaltet werden?

Antwort: Nein. Ein allgemeines Lese-Werkzeug im Server hätte dieselben Rechte wie Mannis heutiger Odoo-Benutzer. Die Frage war also nicht, ob Manni frei lesen darf, sondern auf welchem Weg.

### Die zwei Varianten

| | A: Alles über den Server | B: Lesen direkt, Schreiben über den Server |
| --- | --- | --- |
| Manni liest | über ein Lese-Werkzeug im Server | wie seit 3.11.2026 mit eigenem Odoo-Benutzer, nur lesen |
| Manni schreibt | nur über enge Werkzeuge mit Freigabe | gleich |
| Aufwand | höher: Lese-Werkzeug bauen, Skills umstellen, Etappe E zur Kontrolle wiederholen | kleiner: Der Server enthält nur Werkzeuge, die schreiben |
| Server fällt aus | Manni kann nichts mehr lesen | Lesen geht weiter |
| Schlüssel bei Manni | keiner | ein Lese-Schlüssel, alle zwei Monate zu erneuern (OP-13) |

### Die Gründe für A, nüchtern betrachtet

| Grund für A | Bewertung |
| --- | --- |
| Nur ein Ort mit Schlüsseln | stimmt. Der Lese-Schlüssel kann aber nichts verändern und läuft nach zwei Monaten ab |
| Der Schlüssel könnte beim Modell-Anbieter landen | stimmt. Die Daten selbst landen dort aber in beiden Varianten, sobald Manni liest |
| Alles an einer Stelle protokolliert | gibt es schon: Hermes hält jeden Werkzeugaufruf mit Befehl in `state.db` fest (Grundlage der Auswertung von Etappe E) |
| Heikle Bereiche später sperren | geht auch in Odoo selbst: Der Benutzer «Hermes» bekommt die Gruppen dafür nicht |

### Warum B

- **OWASP LLM06 «Excessive Agency»** verlangt minimale Rechte und dass das Zielsystem die Rechte prüft, nicht das Modell. Ein eigener Odoo-Benutzer, der nur lesen kann, erfüllt das. Direktes Lesen ist darum kein Sicherheitsmangel. Folgenreiche Aktionen brauchen enge Werkzeuge und die Freigabe durch einen Menschen. Genau dafür ist der Server da.
- **Übliche Praxis (Common Practice).** Die verbreiteten Agenten-Frameworks setzen die Freigabe beim Werkzeug an, das handelt (OpenAI Agents SDK `needs_approval`, Claude Agent SDK Freigaben pro Werkzeug, Bedrock AgentCore Gateway mit Regeln pro Werkzeug). Ein Agent mit eigener Identität und Leserechten im Zielsystem ist dabei der Normalfall. Beat: «Beides funktioniert, aber mein Bauchgefühl sagt mir, dass wir mit Variante B eher bei der üblichen Praxis sind. Ob es Best Practice ist, ist eine andere Frage.»
- **Nicht überbauen.** Der Server bleibt klein und wird nur dort gebraucht, wo ein Fehler wirklich Schaden anrichtet.

### Was sich ändert

- Regel 2: Hermes behält seinen Odoo-Schlüssel zum Lesen. Der Server hält nur die Schlüssel zum Schreiben.
- Regel 3: Lesen und Kennzahlen sind keine Werkzeuge des Servers, sondern bleiben Skills.
- OP-13: Der Lese-Schlüssel muss dauerhaft alle zwei Monate erneuert werden.
- Kennzahlen-Bibliothek: bleibt ein Skill. Ein MCP-Werkzeug dafür nur, wenn andere Clients (Claude Desktop, Mitarbeitende) sie brauchen.

### Restrisiko, offen benannt

- Der Lese-Schlüssel steht in Mannis Umgebung. Manni könnte ihn im Terminal sichtbar machen, dann landet er beim Modell-Anbieter. Mit dem Schlüssel lässt sich Odoo nur lesen, und nur aus dem Netz, in dem Odoo erreichbar ist (OP-04).
- Auslöser zum Überdenken: Bekommt Odoo vertrauliche Bereiche, die Manni nicht sehen soll (zum Beispiel Löhne), sperren wir sie zuerst über die Gruppen des Benutzers «Hermes». Reicht das nicht, kommt Variante A wieder auf den Tisch.

### Quellen zum Nachtrag

- OWASP, LLM06:2025 Excessive Agency: https://owasp.org/www-project-top-10-for-large-language-model-applications/2_0_vulns/LLM06_ExcessiveAgency.html
- OpenAI Agents SDK, Human in the loop: https://openai.github.io/openai-agents-python/human_in_the_loop
- Claude Agent SDK, Approvals: https://code.claude.com/docs/en/agent-sdk/approvals
- Arcjet, «canUseTool is not a policy gate» (harte Sperren im Werkzeug): https://arcjet.com/learn/canusetool-is-not-a-policy-gate
- AWS, Govern MCP Tools at Scale with Kiro and AgentCore Gateway: https://builder.aws.com/content/3CS1jTWHngGW3IxFXCjcP2T9l8B/govern-mcp-tools-at-scale-with-kiro-and-agentcore-gateway

## Quellen

- AI-First, «KI-Betriebssystem 2.0»: https://ai-first.ai/insights/ai-first-ki-betriebssystem-2-0
- Hermes Agent, Tools & Toolsets: https://hermes-agent.nousresearch.com/docs/user-guide/features/tools
- Hermes Agent, MCP (Sampling, Filter pro Server): https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp
- Hermes Agent, Plugin withHuman (Freigabe über `pre_tool_call`, nicht eingesetzt): https://hermes-agent.nousresearch.com/docs/plugins/withhuman
- Stacklok, MCP Security Best Practices 2026: https://stacklok.com/blog/mcp-security-best-practices-what-every-enterprise-team-needs-to-know-in-2026/
- CData, Enterprise MCP Security Best Practices 2026: https://www.cdata.com/blog/enterprise-mcp-security-best-practices-2026
