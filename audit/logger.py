import json
import logging
from datetime import datetime, timezone
from pathlib import Path

Path("audit/logs").mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename="audit/logs/tool_calls.jsonl",
    level=logging.INFO,
    format="%(message)s",
)

def log_tool_call(tool_name: str, args: dict) -> None:
    """
    Write a structured audit record for every MCP tool invocation.
    Format: newline-delimited JSON (JSONL) — easy to ingest into SIEM/Splunk.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "args": args,
    }
    logging.info(json.dumps(record))
