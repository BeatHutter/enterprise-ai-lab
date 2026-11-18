# Decisions

The key architecture and governance decisions of the lab, newest first. Each was taken before building the part it concerns and recorded with its reasoning. The full decision log is kept in the private working repository.

## D10 · Publishing by allowlist, not blocklist (13 Nov 2026)

**Decision.** Only files listed in a packing list leave the private working repository. A script copies them, neutralises paths and host names, and stops on secrets (gitleaks), forbidden words or oversized files. Nothing is ever edited directly in the public repository.

**Why.** New files stay private by default. A blocklist fails silently the first time someone forgets to add a file to it.

## D9 · Observability with Langfuse, not a generic tracing stack (13 Nov 2026)

**Decision.** Every agent session is traced in Langfuse (cloud, EU) through the official Hermes plugin. A daily job without a model reports cost outliers.

**Why.** Generic tools such as Grafana or Jaeger know nothing about prompts, tokens, model prices or evals. Langfuse is open source and can be self-hosted later, so there is no lock-in.

## D8 · Workflows outside the ERP, the ERP only for records (11 Nov 2026)

**Decision.** Routing, triage and reminders run in the agent and its scheduled jobs. Workflow features of Odoo (mail aliases that create leads, automated actions) are not used.

**Why.** Customers use other ERPs, such as bexio. Workflows built inside one ERP must be rebuilt for the next customer. Records exist in every ERP.

**Trade-off.** Some convenience of Odoo is left unused.

## D7 · Inbox run by the agent, mailbox read-only via OAuth (11 Nov 2026)

**Decision.** The agent checks the mailbox every five minutes with a scheduled job. A script without a model runs first and wakes the agent only when there is new mail. Gmail access uses OAuth with the `gmail.readonly` scope. No workflow tool (n8n) for now.

**Why.** The same pattern as for the ERP: read-only access, writing only through narrow tools. An app password cannot be limited to reading, OAuth can. The pre-check keeps cost at zero when nothing arrives.

**Trade-off.** Mail in the spam folder is not seen. Gmail's filter also caught a phishing test mail, so this cuts both ways.

## D6 · Warnings instead of hard limits on drafts (10 Nov 2026)

**Decision.** A supplier invoice draft above CHF 50,000 or above three times the supplier's largest invoice so far is created with a warning, not rejected. Only a human can override a check. The tool has no parameter to switch checks off.

**Why.** A hard limit pushed large invoices back into manual work although a draft commits nothing. Comparing with the supplier's history catches decimal errors that a fixed threshold misses. Limits belong to posting and paying.

## D5 · Self-improvement off while building and measuring (9 Nov 2026)

**Decision.** The harness's automatic skill and memory updates are switched off. Skill changes go through review and versioning.

**Why.** After conversations, the harness created and changed skills on its own, even against an explicit instruction, and the agent used them immediately. Measurements would track a moving target. Self-improvement will be tested later as a separate experiment.

## D4 · Read directly, write only through the MCP server (9 Nov 2026)

**Decision.** The agent keeps its own read-only Odoo user and reads directly. The MCP server contains only tools that write.

**Why.** A generic read tool on the server would have exactly the same rights as the read-only user, so routing reads through it adds effort without adding safety. OWASP LLM06 asks for minimal rights in the target system and approval for consequential actions. Both are met.

**Trade-off.** A read key sits in the agent's environment and is rotated every two months.

## D3 · One agent with skills, permissions in the tools (6 Nov 2026)

**Decision.** Manni is the only agent. Domain knowledge comes from skills. Write permissions live in a dedicated MCP server with one key per caller, narrow tools, checks and approval by button. This replaced an earlier plan of one specialist agent per department as a security boundary.

**Why.** All agent profiles run under the same Linux user, and an agent with a terminal can read every profile's configuration. Separate profiles would separate rights only on paper. Details: [architecture.md](architecture.md).

**Trade-off.** The agent keeps its terminal. The residual risk and the trigger to revisit it are documented.

## D2 · Fixed KPI definitions, no calculating by the model (3 Nov 2026)

**Decision.** Every KPI has one definition in a catalogue and one calculation path in code, reconciled against Odoo's own reports. The agent calls the library and only interprets.

**Why.** Different queries for the same KPI returned different figures. A fixed path always returns the same number. The agent can neither change the catalogue nor the code.

## D1 · Isolated agent, test data with known answers (1 to 2 Nov 2026)

**Decision.** The agent runs as its own Linux service user without access to the operator's files, the Windows drive, Docker or the local network. It cannot update itself or install software. The test data come from a generator with five built-in anomalies. Agents under test cannot read the repository, because it contains the answers.

**Why.** Results only count if the agent cannot see the solution and cannot change its own setup. Every change to the agent is made deliberately by a human.
