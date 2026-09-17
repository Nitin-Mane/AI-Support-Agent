"""Capture a real `agentcore invoke` transcript for one classroom scenario."""

import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import boto3
import yaml
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
scenarios = {
    "01_order": {
        "prompt": "Can you track order ORD-001?",
        "customer_id": "CUST-123",
        "session_id": "t1",
    },
    "02_refund": {
        "prompt": "I want to return my Kindle Paperwhite (ORD-002). Please initiate a refund.",
        "customer_id": "CUST-123",
        "session_id": "t2",
    },
    "03_rag": {
        "prompt": "What are the benefits of the Platinum loyalty tier?",
        "customer_id": "CUST-123",
        "session_id": "t3",
    },
    "04_memory_a": {
        "prompt": "Hi, I am Jane. I prefer concise responses.",
        "customer_id": "CUST-123",
        "session_id": "s-A",
    },
    "04_memory_b": {
        "prompt": "Do you remember my name and communication preference?",
        "customer_id": "CUST-123",
        "session_id": "s-B",
    },
    "05_discount": {
        "prompt": "I am a Gold member with 4250 points. Calculate my discount on a $150 standard order.",
        "customer_id": "CUST-123",
        "session_id": "t5",
    },
    "06_browser": {
        "prompt": "Go to https://www.udacity.com and tell me the page title.",
        "customer_id": "CUST-123",
        "session_id": "t6",
    },
}
name = sys.argv[1]
payload = scenarios[name]
if "--raw" in sys.argv:
    credentials = json.loads((ROOT / ".local/sandbox_credentials.json").read_text())
    session = boto3.Session(region_name="us-east-1", **credentials)
    configuration = yaml.safe_load(
        (ROOT / "deployment/.bedrock_agentcore.yaml").read_text()
    )
    arn = configuration["agents"]["udacity_support_p02"]["bedrock_agentcore"][
        "agent_arn"
    ]
    runtime_session = str(uuid.uuid4())
    started = datetime.now(timezone.utc).isoformat()
    response = session.client("bedrock-agentcore").invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=runtime_session,
        payload=json.dumps(payload).encode(),
        contentType="application/json",
        accept="application/json",
    )
    body = response["response"].read().decode()
    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        pass
    record = {
        "started_utc": started,
        "runtime_session_id": runtime_session,
        "runtime_arn": arn,
        "input": payload,
        "http_status": response["ResponseMetadata"]["HTTPStatusCode"],
        "output": body,
    }
    folder = ROOT / "evidence/live"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (name + ".json")
    if path.exists():
        path.rename(
            path.with_name(
                name
                + "_"
                + datetime.now(timezone.utc).strftime("%H%M%S")
                + "_previous.json"
            )
        )
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "file": str(path),
                "http_status": record["http_status"],
                "output": {k: v for k, v in body.items() if k != "messages"}
                if isinstance(body, dict)
                else body,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    sys.exit(1 if isinstance(body, dict) and body.get("error") else 0)
env = os.environ.copy()
env.update(
    {
        k.upper(): v
        for k, v in json.loads(
            (ROOT / ".local/sandbox_credentials.json").read_text()
        ).items()
    }
)
env.update(
    AWS_DEFAULT_REGION="us-east-1",
    AWS_REGION="us-east-1",
    PYTHONUTF8="1",
    PYTHONIOENCODING="utf-8",
    AGENTCORE_SUPPRESS_RECOMMENDATION="1",
    NO_COLOR="1",
    COLUMNS="160",
)
cli = ROOT / ".venv/Scripts/agentcore.exe"
command = [str(cli), "invoke", json.dumps(payload)]
started = datetime.now(timezone.utc).isoformat()
result = subprocess.run(
    command,
    cwd=ROOT / "deployment",
    env=env,
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    timeout=600,
)
transcript = f"Started UTC: {started}\nCommand: agentcore invoke {
    json.dumps(payload)
}\nExit code: {result.returncode}\n\nSTDOUT\n{result.stdout}\nSTDERR\n{result.stderr}"
folder = ROOT / "evidence/live"
folder.mkdir(parents=True, exist_ok=True)
path = folder / (name + ".txt")
if path.exists():
    path.rename(
        path.with_name(
            name + "_" + datetime.now(timezone.utc).strftime("%H%M%S") + "_previous.txt"
        )
    )
path.write_text(transcript, encoding="utf-8")
print(transcript)
sys.exit(result.returncode)
