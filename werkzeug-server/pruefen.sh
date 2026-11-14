#!/usr/bin/env bash
# Prüft den Werkzeug-Server (Bauschritt W0). Ändert nichts, gibt keine Schlüssel aus.
# Aufruf: sudo bash werkzeug-server/pruefen.sh
set -u

if [ "$(id -u)" -ne 0 ]; then
    echo "Bitte mit sudo aufrufen: sudo bash werkzeug-server/pruefen.sh"
    exit 1
fi

# exportiert, weil die Prüfungen in eigenen bash-Aufrufen laufen
export ordner=/home/operator/muster-kmu/werkzeug-server
ok=0
fehler=0

pruefe() {
    local name="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "ok      $name"
        ok=$((ok + 1))
    else
        echo "FEHLER  $name"
        fehler=$((fehler + 1))
    fi
}

nicht() { ! "$@"; }
als_hermes() { runuser -u hermes -- "$@"; }
als_operator() { runuser -u operator -- "$@"; }
compose() { als_operator docker compose -f "$ordner/docker-compose.yml" "$@"; }

# MCP-Aufruf im Container. $1 Datei mit Schlüssel (leer = ohne), $2 Werkzeug. Gibt «OK …» oder «FEHLER …» aus
mcp() {
    local schluessel=""
    [ -n "$1" ] && schluessel=$(cat "$1")
    compose exec -T -e SCHLUESSEL="$schluessel" werkzeug-server python - "$2" < "$ordner/pruefung/mcp_aufruf.py" 2>/dev/null | tail -1
}

http_status() { curl -s -m 3 -o /dev/null -w '%{http_code}' -X POST "$@"; }

echo "== Container"
pruefe "Container läuft" bash -c "$(declare -f als_operator compose); compose ps --status running -q | grep -q ."
pruefe "Port nur auf 127.0.0.1 veröffentlicht" bash -c "$(declare -f als_operator compose); [ \"\$(compose port werkzeug-server 8090)\" = 127.0.0.1:8090 ]"
pruefe "Container läuft nicht als root" bash -c "$(declare -f als_operator compose); [ \"\$(compose exec -T werkzeug-server id -u)\" != 0 ]"
pruefe "Dateisystem im Container nur lesbar" bash -c "$(declare -f als_operator compose); ! compose exec -T werkzeug-server touch /app/test"

echo "== Erreichbarkeit"
pruefe "127.0.0.1:8090 antwortet (401 ohne Schlüssel)" bash -c '[ "$(curl -s -m 3 -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8090/mcp)" = 401 ]'
for adresse in $(hostname -I); do
    case "$adresse" in *:*) url="http://[$adresse]:8090/mcp" ;; *) url="http://$adresse:8090/mcp" ;; esac
    pruefe "nicht erreichbar über $adresse" bash -c "[ \"\$(curl -s -m 3 -o /dev/null -w '%{http_code}' -X POST $url)\" = 000 ]"
done

echo "== Schlüssel und Rechte"
pruefe "ohne Schlüssel abgewiesen" bash -c "$(declare -f als_operator compose mcp); mcp '' ping | grep -q '^FEHLER'"
pruefe "falscher Schlüssel abgewiesen" bash -c "$(declare -f als_operator compose mcp); echo falsch > /tmp/falsch.$$; mcp /tmp/falsch.$$ ping | grep -q '^FEHLER'; r=\$?; rm -f /tmp/falsch.$$; exit \$r"
pruefe "richtiger Schlüssel: ping antwortet" bash -c "$(declare -f als_operator compose mcp); mcp $ordner/pruefschluessel.txt ping | grep -q '^OK pong'"
pruefe "Schlüssel ohne Recht: ping verweigert" bash -c "$(declare -f als_operator compose mcp); mcp $ordner/pruefschluessel-ohne-recht.txt ping | grep -q 'darf das Werkzeug'"
pruefe "zugang.json enthält keine Schlüssel, nur Hashes" bash -c "! grep -q -f $ordner/pruefschluessel.txt $ordner/zugang.json"
pruefe "Protokoll schreibt Aufrufe" bash -c "$(declare -f als_operator compose); compose exec -T werkzeug-server tail -1 /daten/protokoll.jsonl | grep -q zeit"

echo "== Sicht von hermes"
pruefe "hermes erreicht 127.0.0.1:8090" bash -c "$(declare -f als_hermes); [ \"\$(als_hermes curl -s -m 3 -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8090/mcp)\" = 401 ]"
pruefe "hermes liest zugang.json nicht" nicht als_hermes cat "$ordner/zugang.json"
pruefe "hermes liest Odoo-Zugang des Servers nicht" nicht als_hermes test -r "$ordner/.env"
pruefe "hermes liest Prüfschlüssel nicht" nicht als_hermes cat "$ordner/pruefschluessel.txt"
pruefe "hermes erreicht Docker nicht" nicht als_hermes docker ps
pruefe "hermes kommt nicht in die Einhängungen von Docker Desktop" nicht als_hermes ls /mnt/wsl/docker-desktop-bind-mounts

echo
echo "Ergebnis: $ok ok, $fehler FEHLER"
[ "$fehler" -eq 0 ]
