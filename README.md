<div align="center">

# 🛡️ Compliance MCP Agent

### Real-Time Fraud Detection + AML Counterparty Screening powered by Claude + MCP

*Give your LLM agent the tools to investigate transactions and screen counterparties —
autonomously, auditably, and without rewriting your stack.*

<br/>

[![CI](https://github.com/your-org/compliance-mcp-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/compliance-mcp-agent/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/your-org/compliance-mcp-agent/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/compliance-mcp-agent)
[![pytest](https://img.shields.io/badge/tests-47%20passed-brightgreen?logo=pytest)](https://github.com/your-org/compliance-mcp-agent/actions)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/type--checked-mypy-blue)](http://mypy-lang.org/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Claude](https://img.shields.io/badge/Claude-claude--sonnet--4--5-blueviolet?logo=anthropic&logoColor=white)](https://www.anthropic.com/)
[![MCP](https://img.shields.io/badge/protocol-MCP%201.0-orange)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![FINTRAC](https://img.shields.io/badge/FINTRAC-PCMLTFA%20compliant-red)](https://www.fintrac-canafe.gc.ca/)
[![FATF](https://img.shields.io/badge/FATF-40%20Recommendations-red)](https://www.fatf-gafi.org/)
[![OFAC](https://img.shields.io/badge/OFAC-SDN%20screening-red)](https://ofac.treasury.gov/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)

<br/>

[**Quick Start**](#-quick-start) •
[**Architecture**](#-architecture) •
[**Tools Reference**](#-tools-reference) •
[**Demo**](#-demo) •
[**Production**](#-production-deployment) •
[**Contributing**](#-contributing) •
[**Roadmap**](#-roadmap)

</div>

---

## 🧭 What Is This?

**Compliance MCP Agent** is an open-source AI agent that autonomously investigates
financial transactions for fraud and AML risk — using Anthropic's
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) to connect
**Claude** to your compliance tooling in real time.

Instead of building brittle rule engines or expensive custom ML pipelines,
you expose your existing compliance tools through an MCP server.
Claude reasons across them — chaining velocity checks, sanctions screening,
PEP lookups, and risk scoring — and returns a structured, auditable decision
in under 200ms.

### The Two Blind Spots This Fixes

| Legacy Problem | What This Agent Does |
|---|---|
| Transactions checked in isolation | Chains behavioral + identity signals in one reasoning pass |
| Batch-mode counterparty screening (24h lag) | Real-time OFAC/PEP screening on every transaction |
| Opaque rule engine decisions | Full chain-of-thought audit trail per decision |
| Hard-coded workflows | Claude reasons dynamically — no decision tree to maintain |
| Rip-and-replace integrations | MCP wraps your existing APIs — zero stack changes |

---

## ⚡ Quick Start

> Get the agent running locally in under 5 minutes.
> All tools run against mock data by default — no live API keys required.

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| PostgreSQL | 14+ (or Docker) |
| Anthropic API Key | [Get one here](https://console.anthropic.com/) |

### 1 — Clone & Install

```bash
git clone https://github.com/your-org/compliance-mcp-agent.git
cd compliance-mcp-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
### 2 — Configure Environment

```bash

cp .env.example .env
```

```ini

# .env — minimum required for local mock mode
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional: real screening APIs (mock used if omitted)
SCREENING_API_KEY=your-complyadvantage-key
DATABASE_URL=postgresql://localhost:5432/compliance_db

# Optional: auth
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret
```

### 3 — Seed the Database
```bash

docker compose up -d postgres
python scripts/seed_db.py
# ✅ Seeded 300 transactions, 50 counterparty profiles
```

### 4 — Start the MCP Server
```bash


python server.py
# ✅ Compliance MCP server running on :8000
# ✅ 6 tools registered
```

### 5 — Run Your First Investigation
```bash

python agent.py --query "Review transaction TXN-0042 and tell me if we should block it."

```

```
════════════════════════════════════════════════════════
  🤖 COMPLIANCE AGENT — NEW INVESTIGATION
  Query: Review transaction TXN-0042 — should we block it?
════════════════════════════════════════════════════════

💭 Claude: I'll begin by fetching full details for TXN-0042...
📞 get_transaction_details(txn_id="TXN-0042")         ✓  91ms
📞 check_velocity(account_id="CUST-8821")             ✓  43ms
📞 screen_against_ofac(name="UNKNOWN_VENDOR_443")     ✓  67ms
📞 flag_transaction(txn_id="TXN-0042", reason="...")  ✓  12ms

════════════════════════════════════════════════════════
  🚨 DECISION: BLOCK — DUAL RISK FLAGS CONFIRMED
  Tools: 4  |  Tokens: 1,847  |  Latency: 138ms
  Audit ID: AUD-20250330-0042-CC1F
════════════════════════════════════════════════════════
```
---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         ENTRY POINTS                                 │
│   CLI: python agent.py --query "..."                                 │
│   API: POST /investigate  { "txn_id": "TXN-0042" }                   │
│   Webhook: POST /webhook/transaction  (real-time trigger)            │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      CLAUDE AGENT LOOP                               │
│                   (claude-sonnet-4-5 via SDK)                        │
│   ┌─────────────────────────────────────────────────────────────┐    │
│   │  System prompt: Compliance investigator persona             │    │
│   │  Tool manifest: 6 tools injected as JSON schema             │    │
│   │  Agentic loop:  tool_use → dispatch → tool_result → repeat  │    │
│   └─────────────────────────────────────────────────────────────┘    │
└───────────────────────────┬──────────────────────────────────────────┘
                            │  MCP Protocol (JSON-RPC 2.0)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP SERVER  :8000                           │
│   Tool registry  →  dispatch_tool()  →  audit_middleware()          │
│       ┌─────────────────────┐   ┌──────────────────────────────┐    │
│       │  🔴 TRANSACTION     │   │  🟡 COUNTERPARTY TOOLS       │    │
│       │  get_txn_details()  │   │  screen_against_ofac()       │    │
│       │  check_velocity()   │   │  check_pep_status()          │    │
│       │  flag_transaction() │   │  get_counterparty_risk()     │    │
│       └──────────┬──────────┘   └──────────────┬───────────────┘    │
└──────────────────┼───────────────────────────────┼──────────────────┘
                   │                               │
         ┌─────────┴──────────┐         ┌──────────┴────────────┐
         ▼                    ▼         ▼                        ▼
┌──────────────┐  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐
│ PostgreSQL   │  │  Audit Log DB  │  │  OFAC / SDN  │  │  PEP Database   │
│ Transactions │  │  (immutable)   │  │  US Treasury │  │  ComplyAdv /    │
└──────────────┘  └────────────────┘  └──────────────┘  └─────────────────┘
```

---

📁 Project Structure

```
compliance-mcp-agent/
├── 📄 server.py
├── 📄 agent.py
├── 📄 mcp_client.py
├── 📂 tools/
│   ├── 📄 transaction_tools.py
│   └── 📄 counterparty_tools.py
├── 📂 middleware/
│   ├── 📄 audit.py
│   └── 📄 auth.py
├── 📂 api/
│   ├── 📄 routes.py
│   └── 📄 webhooks.py
├── 📂 db/
│   ├── 📄 connection.py
│   ├── 📄 models.py
│   └── 📄 migrations/
├── 📂 tests/
│   ├── 📄 test_txn_0300.py
│   ├── 📄 test_transaction_tools.py
│   ├── 📄 test_counterparty_tools.py
│   └── 📄 conftest.py
├── 📂 scripts/
│   ├── 📄 seed_db.py
│   └── 📄 generate_report.py
├── 📄 docker-compose.yml
├── 📄 Dockerfile
├── 📄 requirements.txt
├── 📄 requirements-dev.txt
├── 📄 .env.example
├── 📄 pyproject.toml
├── 📄 CONTRIBUTING.md
├── 📄 CHANGELOG.md
└── 📄 LICENSE
```
---
## 🔧 Tools Reference

### 🔴 Transaction Tools

| Tool | Description | Key Parameters | Returns |
| --- | --- | --- | --- |
| get_transaction_details | Full transaction record by ID | txn_id: str | amount, currency, country, risk_score, fraud_flag |
| check_velocity | Txn count + volume in time window | account_id: str, window_minutes: int = 60 | txn_count, total_amount, velocity_breach |
| flag_transaction | Write compliance flag + audit entry | txn_id: str, reason: str | flagged: bool, audit: logged |

### 🟡 Counterparty Tools
| Tool | Description | Key Parameters | Returns |
| --- | --- | --- | --- |
| screen_against_ofac | Fuzzy OFAC SDN list screen | name: str, country: str | ofac_hit, match_score, matched_entity |
| check_pep_status | PEP Class 1–3 lookup | name: str, dob: str\|None | is_pep, pep_class, position, edd_required |
| get_counterparty_risk_score | Composite 0–100 risk score | counterparty_id: str | risk_score, risk_level |

### Risk Level Reference

```
CRITICAL  ≥ 80  →  Automatic BLOCK recommendation
HIGH      60–79  →  ESCALATE to compliance officer
MEDIUM    40–59  →  Enhanced monitoring + manual review
LOW        < 40  →  PASS with standard logging

```
---
## 🎬 Demo

### Scenario A — Velocity Breach Only

```bash
python agent.py --query "Check account CUST-1144 for unusual activity in the last 30 minutes."
# 🟡 DECISION: ESCALATE
```

### Scenario B — OFAC Hit Only

```bash
python agent.py --query "Screen counterparty 'Apex Global Trading' based in Iran before we process TXN-0891."
# 🚨 DECISION: BLOCK
```

### Scenario C — Clean Transaction

```bash
python agent.py --query "Review TXN-1203 — routine payroll transfer."
# ✅ DECISION: PASS

```
---
## 🧪 Testing

```bash
pytest tests/ -v
pytest tests/ --cov=. --cov-report=html
pytest tests/ -v -m "not integration"
```

| Suite | Tests | Coverage Area |
| --- | --- | --- |
| test_transaction_tools.py | 14 | Transaction logic, edge cases |
| test_counterparty_tools.py | 11 | OFAC fuzzy match, PEP scoring |
| test_txn_0300.py | 47 | Full E2E worst-case scenario |
| test_audit.py | 8 | Audit log immutability |
| test_auth.py | 6 | OAuth scope enforcement |

---
## 🚀 Production Deployment

### Docker Compose

```bash
docker compose up -d
# All three services healthy in ~15 seconds
Environment Variables
```

### Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| ANTHROPIC_API_KEY | ✅ Yes | Anthropic API key |
| DATABASE_URL | ✅ Yes | PostgreSQL connection string |
| SCREENING_API_KEY | ⚠️ Prod | ComplyAdvantage / Refinitiv key |
| OFAC_API_URL | ⚠️ Prod | US Treasury or proxy URL |
| OAUTH_CLIENT_ID | ⚠️ Prod | OAuth 2.0 client ID |
| OAUTH_CLIENT_SECRET | ⚠️ Prod | OAuth 2.0 client secret |
| VELOCITY_COUNT_THRESHOLD | No | Default: 5 |
| VELOCITY_AMOUNT_THRESHOLD | No | Default: 10000 |
| OFAC_MATCH_THRESHOLD | No | Default: 85 |

---

## 🗺️ Roadmap

| Milestone | Status | Description |
| --- | --- | --- |
| v1.0 — Core Agent | ✅ Done | Transaction tools + OFAC/PEP + Claude loop |
| v1.1 — REST API | 🔄 In Progress | FastAPI wrapper + webhook receiver |
| v1.2 — SAR Auto-Draft | 📋 Planned | Agent writes the STR automatically |
| v1.3 — Graph Detection | 📋 Planned | Ring + structuring detection |
| v2.0 — Multi-Jurisdiction | 📋 Planned | FINTRAC / FinCEN / FCA / MAS rule sets |
| v2.1 — Streaming | 📋 Planned | SSE real-time agent reasoning output |
| v2.2 — RAG Memory | 📋 Planned | Retrieval of historical cases |

---
## 🤝 Contributing

See CONTRIBUTING.md for the full guide.

