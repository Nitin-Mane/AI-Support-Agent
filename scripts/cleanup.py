"""Remove only resources recorded for this project in the selected sandbox."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    state = json.loads((ROOT / ".local/resources.json").read_text())
    if not args.execute:
        print(json.dumps(state, indent=2))
        print(
            "Review the recorded identifiers; add --execute to remove these resources."
        )
        return
    session = boto3.Session(
        region_name="us-east-1",
        **json.loads((ROOT / ".local/sandbox_credentials.json").read_text()),
    )
    account = session.client("sts").get_caller_identity()["Account"]
    if account != "090165623118":
        raise RuntimeError("Cleanup is restricted to the selected Udacity sandbox.")
    control = session.client("bedrock-agentcore-control")
    report = {"started_utc": datetime.now(timezone.utc).isoformat(), "actions": []}
    destination = ROOT / "evidence/cleanup.json"

    def record(label, result, error=""):
        report["actions"].append({"resource": label, "result": result, "error": error})
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(label + ": " + result, flush=True)

    def remove(label, operation, **kwargs):
        try:
            operation(**kwargs)
            record(label, "deletion_requested")
        except ClientError as exc:
            if exc.response["Error"]["Code"] in (
                "ResourceNotFoundException",
                "NotFoundException",
                "NoSuchEntity",
                "NoSuchBucket",
            ):
                record(label, "already_absent")
            else:
                record(label, "failed", str(exc))

    # These two session IDs were captured in this project's Browser test traces.
    browser = session.client("bedrock-agentcore")
    for session_id in ("01M2K3VA6DSDEKV8SY8C1ZZ3BK", "01M2K3QFRKFQPZ0KYN89MPZ97A"):
        try:
            status = browser.get_browser_session(
                browserIdentifier="aws.browser.v1", sessionId=session_id
            )["status"]
            if status in ("TERMINATED", "STOPPED", "READY_TO_TERMINATE"):
                record("browser/" + session_id, "already_stopped")
            else:
                remove(
                    "browser/" + session_id,
                    browser.stop_browser_session,
                    browserIdentifier="aws.browser.v1",
                    sessionId=session_id,
                )
        except ClientError as exc:
            record(
                "browser/" + session_id,
                "already_absent"
                if exc.response["Error"]["Code"] == "ResourceNotFoundException"
                else "failed",
                str(exc),
            )

    runtime_id = state.get("runtime_id")
    if runtime_id:
        if not runtime_id.startswith("udacity_support_p02-"):
            raise RuntimeError("Unexpected runtime identifier.")
        remove("runtime", control.delete_agent_runtime, agentRuntimeId=runtime_id)
    for key in ("order_target", "refund_target"):
        if key in state:
            remove(
                key,
                control.delete_gateway_target,
                gatewayIdentifier=state["gateway_id"],
                targetId=state[key],
            )
    if "gateway_id" in state:
        for _ in range(30):
            try:
                if not control.list_gateway_targets(
                    gatewayIdentifier=state["gateway_id"]
                ).get("items"):
                    break
            except control.exceptions.ResourceNotFoundException:
                break
            time.sleep(5)
        remove("gateway", control.delete_gateway, gatewayIdentifier=state["gateway_id"])
    if "memory_id" in state:
        remove("memory", control.delete_memory, memoryId=state["memory_id"])
    if "api_id" in state:
        remove(
            "rest_api",
            session.client("apigateway").delete_rest_api,
            restApiId=state["api_id"],
        )
    for key in ("order_tracker", "refund_processor"):
        if key in state:
            if f":{account}:function:udacity-p02-" not in state[key]:
                raise RuntimeError("Unexpected Lambda ARN.")
            remove(
                key, session.client("lambda").delete_function, FunctionName=state[key]
            )
    if "alarm" in state:
        remove(
            "alarm",
            session.client("cloudwatch").delete_alarms,
            AlarmNames=[state["alarm"]],
        )

    s3 = session.client("s3")
    for bucket, prefix in [
        (state.get("bucket"), "product_catalog.txt"),
        (state.get("runtime_bucket"), "udacity_support_p02/"),
    ]:
        if not bucket:
            continue
        if account not in bucket:
            raise RuntimeError("Unexpected bucket name.")
        try:
            for page in s3.get_paginator("list_objects_v2").paginate(
                Bucket=bucket, Prefix=prefix
            ):
                objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
                if objects:
                    response = s3.delete_objects(
                        Bucket=bucket, Delete={"Objects": objects}
                    )
                    if response.get("Errors"):
                        raise RuntimeError(str(response["Errors"]))
            if s3.list_objects_v2(Bucket=bucket, MaxKeys=1).get("KeyCount", 0) == 0:
                remove("bucket/" + bucket, s3.delete_bucket, Bucket=bucket)
            else:
                record("bucket/" + bucket, "retained_unrelated_objects")
        except ClientError as exc:
            record(
                "bucket/" + bucket,
                "already_absent"
                if exc.response["Error"]["Code"] == "NoSuchBucket"
                else "failed",
                str(exc),
            )

    if runtime_id:
        for _ in range(60):
            try:
                control.get_agent_runtime(agentRuntimeId=runtime_id)
            except control.exceptions.ResourceNotFoundException:
                record("runtime", "verified_absent")
                break
            time.sleep(5)
    if "log_group" in state:
        remove(
            "runtime_logs",
            session.client("logs").delete_log_group,
            logGroupName=state["log_group"],
        )
    for function in ("udacity-p02-order-tracker", "udacity-p02-refund-processor"):
        remove(
            "lambda_logs/" + function,
            session.client("logs").delete_log_group,
            logGroupName="/aws/lambda/" + function,
        )
    iam = session.client("iam")
    for key, arn in state.items():
        if key.endswith("_role"):
            name = arn.rsplit("/", 1)[-1]
            if not name.startswith("udacity-p02-"):
                raise RuntimeError("Refusing to remove a role outside this project.")
            remove(
                "inline_policy/" + name,
                iam.delete_role_policy,
                RoleName=name,
                PolicyName="udacity-p02",
            )
            remove("role/" + name, iam.delete_role, RoleName=name)
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report["deletion_failures"] = [
        x for x in report["actions"] if x["result"] == "failed"
    ]
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Cleanup requests finished. Run the independent resource audit.", flush=True)


if __name__ == "__main__":
    main()
