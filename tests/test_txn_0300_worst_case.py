# tests/test_txn_0300_worst_case.py

import pytest
from unittest.mock import patch, MagicMock
from mcp_client import MCPClient  # adjust to your actual client import


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """Spin up MCP client connected to the server."""
    c = MCPClient(host="localhost", port=8000)
    c.connect()
    yield c
    c.disconnect()


@pytest.fixture(scope="module")
def txn_details(client):
    """Fetch TXN-0300 once and reuse across tests."""
    return client.call_tool("get_transaction_details", {"txn_id": "TXN-0300"})


@pytest.fixture(scope="module")
def risk_data(client):
    return client.call_tool("get_risk_score", {"customer_id": "CUST-8821"})


@pytest.fixture(scope="module")
def fraud_data(client):
    return client.call_tool("get_fraud_history", {"customer_id": "CUST-8821"})


@pytest.fixture(scope="module")
def customer_data(client):
    return client.call_tool("get_customer_profile", {"customer_id": "CUST-8821"})


# ─────────────────────────────────────────────
# STEP 1 — Transaction Details
# ─────────────────────────────────────────────

class TestTransactionDetails:

    def test_txn_id_matches(self, txn_details):
        assert txn_details["txn_id"] == "TXN-0300"

    def test_amount_is_high_value(self, txn_details):
        assert txn_details["amount"] >= 9000, "Expected high-value transaction"

    def test_currency_is_usd(self, txn_details):
        assert txn_details["currency"] == "USD"

    def test_status_is_flagged(self, txn_details):
        assert txn_details["status"] == "FLAGGED"

    def test_fraud_flag_is_true(self, txn_details):
        assert txn_details["fraud_flag"] is True

    def test_merchant_is_unknown(self, txn_details):
        assert "UNKNOWN" in txn_details["merchant"].upper()

    def test_country_is_high_risk(self, txn_details):
        HIGH_RISK_COUNTRIES = {"NG", "KP", "IR", "SY", "CU"}
        assert txn_details["country"] in HIGH_RISK_COUNTRIES

    def test_channel_is_api(self, txn_details):
        assert txn_details["channel"] == "API"

    def test_risk_score_is_critical(self, txn_details):
        assert txn_details["risk_score"] >= 90, (
            f"Expected risk_score >= 90, got {txn_details['risk_score']}"
        )

    def test_customer_id_is_correct(self, txn_details):
        assert txn_details["customer_id"] == "CUST-8821"

    def test_notes_contain_anomaly(self, txn_details):
        notes = txn_details.get("notes", "").lower()
        assert any(kw in notes for kw in ["anomaly", "breach", "velocity", "flag"])

    def test_response_has_no_null_fields(self, txn_details):
        required_fields = [
            "txn_id", "amount", "currency", "status",
            "customer_id", "timestamp", "merchant",
            "country", "channel", "risk_score", "fraud_flag"
        ]
        for field in required_fields:
            assert txn_details.get(field) is not None, f"Field '{field}' is null"


# ─────────────────────────────────────────────
# STEP 2 — Risk Score
# ─────────────────────────────────────────────

class TestRiskScore:

    def test_risk_level_is_critical(self, risk_data):
        assert risk_data["risk_level"] == "CRITICAL"

    def test_risk_score_matches_txn(self, txn_details, risk_data):
        assert risk_data["risk_score"] == txn_details["risk_score"], (
            "Risk score mismatch between transaction and risk profile"
        )

    def test_velocity_breach_flag_present(self, risk_data):
        assert "velocity_breach" in risk_data["flags"]

    def test_geo_anomaly_flag_present(self, risk_data):
        assert "geo_anomaly" in risk_data["flags"]

    def test_new_device_flag_present(self, risk_data):
        assert "new_device" in risk_data["flags"]

    def test_flags_list_not_empty(self, risk_data):
        assert isinstance(risk_data["flags"], list)
        assert len(risk_data["flags"]) >= 2, "Expected multiple risk flags"


# ─────────────────────────────────────────────
# STEP 3 — Fraud History
# ─────────────────────────────────────────────

class TestFraudHistory:

    def test_has_open_cases(self, fraud_data):
        assert fraud_data["open_cases"] >= 1, "Expected at least 1 open fraud case"

    def test_has_confirmed_fraud(self, fraud_data):
        assert fraud_data["confirmed_fraud"] >= 1, "Expected at least 1 confirmed fraud"

    def test_total_flagged_txns_is_high(self, fraud_data):
        assert fraud_data["total_flagged_txns"] >= 3

    def test_last_incident_is_recent(self, fraud_data):
        from datetime import datetime, timezone, timedelta

        last_incident = datetime.fromisoformat(
            fraud_data["last_incident"].replace("Z", "+00:00")
        )
        cutoff = datetime.now(timezone.utc) - timedelta(days=60)
        assert last_incident > cutoff, (
            f"Last incident {last_incident} is too old — expected within 60 days"
        )


# ─────────────────────────────────────────────
# STEP 4 — Customer Profile
# ─────────────────────────────────────────────

class TestCustomerProfile:

    def test_customer_is_flagged(self, customer_data):
        assert customer_data["flagged"] is True

    def test_kyc_is_not_verified(self, customer_data):
        assert customer_data["kyc_status"] != "VERIFIED", (
            "KYC should not be VERIFIED for a high-risk worst-case customer"
        )

    def test_account_is_new(self, customer_data):
        """Account age should be under 30 days for worst-case scenario."""
        age_str = customer_data["account_age"]  # e.g. "14 days"
        age_days = int(age_str.split()[0])
        assert age_days <= 30, f"Expected new account, got: {age_str}"

    def test_geo_mismatch_with_txn(self, customer_data, txn_details):
        """Customer's usual country should differ from transaction country."""
        assert customer_data["usual_country"] != txn_details["country"], (
            "Expected geo mismatch between customer home country and txn country"
        )


# ─────────────────────────────────────────────
# STEP 5 — End-to-End Agent Decision
# ─────────────────────────────────────────────

class TestAgentDecision:

    def test_agent_recommends_block(
        self, client, txn_details, risk_data, fraud_data, customer_data
    ):
        """
        Feed all 4 tool results into the agent and assert it recommends BLOCK.
        """
        context = {
            "transaction": txn_details,
            "risk":        risk_data,
            "fraud":       fraud_data,
            "customer":    customer_data,
        }

        decision = client.call_tool("get_agent_decision", {"context": context})

        assert decision["action"] in ("BLOCK", "ESCALATE"), (
            f"Expected BLOCK or ESCALATE, got: {decision['action']}"
        )
        assert decision["confidence"] >= 0.90, (
            f"Expected high confidence, got: {decision['confidence']}"
        )

    def test_all_tools_respond_within_sla(self, client):
        """Each tool must respond within 200ms."""
        import time

        tools = [
            ("get_transaction_details",  {"txn_id": "TXN-0300"}),
            ("get_risk_score",           {"customer_id": "CUST-8821"}),
            ("get_fraud_history",        {"customer_id": "CUST-8821"}),
            ("get_customer_profile",     {"customer_id": "CUST-8821"}),
        ]

        for tool_name, args in tools:
            start = time.monotonic()
            client.call_tool(tool_name, args)
            elapsed_ms = (time.monotonic() - start) * 1000
            assert elapsed_ms < 200, (
                f"Tool '{tool_name}' took {elapsed_ms:.1f}ms — exceeds 200ms SLA"
            )


# ─────────────────────────────────────────────
# STEP 6 — Negative / Edge Cases
# ─────────────────────────────────────────────

class TestEdgeCases:

    def test_invalid_txn_id_returns_error(self, client):
        result = client.call_tool("get_transaction_details", {"txn_id": "TXN-FAKE"})
        assert result.get("error") is not None or result.get("status") == "NOT_FOUND"

    def test_missing_txn_id_raises(self, client):
        with pytest.raises(Exception, match="(missing|required|invalid)"):
            client.call_tool("get_transaction_details", {})

    def test_response_is_valid_json(self, txn_details):
        import json
        # If fixture loaded, it's already a dict — just confirm it's serializable
        serialized = json.dumps(txn_details)
        assert isinstance(serialized, str)
