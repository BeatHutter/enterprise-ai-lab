# Test sets

Every use case is tested against expected values fixed before the run. Each set contains traps the agent must not fall for. The expected values (`sollwerte.json`) are never given to the agent, and the agent cannot read this repository.

| Folder or file | Use case | Content |
| --- | --- | --- |
| `prueffaelle.md`, `pruefskript.py` | Monthly report | Five anomalies P1 to P5 built into two years of data, with target values. The script recalculates them from Odoo |
| `belege-uc001/` | Supplier invoice as draft | 10 PDF invoices in CHF and EUR, including a calculation error, a duplicate and a deception attempt |
| `anfragen-uc005/` | Quote as draft | 10 customer requests, including a discount demand, an unknown customer and a hidden instruction to the AI |
| `posteingang/` | Inbox | 12 mixed emails: order, complaint, dunning letter, application, advertising, spam, plus three traps (forged bank details, login link, hidden instruction) |

Results per run: [docs/erkenntnisse.md](../docs/erkenntnisse.md) (German).

Two kinds of checks are used. Unambiguous results, such as figures and records in the ERP, are compared exactly. Results that need judgement, such as a classification or a comment, are assessed against criteria. Next step: running these sets automatically on every change of a skill or model.
