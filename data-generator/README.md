# Data generator

Builds the business history of Muster AG in Odoo through its API: customers, suppliers, items, quotes, invoices, payments and monthly postings from January 2025 to October 2026. The story behind it is in the [scenario](../docs/drehbuch-muster-ag.md).

Five anomalies are built in on purpose, such as a supplier price increase, a customer who pays later and later, and an invoice paid twice. They are the test cases P1 to P5 in [tests/prueffaelle.md](../tests/prueffaelle.md). Nothing in Odoo hints at them; the agent has to find them on its own.

## Properties

- Python standard library only, Odoo via XML-RPC with an API key
- Reproducible: a fixed random seed produces the same data on every run
- Dry run by default; writes only with `--schreiben` and skips what already exists
- Master data in `daten/` as CSV. The column `notiz` is for humans only and never reaches Odoo

## Steps

| Step | Command | Writes to Odoo |
| --- | --- | --- |
| Connection test | `python3 etappe1_verbindung.py` | no |
| Master data | `python3 etappe2_stammdaten.py [--schreiben]` | with `--schreiben` |
| Transactions | `python3 etappe3_4_bewegungen.py --bis 2026-10-31 [--schreiben]` | with `--schreiben` |
| Control | `python3 etappe3_4_bewegungen.py --bis 2026-10-31 --kontrolle` | no |

`anfragen_uc005.py` and `belege_uc001.py` generate the test sets for quotes and supplier invoices with their expected values. `tests/pruefskript.py` recalculates P1 to P5 from Odoo data only, without using anything from the generator.
