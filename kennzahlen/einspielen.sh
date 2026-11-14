#!/usr/bin/env bash
# Spielt die Kennzahlen-Bibliothek aus dem committeten und gepushten Git-Stand nach
# /opt/muster-kennzahlen ein. Als operator, ohne sudo. Prüft am Ende selbst und fasst zusammen.
#
# Aufruf: bash kennzahlen/einspielen.sh
# Voraussetzung (einmalig, Beat): sudo install -d -o operator -g hermes -m 2750 /opt/muster-kennzahlen

set -euo pipefail

ZIEL=/opt/muster-kennzahlen
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
fehler=0
ok()    { echo "  ok      $*"; }
falsch() { echo "  FEHLER  $*"; fehler=$((fehler + 1)); }

echo "Kennzahlen-Bibliothek einspielen nach $ZIEL"

# --- 1. Vorbedingungen --------------------------------------------------------
[ "$(id -un)" = operator ] || { echo "Abbruch: als operator ausführen, nicht als $(id -un)."; exit 1; }
[ -d "$ZIEL" ] || { echo "Abbruch: $ZIEL fehlt. Einmalig: sudo install -d -o operator -g hermes -m 2750 $ZIEL"; exit 1; }
[ "$(stat -c '%U:%G' "$ZIEL")" = operator:hermes ] || { echo "Abbruch: $ZIEL gehört nicht operator:hermes."; exit 1; }
if [ -n "$(git -C "$REPO" status --porcelain -- kennzahlen)" ]; then
  echo "Abbruch: kennzahlen/ hat Änderungen, die nicht committet sind:"
  git -C "$REPO" status --short -- kennzahlen
  exit 1
fi
git -C "$REPO" fetch -q origin
if [ -n "$(git -C "$REPO" rev-list '@{u}..HEAD' -- kennzahlen)" ]; then
  echo "Abbruch: Commits in kennzahlen/ sind noch nicht gepusht. Erst pushen, GitHub ist das Gedächtnis."
  exit 1
fi
COMMIT=$(git -C "$REPO" rev-parse --short HEAD)

# --- 2. Genau den committeten Stand bereitstellen -----------------------------
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
git -C "$REPO" archive HEAD kennzahlen | tar -x -C "$STAGE"
mkdir -p "$STAGE/opt"
cp "$STAGE/kennzahlen/katalog.md" "$STAGE/kennzahlen/kennzahl.py" "$STAGE/opt/"
mkdir -p "$STAGE/opt/kennzahlen"
cp "$STAGE"/kennzahlen/kennzahlen/*.py "$STAGE/opt/kennzahlen/"
cp -r "$STAGE/kennzahlen/skills" "$STAGE/opt/skills"
# Nicht eingespielt: plan-kennzahlen.md, pruefung/, einspielen.sh, rechte-pruefen.sh (bleiben bei operator)

( cd "$STAGE/opt" && find . -type f ! -name STAND -print0 | sort -z | xargs -0 sha256sum ) > "$STAGE/pruefsummen"
{
  echo "Kennzahlen-Bibliothek der Muster AG"
  echo "Commit:      $COMMIT (Arbeitsrepository, kennzahlen/)"
  echo "Eingespielt: $(date '+%d.%m.%Y %H:%M') durch $(id -un)"
  echo "Katalog:     $(grep -m1 -o 'Version [0-9.]*, freigegeben am [0-9.]*' "$STAGE/opt/katalog.md")"
  echo
  echo "Prüfsummen (sha256sum -c, im Ordner $ZIEL):"
  cat "$STAGE/pruefsummen"
} > "$STAGE/opt/STAND"

# --- 3. Einspielen mit festen Rechten ------------------------------------------
rsync -r --delete --perms --chmod=D2750,F0640 "$STAGE/opt/" "$ZIEL/"
chmod 0750 "$ZIEL/kennzahl.py"

# --- 4. Selbstprüfung -----------------------------------------------------------
echo
echo "Selbstprüfung"
falsche_besitzer=$(find "$ZIEL" ! -user operator -o ! -group hermes | wc -l)
[ "$falsche_besitzer" -eq 0 ] && ok "alles gehört operator:hermes" || falsch "$falsche_besitzer Einträge mit falschem Besitzer"
schreibbar=$(find "$ZIEL" -perm /g+w,o+rwx | wc -l)
[ "$schreibbar" -eq 0 ] && ok "keine Gruppe oder andere mit Schreibrecht" || falsch "$schreibbar Einträge mit Schreibrecht für Gruppe oder andere"
falsche_ordner=$(find "$ZIEL" -type d ! -perm 2750 | wc -l)
[ "$falsche_ordner" -eq 0 ] && ok "Ordner 2750" || falsch "$falsche_ordner Ordner nicht 2750"
[ "$(stat -c '%a' "$ZIEL/kennzahl.py")" = 750 ] && ok "kennzahl.py 0750" || falsch "kennzahl.py nicht 0750"
( cd "$ZIEL" && sed -n '/^Prüfsummen/,$p' STAND | tail -n +2 | sha256sum -c --quiet ) && ok "Prüfsummen stimmen" || falsch "Prüfsummen weichen ab"
for weg in plan-kennzahlen.md pruefung einspielen.sh rechte-pruefen.sh __pycache__; do
  [ -z "$(find "$ZIEL" -name "$weg")" ] || falsch "$weg liegt in $ZIEL"
done
ok "nur Katalog, Rechenwege und Skill eingespielt"
if liste=$(python3 -B "$ZIEL/kennzahl.py" liste 2>&1); then
  anzahl=$(python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' <<<"$liste")
  ok "kennzahl.py liste: $anzahl Kennzahlen und Bausteine, Katalog und Rechenwege passen"
  fehlend=$(python3 -c '
import json, sys
skill = open(sys.argv[1], encoding="utf-8").read()
print(" ".join(k["kennung"] for k in json.load(sys.stdin) if "`" + k["kennung"] + "`" not in skill))
' "$ZIEL/skills/kennzahlen-abrufen/SKILL.md" <<<"$liste")
  [ -z "$fehlend" ] && ok "jede Kennung steht im Skill" || falsch "im Skill fehlen: $fehlend"
else
  falsch "kennzahl.py liste: $liste"
fi
[ -z "$(find "$ZIEL" -name __pycache__)" ] && ok "kein __pycache__" || falsch "__pycache__ entstanden"

echo
echo "Zusammenfassung"
echo "  Commit $COMMIT eingespielt nach $ZIEL, $(find "$ZIEL" -type f | wc -l) Dateien."
echo "  Stand und Prüfsummen: $ZIEL/STAND"
if [ "$fehler" -eq 0 ]; then
  echo "  Selbstprüfung bestanden."
else
  echo "  Selbstprüfung: $fehler Fehler."
  exit 1
fi
