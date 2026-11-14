#!/usr/bin/env bash
# Holt die OCA-Module für Odoo 18 und kopiert die benötigten nach addons/.
# Danach: docker compose up -d --build
set -euo pipefail
cd "$(dirname "$0")"

BRANCH=18.0
mkdir -p oca addons

clone() {
  local repo=$1
  if [ -d "oca/$repo" ]; then
    git -C "oca/$repo" pull --ff-only
  else
    git clone --depth 1 -b "$BRANCH" "https://github.com/OCA/$repo.git" "oca/$repo"
  fi
}

clone account-financial-reporting
clone mis-builder
clone reporting-engine
clone server-ux

for m in \
  account-financial-reporting/account_financial_report \
  account-financial-reporting/mis_template_financial_report \
  mis-builder/mis_builder \
  reporting-engine/report_xlsx \
  server-ux/date_range
do
  rm -rf "addons/$(basename "$m")"
  cp -r "oca/$m" addons/
done

echo "Fertig: $(ls addons | wc -l) Module in addons/. Jetzt: docker compose up -d --build"
