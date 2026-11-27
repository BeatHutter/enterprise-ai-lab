#!/usr/bin/env bash
# Prüft jede Regel der CRM-Werkzeuge für K4 / UC-029:
# verkaufschance_anlegen, notiz_an_chance, aktivitaet_planen und offerte_entwurf_anlegen mit chance_id.
# Schreibt Testdatensätze (Titel mit Präfix TEST-K4-…) in Odoo und löscht sie am Ende wieder.
# Aufruf als operator: bash werkzeug-server/pruefung/crm_pruefen.sh
set -u
cd "$(dirname "$0")/.."

ok=0
fehler=0
ref="TEST-K4-$(date +%H%M%S)"

aufruf() {
    local werkzeug="$1"
    local args="$2"
    local rueckfrage="${3:-ablehnen}"
    docker compose exec -T -e SCHLUESSEL="$(cat pruefschluessel.txt)" -e RUECKFRAGE="$rueckfrage" werkzeug-server \
        python - "$werkzeug" "$args" < pruefung/mcp_aufruf.py 2>&1 | tail -1
}

pruefe() {
    local name="$1"
    local muster="$2"
    local werkzeug="$3"
    local args="$4"
    local rueckfrage="${5:-ablehnen}"
    local antwort
    antwort=$(aufruf "$werkzeug" "$args" "$rueckfrage")
    if echo "$antwort" | grep -q -E "$muster"; then
        echo "ok      $name"
        ok=$((ok + 1))
    else
        echo "FEHLER  $name"
        echo "        Antwort: $antwort"
        fehler=$((fehler + 1))
    fi
}

echo "== 1. Prüfregeln verkaufschance_anlegen (dürfen nichts anlegen)"
pruefe "Titel leer" \
    "ABGELEHNT: Der Titel.*leer" \
    verkaufschance_anlegen '{"titel": "   ", "firma": "Gemeinde Hügelfingen"}'

pruefe "Weder Firma noch E-Mail" \
    "ABGELEHNT: Mindestens Firma.*oder E-Mail" \
    verkaufschance_anlegen "{\"titel\": \"$ref Ohne Kontakt\"}"

pruefe "Ungültige E-Mail" \
    "ABGELEHNT: Ungültige E-Mail" \
    verkaufschance_anlegen "{\"titel\": \"$ref Ungültige Mail\", \"email\": \"keine-mail\"}"

pruefe "Negativer Schätzwert" \
    "ABGELEHNT: Geschätzter Wert darf nicht negativ" \
    verkaufschance_anlegen "{\"titel\": \"$ref Negativ\", \"firma\": \"Test\", \"geschaetzter_wert\": -100}"

pruefe "Ungültiges Fristdatum" \
    "ABGELEHNT: Frist .*kein gültiges Datum" \
    verkaufschance_anlegen "{\"titel\": \"$ref Frist\", \"firma\": \"Test\", \"frist\": \"31.12.2026\"}"

pruefe "Unbekannte Verkaufsperson" \
    "ABGELEHNT: Unbekannte Verkaufsperson" \
    verkaufschance_anlegen "{\"titel\": \"$ref Person\", \"firma\": \"Test\", \"zustaendig\": \"Max Mustermann\"}"

pruefe "Unbekanntes Merkmal" \
    "ABGELEHNT: Unbekannte Merkmale: Fantasie" \
    verkaufschance_anlegen "{\"titel\": \"$ref Merkmal\", \"firma\": \"Test\", \"merkmale\": [\"Fantasie\"]}"

pruefe "Unbekannte Quelle" \
    "ABGELEHNT: Unbekannte Quelle" \
    verkaufschance_anlegen "{\"titel\": \"$ref Quelle\", \"firma\": \"Test\", \"quelle\": \"Brieftaube\"}"

echo "== 2. Erfolgsfälle verkaufschance_anlegen (Neukunde + Warnungen)"
antw_neu=$(aufruf verkaufschance_anlegen "{\"titel\": \"$ref Gemeinde Hügelfingen: Velounterstand Bahnhof\", \"firma\": \"Gemeinde Hügelfingen\", \"kontaktperson\": \"Lukas Frei\", \"funktion\": \"Bauverwalter\", \"email\": \"info@huegelfingen.example\", \"strasse\": \"Dorfstrasse 1\", \"plz\": \"8999\", \"ort\": \"Hügelfingen\", \"geschaetzter_wert\": 18500, \"merkmale\": [\"Gemeinde\"], \"quelle\": \"E-Mail\", \"frist\": \"2027-02-28\", \"beschreibung\": \"Velounterstand 10 Plätze mit Glasdach beim Bahnhof.\"}")
if echo "$antw_neu" | grep -q -E "VERKAUFSCHANCE ANGELEGT: ID [0-9]+.*Stufe Neu, zuständig Reto Kälin, geschätzter Wert 18,500.00 CHF, Merkmale: Gemeinde"; then
    echo "ok      Neukunde Hügelfingen angelegt (automatisch Reto Kälin zugeteilt)"
    ok=$((ok + 1))
else
    echo "FEHLER  Neukunde Hügelfingen anlegen"
    echo "        Antwort: $antw_neu"
    fehler=$((fehler + 1))
fi
chance_id=$(echo "$antw_neu" | sed -n 's/.*VERKAUFSCHANCE ANGELEGT: ID \([0-9]*\).*/\1/p')

pruefe "Zweite Chance gleicher Kontakt: Dubletten-Warnung" \
    "VERKAUFSCHANCE ANGELEGT: .*WARNUNG.*bereits offene Verkaufschance.*Möglicherweise doppelt" \
    verkaufschance_anlegen "{\"titel\": \"$ref Hügelfingen Dublette\", \"firma\": \"Gemeinde Hügelfingen\", \"email\": \"info@huegelfingen.example\", \"geschaetzter_wert\": 18500}"

pruefe "Bestehender Kunde (Gemeinde Talbach): Kunden-Warnung" \
    "VERKAUFSCHANCE ANGELEGT: .*WARNUNG.*bereits als Kunde" \
    verkaufschance_anlegen "{\"titel\": \"$ref Talbach Anfrage\", \"firma\": \"Gemeinde Talbach\", \"geschaetzter_wert\": 12000}"

pruefe "Schätzwert über 100'000: Schwellenwert-Warnung" \
    "VERKAUFSCHANCE ANGELEGT: .*WARNUNG.*über 100,000 CHF.*IVöB" \
    verkaufschance_anlegen "{\"titel\": \"$ref Grossprojekt\", \"firma\": \"Gemeinde Grossmatt\", \"geschaetzter_wert\": 160000}"

echo "== 3. Prüfregeln und Erfolg notiz_an_chance"
pruefe "Notiz an unbekannte Chance" \
    "ABGELEHNT: Keine Verkaufschance mit der ID 999999" \
    notiz_an_chance '{"chance_id": 999999, "notiz": "Test"}'

pruefe "Leere Notiz" \
    "ABGELEHNT: Der Notiztext darf nicht leer sein" \
    notiz_an_chance "{\"chance_id\": ${chance_id:-1}, \"notiz\": \"   \"}"

pruefe "Qualifizierungsnotiz an Hügelfingen anhängen" \
    "NOTIZ AN CHANCE ANGEHÄNGT: Chance ID ${chance_id:-0}.*Autor Manni \(KI-Assistent\)" \
    notiz_an_chance "{\"chance_id\": ${chance_id:-1}, \"notiz\": \"Qualifizierungsvorschlag:\n- Bedarf: VE-100 Velounterstand 10 Plätze (CHF 14'800)\n- Budget & Zeitpunkt: beim Erstkontakt klären\n- Öffentliches Beschaffungswesen (IVöB): unter CHF 150'000 freihändige Vergabe möglich.\"}"

echo "== 4. Prüfregeln und Erfolg aktivitaet_planen"
pruefe "Ungültige Aktivitätsart" \
    "ABGELEHNT: Unbekannte Aktivitätsart" \
    aktivitaet_planen "{\"chance_id\": ${chance_id:-1}, \"zusammenfassung\": \"Anrufen\", \"faellig_am\": \"2026-12-02\", \"art\": \"fax\"}"

pruefe "Ungültiges Fälligkeitsdatum" \
    "ABGELEHNT: Fälligkeitsdatum .*kein gültiges Datum" \
    aktivitaet_planen "{\"chance_id\": ${chance_id:-1}, \"zusammenfassung\": \"Anrufen\", \"faellig_am\": \"morgen\"}"

pruefe "Aktivität für Reto Kälin an Hügelfingen planen" \
    "AKTIVITÄT GEPLANT: ID [0-9]+, Anruf «Erstkontakt und Qualifizierung Lukas Frei» an Chance ID ${chance_id:-0}.*für Reto Kälin, fällig am 2026-12-01" \
    aktivitaet_planen "{\"chance_id\": ${chance_id:-1}, \"zusammenfassung\": \"Erstkontakt und Qualifizierung Lukas Frei\", \"faellig_am\": \"2026-12-01\", \"art\": \"call\", \"notiz\": \"Bedarf, Fundament und Liefertermin Frühling 2027 klären.\"}"

echo "== 5. Neukunde anlegen mit Freigabe per Knopf (kunde_anlegen) und Offerte (offerte_entwurf_anlegen)"
pruefe "Offerte auf Chance in Stufe Neu wird abgelehnt" \
    "ABGELEHNT: Verkaufschance ID ${chance_id:-0}.*steht noch in der Stufe «Neu»" \
    offerte_entwurf_anlegen "{\"kunde_id\": 8, \"chance_id\": ${chance_id:-1}, \"kundenreferenz\": \"$ref\", \"positionen\": [{\"artikel\": \"VE-100\", \"menge\": 1}]}"

pruefe "kunde_anlegen: Dubletten-Sperre bei bestehendem Kunden (Gemeinde Talbach)" \
    "ABGELEHNT: Kontakt oder E-Mail-Domain existiert in Odoo bereits: Gemeinde Talbach" \
    kunde_anlegen '{"firma": "Gemeinde Talbach", "ort": "Talbach", "email": "info@talbach.example"}' \
    annehmen

pruefe "kunde_anlegen: Ungültige Preisliste wird abgelehnt" \
    "ABGELEHNT: Unbekannte Preisliste" \
    kunde_anlegen '{"firma": "Testfirma", "ort": "Zürich", "email": "info@testfirma.example", "preisliste": "50 Prozent Rabatt"}' \
    annehmen

pruefe "kunde_anlegen: Ohne Ort wird abgelehnt" \
    "ABGELEHNT: Der Ort des Kunden muss angegeben sein" \
    kunde_anlegen '{"firma": "Testfirma", "email": "info@testfirma.example"}' \
    annehmen

pruefe "kunde_anlegen: Ohne Elicitation (z. B. im Cron-Job) geschlossen abgelehnt" \
    "ABGELEHNT DURCH MENSCH \(Der Client kann keine Rückfrage stellen.*\): Neukunde «Gemeinde Hügelfingen» wurde nicht angelegt" \
    kunde_anlegen "{\"chance_id\": ${chance_id:-1}}" \
    keine

pruefe "kunde_anlegen: Mensch klickt Ablehnen am Knopf -> nichts angelegt" \
    "ABGELEHNT DURCH MENSCH \(abgelehnt\): Neukunde «Gemeinde Hügelfingen» wurde nicht angelegt" \
    kunde_anlegen "{\"chance_id\": ${chance_id:-1}}" \
    ablehnen

antw_kunde=$(aufruf kunde_anlegen "{\"chance_id\": ${chance_id:-1}}" annehmen)
if echo "$antw_kunde" | grep -q -E "KUNDE ANGELEGT \(MIT FREIGABE\): ID [0-9]+, «Gemeinde Hügelfingen».*8999 Hügelfingen, Preisliste Standard, Kontaktperson Lukas Frei.*verknüpft mit Verkaufschance ID ${chance_id:-0}.*Stufe jetzt «Qualifiziert»"; then
    echo "ok      kunde_anlegen: Mit Freigabe per Knopf angelegt, Kontaktperson erstellt und Chance auf Qualifiziert gesetzt"
    ok=$((ok + 1))
else
    echo "FEHLER  kunde_anlegen mit Freigabe"
    echo "        Antwort: $antw_kunde"
    fehler=$((fehler + 1))
fi
neukunde_id=$(echo "$antw_kunde" | sed -n 's/.*KUNDE ANGELEGT (MIT FREIGABE): ID \([0-9]*\).*/\1/p')

pruefe "Offerte mit falscher Kunde-ID zur Chance wird abgelehnt" \
    "ABGELEHNT: Verkaufschance ID ${chance_id:-0} gehört zu Gemeinde Hügelfingen" \
    offerte_entwurf_anlegen "{\"kunde_id\": 31, \"chance_id\": ${chance_id:-1}, \"kundenreferenz\": \"$ref\", \"positionen\": [{\"artikel\": \"VE-100\", \"menge\": 1}]}"

pruefe "Offerte für neuen Kunden Hügelfingen erfolgreich mit qualifizierter Chance verknüpft" \
    "ANGEBOT ALS ENTWURF ANGELEGT: S[0-9]+ für Gemeinde Hügelfingen, verknüpft mit Chance ID ${chance_id:-0}.*Verkäufer Reto Kälin" \
    offerte_entwurf_anlegen "{\"kunde_id\": ${neukunde_id:-8}, \"chance_id\": ${chance_id:-1}, \"kundenreferenz\": \"$ref\", \"positionen\": [{\"artikel\": \"VE-100\", \"menge\": 1}]}"

echo "== 6. Kontrolle in Odoo (Autor «Manni (KI-Assistent)», Kunde, Aktivität, Verknüpfung) und Aufräumen"
python3 - "$ref" "${chance_id:-0}" "${neukunde_id:-0}" <<'EOF'
import sys
sys.path.insert(0, "../data-generator")
from odoo_client import OdooClient

ref, cid, kid = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
o = OdooClient(); o.login()
fehler = 0

# 1. Prüfen, dass Notiz mit Autor «Manni (KI-Assistent)» an der Chance hängt
notizen = o.search_read(
    "mail.message",
    [("model", "=", "crm.lead"), ("res_id", "=", cid), ("message_type", "=", "comment")],
    ["author_id", "body"],
)
autoren = {n["author_id"][1] for n in notizen if n.get("author_id")}
if "Manni (KI-Assistent)" in autoren and any("Qualifizierungsvorschlag" in (n["body"] or "") for n in notizen):
    print("ok      Notiz an der Chance trägt den Autor «Manni (KI-Assistent)»")
else:
    print(f"FEHLER  Autor oder Inhalt der Notiz stimmt nicht (Autoren: {autoren})")
    fehler += 1

# 2. Prüfen, dass die geplante Aktivität existiert
aktivitaeten = o.search_read(
    "mail.activity",
    [("res_model", "=", "crm.lead"), ("res_id", "=", cid)],
    ["id", "summary", "user_id", "date_deadline"],
)
if len(aktivitaeten) == 1 and aktivitaeten[0]["user_id"][1] == "Reto Kälin":
    print("ok      Aktivität in Odoo für Reto Kälin eingetragen")
else:
    print(f"FEHLER  Aktivität fehlt oder falsch: {aktivitaeten}")
    fehler += 1

# 3. Prüfen, dass das Test-Angebot mit der Chance und dem Neukunden verknüpft ist
angebote = o.search_read(
    "sale.order",
    [("client_order_ref", "=like", "TEST-K4-%")],
    ["id", "name", "state", "partner_id", "opportunity_id", "client_order_ref"],
)
eigene_ang = [a for a in angebote if a["client_order_ref"] == ref]
if (
    len(eigene_ang) == 1
    and eigene_ang[0]["opportunity_id"]
    and eigene_ang[0]["opportunity_id"][0] == cid
    and eigene_ang[0]["partner_id"][0] == kid
):
    print(f"ok      Angebot {eigene_ang[0]['name']} ist mit Neukunde ID {kid} und Chance ID {cid} verknüpft")
else:
    print(f"FEHLER  Verknüpfung Angebot -> Kunde/Chance fehlt: {eigene_ang}")
    fehler += 1

# 4. Aufräumen: Test-Angebote, Aktivitäten, Test-Chancen und Test-Kunden löschen
ang_ids = [a["id"] for a in angebote if a["state"] == "draft"]
if ang_ids:
    o.call("sale.order", "unlink", ang_ids)

chancen = o.search_read(
    "crm.lead",
    [("name", "=like", "TEST-K4-%")],
    ["id"],
    context={"active_test": False},
)
ch_ids = [c["id"] for c in chancen]
if ch_ids:
    act_ids = [a["id"] for a in o.search_read("mail.activity", [("res_model", "=", "crm.lead"), ("res_id", "in", ch_ids)], ["id"])]
    if act_ids:
        o.call("mail.activity", "unlink", act_ids)
    o.call("crm.lead", "unlink", ch_ids)

partner = o.search_read(
    "res.partner",
    ["|", ("id", "=", kid), ("parent_id", "=", kid)],
    ["id", "parent_id"],
    context={"active_test": False},
)
kind_ids = [p["id"] for p in partner if p.get("parent_id")]
haupt_ids = [p["id"] for p in partner if not p.get("parent_id")]
if kind_ids:
    o.call("res.partner", "unlink", kind_ids)
if haupt_ids:
    o.call("res.partner", "unlink", haupt_ids)

print(f"ok      Aufgeräumt: {len(ang_ids)} Test-Angebot(e), {len(ch_ids)} Test-Chance(n) und {len(partner)} Test-Kontakt(e) gelöscht")
sys.exit(fehler)
EOF
if [ $? -eq 0 ]; then
    ok=$((ok + 4))
else
    fehler=$((fehler + 1))
fi

echo
echo "Ergebnis: $ok ok, $fehler FEHLER"
[ "$fehler" -eq 0 ]
