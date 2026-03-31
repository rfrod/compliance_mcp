# Architecture Deep Dive

This document explains the internal design of Compliance MCP Agent —
how components connect, why they were designed this way, and how to
extend the system without breaking existing behaviour.

---

## Table of Contents

- [System Overview](#system-overview)
- [The MCP Protocol](#the-mcp-protocol)
- [Claude Agent Loop](#claude-agent-loop)
- [Tool Design Principles](#tool-design-principles)
- [Audit Trail Design](#audit-trail-design)
- [Authentication Model](#authentication-model)
- [Database Schema](#database-schema)
- [Extending the System](#extending-the-system)

---

## System Overview

```
User / Webhook │ ▼ FastAPI (:8080) ← REST API + webhook receiver │ ▼ agent.py ← Claude agentic loop │ POST /v1/messages ▼ Anthropic API ← claude-sonnet-4-5 │ tool_use blocks ▼ server.py (:8000) ← MCP server + tool dispatcher │ ├── transaction_tools.py ← PostgreSQL queries ├── counterparty_tools.py ← OFAC/PEP/risk APIs └── audit_middleware.py ← Immutable audit writes
```


---

## The MCP Protocol

MCP (Model Context Protocol) is an open standard by Anthropic for connecting
LLMs to external tools in a structured, auditable way.

In this implementation:

1. **Tool manifest** — a JSON schema array describing all 6 tools is sent
   to Claude on every API call via the `tools` parameter
2. **Tool selection** — Claude returns `stop_reason: "tool_use"` with one or
   more `tool_use` content blocks, each containing `name` and `input`
3. **Dispatch** — `dispatch_tool()` maps the tool name to its Python function
   and executes it with the provided arguments
4. **Result injection** — results are returned to Claude as `tool_result`
   content blocks in the next `user` turn
5. **Loop** — steps 2–4 repeat until Claude returns `stop_reason: "end_turn"`

### Why not LangChain / LlamaIndex?

- Zero abstraction overhead — direct SDK calls are transparent and debuggable
- Full control over the message array — no hidden prompt injection
- MCP is the emerging open standard — building on it directly means no
  migration cost when tooling matures
- Easier to audit — every tool call is explicit in the code

---

## Claude Agent Loop

```python
while True:
    response = client.messages.create(
        model    = "claude-sonnet-4-5",
        tools    = COMPLIANCE_TOOLS,   # ← tool manifest
        messages = messages,           # ← full conversation history
    )

    if response.stop_reason == "tool_use":
        # Execute tools, append results, continue loop
        ...

    elif response.stop_reason == "end_turn":
        # Return Claude's final structured answer
        return final_text
```

Key design decisions:

| Decision | Rationale |
| --- | --- |
| Single while True loop | Simplest structure; Claude self-terminates via end_turn |
| Append both sides to messages[] | Maintains full context across tool calls |
| All tool results in one user turn | Batch results = fewer API round-trips |
| Audit write inside dispatch | Every tool call is logged regardless of agent outcome |

---
## Tool Design Principles
Every MCP tool in this system follows these rules:

### 1. Single Responsibility
Each tool does exactly one thing. check_velocity counts transactions. It does not flag them. Flagging is flag_transaction's job.

### 2. Deterministic Outputs
Same input → same output shape, always. Claude's reasoning depends on being able to parse tool results reliably.

### 3. Always Return a Dict
Tools never raise exceptions into Claude's context. Errors are returned as {"error": "description"}. Claude handles errors gracefully in its reasoning.

### 4. Compliance-First Naming
Tool names and field names use compliance industry terminology (ofac_hit, pep_class, velocity_breach) so Claude's domain reasoning is grounded in correct language.

### 5. Schema Completeness
Every parameter has a description in the JSON schema. Claude reads these descriptions when deciding how to call the tool. Vague descriptions produce bad calls.

---
## Audit Trail Design
The audit log is the most compliance-critical component of the system.

### Schema

```sql
CREATE TABLE mcp_audit_log (
    id             BIGSERIAL PRIMARY KEY,
    audit_id       VARCHAR(40)  NOT NULL UNIQUE,   -- AUD-YYYYMMDD-txnid-hash
    timestamp      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    user_id        VARCHAR(100) NOT NULL,
    tool_name      VARCHAR(100) NOT NULL,
    tool_args      JSONB        NOT NULL,
    tool_result    JSONB        NOT NULL,
    latency_ms     INTEGER,
    session_id     VARCHAR(100)
);

-- Append-only enforcement
REVOKE UPDATE ON mcp_audit_log FROM compliance_user;
REVOKE DELETE ON mcp_audit_log FROM compliance_user;
```

