# 🤝 Contributing to Compliance MCP Agent

Thank you for investing your time in contributing to this project.
Every contribution — bug reports, new tools, docs fixes, and test cases —
directly helps compliance engineers ship more reliable, auditable AI agents.

---

## Table of Contents

- [Before You Start](#before-you-start)
- [Development Setup](#development-setup)
- [Branch Naming](#branch-naming-convention)
- [Commit Messages](#commit-message-format)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Good First Issues](#good-first-issues)
- [Adding a New Tool](#adding-a-new-tool)
- [Code Style](#code-style)
- [Code of Conduct](#code-of-conduct)

---

## Before You Start

1. Read the [README](README.md) fully
2. Search [open issues](https://github.com/your-org/compliance-mcp-agent/issues)
   — your idea may already be tracked
3. For large changes, **open a discussion issue first** before writing code
4. For security vulnerabilities, email `security@your-org.com` — do not open a public issue

---

## Development Setup

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/compliance-mcp-agent.git
cd compliance-mcp-agent

# 2. Create a feature branch
git checkout -b feat/your-feature-name

# 3. Set up virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 4. Install dev dependencies
pip install -r requirements-dev.txt

# 5. Install pre-commit hooks
pre-commit install
# Hooks: ruff (lint), ruff (format), mypy (types), pytest (smoke)

# 6. Copy and configure environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY for integration tests

# 7. Start dependencies
docker compose up -d postgres
python scripts/seed_db.py

# 8. Verify everything works
pytest tests/ -v
# Expected: 47 passed
```
---

## Branch Naming Convention

| Type | Pattern | Example |
| --- | --- | --- |
| Feature | feat/short-description | feat/sar-auto-draft |
| Bug fix | fix/short-description | fix/ofac-timeout-handling |
| Documentation | docs/short-description | docs/pep-tool-examples |
| Tests | test/short-description | test/velocity-edge-cases |
| Refactor | refactor/short-description | refactor/audit-middleware |
| Chore | chore/short-description | chore/update-dependencies |

---

## Commit Message Format

We follow Conventional Commits:
```
<type>(<scope>): <short summary in present tense>

[optional body — explain the WHY, not the what]

[optional footer — Closes #issue, BREAKING CHANGE: description]

```

Allowed types: feat · fix · docs · test · refactor · chore · perf

Allowed scopes: tools · agent · server · api · db · audit · auth · ci · docs

### Examples

```bash
# Feature
git commit -m "feat(tools): add adverse_media_check tool with Factiva integration"

# Bug fix
git commit -m "fix(ofac): handle timeout gracefully when Treasury API unavailable"

# With body
git commit -m "feat(agent): add streaming support via SSE

Previously the agent returned the full response only on end_turn.
This commit adds server-sent events so reasoning steps are streamed
to the client in real time, reducing perceived latency by ~60%.

Closes #47"

# Breaking change
git commit -m "feat(tools): rename get_txn_details to get_transaction_details

BREAKING CHANGE: tool name changed. Update all callers to use the new name.
The old name will be removed in v2.0."
```
---

## Pull Request Guidelines

###Before Opening a PR
Run this checklist locally:

```bash
# Lint
ruff check .

# Format check
ruff format --check .

# Type check
mypy .

# Full test suite
pytest tests/ -v

# Coverage (must be ≥ 90% for new code)
pytest tests/ --cov=. --cov-report=term-missing

```

### PR Requirements

```
☐ All tests pass (pytest tests/ -v)
☐ Zero lint errors (ruff check .)
☐ Zero type errors (mypy .)
☐ New code has test coverage ≥ 90%
☐ New MCP tools are registered in server.py
☐ New tools have full docstrings + input_schema
☐ CHANGELOG.md updated under [Unreleased]
☐ PR description explains what changed AND why
☐ Screenshots / terminal output included for UX changes

```

### PR Description Template
When you open a PR, the template will auto-populate. Fill it out fully — reviewers should not need to ask "what does this do?" after reading your description.

## Good First Issues
New to the codebase? These are well-scoped and fully documented:

| Issue | Difficulty | Skills Needed |
| --- | --- | --- |
| Add get_adverse_media(name) tool | 🟢 Easy | Python, REST API |
| Write tests for check_pep_status edge cases | 🟢 Easy | pytest, fixtures |
| Add Redis caching layer to OFAC calls | 🟡 Medium | Redis, async Python |
| Build draft_sar_report(txn_id) tool | 🟡 Medium | Python, compliance domain |
| Implement detect_transaction_ring() | 🔴 Hard | Graph algorithms, NetworkX |
| Multi-jurisdiction rule config system | 🔴 Hard | Architecture, Python |

Browse tagged issues: good first issue · help wanted

## Adding a New Tool
Follow these four steps to add a tool that Claude can call:

### Step 1 — Implement the function

```python

# tools/counterparty_tools.py

def get_adverse_media(name: str, days_lookback: int = 90) -> dict:
    """
    Search adverse media for a counterparty name.

    Args:
        name:          Full legal name of the individual or entity.
        days_lookback: How many days back to search. Default: 90.

    Returns:
        {
            "name": str,
            "adverse_media_hit": bool,
            "article_count": int,
            "severity": "NONE" | "LOW" | "MEDIUM" | "HIGH",
            "sources": list[str]
        }
    """
    # Your implementation here
    ...

```

### Step 2 — Register the JSON schema in server.py

```python
# server.py — add to COMPLIANCE_TOOLS list

{
    "name": "get_adverse_media",
    "description": (
        "Search news and adverse media sources for negative coverage "
        "of a counterparty. Returns hit flag, article count, severity, "
        "and source list. Lookback window is configurable."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Full legal name of the individual or entity"
            },
            "days_lookback": {
                "type": "integer",
                "description": "Days to look back. Default: 90",
                "default": 90
            }
        },
        "required": ["name"]
    }
}
```

### Step 3 — Add to the dispatch registry

```python
# server.py — add to TOOL_REGISTRY dict

TOOL_REGISTRY = {
    ...
    "get_adverse_media": get_adverse_media,   # ← add this line
}
```

### Step 4 — Write tests

```python
# tests/test_counterparty_tools.py

def test_adverse_media_hit_returns_correct_shape():
    result = get_adverse_media("Corrupt Entity Ltd")
    assert "adverse_media_hit" in result
    assert "severity" in result
    assert result["severity"] in ["NONE", "LOW", "MEDIUM", "HIGH"]

def test_adverse_media_clean_entity_returns_no_hit():
    result = get_adverse_media("Legitimate Corp Inc")
    assert result["adverse_media_hit"] is False
    assert result["severity"] == "NONE"

```

Code Style
We use Ruff for both linting and formatting. Config lives in pyproject.toml:

```toml


[tool.ruff]
line-length    = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "ANN", "S", "B"]
ignore = ["ANN101", "ANN102"]

[tool.mypy]
python_version         = "3.11"
strict                 = true
ignore_missing_imports = true
```
## Key rules:

- Line length: 100 characters
- Type hints: required on all public functions
- Docstrings: required on all MCP tool functions
- No print() in library code — use logging
- No hardcoded secrets — use environment variables

---
## Code of Conduct
This project follows the Contributor Covenant Code of Conduct v2.1.

By participating, you agree to:

- Use welcoming and inclusive language
- Respect differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community
Report unacceptable behaviour to conduct@your-org.com. All reports will be reviewed and investigated promptly and confidentially.
