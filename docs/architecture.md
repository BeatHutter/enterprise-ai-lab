# Architecture: one agent, permissions in the tools

How the agent accesses business systems and how its permissions are limited. Decisions behind it: [decisions.md](decisions.md).

## In one sentence

One agent reads the ERP directly with a read-only user. Anything that writes goes through narrow tools on a dedicated MCP server, which holds the write credentials, checks every call and asks a human before anything with consequences.

## Overview

```
Human (Telegram chat)
   │  tasks · approval by button for anything consequential
   ▼
Agent "Manni" (Hermes harness, own Linux service user)
   │  domain knowledge from versioned skills
   │
   ├── read: directly, read-only ERP user, KPI library
   │
   └── write: MCP calls with the agent's own key
        ▼
     MCP tool server (Docker, localhost only)
        │  Is this key allowed to use this tool? Do the checks pass?
        │  holds the ERP write credentials, out of the agent's reach
        ▼
     Odoo ERP
        server user has only the rights its tools need
```

## Principles

1. **One agent, knowledge from skills.** A skill adds know-how and a procedure, never additional rights. A second agent is only justified by workload, not by security (see below).
2. **Reading is direct and broad.** Free exploration is what lets the agent find anomalies no fixed report covers. It is limited by the ERP user, which can only read.
3. **Writing only through narrow tools.** Each tool does one thing, for example "create supplier invoice draft". Tools for paying, deleting or sending do not exist, so nothing can trigger them.
4. **Content is not a command.** Text in an email or document is material to work on. Instructions inside it are reported, not followed.

## Four locks

| Lock | Question | Example |
| --- | --- | --- |
| 1 Narrow tool | What can the agent do at all? | `offerte_entwurf_anlegen` creates a draft quote. There is no generic "write to the ERP" |
| 2 Checks in the server | Is the content plausible? | Customer exists, items are saleable, totals add up, no duplicate, only expense accounts |
| 3 Human approval | Who presses the last button? | Drafts need none. Posting and sending require approval by button |
| 4 Permissions in the system | What if everything else fails? | The server's ERP user has no admin or manager groups. Odoo cannot separate "draft" from "post" by group, so that split is enforced by the tool |

The agent cannot switch off a check: no tool has a parameter for it. Unusual but valid cases, such as a very large invoice, are created with a warning for the human instead of being blocked.

## Write levels

| Level | Meaning | Examples | Approval |
| --- | --- | --- | --- |
| 1 | harmless, reversible | note, draft | none, a human continues in the ERP |
| 2 | binding internally | post a document, change a contact | button |
| 3 | external effect or money | send, confirm, pay, change bank details | button, or the tool does not exist |

Today only level 1 tools exist. The approval button for levels 2 and 3 is built and tested.

## Approval by button, not by text

The MCP server asks for approval through MCP elicitation. The chat shows a button with the actual parameters of the call, not the agent's summary. The agent cannot press it, and one tap approves exactly one call. A typed "OK, send it" does not count: an incoming email could contain the same sentence.

## Why no specialist agents as a security boundary

All agent profiles of the harness run under the same Linux user. An agent with a terminal can read every profile's configuration, so separate profiles separate rights only on paper. Real separation would need one Linux user and one installation per agent, which is costly to run and not what an SME needs. The common practice is the same as here: permissions live at the tool, not at the agent. This matches OWASP LLM06 "Excessive Agency": minimal rights, enforced by the target system, human approval for consequential actions.

A specialist agent makes sense when an area needs long chains of steps with its own judgement, overloads the main agent's context, or needs its own model or budget.

## Residual risk, stated openly

- The agent keeps its terminal. It could read its own read-only ERP key and its key for the tool server. With both it can only read or create drafts.
- The design protects against mistakes and deception, for example a manipulated email. It does not protect against an agent that deliberately hunts for credentials. With fictitious data and drafts only, that is acceptable.
- **Trigger to revisit:** as soon as an agent gets a right whose misuse causes real damage without approval, or exposes confidential data such as salaries, it loses the terminal or the terminal runs in a sandbox.
- Known gap before level 2: with terminal and key, a tool call could bypass the approval button. This is closed before the first level 2 tool goes live.

## Transfer to an SME

- **Employees** use their own assistant on the desktop and sign in to the same tool server with their own account and rights.
- **Background agents** like Manni have their own key on the tool server and their own read-only user in the target system.
- Both use the same tools, checks and approvals. Only the source of identity differs.

## Sources

- OWASP, LLM06:2025 Excessive Agency: https://owasp.org/www-project-top-10-for-large-language-model-applications/2_0_vulns/LLM06_ExcessiveAgency.html
- Model Context Protocol, Elicitation: https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation
- Hermes Agent, MCP: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp
- OpenAI Agents SDK, Human in the loop: https://openai.github.io/openai-agents-python/human_in_the_loop
- Claude Agent SDK, Approvals: https://code.claude.com/docs/en/agent-sdk/approvals
