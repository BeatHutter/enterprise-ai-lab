#!/usr/bin/env bash
# Prüft jede Regel von offerte_entwurf_anlegen mit einem eigenen Aufruf (Etappe UC-005, Bauschritt O1).
# Schreibt in Odoo: Erfolgsfälle legen Angebote mit Kundenreferenz TEST-O1-… an, das Skript löscht sie am Ende wieder.
# Vorher Sicherung (Regel 4). Aufruf als operator: bash werkzeug-server/pruefung/offerte_pruefen.sh
set -u
cd "$(dirname "$0")/.."

ok=0
fehler=0
ref="TEST-O1-$(date +%H%M%S)"

aufruf() {
    docker compose exec -T -e SCHLUESSEL="$(cat pruefschluessel.txt)" werkzeug-server \
        python - offerte_entwurf_anlegen "$1" < pruefung/mcp_aufruf.py 2>&1 | tail -1
}

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

# $1 Kunde, $2 Positionen als JSON-Liste
angebot() { echo "{\"kunde_id\": $1, \"positionen\": $2, \"kundenreferenz\": \"$ref\"}"; }

echo "== Prüfregeln (dürfen nichts anlegen)"
pruefe "Kunde gibt es nicht"            "ABGELEHNT: Kein aktiver Kontakt"     "$(angebot 99999 '[{"artikel": "BA-100", "menge": 1}]')"
pruefe "Kontakt ist kein Kunde"         "ABGELEHNT: .*nicht als Kunde"        "$(angebot 47 '[{"artikel": "BA-100", "menge": 1}]')"
pruefe "Artikel gibt es nicht"          "ABGELEHNT: Artikel TB-500 .*Gültige Codes" "$(angebot 8 '[{"artikel": "TB-500", "menge": 1}]')"
pruefe "Menge 0"                        "ABGELEHNT: Menge für BA-100"         "$(angebot 8 '[{"artikel": "BA-100", "menge": 0}]')"
pruefe "Halbe Parkbank"                 "ABGELEHNT: BA-100 wird in ganzen Stück" "$(angebot 8 '[{"artikel": "BA-100", "menge": 1.5}]')"
pruefe "Keine Positionen"               "ABGELEHNT: .*keine Positionen"       "$(angebot 8 '[]')"

echo "== Erfolgsfälle"
pruefe "Gemeinde: Standardpreis, ohne Rabatt" "ANGEBOT ALS ENTWURF ANGELEGT: .*Preisliste Standard.*1,850.00 = 3,700.00" \
    "$(angebot 8 '[{"artikel": "BA-100", "menge": 2}, {"artikel": "DL-010", "menge": 1.5}]')"
pruefe "Gartenbauer: Preisliste 10 %"   "ANGEBOT ALS ENTWURF ANGELEGT: .*Wiederverkäufer.*− 10 %" \
    "$(angebot 31 '[{"artikel": "GR-080", "menge": 4}]')"
pruefe "Zweites Angebot gleicher Kunde und Artikel: Warnung" "ANGEBOT ALS ENTWURF ANGELEGT: .*WARNUNG.*Möglicherweise doppelt" \
    "$(angebot 8 '[{"artikel": "BA-100", "menge": 3}]')"
pruefe "Ungewöhnliche Menge: Warnung"   "ANGEBOT ALS ENTWURF ANGELEGT: .*WARNUNG.*VE-010 ist mehr als 5-mal" \
    "$(angebot 22 '[{"artikel": "VE-010", "menge": 500}]')"
pruefe "Total über 100'000: Warnung"    "ANGEBOT ALS ENTWURF ANGELEGT: .*WARNUNG.*über 100,000" \
    "$(angebot 7 '[{"artikel": "VE-200", "menge": 6}]')"

echo "== Kontrolle in Odoo und Aufräumen (als Admin)"
python3 - "$ref" <<'EOF'
import sys
sys.path.insert(0, "../data-generator")
from odoo_client import OdooClient
ref = sys.argv[1]
o = OdooClient(); o.login()
angebote = o.search_read("sale.order", [("client_order_ref", "=like", "TEST-O1-%")],
                         ["name", "client_order_ref", "state", "user_id", "create_uid", "amount_untaxed"])
fehler = 0
eigene = [a for a in angebote if a["client_order_ref"] == ref]
for a in eigene:
    print(f"        {a['name']}: Status {a['state']}, Verkäufer {a['user_id'][1]}, netto {a['amount_untaxed']}")
if len(eigene) != 5 or any(a["state"] != "draft" or a["create_uid"][1] != "Werkzeug-Server" for a in eigene):
    print("FEHLER  genau fünf Angebote dieses Laufs, alle Entwurf und vom Werkzeug-Server"); fehler += 1
else:
    print("ok      fünf Angebote dieses Laufs, alle Entwurf und vom Werkzeug-Server")
loeschen = [a["id"] for a in angebote if a["state"] == "draft"]
if loeschen:
    o.call("sale.order", "unlink", loeschen)
print(f"ok      {len(loeschen)} Test-Angebot(e) gelöscht")
sys.exit(fehler)
EOF
[ $? -eq 0 ] && ok=$((ok + 2)) || fehler=$((fehler + 1))

echo
echo "Ergebnis: $ok ok, $fehler FEHLER"
[ "$fehler" -eq 0 ]
