import os
import asyncio
from mcp.server.fastmcp import FastMCP
from tools.transaction_tools import (
    get_transaction_details,
    check_velocity,
    flag_transaction,
)
from tools.counterparty_tools import (
    screen_against_ofac,
    check_pep_status,
    get_counterparty_risk_score,
)
from audit.logger import log_tool_call

# ── Init ───────────────────────────────────────────────────────
app = FastMCP("compliance-mcp-agent")

# ── Transaction Tools ──────────────────────────────────────────

@app.tool()
async def tool_get_transaction_details(txn_id: str) -> dict:
    """Retrieve full details of a transaction by its ID."""
    log_tool_call("get_transaction_details", {"txn_id": txn_id})
    return await get_transaction_details(txn_id)

@app.tool()
async def tool_check_velocity(account_id: str, window_minutes: int = 10) -> dict:
    """Check how many transactions an account made in the last N minutes."""
    log_tool_call("check_velocity", {"account_id": account_id, "window_minutes": window_minutes})
    return await check_velocity(account_id, window_minutes)

@app.tool()
async def tool_flag_transaction(txn_id: str, reason: str) -> dict:
    """Flag a transaction for review or blocking with a stated reason."""
    log_tool_call("flag_transaction", {"txn_id": txn_id, "reason": reason})
    return await flag_transaction(txn_id, reason)

# ── Counterparty Tools ─────────────────────────────────────────

@app.tool()
async def tool_screen_against_ofac(name: str, country: str = "") -> dict:
    """Screen a counterparty name against the OFAC SDN watchlist."""
    log_tool_call("screen_against_ofac", {"name": name, "country": country})
    return await screen_against_ofac(name, country)

@app.tool()
async def tool_check_pep_status(name: str, dob: str = "") -> dict:
    """Check if a counterparty is a Politically Exposed Person (PEP)."""
    log_tool_call("check_pep_status", {"name": name, "dob": dob})
    return await check_pep_status(name, dob)

@app.tool()
async def tool_get_counterparty_risk_score(counterparty_id: str) -> dict:
    """Return a composite risk score for a counterparty based on all checks."""
    log_tool_call("get_counterparty_risk_score", {"counterparty_id": counterparty_id})
    return await get_counterparty_risk_score(counterparty_id)

# ── Entrypoint ─────────────────────────────────────────────────

if __name__ == "__main__":
    app.run()
