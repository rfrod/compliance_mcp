# agent.py  ──  Claude agentic loop with full tool execution

import os, json, anthropic
from tools import COMPLIANCE_TOOLS
from dispatcher import dispatch_tool
from middleware.audit import audit_middleware

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a compliance AI agent for a regulated financial institution.

Your job is to investigate transactions and counterparties for fraud, 
AML risk, and sanctions violations using the tools available to you.

ALWAYS follow this investigation order:
1. Fetch transaction details first
2. Run velocity check on the customer account
3. Screen the counterparty against OFAC
4. Check PEP status if counterparty is an individual
5. Get composite risk score
6. Flag the transaction if ANY risk threshold is breached
7. Return a structured BLOCK / REVIEW / PASS decision with full reasoning

You MUST cite specific tool results in your final decision.
Every flag you write becomes a regulatory audit record — be precise."""


def run_compliance_agent(query: str, user_id: str = "system") -> str:
    """
    Run Claude as a compliance agent against a natural-language query.
    Executes the full tool-use loop until Claude reaches end_turn.
    """
    messages = [{"role": "user", "content": query}]

    print(f"\n{'═'*60}")
    print(f"  🤖 COMPLIANCE AGENT — NEW INVESTIGATION")
    print(f"  Query: {query}")
    print(f"{'═'*60}\n")

    # ── Agentic loop ──────────────────────────────────────────────
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=COMPLIANCE_TOOLS,
            messages=messages,
        )

        # ── Case 1: Claude wants to call tools ───────────────────
        if response.stop_reason == "tool_use":

            # Append Claude's full response (may contain text + tool calls)
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []

            for block in response.content:

                # Print any reasoning Claude narrates before the tool call
                if block.type == "text" and block.text.strip():
                    print(f" Claude: {block.text.strip()}\n")

                # Execute each tool Claude selected
                if block.type == "tool_use":
                    print(f" Calling tool : {block.name}")
                    print(f" Arguments    : {json.dumps(block.input, indent=2)}")

                    result_json = dispatch_tool(block.name, block.input)
                    result_dict = json.loads(result_json)

                    print(f"📦 Result       : {json.dumps(result_dict, indent=2)}\n")

                    # Write every tool call to the audit log
                    audit_middleware(
                        tool_name=block.name,
                        args=block.input,
                        result=result_dict,
                        user_id=user_id,
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_json,
                        }
                    )

            # Feed all tool results back to Claude in one turn
            messages.append({"role": "user", "content": tool_results})

        # ── Case 2: Claude has finished reasoning → final answer ──
        elif response.stop_reason == "end_turn":
            final = next((b.text for b in response.content if hasattr(b, "text")), "")
            print(f"{'═'*60}")
            print("  AGENT FINAL DECISION")
            print(f"{'═'*60}")
            print(final)
            return final

        # ── Case 3: Unexpected stop ───────────────────────────────
        else:
            raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")


# ── Entry point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    run_compliance_agent(
        query="Review transaction TXN-0042 and tell me if we should block it.",
        user_id="compliance-officer-001",
    )
