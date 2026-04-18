# server.py  ──  Full MCP server + Claude tool manifest

import json
from dotenv import load_dotenv
from audit.audit_middleware import AuditMiddleware, wrap_tool_call
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

load_dotenv()

# Tool dispatcher — routes Claude's calls to real functions ──

TOOL_REGISTRY = {
    "get_transaction_details": get_transaction_details,
    "check_velocity": check_velocity,
    "flag_transaction": flag_transaction,
    "screen_against_ofac": screen_against_ofac,
    "check_pep_status": check_pep_status,
    "get_counterparty_risk_score": get_counterparty_risk_score,
}

audit = AuditMiddleware(db_conn=get_db_connection())


def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    """Execute the tool Claude selected and return result as JSON string."""
    if tool_name not in TOOL_REGISTRY:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    # In your dispatch function:
    result = wrap_tool_call(
        audit=audit,
        user_id=request.user_id,
        session_id=request.session_id,
        tool_name=tool_name,
        tool_fn=TOOL_REGISTRY[tool_name],
        tool_args=tool_input,
    )

    fn = TOOL_REGISTRY[tool_name]
    result = fn(**tool_input)
    return json.dumps(result)
