import json
from pathlib import Path
from rapidfuzz import fuzz

# Load mock watchlists at startup
_OFAC_LIST = json.loads(Path("data/watchlists/ofac.json").read_text())
_PEP_LIST  = json.loads(Path("data/watchlists/pep.json").read_text())

FUZZY_MATCH_THRESHOLD = 85  # % similarity for a name match


def _fuzzy_match(name: str, watchlist: list[dict], name_key: str = "name") -> list[dict]:
    """Return watchlist entries that fuzzy-match the given name."""
    hits = []
    for entry in watchlist:
        score = fuzz.token_sort_ratio(name.lower(), entry[name_key].lower())
        if score >= FUZZY_MATCH_THRESHOLD:
            hits.append({**entry, "match_score": score})
    return sorted(hits, key=lambda x: x["match_score"], reverse=True)


async def screen_against_ofac(name: str, country: str = "") -> dict:
    hits = _fuzzy_match(name, _OFAC_LIST)

    # Optionally narrow by country
    if country and hits:
        hits = [h for h in hits if country.lower() in h.get("country", "").lower()] or hits

    return {
        "screened_name": name,
        "ofac_hit": len(hits) > 0,
        "matches": hits[:3],  # Top 3 matches
        "risk_flag": "OFAC_MATCH" if hits else None,
    }


async def check_pep_status(name: str, dob: str = "") -> dict:
    hits = _fuzzy_match(name, _PEP_LIST)

    # Narrow by DOB if provided
    if dob and hits:
        hits = [h for h in hits if h.get("dob", "") == dob] or hits

    return {
        "screened_name": name,
        "is_pep": len(hits) > 0,
        "matches": hits[:3],
        "risk_flag": "PEP_MATCH" if hits else None,
    }


async def get_counterparty_risk_score(counterparty_id: str) -> dict:
    """
    Composite risk score combining OFAC + PEP results.
    Score: 0.0 (clean) → 1.0 (high risk / block immediately).
    """
    from db.seed_db import get_db_session
    from sqlalchemy import text

    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT * FROM counterparties WHERE counterparty_id = :id"),
            {"counterparty_id": counterparty_id},
        )
        row = result.mappings().first()
        if not row:
            return {"error": f"Counterparty {counterparty_id} not found"}
        cp = dict(row)

    ofac_result = await screen_against_ofac(cp["name"], cp.get("country", ""))
    pep_result  = await check_pep_status(cp["name"], cp.get("dob", ""))

    score = 0.0
    flags = []

    if ofac_result["ofac_hit"]:
        score += float(os.getenv("OFAC_HIT_SCORE", 1.0))
        flags.append("OFAC_MATCH")
    if pep_result["is_pep"]:
        score += float(os.getenv("PEP_HIT_SCORE", 0.6))
        flags.append("PEP_MATCH")

    score = min(score, 1.0)  # Cap at 1.0

    return {
        "counterparty_id": counterparty_id,
        "name": cp["name"],
        "risk_score": round(score, 2),
        "risk_level": "HIGH" if score >= 0.8 else "MEDIUM" if score >= 0.4 else "LOW",
        "flags": flags,
        "recommendation": "BLOCK" if score >= 0.8 else "REVIEW" if score >= 0.4 else "PASS",
    }
