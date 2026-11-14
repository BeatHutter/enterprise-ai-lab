#!/usr/bin/env bash
# Prüft als hermes: Kennzahlen-Bibliothek lesen und ausführen ja, ändern nein. Skill eingebunden,
# kein gleichnamiger Skill mit Vorrang. Ändert nichts, ausser ein Schreibversuch gelingt (dann FEHLER).
#
# Aufruf als operator: sudo bash kennzahlen/rechte-pruefen.sh

set -uo pipefail

ZIEL=/opt/muster-kennzahlen
fehler=0
ok()     { echo "  ok      $*"; }
falsch() { echo "  FEHLER  $*"; fehler=$((fehler + 1)); }
als_hermes() { runuser -u hermes -- env -i HOME=/home/hermes PATH=/usr/bin:/bin COLUMNS=200 bash -c "cd /home/hermes && $1"; }
# Mit dem Odoo-Zugang von hermes: nur die vier ODOO_*-Zeilen aus seiner .env, nie ausgegeben
LADE_ODOO='while IFS="=" read -r k v; do case "$k" in ODOO_URL|ODOO_DB|ODOO_USER|ODOO_API_KEY) export "$k=$(printf %s "$v" | tr -d "\"\047\r")";; esac; done < /home/hermes/.hermes/.env'
mit_odoo() { als_hermes "$LADE_ODOO; $1"; }

[ "$(id -u)" -eq 0 ] || { echo "Abbruch: mit sudo starten: sudo bash $0"; exit 1; }
echo "Rechteprüfung Kennzahlen-Bibliothek als hermes ($(date '+%d.%m.%Y %H:%M'))"

echo
echo "1. Lesen und ausführen (muss gehen)"
als_hermes "head -1 $ZIEL/katalog.md" >/dev/null 2>&1 && ok "Katalog lesen" || falsch "Katalog lesen"
als_hermes "cat $ZIEL/skills/kennzahlen-abrufen/SKILL.md" >/dev/null 2>&1 && ok "Skill lesen" || falsch "Skill lesen"
als_hermes "cat $ZIEL/STAND" >/dev/null 2>&1 && ok "STAND lesen" || falsch "STAND lesen"
als_hermes "python3 -B $ZIEL/kennzahl.py liste" >/dev/null 2>&1 && ok "kennzahl.py liste" || falsch "kennzahl.py liste"
als_hermes "python3 -B $ZIEL/kennzahl.py katalog ebitda" >/dev/null 2>&1 && ok "kennzahl.py katalog ebitda" || falsch "kennzahl.py katalog"

echo
echo "2. Rechnen mit dem Odoo-Benutzer «Hermes» (muss gehen)"
for aufruf in "nettoerloes --von 2026-01-01 --bis 2026-10-31" \
              "nettoerloes_nach_segment --von 2026-01-01 --bis 2026-10-31" \
              "ebitda --von 2025-01-01 --bis 2025-12-31" \
              "debitoren_altersstruktur --stichtag 2026-10-31" \
              "debitorenfrist --von 2026-01-01 --bis 2026-10-31"; do
  if ausgabe=$(mit_odoo "python3 -B $ZIEL/kennzahl.py $aufruf --format text" 2>&1); then
    ok "$aufruf: $(sed -n 's/^Wert: //p' <<<"$ausgabe")"
  else
    falsch "$aufruf: $ausgabe"
  fi
done

echo
echo "3. Ändern (muss scheitern)"
versuch() {  # Beschreibung, Befehl
  if als_hermes "$2" >/dev/null 2>&1; then falsch "$1 GELANG"; else ok "$1 abgelehnt"; fi
}
versuch "neue Datei anlegen"        "touch $ZIEL/probe"
versuch "Katalog ergänzen"          "echo x >> $ZIEL/katalog.md"
versuch "Katalog löschen"           "rm -f $ZIEL/katalog.md"
versuch "Katalog umbenennen"        "mv $ZIEL/katalog.md $ZIEL/k.md"
versuch "Rechte ändern"             "chmod 777 $ZIEL/kennzahl.py"
versuch "Rechenweg überschreiben"   "echo x > $ZIEL/kennzahlen/k01_nettoerloes.py"
versuch "Ordner anlegen"            "mkdir $ZIEL/kennzahlen/neu"
versuch "Skill ändern"              "echo x >> $ZIEL/skills/kennzahlen-abrufen/SKILL.md"
versuch "Skill-Ordner anlegen"      "mkdir $ZIEL/skills/eigener-skill"
( cd "$ZIEL" && sed -n '/^Prüfsummen/,$p' STAND | tail -n +2 | sha256sum -c --quiet ) \
  && ok "Prüfsummen unverändert" || falsch "Prüfsummen weichen ab: neu einspielen mit bash kennzahlen/einspielen.sh"

echo
echo "4. Skill eingebunden, kein Schatten-Skill"
if grep -A3 -E '^\s*external_dirs:' /home/hermes/.hermes/config.yaml | grep -q "$ZIEL/skills"; then
  ok "skills.external_dirs enthält $ZIEL/skills"
else
  falsch "skills.external_dirs enthält $ZIEL/skills nicht"
fi
schatten=$(grep -rl --include=SKILL.md -E '^name:\s*kennzahlen-abrufen\s*$' /home/hermes/hermes-skills /home/hermes/.hermes/skills 2>/dev/null)
[ -z "$schatten" ] && ok "kein gleichnamiger Skill in hermes-skills oder ~/.hermes/skills" || falsch "gleichnamiger Skill mit Vorrang: $schatten"
# Anmelde-Shell wie im Betrieb: mit env -i liefert hermes skills list keine Zeilen
liste=$(runuser -l hermes -c 'COLUMNS=200 hermes skills list 2>&1')
if grep -E "kennzahlen-abrufen" <<<"$liste" | grep -q "external"; then
  ok "hermes skills list zeigt kennzahlen-abrufen (Quelle external)"
else
  falsch "hermes skills list zeigt kennzahlen-abrufen nicht als external"
fi
grep -q "kennzahlen-abrufen" /home/hermes/.hermes/SOUL.md && ok "SOUL.md enthält den Satz zu kennzahlen-abrufen" || falsch "SOUL.md ohne Satz zu kennzahlen-abrufen"

echo
if [ "$fehler" -eq 0 ]; then echo "Ergebnis: alles bestanden."; else echo "Ergebnis: $fehler Fehler."; exit 1; fi
