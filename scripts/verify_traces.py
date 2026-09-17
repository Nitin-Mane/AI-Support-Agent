"""Audit and verify agent execution traces against expected outputs and tool contracts."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACES_DIR = ROOT / "examples" / "traces"


def tool_results(record: dict) -> list[tuple[str, dict]]:
    """Extract tool names and outputs from agent execution messages."""
    tools = {
        block["toolUse"]["toolUseId"]: block["toolUse"]["name"]
        for message in record.get("output", {}).get("messages", [])
        for block in message.get("content", [])
        if "toolUse" in block
    }
    results = []
    for message in record.get("output", {}).get("messages", []):
        for block in message.get("content", []):
            if "toolResult" in block:
                tool_id = block["toolResult"]["toolUseId"]
                results.append((tools.get(tool_id, "unknown"), block["toolResult"]))
    return results


def load_record(name: str) -> dict:
    path = TRACES_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def audit_traces() -> dict:
    checks = {}

    # 1. Order tracking
    order_text = (TRACES_DIR / "01_order_tracking.txt").read_text(encoding="utf-8")
    checks["order_tracking"] = (
        "ORD-001" in order_text
        and "UPS" in order_text
        and "TRK987654321" in order_text
        and "September 17, 2026" in order_text
    )

    # 2. Refund processing
    refund = load_record("02_refund_processing")
    results = tool_results(refund)
    checks["refund_processing"] = (
        any(name == "refund-processor___initiate_refund" and result.get("status") == "success" for name, result in results)
        and "APPROVED" in json.dumps(refund)
        and "3-5 business days" in json.dumps(refund)
    )

    # 3. Knowledge Base RAG
    rag = load_record("03_knowledge_retrieval")
    rag_tools = [r for name, r in tool_results(rag) if name == "search_knowledge_base"]
    rag_text = json.dumps(rag_tools).lower()
    checks["knowledge_retrieval"] = (
        bool(rag_tools)
        and all(x in rag_text for x in ("same-day", "15%", "priority"))
        and "not configured" not in rag_text
    )

    # 4. Cross-session memory
    session_a = load_record("04_memory_session_a")
    session_b = load_record("04_memory_session_b")
    checks["memory_recall"] = (
        session_a["input"]["customer_id"] == session_b["input"]["customer_id"]
        and session_a["runtime_session_id"] != session_b["runtime_session_id"]
        and "Jane" in session_b["output"].get("response", "")
        and "concise" in session_b["output"].get("response", "").lower()
    )

    # 5. Discount calculation
    discount = load_record("05_discount_calculation")
    discount_tools = [r for n, r in tool_results(discount) if n == "calculate_loyalty_discount"]
    discount_result = json.loads(discount_tools[0]["content"][0]["text"]) if discount_tools else {}
    checks["discount_calculation"] = (
        discount_result.get("points_redeemed") == 4000
        and discount_result.get("tier_discount_pct") == 10.0
        and discount_result.get("final_total") == 99.0
        and discount_result.get("remaining_points") == 349
        and "99" in discount["output"].get("response", "")
    )

    # 6. Browser automation
    browser = load_record("06_browser_automation")
    browser_tools = [r for n, r in tool_results(browser) if n == "browser"]
    checks["browser_automation"] = (
        len(browser_tools) > 0
        and any("Advance Your Career" in json.dumps(r) for r in browser_tools)
        and "Advance Your Career" in browser["output"].get("response", "")
    )

    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "scenarios_passed": sum(checks.values()),
        "total_scenarios": len(checks),
        "details": checks,
    }
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    audit_traces()
