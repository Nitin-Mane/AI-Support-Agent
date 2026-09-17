"""Verify the recorded responses from the fresh revision deployment."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from verify_traces import tool_results

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "examples/cloud_revision"


def load(name):
    return json.loads((DIRECTORY / f"{name}.json").read_text(encoding="utf-8"))


def successful(result):
    return (result.get("status") == "success" and not result.get("isError")
            and any(block.get("text") or block.get("json")
                    for block in result.get("content", [])))


def verify():
    records = {name: load(name) for name in (
        "order", "refund", "rag", "memory_a", "memory_b", "discount",
        "browser", "gateway_failure",
    )}
    source = load("source_verification")
    digest = hashlib.sha256((ROOT / "main.py").read_bytes()).hexdigest()
    same_source = source["uploaded_main_sha256"] == digest and all(
        record["source_sha256"] == digest for record in records.values())
    same_runtime = len({r["runtime_arn"] for r in records.values()}) == 1
    http_ok = all(r.get("http_status") == 200 for r in records.values())
    order = dict(tool_results(records["order"]))
    order_data = json.loads(order["order-tracker___get_order"]["content"][0]["text"])
    gateway = [(name, result) for name, result in tool_results(records["refund"])
               if "___" in name]
    gateway_ok = all(successful(result) for _, result in gateway) and {
        "order-tracker___get_order", "refund-processor___initiate_refund"
    }.issubset({name for name, _ in gateway})
    # Require JSON payloads, including the Lambda proxy response body.
    for _, result in gateway:
        data = json.loads(result["content"][0]["text"])
        if "body" in data:
            data = json.loads(data["body"])
        gateway_ok = gateway_ok and isinstance(data, dict) and bool(data)
    calculation = dict(tool_results(records["discount"]))["calculate_loyalty_discount"]
    value = json.loads(calculation["content"][0]["text"])
    browser_results = [r for n, r in tool_results(records["browser"]) if n == "browser"]
    browser_response = records["browser"]["output"].get("response", "")
    rag_results = [r for n, r in tool_results(records["rag"]) if n == "search_knowledge_base"]
    rag_text = json.dumps(rag_results).lower()
    memory_a, memory_b = records["memory_a"], records["memory_b"]
    recall = memory_b["output"].get("response", "").lower()
    scenarios = {
        "order_tracking": successful(order["order-tracker___get_order"])
            and order_data["tracking_number"] == "TRK987654321"
            and order_data["carrier"] == "UPS",
        "refund_processing": gateway_ok and "APPROVED" in json.dumps(records["refund"]),
        "knowledge_retrieval": bool(rag_results) and "not configured" not in rag_text
            and all(word in rag_text for word in ("same-day", "15%", "priority")),
        "memory_recall": memory_a["input"]["customer_id"] == memory_b["input"]["customer_id"]
            and memory_a["runtime_session_id"] != memory_b["runtime_session_id"]
            and "jane" in recall and "concise" in recall,
        "discount_calculation": value.get("calculation_mode") == "code_interpreter"
            and value.get("points_redeemed") == 4000 and value.get("final_total") == 99.0
            and value.get("remaining_points") == 349,
        "browser_automation": any(successful(r) and "Udacity" in json.dumps(r)
                                  for r in browser_results) and "Udacity" in browser_response,
    }
    failure = records["gateway_failure"]["output"]
    logs = load("runtime_logs")
    corrections = {
        "missing_kb_guard": "kb_id is empty or missing" in rag_text
            and "configure KB_ID" in records["rag"]["output"]["response"],
        "gateway_failure_message": failure.get("error_code") == "GATEWAY_UNAVAILABLE"
            and "retry" in failure.get("error", "").lower()
            and "administrator" in failure.get("error", "").lower(),
        "gateway_success_and_failure_logging": any("Gateway connected successfully" in e["message"] for e in logs)
            and any("Gateway tool loading failed" in e["message"] for e in logs),
        "well_formed_gateway_responses": gateway_ok,
    }
    cli_path = DIRECTORY / "agentcore_invoke.json"
    cli = json.loads(cli_path.read_text(encoding="utf-8")) if cli_path.exists() else {}
    cli_text_path = DIRECTORY / "agentcore_invoke.txt"
    cli_text = cli_text_path.read_text(encoding="utf-8") if cli_text_path.exists() else ""
    cli_ok = (cli.get("exit_code") == 0 and cli.get("uploaded_main_sha256") == digest
              and cli.get("runtime_arn", "missing ARN") in cli_text
              and "TRK987654321" in cli_text and "UPS" in cli_text)
    report = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Fresh AWS invocation records from September 17, 2026; verification reads saved responses",
        "runtime_arn": records["order"]["runtime_arn"],
        "runtime_versions": {key: r["runtime_version"] for key, r in records.items()},
        "source_sha256": digest, "uploaded_source_matches_current": same_source,
        "same_runtime": same_runtime, "all_http_200": http_ok,
        "scenarios_passed": sum(scenarios.values()), "total_scenarios": 6,
        "scenarios": scenarios, "reviewer_corrections": corrections,
        "browser_recovered_validation_errors": sum(not successful(r) for r in browser_results),
        "deployment_cli_evidence": {"passed": cli_ok, "runtime_arn": cli.get("runtime_arn"),
                                    "record": "agentcore_invoke.json", "output": "agentcore_invoke.txt"},
        "rag_blocker": load("rag_permission"),
        "submission_ready": same_source and same_runtime and http_ok
            and all(scenarios.values()) and all(corrections.values()) and cli_ok,
    }
    (DIRECTORY / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    verify()
