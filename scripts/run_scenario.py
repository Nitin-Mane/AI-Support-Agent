"""Scenario runner for evaluating customer support agent capabilities."""

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]

SCENARIOS = {
    "order": {
        "prompt": "Can you track order ORD-001?",
        "customer_id": "CUST-123",
        "session_id": "eval-order-1",
    },
    "refund": {
        "prompt": "I want to return my Kindle Paperwhite (ORD-002). Please initiate a refund.",
        "customer_id": "CUST-123",
        "session_id": "eval-refund-1",
    },
    "rag": {
        "prompt": "What are the benefits of the Platinum loyalty tier?",
        "customer_id": "CUST-123",
        "session_id": "eval-rag-1",
    },
    "memory_a": {
        "prompt": "Hi, I am Jane. I prefer concise responses.",
        "customer_id": "CUST-123",
        "session_id": "eval-mem-a",
    },
    "memory_b": {
        "prompt": "Do you remember my name and communication preference?",
        "customer_id": "CUST-123",
        "session_id": "eval-mem-b",
    },
    "discount": {
        "prompt": "I am a Gold member with 4250 points. Calculate my discount on a $150 standard order.",
        "customer_id": "CUST-123",
        "session_id": "eval-discount-1",
    },
    "browser": {
        "prompt": "Go to https://www.udacity.com and tell me the page title.",
        "customer_id": "CUST-123",
        "session_id": "eval-browser-1",
    },
}


async def run_local(scenario_key: str):
    """Run scenario locally through the main module entrypoint."""
    sys.path.insert(0, str(ROOT))
    import main

    payload = SCENARIOS[scenario_key]
    print(f"Executing scenario '{scenario_key}' locally...")
    print(f"Prompt: {payload['prompt']}")
    result = await main.invoke(payload)
    print("\nResponse:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def run_remote(scenario_key: str, runtime_arn: str, region: str = "us-east-1"):
    """Invoke deployed AgentCore Runtime via boto3."""
    session = boto3.Session(region_name=region)
    client = session.client("bedrock-agentcore")
    payload = SCENARIOS[scenario_key]
    runtime_session = str(uuid.uuid4())

    print(f"Invoking runtime {runtime_arn} for scenario '{scenario_key}'...")
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=runtime_session,
        payload=json.dumps(payload).encode("utf-8"),
        contentType="application/json",
        accept="application/json",
    )
    body = response["response"].read().decode("utf-8")
    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        pass

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario_key,
        "runtime_arn": runtime_arn,
        "runtime_session_id": runtime_session,
        "input": payload,
        "http_status": response["ResponseMetadata"]["HTTPStatusCode"],
        "output": body,
    }
    print(json.dumps(record, indent=2, ensure_ascii=False))


def main_cli():
    parser = argparse.ArgumentParser(description="Evaluate agent scenarios")
    parser.add_argument(
        "scenario",
        choices=list(SCENARIOS.keys()) + ["all"],
        help="Scenario identifier to execute",
    )
    parser.add_argument(
        "--runtime-arn",
        default=os.getenv("AGENT_RUNTIME_ARN"),
        help="AgentCore Runtime ARN for remote invocation",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION", "us-east-1"),
        help="AWS region (default: us-east-1)",
    )
    args = parser.parse_args()

    scenarios = list(SCENARIOS.keys()) if args.scenario == "all" else [args.scenario]

    for key in scenarios:
        if args.runtime_arn:
            run_remote(key, args.runtime_arn, args.region)
        else:
            asyncio.run(run_local(key))


if __name__ == "__main__":
    main_cli()
