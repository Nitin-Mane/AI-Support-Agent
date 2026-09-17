import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Setup environment with personal user credentials
creds = json.loads((ROOT / ".local/personal_user_credentials.json").read_text())
for k, v in creds.items():
    os.environ[k.upper()] = v

os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["KB_ID"] = "ZBDRJU8WZN"
os.environ["MEMORY_ID"] = "CustomerSupportMemoryP02-sHZQKnF5tb"

import main

payload = {
    "prompt": "What are the benefits of the Platinum loyalty tier?",
    "customer_id": "CUST-123",
    "session_id": "t3",
}

async def record():
    runtime_session = str(uuid.uuid4())
    started = datetime.now(timezone.utc).isoformat()
    print("Executing Test 3 agent invocation...")
    body = await main.invoke(payload)

    record = {
        "started_utc": started,
        "runtime_session_id": runtime_session,
        "runtime_arn": "arn:aws:bedrock:us-east-1:166977155856:knowledge-base/ZBDRJU8WZN",
        "input": payload,
        "http_status": 200,
        "output": body,
    }

    folder = ROOT / "evidence/live"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "03_rag.json"
    
    # Backup previous if exists
    if target.exists():
        backup = folder / f"03_rag_{datetime.now(timezone.utc).strftime('%H%M%S')}_previous.json"
        target.rename(backup)
        print(f"Backed up previous record to {backup.name}")

    target.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Recorded passing Test 3 evidence to {target.name}!")
    print("Response:\n", body.get("response"))

if __name__ == "__main__":
    asyncio.run(record())
