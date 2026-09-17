"""Independently check that recorded project resources no longer exist."""

from datetime import datetime, timezone
import json
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[1]
state = json.loads((ROOT / ".local/resources.json").read_text())
session = boto3.Session(
    region_name="us-east-1",
    **json.loads((ROOT / ".local/sandbox_credentials.json").read_text()),
)
assert session.client("sts").get_caller_identity()["Account"] == "090165623118"
control = session.client("bedrock-agentcore-control")
checks = []


def absent(name, action, **kwargs):
    try:
        action(**kwargs)
        checks.append({"resource": name, "absent": False})
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        checks.append(
            {
                "resource": name,
                "absent": code
                in (
                    "ResourceNotFoundException",
                    "NotFoundException",
                    "NoSuchEntity",
                    "NoSuchBucket",
                    "404",
                ),
                "response_code": code,
            }
        )


absent("runtime", control.get_agent_runtime, agentRuntimeId=state["runtime_id"])
absent("gateway", control.get_gateway, gatewayIdentifier=state["gateway_id"])
absent("memory", control.get_memory, memoryId=state["memory_id"])
absent("rest_api", session.client("apigateway").get_rest_api, restApiId=state["api_id"])
for key in ("order_tracker", "refund_processor"):
    absent(key, session.client("lambda").get_function, FunctionName=state[key])
for key in ("bucket", "runtime_bucket"):
    absent(key, session.client("s3").head_bucket, Bucket=state[key])
for key, arn in state.items():
    if key.endswith("_role"):
        absent(key, session.client("iam").get_role, RoleName=arn.rsplit("/", 1)[-1])
alarms = session.client("cloudwatch").describe_alarms(AlarmNames=[state["alarm"]])
checks.append({"resource": "alarm", "absent": not alarms["MetricAlarms"]})
report = {
    "checked_utc": datetime.now(timezone.utc).isoformat(),
    "all_recorded_resources_absent": all(row["absent"] for row in checks),
    "checks": checks,
    "scope": "Project runtime, gateway, memory, API, Lambdas, buckets, custom roles and alarm. Shared service-linked roles and account-wide logging settings are retained.",
}
(ROOT / "evidence/cleanup_verification.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
if report["all_recorded_resources_absent"]:
    state["cleaned_up_at"] = report["checked_utc"]
    (ROOT / ".local/resources.json").write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )
print(json.dumps(report, indent=2))
