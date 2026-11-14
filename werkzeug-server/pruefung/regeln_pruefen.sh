#!/usr/bin/env bash
# Prüft jede Prüfregel von lieferantenrechnung_entwurf_anlegen mit einem eigenen Aufruf (Bauschritt W2).
# Schreibt in Odoo: Der Erfolgsfall legt einen Entwurf mit Rechnungsnummer TEST-W2-… an, das Skript löscht ihn am Ende wieder.
# Vorher Sicherung (Regel 4). Aufruf als operator: bash werkzeug-server/pruefung/regeln_pruefen.sh
set -u
cd "$(dirname "$0")/.."

ok=0
fehler=0
nr="TEST-W2-$(date +%H%M%S)"

aufruf() {
    docker compose exec -T -e SCHLUESSEL="$(cat pruefschluessel.txt)" werkzeug-server \
        python - lieferantenrechnung_entwurf_anlegen "$1" < pruefung/mcp_aufruf.py 2>&1 | tail -1
}

# $1 Name, $2 erwarteter Anfang der Antwort (grep -E), $3 Argumente als JSON
pruefe() {
    local antwort
    antwort=$(aufruf "$3")
    if echo "$antwort" | grep -q -E "$2"; then
        echo "ok      $1"
        ok=$((ok + 1))
    else
        echo "FEHLER  $1"
        echo "        Antwort: $antwort"
        fehler=$((fehler + 1))
    fi
}

# Gültige Grundlage: Stahlcenter Limmat AG (47), zwei Positionen, 8,1 % Vorsteuer
basis() {
    python3 -c "
import json, sys
d = {'lieferant_id': 47, 'rechnungsnummer': '$nr', 'rechnungsdatum': '2026-11-05', 'faelligkeit': '2026-12-05',
     'waehrung': 'CHF', 'zahlungsreferenz': '210000000003139471430009017', 'bestellung': 'P00283',
     'positionen': [{'text': 'Stahlrohr 60x40x3, 6 m', 'konto': '4000', 'mwst': '8.1%', 'betrag_netto': 1250.00},
                    {'text': 'Transportpauschale', 'konto': '4400', 'mwst': '8.1%', 'betrag_netto': 80.00}],
     'total_brutto': 1437.73}
d.update(json.loads(sys.argv[1]))
print(json.dumps(d))" "$1"
}

echo "== Prüfregeln (dürfen nichts anlegen)"
pruefe "Lieferant gibt es nicht"           "ABGELEHNT: Kein aktiver Kontakt"        "$(basis '{"lieferant_id": 99999}')"
pruefe "Kontakt ist kein Lieferant"        "ABGELEHNT: .*nicht als Lieferant"       "$(basis '{"lieferant_id": 30}')"
pruefe "Doppelerfassung"                   "ABGELEHNT: .*schon erfasst"             "$(basis '{"rechnungsnummer": "SCL-2026-0957"}')"
pruefe "Währung nicht aktiv"               "ABGELEHNT: Währung GBP"                 "$(basis '{"waehrung": "GBP"}')"
pruefe "Konto ausserhalb 4xxx/6xxx"        "ABGELEHNT: Konto 1020 ist nicht erlaubt" "$(basis '{"positionen": [{"text": "x", "konto": "1020", "mwst": "8.1%", "betrag_netto": 1330}]}')"
pruefe "Konto gibt es nicht"               "ABGELEHNT: Konto 6999 gibt es"          "$(basis '{"positionen": [{"text": "x", "konto": "6999", "mwst": "8.1%", "betrag_netto": 1330}]}')"
pruefe "Kein Vorsteuer-Code"               "ABGELEHNT: MWST-Code 100% GS"           "$(basis '{"positionen": [{"text": "x", "konto": "4000", "mwst": "100% GS", "betrag_netto": 1330}]}')"
pruefe "Fälligkeit vor Rechnungsdatum"     "ABGELEHNT: Fälligkeit"                  "$(basis '{"faelligkeit": "2026-10-01"}')"
pruefe "Bestellung eines anderen Lieferanten" "ABGELEHNT: Bestellung P00280 gehört" "$(basis '{"bestellung": "P00280"}')"
pruefe "Rechenfehler auf dem Beleg"        "ABGELEHNT: Total laut Beleg .*Differenz" "$(basis '{"total_brutto": 1473.73}')"

echo "== Erfolgsfall"
pruefe "Gültiger Beleg wird Entwurf"       "^OK ENTWURF ANGELEGT: .*Status Entwurf" "$(basis '{}')"
pruefe "Über 50'000: angelegt mit Warnung"   "ENTWURF ANGELEGT: .*WARNUNG.*über 50,000" "$(basis '{"rechnungsnummer": "'"$nr"'-GROSS", "bestellung": null, "positionen": [{"text": "Laserschneidanlage Anzahlung", "konto": "4000", "mwst": "8.1%", "betrag_netto": 55500}], "total_brutto": 59995.50}')"
pruefe "Dreifaches des Lieferanten: Warnung" "ENTWURF ANGELEGT: .*WARNUNG.*3-mal" "$(basis '{"lieferant_id": 56, "rechnungsnummer": "'"$nr"'-KOMMA", "bestellung": null, "positionen": [{"text": "Inneneimer 35 l", "konto": "4000", "mwst": "8.1%", "betrag_netto": 30000}], "total_brutto": 32430.00}')"
pruefe "Zweiter Versuch mit gleicher Nummer" "ABGELEHNT: .*schon erfasst .*Status draft" "$(basis '{}')"

echo "== Kontrolle in Odoo und Aufräumen (als Admin)"
python3 - "$nr" <<'EOF'
import sys
sys.path.insert(0, "../data-generator")
from odoo_client import OdooClient
nr = sys.argv[1]
o = OdooClient(); o.login()
belege = o.search_read("account.move", [("ref", "like", "TEST-W2-"), ("move_type", "=", "in_invoice")],
                       ["ref", "state", "amount_total", "create_uid", "invoice_origin", "payment_reference"])
fehler = 0
for b in belege:
    print(f"        {b['ref']}: Status {b['state']}, Total {b['amount_total']}, angelegt von {b['create_uid'][1]}, Bestellung {b['invoice_origin']}")
eigene = [b for b in belege if b["ref"] == nr]  # Hauptfall; -GROSS und -KOMMA sind Warnfälle
if len(eigene) != 1 or eigene[0]["state"] != "draft" or eigene[0]["create_uid"][1] != "Werkzeug-Server":
    print("FEHLER  genau ein Entwurf dieses Laufs, angelegt vom Werkzeug-Server"); fehler += 1
else:
    print("ok      genau ein Entwurf dieses Laufs, angelegt vom Werkzeug-Server")
# Nach dem Rechenfehler darf kein Rest bleiben: nur der eine Entwurf trägt diese Nummer
entwuerfe = [b["id"] for b in belege if b["state"] == "draft"]
if entwuerfe:
    o.call("account.move", "unlink", entwuerfe)
print(f"ok      {len(entwuerfe)} Test-Entwurf/Entwürfe gelöscht")
sys.exit(fehler)
EOF
[ $? -eq 0 ] && ok=$((ok + 2)) || fehler=$((fehler + 1))

echo
echo "Ergebnis: $ok ok, $fehler FEHLER"
[ "$fehler" -eq 0 ]
