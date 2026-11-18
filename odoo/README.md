# Odoo 18

The ERP of Muster AG: Odoo 18 Community with Swiss localisation (chart of accounts, VAT, CHF) and OCA reporting modules, because Odoo Community has no balance sheet or profit and loss report of its own.

| File | Content |
| --- | --- |
| `docker-compose.yml` | Odoo 18 and PostgreSQL 16 |
| `Dockerfile` | Odoo 18 plus the Python library MIS Builder needs |
| `fetch-oca.sh` | Fetches the OCA modules for 18.0: Account Financial Reports, MIS Builder with templates for profit and loss and balance sheet, plus dependencies |

Setup: `bash fetch-oca.sh`, then `docker compose up -d --build`. Installed apps: Invoicing, Sales, Purchase, Contacts. No demo data; the business data come from the [data generator](../data-generator/).
