# Agent setup

Configuration templates for the agent "Manni" on [Hermes Agent](https://hermes-agent.nousresearch.com/), an open-source agent harness. Hermes runs as a service under its own Linux user. These files are the reviewed source; changes reach the agent only after approval.

## Files

| Path | Content |
| --- | --- |
| `SOUL-hauptagent.md` | Persona and fixed rules: figures only from the KPI library, ask instead of guess, no effect outside the lab, no updates or installs, no workarounds for blocks, report everything created unasked |
| `config-zusatz.yaml` | Additions to the Hermes configuration: hard blocks for self-updates and installs, every software installation escalated to a human |
| `mcp-werkzeug-server.yaml` | Connection to the [tool server](../werkzeug-server/): allowed tools listed explicitly, approval by elicitation, sampling off |
| `skills/` | Versioned skills, each a `SKILL.md` with procedure and rules, some with scripts |
| `scripts/` | Pre-checks and daily jobs that run without a model |

## Skills

| Skill | Use case |
| --- | --- |
| `monatsbericht` | Monthly report for management: KPIs from the KPI library, drivers traced down to documents, special effects shown |
| `lieferantenrechnung-erfassen` | Read a supplier invoice (PDF), determine supplier and accounts, create a draft via the tool server |
| `offerte-erstellen` | Read a customer request, find customer and items, create a draft quote via the tool server |
| `gmail-lesen` | Read the mailbox, read-only (OAuth scope `gmail.readonly`) |
| `mail-einordnen` | Classify every new email (category, confidence, sensitive yes or no) and log it |
| `posteingang-bearbeiten` | Act on logged emails: quote requests from known senders become draft quotes, everything else a summary with a proposal |

The KPI skill `kennzahlen-abrufen` lives with the [KPI library](../kennzahlen/). A general read-only ERP skill was written by the agent itself and is not part of this extract.

## Scheduled jobs

| Script | Runs | Purpose |
| --- | --- | --- |
| `posteingang_vorpruefung.py` | every 5 min | Checks for new mail without a model. Wakes the agent only if there is any |
| `posteingang_offen_pruefen.py` | every 5 min | Hands open log entries to the agent. Decides by script, not by model, whether the sender is known and the agent may act |
| `kosten_pruefen.py` | daily | Reports days or single runs above the cost limit |
| `gmail_token_pruefen.py` | daily | Reports when mailbox access has expired or was revoked |

The pre-checks keep model cost at zero when there is nothing to do. The daily jobs stay silent unless something needs attention.
