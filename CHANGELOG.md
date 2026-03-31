# Changelog

All notable changes to **Compliance MCP Agent** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Nothing yet — be the first to contribute!

### Changed
- Nothing yet

### Fixed
- Nothing yet

---

## [1.0.0] — 2025-03-31

### Added
- `get_transaction_details` MCP tool — fetches full transaction record by ID
- `check_velocity` MCP tool — count + volume in configurable time window
- `flag_transaction` MCP tool — write immutable compliance flag + audit entry
- `screen_against_ofac` MCP tool — fuzzy SDN list screening (threshold: 85%)
- `check_pep_status` MCP tool — PEP Class 1–3 lookup with EDD flag
- `get_counterparty_risk_score` MCP tool — composite 0–100 risk score
- Claude agent loop (`agent.py`) — full `tool_use` → `end_turn` agentic cycle
- MCP server (`server.py`) — tool manifest registration + JSON-RPC dispatch
- Audit middleware — immutable append-only log, FINTRAC PCMLTFA compliant
- OAuth 2.0 scope enforcement per tool (`compliance:read` / `compliance:write`)
- FastAPI REST endpoint `POST /investigate`
- Webhook receiver `POST /webhook/transaction`
- PostgreSQL schema + Alembic migrations
- Seed script — 300 synthetic transactions, 50 counterparty profiles
- Docker Compose — postgres + mcp_server + agent_api
- 47-test end-to-end suite (`test_txn_0300.py`)
- Full unit test suites for transaction tools, counterparty tools, audit, auth
- GitHub Actions CI — lint + test on every PR
- GitHub Actions release — tag → PyPI + GitHub Release

### Architecture
- MCP Protocol: JSON-RPC 2.0 over HTTP
- Claude model: `claude-sonnet-4-5`
- Python: 3.11+
- Database: PostgreSQL 16
- Linting: Ruff
- Type checking: mypy (strict)

---

## [0.3.0-beta] — 2025-03-15

### Added
- `check_velocity` tool with configurable window
- Velocity breach threshold configuration via env vars
- Mock OFAC fixture data for local development

### Changed
- Refactored tool dispatch from if/elif chain to registry dict
- Improved audit log schema — added `tool_name`, `latency_ms` columns

### Fixed
- OFAC match score threshold was using `>=` instead of `>` — off-by-one
- Velocity window was exclusive of boundary timestamp — now inclusive

---

## [0.2.0-beta] — 2025-03-01

### Added
- `screen_against_ofac` tool with fuzzy matching via `rapidfuzz`
- `check_pep_status` tool — PEP Class 1 and 2 coverage
- Audit middleware first implementation
- `.env.example` with all supported variables

### Changed
- Tool schema format updated to match MCP 1.0 spec
- System prompt rewritten to enforce investigation order

### Fixed
- Agent loop did not handle `max_tokens` exceeded — now raises `AgentLimitError`
- Tool results were serialised with `str()` instead of `json.dumps()` — fixed

---

## [0.1.0-alpha] — 2025-02-15

### Added
- Initial project scaffold
- `get_transaction_details` tool (PostgreSQL-backed)
- `flag_transaction` tool (basic DB write)
- Claude agentic loop proof-of-concept
- Basic MCP server with two tools registered
- README and MIT licence
