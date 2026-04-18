COMPLIANCE_TOOLS = [

    # 🔴 Transaction Tools
    {
        "name": "get_transaction_details",
        "description": (
            "Fetch full details of a transaction by ID. "
            "Returns amount, currency, merchant, destination country, "
            "channel, timestamp, risk_score, and fraud_flag."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "txn_id": {
                    "type": "string",
                    "description": "The unique transaction identifier, e.g. TXN-0042"
                }
            },
            "required": ["txn_id"]
        }
    },
    {
        "name": "check_velocity",
        "description": (
            "Count transactions from an account in the last N minutes. "
            "Returns txn_count, total_amount, and whether a velocity "
            "threshold has been breached (>5 txns or >$10,000 in window)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "The account or customer ID to check"
                },
                "window_minutes": {
                    "type": "integer",
                    "description": "Lookback window in minutes. Defaults to 60.",
                    "default": 60
                }
            },
            "required": ["account_id"]
        }
    },
    {
        "name": "flag_transaction",
        "description": (
            "Write a compliance flag against a transaction with a reason. "
            "Updates transaction status to FLAGGED and writes an immutable "
            "audit log entry for FINTRAC/FATF compliance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "txn_id":  {"type": "string", "description": "Transaction to flag"},
                "reason":  {"type": "string", "description": "Plain-English flag reason for the audit log"}
            },
            "required": ["txn_id", "reason"]
        }
    },

    # 🟡 Counterparty Tools
    {
        "name": "screen_against_ofac",
        "description": (
            "Screen a counterparty name and country against the OFAC SDN "
            "sanctions list using fuzzy matching (threshold: 85%). "
            "Returns ofac_hit (bool), match_score, matched_entity, and recommended action."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name":    {"type": "string", "description": "Full legal name of the counterparty"},
                "country": {"type": "string", "description": "ISO 3166-1 alpha-2 country code, e.g. NG"}
            },
            "required": ["name", "country"]
        }
    },
    {
        "name": "check_pep_status",
        "description": (
            "Check if a counterparty is a Politically Exposed Person (PEP). "
            "Covers PEP Class 1 (heads of state) through Class 3 (associates). "
            "Returns is_pep, pep_class, position, and whether enhanced due diligence is required."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string",  "description": "Full name of the individual"},
                "dob":  {"type": "string",  "description": "Date of birth ISO 8601 (YYYY-MM-DD). Optional but improves accuracy."}
            },
            "required": ["name"]
        }
    },
    {
        "name": "get_counterparty_risk_score",
        "description": (
            "Get a composite risk score (0–100) for a known counterparty. "
            "Combines OFAC hit, PEP status, adverse media, and transaction history. "
            "Risk levels: LOW <40, MEDIUM 40–59, HIGH 60–79, CRITICAL ≥80."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "counterparty_id": {
                    "type": "string",
                    "description": "Internal counterparty identifier"
                }
            },
            "required": ["counterparty_id"]
        }
    },
]
