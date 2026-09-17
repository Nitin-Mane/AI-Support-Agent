"""Stage only runtime files and create its service execution role."""

import json
import shutil
from provision import ROOT, REGION, account, allow, role, state

runtime_role = role(
    "runtime",
    "bedrock-agentcore.amazonaws.com",
    [
        allow(
            ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            [
                "arn:aws:bedrock:*::foundation-model/amazon.nova-2-lite-v1:0",
                f"arn:aws:bedrock:*:{account}:inference-profile/*nova-2-lite*",
                "arn:aws:bedrock:*::inference-profile/*nova-2-lite*",
            ],
        ),
        allow(
            ["bedrock:Retrieve"], f"arn:aws:bedrock:{REGION}:{account}:knowledge-base/*"
        ),
        allow(
            [
                "bedrock-agentcore:GetMemory",
                "bedrock-agentcore:RetrieveMemoryRecords",
                "bedrock-agentcore:CreateEvent",
            ],
            f"arn:aws:bedrock-agentcore:{REGION}:{account}:memory/{state['memory_id']}*",
        ),
        allow(
            [
                "bedrock-agentcore:StartCodeInterpreterSession",
                "bedrock-agentcore:InvokeCodeInterpreter",
                "bedrock-agentcore:StopCodeInterpreterSession",
                "bedrock-agentcore:GetCodeInterpreterSession",
                "bedrock-agentcore:StartBrowserSession",
                "bedrock-agentcore:StopBrowserSession",
                "bedrock-agentcore:GetBrowserSession",
                "bedrock-agentcore:UpdateBrowserStream",
                "bedrock-agentcore:ConnectBrowserAutomationStream",
                "bedrock-agentcore:ConnectBrowserLiveViewStream",
            ],
            "*",
        ),
        allow(
            [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams",
            ],
            f"arn:aws:logs:{REGION}:{account}:*",
        ),
        allow(
            [
                "xray:PutTraceSegments",
                "xray:PutTelemetryRecords",
                "xray:GetSamplingRules",
                "xray:GetSamplingTargets",
            ],
            "*",
        ),
        allow(["cloudwatch:PutMetricData"], "*"),
        allow(
            [
                "bedrock-agentcore:GetWorkloadAccessToken",
                "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
            ],
            f"arn:aws:bedrock-agentcore:{REGION}:{account}:workload-identity-directory/*",
        ),
    ],
)
config = {
    "REGION": REGION,
    "GATEWAY_URL": state["gateway_url"],
    "KB_ID": state.get("kb_id", ""),
    "MEMORY_ID": state["memory_id"],
}
(ROOT / "config.json").write_text(json.dumps(config, indent=2))
stage = ROOT / "deployment"
stage.mkdir(exist_ok=True)
for name in ("main.py", "config.json", "requirements.txt"):
    shutil.copy2(ROOT / name, stage / name)
print(
    "Runtime files staged:", ", ".join(p.name for p in stage.iterdir() if p.is_file())
)
