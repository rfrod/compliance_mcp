import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import (
    Column, String, Float, DateTime, Text, ForeignKey, text
)

# ── Database Setup ─────────────────────────────────────────────────────────────

DB_PATH = Path("db/compliance.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@asynccontextmanager
async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session


# ── Schema ─────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


CREATE_ACCOUNTS = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id          TEXT PRIMARY KEY,
    owner_name          TEXT NOT NULL,
    email               TEXT,
    country             TEXT NOT NULL,
    account_type        TEXT DEFAULT 'PERSONAL',   -- PERSONAL | BUSINESS
    status              TEXT DEFAULT 'ACTIVE',      -- ACTIVE | SUSPENDED | CLOSED
    kyc_verified        INTEGER DEFAULT 0,          -- 0 = No, 1 = Yes
    created_at          TEXT NOT NULL
);
"""

CREATE_COUNTERPARTIES = """
CREATE TABLE IF NOT EXISTS counterparties (
    counterparty_id     TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    country             TEXT NOT NULL,
    dob                 TEXT,                       -- for PEP matching
    entity_type         TEXT DEFAULT 'INDIVIDUAL',  -- INDIVIDUAL | COMPANY
    bank_swift          TEXT,
    created_at          TEXT NOT NULL
);
"""

CREATE_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS transactions (
    txn_id                  TEXT PRIMARY KEY,
    account_id              TEXT NOT NULL REFERENCES accounts(account_id),
    counterparty_id         TEXT NOT NULL REFERENCES counterparties(counterparty_id),
    amount                  REAL NOT NULL,
    currency                TEXT DEFAULT 'USD',
    originating_country     TEXT NOT NULL,
    destination_country     TEXT NOT NULL,
    payment_method          TEXT DEFAULT 'WIRE',    -- WIRE | ACH | CRYPTO | CARD
    status                  TEXT DEFAULT 'PENDING', -- PENDING | CLEARED | FLAGGED | BLOCKED
    flag_reason             TEXT,
    flagged_at              TEXT,
    created_at              TEXT NOT NULL
);
"""

CREATE_AUDIT_LOG = """
CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    tool            TEXT NOT NULL,
    args            TEXT NOT NULL,      -- JSON string
    result_summary  TEXT               -- optional short summary
);
"""


# ── Seed Data ──────────────────────────────────────────────────────────────────

def ts(minutes_ago: int = 0) -> str:
    """Return a UTC ISO timestamp N minutes in the past."""
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


ACCOUNTS = [
    {
        "account_id":   "ACC-1001",
        "owner_name":   "Rafael Torres",
        "email":        "rafael.torres@example.com",
        "country":      "CA",
        "account_type": "PERSONAL",
        "status":       "ACTIVE",
        "kyc_verified": 1,
        "created_at":   ts(43200),   # ~30 days ago
    },
    {
        "account_id":   "ACC-1002",
        "owner_name":   "Northgate Holdings Ltd.",
        "email":        "ops@northgate-holdings.com",
        "country":      "CA",
        "account_type": "BUSINESS",
        "status":       "ACTIVE",
        "kyc_verified": 1,
        "created_at":   ts(86400),
    },
    {
        "account_id":   "ACC-1003",
        "owner_name":   "Elena Vasquez",
        "email":        "evasquez@mail.com",
        "country":      "MX",
        "account_type": "PERSONAL",
        "status":       "ACTIVE",
        "kyc_verified": 0,           # ⚠️ Not KYC-verified
        "created_at":   ts(1440),
    },
    {
        "account_id":   "ACC-1004",
        "owner_name":   "Phantom Exports Inc.",
        "email":        "contact@phantom-exports.io",
        "country":      "RU",
        "account_type": "BUSINESS",
        "status":       "SUSPENDED",  # ⚠️ Suspended account
        "kyc_verified": 0,
        "created_at":   ts(2880),
    },
]

COUNTERPARTIES = [
    {
        "counterparty_id": "CP-001",
        "name":            "Green Valley Supplies",
        "country":         "US",
        "dob":             None,
        "entity_type":     "COMPANY",
        "bank_swift":      "CHASUS33",
        "created_at":      ts(50000),
    },
    {
        "counterparty_id": "CP-002",
        "name":            "Viktor Petrov",          # ⚠️ OFAC match
        "country":         "RU",
        "dob":             "1970-05-15",
        "entity_type":     "INDIVIDUAL",
        "bank_swift":      "VTBRRUMM",
        "created_at":      ts(7200),
    },
    {
        "counterparty_id": "CP-003",
        "name":            "Carlos Mendez",          # ⚠️ PEP match
        "country":         "MX",
        "dob":             "1965-03-12",
        "entity_type":     "INDIVIDUAL",
        "bank_swift":      "BNMXMXMM",
        "created_at":      ts(3000),
    },
    {
        "counterparty_id": "CP-004",
        "name":            "Amara Diallo",           # ⚠️ PEP match
        "country":         "NG",
        "dob":             "1971-07-22",
        "entity_type":     "INDIVIDUAL",
        "bank_swift":      "CITINGLA",
        "created_at":      ts(4320),
    },
    {
        "counterparty_id": "CP-005",
        "name":            "Pacific Rim Trading Co.",
        "country":         "SG",
        "dob":             None,
        "entity_type":     "COMPANY",
        "bank_swift":      "DBSSSGSG",
        "created_at":      ts(20000),
    },
]

TRANSACTIONS = [
    # ✅ Clean transaction — low amount, same country, clean counterparty
    {
        "txn_id":               "TXN-0001",
        "account_id":           "ACC-1001",
        "counterparty_id":      "CP-001",
        "amount":               250.00,
        "currency":             "USD",
        "originating_country":  "CA",
        "destination_country":  "US",
        "payment_method":       "ACH",
        "status":               "CLEARED",
        "flag_reason":          None,
        "flagged_at":           None,
        "created_at":           ts(120),
    },
    # ⚠️ High amount + OFAC counterparty
    {
        "txn_id":               "TXN-0042",
        "account_id":           "ACC-1001",
        "counterparty_id":      "CP-002",   # Viktor Petrov — OFAC
        "amount":               48500.00,   # Above $10k threshold
        "currency":             "USD",
        "originating_country":  "CA",
        "destination_country":  "RU",       # Cross-border
        "payment_method":       "WIRE",
        "status":               "PENDING",
        "flag_reason":          None,
        "flagged_at":           None,
        "created_at":           ts(5),
    },
    # ⚠️ Velocity burst — 6 transactions in 10 minutes from ACC-1003
    {
        "txn_id":               "TXN-0100",
        "account_id":           "ACC-1003",
        "counterparty_id":      "CP-005",
        "amount":               900.00,
        "currency":             "USD",
        "originating_country":  "MX",
        "destination_country":  "SG",
        "payment_method":       "WIRE",
        "status":               "PENDING",
        "flag_reason":          None,
        "flagged_at":           None,
        "created_at":           ts(2),
    },
    {
        "txn_id":               "TXN-0101",
        "account_id":           "ACC-1003",
        "counterparty_id":      "CP-005",
        "amount":               850.00,
        "currency":             "USD",
        "originating_country":  "MX",
        "destination_country":  "SG",
        "payment_method":       "WIRE",
        "status":               "PENDING",
        "flag_reason":          None,
        "flagged_at":           None,
        "created_at":           ts(3),
    },
    {
        "txn_id":               "TXN-0102",
        "account_id":           "ACC-1003",
        "counterparty_id":      "CP-005",
        "amount":               920.00,
        "currency":             "USD",
        "originating_country":  "MX",
        "destination_country":  "SG",
        "payment_method":       "WIRE",
        "status":               "PENDING",
        "flag_reason":          None,
        "flagged_at":           None,
        "created_at":           ts(4),
    },
    {
        "txn_id":               "TXN-0103",
        "account_id":           "ACC-1003",
        "counterparty_id":      "CP-005",
        "amount":               870.00,
        "currency":             "USD",
        "originating_country":  "MX",
        "destination_country":  "SG",
        "payment_method":       "WIRE",
        "status":               "PENDING",
        "flag_reason":          None,
        "flagged_at":           None,
        "created_at":           ts(5),
    },
    {
        "txn_id":               "TXN-0104",
        "account_id":           "ACC-1003",
        "counterparty_id":      "CP-005",
        "amount":               910.00,
        "currency":             "USD",
        "originating_country":  "MX",
        "destination_country":  "SG",
        "payment_method":       "WIRE",
        "status":               "PENDING",
        "flag_reason":          None,
        "flagged_at":           None,
        "created_at":           ts(6),
    },
    {
        "txn_id":               "TXN-0105",
        "account_id":           "ACC-1003",
        "counterparty_id":      "CP-005",
        "amount":               880.00,
        "currency":             "USD",
        "originating_country":  "MX",
        "destination_country":  "SG",
        "payment_method":       "WIRE",
        "status":               "PENDING",
        "flag_reason":          None,
        "flagged_at":           None,
        "created_at":           ts(7),
    },
    # ⚠️ PEP counterparty + non-KYC account
    {
        "txn_id":               "TXN-0200",
        "account_id":           "ACC-1003",  # Not KYC verified
        "counterparty_id":      "CP-003",    # Carlos Mendez — PEP
        "amount":               15000.00,
        "currency":             "USD",
        "originating_country":  "MX",
        "destination_country":  "MX",
        "payment_method":       "WIRE",
        "status":               "PENDING",
        "flag_reason":          None,
        "flagged_at":           None,
        "created_at":           ts(15),
    },
    # ⚠️ Suspended account attempting a transaction
    {
        "txn_id":               "TXN-0300",
        "account_id":           "ACC-1004",  # Suspended
        "counterparty_id":      "CP-002",    # Viktor Petrov — OFAC
        "amount":               99000.00,
        "currency":             "USD",
        "originating_country":  "RU",
        "destination_country":  "AE",        # UAE — high-risk jurisdiction
        "payment_method":       "CRYPTO",
        "status":               "PENDING",
        "flag_reason":          None,
        "flagged_at":           None,
        "created_at":           ts(1),
    },
]


# ── DB Initialization & Seeding ────────────────────────────────────────────────

async def create_tables():
    async with engine.begin() as conn:
        await conn.execute(text(CREATE_ACCOUNTS))
        await conn.execute(text(CREATE_COUNTERPARTIES))
        await conn.execute(text(CREATE_TRANSACTIONS))
        await conn.execute(text(CREATE_AUDIT_LOG))
    print("✅ Tables created.")


async def seed_table(session: AsyncSession, table: str, rows: list[dict], pk: str):
    for row in rows:
        exists = await session.execute(
            text(f"SELECT 1 FROM {table} WHERE {pk} = :{pk}"),
            {pk: row[pk]},
        )
        if not exists.scalar():
            cols    = ", ".join(row.keys())
            vals    = ", ".join(f":{k}" for k in row.keys())
            await session.execute(text(f"INSERT INTO {table} ({cols}) VALUES ({vals})"), row)

    await session.commit()
    print(f"✅ Seeded {len(rows)} rows → {table}")


async def seed_all():
    async with AsyncSessionLocal() as session:
        await seed_table(session, "accounts",        ACCOUNTS,        "account_id")
        await seed_table(session, "counterparties",  COUNTERPARTIES,  "counterparty_id")
        await seed_table(session, "transactions",    TRANSACTIONS,    "txn_id")


async def main():
    print("🚀 Initializing compliance database...")
    await create_tables()
    await seed_all()
    print("\n🎯 Interesting test cases:")
    print("  TXN-0042  → High amount + OFAC counterparty (Viktor Petrov)")
    print("  TXN-0100~ → Velocity burst (6 txns in 10 min, ACC-1003)")
    print("  TXN-0200  → PEP counterparty + non-KYC account")
    print("  TXN-0300  → Suspended account + OFAC + crypto + high-risk jurisdiction")
    print(f"\n📁 Database written to: {DB_PATH.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
