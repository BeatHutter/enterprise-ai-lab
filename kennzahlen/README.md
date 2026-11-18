# KPI library (semantic layer)

One fixed definition and one calculation path per KPI, so the agent always gets the same number for the same question. The agent calls the library and interprets the result; it never adds up figures itself.

## Three parts, kept apart

| Part | Content | Who may change it |
| --- | --- | --- |
| `katalog.md` | Meaning and rule of every KPI: accounts, period, sign, rounding. Terms follow the Swiss Code of Obligations and the Swiss SME chart of accounts | the business owner, with a version bump per change |
| `kennzahlen/` | One Python module per KPI, read-only access to Odoo | developer, after reconciliation |
| Skill `kennzahlen-abrufen` | How the agent calls the library and quotes the source | reviewed like every skill |

KPIs include net revenue (total and by segment), material cost and ratio, gross profit and margin, personnel cost, EBITDA, EBIT, receivables ageing and days sales outstanding, plus building blocks such as exchange differences and depreciation.

## Usage

```
python3 kennzahl.py liste
python3 kennzahl.py materialquote --von 2026-01-01 --bis 2026-10-31 --aufteilung monat --vergleich vorjahr
python3 kennzahl.py debitoren_altersstruktur --stichtag 2026-10-31 --nach kunde
```

Access to Odoo comes from the environment (`ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY`). Output is JSON by default.

## Checks

- `pruefung/abgleich.py` reconciles every KPI against reports Odoo calculates itself (OCA MIS Builder profit and loss and balance sheet, invoice analysis).
- `einspielen.sh` deploys only the committed state to a directory the agent can read and execute but not change. `rechte-pruefen.sh` verifies this as the agent's user.

Result in the monthly report test: about 250 figures, all correct.
