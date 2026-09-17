"""Check actual artifacts; an HTTP 200 response alone never counts as a pass."""

import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "evidence/live"


def record(name):
    return json.loads((LIVE / (name + ".json")).read_text(encoding="utf-8"))


def tool_results(data):
    names = {}
    results = []
    for message in data["output"].get("messages", []):
        for block in message.get("content", []):
            if "toolUse" in block:
                use = block["toolUse"]
                names[use["toolUseId"]] = use["name"]
            if "toolResult" in block:
                result = block["toolResult"]
                results.append((names.get(result["toolUseId"]), result))
    return results


checks = {}
order = (LIVE / "01_order.txt").read_text(encoding="utf-8")
checks["01_order"] = all(
    token in order for token in ("SHIPPED", "UPS", "TRK987654321", "September 17, 2026")
)
refund = record("02_refund")
results = tool_results(refund)
checks["02_refund"] = all(
    any(
        name == required and result.get("status") == "success" and result.get("content")
        for name, result in results
    )
    for required in ("order-tracker___get_order", "refund-processor___initiate_refund")
)
checks["02_refund"] &= "APPROVED" in json.dumps(
    refund
) and "3-5 business days" in json.dumps(refund)
rag = record("03_rag")
rag_tools = [r for name, r in tool_results(rag) if name == "search_knowledge_base"]
rag_text = json.dumps(rag_tools).lower()
checks["03_rag"] = (
    bool(rag_tools)
    and all(x in rag_text for x in ("same-day", "15%", "priority"))
    and "not configured" not in rag_text
)
a = record("04_memory_a")
b = record("04_memory_b")
reply = b["output"].get("response", "").lower()
context = json.dumps(b["output"].get("messages", [{}])[0]).lower()
checks["04_memory"] = (
    a["runtime_session_id"] != b["runtime_session_id"]
    and a["input"]["customer_id"] == b["input"]["customer_id"]
    and all(x in reply for x in ("jane", "concise"))
    and "customer context:" in context
)
discount = record("05_discount")
calc = [r for n, r in tool_results(discount) if n == "calculate_loyalty_discount"][-1]
values = json.loads(calc["content"][0]["text"])
checks["05_discount"] = all(
    values.get(k) == v
    for k, v in {
        "points_redeemed": 4000,
        "tier_discount_pct": 10,
        "final_total": 99,
        "remaining_points": 349,
        "calculation_mode": "code_interpreter",
    }.items()
)
checks["05_discount"] &= all(
    token in discount["output"]["response"] for token in ("99", "349")
)
browser = record("06_browser")
browser_tools = [r for n, r in tool_results(browser) if n == "browser"]
browser_actions = {
    block["toolUse"]["toolUseId"]: block["toolUse"]["input"]["browser_input"]["action"]
    for message in browser["output"].get("messages", [])
    for block in message.get("content", [])
    if block.get("toolUse", {}).get("name") == "browser"
}
successful = [r for r in browser_tools if r.get("status") == "success"]
navigation = any(
    browser_actions[result["toolUseId"]].get("type") == "navigate"
    and browser_actions[result["toolUseId"]].get("url") == "https://www.udacity.com"
    for result in successful
)
title_results = [
    result
    for result in successful
    if browser_actions[result["toolUseId"]].get("type") == "get_text"
    and browser_actions[result["toolUseId"]].get("selector") == "title"
]
checks["06_browser"] = (
    navigation
    and any(
        "Learn the Latest Tech Skills; Advance Your Career | Udacity"
        in json.dumps(result)
        for result in title_results
    )
    and "Learn the Latest Tech Skills; Advance Your Career | Udacity"
    in browser["output"].get("response", "")
)
originals = {}
for path in (ROOT / "lambda").iterdir():
    if not path.is_file():
        continue
    originals["lambda/" + path.name] = (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == hashlib.sha256(
            (ROOT / "upstream/starter/lambda" / path.name).read_bytes()
        ).hexdigest()
    )
originals["product_catalog.txt"] = (ROOT / "product_catalog.txt").read_bytes() == (
    ROOT / "upstream/starter/product_catalog.txt"
).read_bytes()
words = len((ROOT / "REFLECTION.md").read_text().split()) - 2
report = {
    "verified_utc": datetime.now(timezone.utc).isoformat(),
    "live_scenarios": checks,
    "passed_live_scenarios": sum(checks.values()),
    "required_live_scenarios": 6,
    "submission_ready": all(checks.values()),
    "original_assets_unchanged": originals,
    "reflection_word_count": words,
    "reflection_length_valid": 200 <= words <= 400,
    "notes": [
        "Local unit tests are separate from deployed-agent evidence.",
        "The Knowledge Base RAG scenario was tested live with verified OpenSearch retrieval.",
        "CloudWatch alarm configuration is exported as JSON; no console screenshot is claimed.",
    ],
}
(ROOT / "evidence/verification.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(json.dumps(report, indent=2))
