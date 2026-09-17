"""Exercise the corrected configuration and transport errors locally.

This uses a real MCPClient against a deliberately closed localhost port.
It does not simulate a successful cloud deployment or invoke a Bedrock model.
"""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import sys

os.environ["AWS_EC2_METADATA_DISABLED"] = "true"
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main

destination = ROOT / "examples/revision"
destination.mkdir(parents=True, exist_ok=True)
handler = logging.FileHandler(destination / "gateway_failure.log", mode="w", encoding="utf-8")
logging.getLogger().addHandler(handler)
report = {
    "checked_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "Local execution of corrected main.py; no cloud deployment",
    "main_sha256": hashlib.sha256((ROOT / "main.py").read_bytes()).hexdigest(),
    "cases": {},
}
for label, kb_id in [("missing_kb", None), ("empty_kb", ""), ("whitespace_kb", " \t\n")]:
    main.KB_ID = kb_id
    response = main.search_knowledge_base("What are the Platinum benefits?")
    assert "KB_ID is empty or missing" in response
    report["cases"][label] = {"passed": True, "response": response}

main.MEMORY_ID = ""
main.GATEWAY_URL = "http://127.0.0.1:9/mcp"
main.gateway_client = main.MCPClient(lambda: main.streamable_http_client(main.GATEWAY_URL))
result = asyncio.run(main.invoke({"prompt": "Track ORD-001", "session_id": "review-invalid-gateway"}))
assert result.get("error_code") == "GATEWAY_UNAVAILABLE"
assert "retry" in result["error"].lower()
report["cases"]["invalid_gateway"] = {"passed": True, "response": result}
logging.getLogger().removeHandler(handler)
handler.close()
log_path = destination / "gateway_failure.log"
log_path.write_text(
    "\n".join(line.rstrip() for line in log_path.read_text(encoding="utf-8").splitlines()) + "\n",
    encoding="utf-8",
)
(destination / "failure_checks.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
