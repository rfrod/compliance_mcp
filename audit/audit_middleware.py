# audit_middleware.py
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from audit_middleware import AuditMiddleware, wrap_tool_call
import psycopg2
from psycopg2.extras import Json


class AuditMiddleware:
    """
    Immutable append-only audit logger.
    FINTRAC PCMLTFA s.6 compliant — 5-year retention enforced at DB level.
    """

    def __init__(self, db_conn):
        self.conn = db_conn

    def log(
        self,
        user_id: str,
        tool_name: str,
        tool_args: dict,
        tool_result: dict,
        session_id: str | None = None,
        latency_ms: int | None = None,
    ) -> str:
        """Write one immutable audit entry. Returns the audit_id."""

        audit_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO mcp_audit_log (
                    audit_id,
                    timestamp,
                    user_id,
                    tool_name,
                    tool_args,
                    tool_result,
                    latency_ms,
                    session_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    audit_id,
                    timestamp,
                    user_id,
                    tool_name,
                    Json(tool_args),
                    Json(tool_result),
                    latency_ms,
                    session_id,
                ),
            )
        self.conn.commit()
        return audit_id

    def log_jsonl(
        self,
        user_id: str,
        tool_name: str,
        tool_args: dict,
        tool_result: dict,
        session_id: str | None = None,
        latency_ms: int | None = None,
        jsonl_path: str = "audit.jsonl",
    ) -> str:
        """
        Write one immutable audit entry to both PostgreSQL AND a JSONL file.
        The JSONL file serves as a portable backup / local dev fallback.
        """

        audit_id = self.log(
            user_id=user_id,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            session_id=session_id,
            latency_ms=latency_ms,
        )

        entry = {
            "audit_id": audit_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tool_result": tool_result,
            "latency_ms": latency_ms,
            "session_id": session_id,
        }

        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        return audit_id


def wrap_tool_call(
    audit: AuditMiddleware,
    user_id: str,
    session_id: str,
    tool_name: str,
    tool_fn: Any,
    tool_args: dict,
    jsonl_path: str = "audit.jsonl",
) -> dict:
    """
    Decorator-style wrapper — times the tool call and writes the audit entry.
    Use this in server.py dispatch instead of calling tools directly.

    Usage:
        result = wrap_tool_call(
            audit, user_id, session_id,
            "get_transaction_details",
            get_transaction_details,
            {"txn_id": "TXN-0042"}
        )
    """

    start = time.perf_counter()
    try:
        result = tool_fn(**tool_args)
    except Exception as e:
        result = {"error": str(e)}
    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)

    audit.log_jsonl(
        user_id=user_id,
        tool_name=tool_name,
        tool_args=tool_args,
        tool_result=result,
        session_id=session_id,
        latency_ms=latency_ms,
        jsonl_path=jsonl_path,
    )

    return result
