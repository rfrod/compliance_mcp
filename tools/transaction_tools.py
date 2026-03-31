import os
from datetime import datetime, timedelta
from db.seed_db import get_db_session
from sqlalchemy import text

VELOCITY_LIMIT = int(os.getenv("VELOCITY_LIMIT", 5))
HIGH_AMOUNT_THRESHOLD = float(os.getenv("HIGH_AMOUNT_THRESHOLD", 10000))


async def get_transaction_details(txn_id: str) -> dict:
    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT * FROM transactions WHERE txn_id = :txn_id"),
            {"txn_id": txn_id},
        )
        row = result.mappings().first()
        if not row:
            return {"error": f"Transaction {txn_id} not found"}

        txn = dict(row)
        txn["risk_flags"] = []

        if txn.get("amount", 0) >= HIGH_AMOUNT_THRESHOLD:
            txn["risk_flags"].append("HIGH_AMOUNT")

        if txn.get("originating_country") != txn.get("destination_country"):
            txn["risk_flags"].append("CROSS_BORDER")

        return txn


async def check_velocity(account_id: str, window_minutes: int = 10) -> dict:
    since = datetime.utcnow() - timedelta(minutes=window_minutes)
    async with get_db_session() as session:
        result = await session.execute(
            text("""
                SELECT COUNT(*) as txn_count, SUM(amount) as total_amount
                FROM transactions
                WHERE account_id = :account_id AND created_at >= :since
            """),
            {"account_id": account_id, "since": since.isoformat()},
        )
        row = result.mappings().first()
        txn_count = row["txn_count"] or 0
        total_amount = row["total_amount"] or 0.0

        return {
            "account_id": account_id,
            "window_minutes": window_minutes,
            "txn_count": txn_count,
            "total_amount": total_amount,
            "velocity_breach": txn_count > VELOCITY_LIMIT,
            "risk_flag": "VELOCITY_EXCEEDED" if txn_count > VELOCITY_LIMIT else None,
        }


async def flag_transaction(txn_id: str, reason: str) -> dict:
    async with get_db_session() as session:
        await session.execute(
            text("""
                UPDATE transactions
                SET status = 'FLAGGED', flag_reason = :reason, flagged_at = :now
                WHERE txn_id = :txn_id
            """),
            {"txn_id": txn_id, "reason": reason, "now": datetime.utcnow().isoformat()},
        )
        await session.commit()
    return {"txn_id": txn_id, "status": "FLAGGED", "reason": reason}
