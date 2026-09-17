"""Create the course infrastructure in the explicitly selected Udacity sandbox.

Writes identifiers after each creation so interrupted setup can be resumed.
Credentials must be in .local/sandbox_credentials.json; they are never packaged.
"""

import io
import json
import sys
import time
import zipfile
from pathlib import Path

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

ROOT = Path(__file__).resolve().parents[1]
REGION = "us-east-1"
PREFIX = "udacity-p02"
STATE_PATH = ROOT / ".local/resources.json"
state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
if state.get("cleaned_up_at"):
    state = {}
session = boto3.Session(
    region_name=REGION,
    **json.loads((ROOT / ".local/sandbox_credentials.json").read_text()),
)
identity = session.client("sts").get_caller_identity()
account = identity["Account"]
if account != "090165623118":
    raise RuntimeError("Refusing to provision outside the selected Udacity sandbox.")


def save(key, value):
    state[key] = value
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))
    print("Saved", key, flush=True)
    return value


def role(label, principal, statements):
    iam = session.client("iam")
    name = PREFIX + "-" + label
    try:
        arn = iam.get_role(RoleName=name)["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        arn = iam.create_role(
            RoleName=name,
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": principal},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
        )["Role"]["Arn"]
    iam.put_role_policy(
        RoleName=name,
        PolicyName=PREFIX,
        PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": statements}),
    )
    return save(label + "_role", arn)


def allow(actions, resources):
    return {"Effect": "Allow", "Action": actions, "Resource": resources}


def bootstrap():
    log_arn = f"arn:aws:logs:{REGION}:{account}:*"
    lambda_role = role(
        "lambda",
        "lambda.amazonaws.com",
        [
            allow(
                ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                log_arn,
            )
        ],
    )
    time.sleep(10)
    client = session.client("lambda")
    for label in ("order-tracker", "refund-processor"):
        key = label.replace("-", "_")
        if key in state:
            continue
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.write(ROOT / "lambda" / f"{key}.py", f"{key}.py")
        result = client.create_function(
            FunctionName=PREFIX + "-" + label,
            Runtime="python3.12",
            Role=lambda_role,
            Handler=key + ".lambda_handler",
            Code={"ZipFile": buffer.getvalue()},
            Timeout=30,
            MemorySize=128,
            Tags={"Project": PREFIX},
        )
        save(key, result["FunctionArn"])
        client.get_waiter("function_active_v2").wait(FunctionName=result["FunctionArn"])
    api = session.client("apigateway")
    if "api_id" not in state:
        save(
            "api_id",
            api.create_rest_api(
                name=PREFIX + "-orders", endpointConfiguration={"types": ["REGIONAL"]}
            )["id"],
        )
    api_id = state["api_id"]
    if "api_ready" not in state:
        root = next(
            x["id"]
            for x in api.get_resources(restApiId=api_id)["items"]
            if x["path"] == "/"
        )
        resources = {"/": root}
        for path in (
            "/orders",
            "/orders/{order_id}",
            "/customers",
            "/customers/{customer_id}",
            "/customers/{customer_id}/orders",
        ):
            parent, part = path.rsplit("/", 1)
            resources[path] = api.create_resource(
                restApiId=api_id, parentId=resources[parent or "/"], pathPart=part
            )["id"]
        for path, operation in [
            ("/orders/{order_id}", "get_order"),
            ("/customers/{customer_id}/orders", "get_customer_orders"),
            ("/customers/{customer_id}", "get_customer"),
        ]:
            rid = resources[path]
            parameter = "order_id" if "order_id" in path else "customer_id"
            api.put_method(
                restApiId=api_id,
                resourceId=rid,
                httpMethod="GET",
                authorizationType="NONE",
                operationName=operation,
                requestParameters={"method.request.path." + parameter: True},
            )
            api.put_method_response(
                restApiId=api_id,
                resourceId=rid,
                httpMethod="GET",
                statusCode="200",
                responseModels={"application/json": "Empty"},
            )
            api.put_integration(
                restApiId=api_id,
                resourceId=rid,
                httpMethod="GET",
                type="AWS_PROXY",
                integrationHttpMethod="POST",
                uri=f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{state['order_tracker']}/invocations",
            )
        client.add_permission(
            FunctionName=state["order_tracker"],
            StatementId=PREFIX + "-api",
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=f"arn:aws:execute-api:{REGION}:{account}:{api_id}/*/GET/*",
        )
        api.create_deployment(restApiId=api_id, stageName="prod")
        save("api_ready", True)
    gateway_role = role(
        "gateway",
        "bedrock-agentcore.amazonaws.com",
        [
            allow(["lambda:InvokeFunction"], state["refund_processor"]),
            allow(
                ["execute-api:Invoke"],
                f"arn:aws:execute-api:{REGION}:{account}:{api_id}/prod/GET/*",
            ),
            allow(
                ["apigateway:GET"], f"arn:aws:apigateway:{REGION}::/restapis/{api_id}/*"
            ),
        ],
    )
    control = session.client("bedrock-agentcore-control")
    if "memory_id" not in state:
        r = control.create_memory(
            name="CustomerSupportMemoryP02",
            eventExpiryDuration=7,
            memoryStrategies=[
                {
                    "semanticMemoryStrategy": {
                        "name": "customer_facts",
                        "namespaces": ["cs_agent/{actorId}/facts"],
                    }
                },
                {
                    "userPreferenceMemoryStrategy": {
                        "name": "customer_preferences",
                        "namespaces": ["cs_agent/{actorId}/preferences"],
                    }
                },
            ],
        )
        save("memory_id", r["memory"]["id"])
    if "gateway_id" not in state:
        time.sleep(10)
        r = control.create_gateway(
            name="CustomerSupportGatewayP02",
            roleArn=gateway_role,
            protocolType="MCP",
            authorizerType="NONE",
        )
        save("gateway_id", r["gatewayId"])
        save("gateway_url", r["gatewayUrl"])
    for _ in range(30):
        r = control.get_gateway(gatewayIdentifier=state["gateway_id"])
        if r["status"] == "READY":
            break
        time.sleep(5)
    if "refund_target" not in state:
        r = control.create_gateway_target(
            gatewayIdentifier=state["gateway_id"],
            name="refund-processor",
            targetConfiguration={
                "mcp": {
                    "lambda": {
                        "lambdaArn": state["refund_processor"],
                        "toolSchema": {
                            "inlinePayload": json.loads(
                                (ROOT / "lambda/lambda_schema").read_text()
                            )
                        },
                    }
                }
            },
            credentialProviderConfigurations=[
                {"credentialProviderType": "GATEWAY_IAM_ROLE"}
            ],
        )
        save("refund_target", r["targetId"])
    if "order_target" not in state:
        paths = [
            ("/orders/{order_id}", "get_order"),
            ("/customers/{customer_id}/orders", "get_customer_orders"),
            ("/customers/{customer_id}", "get_customer"),
        ]
        r = control.create_gateway_target(
            gatewayIdentifier=state["gateway_id"],
            name="order-tracker",
            targetConfiguration={
                "mcp": {
                    "apiGateway": {
                        "restApiId": api_id,
                        "stage": "prod",
                        "apiGatewayToolConfiguration": {
                            "toolFilters": [
                                {"filterPath": p, "methods": ["GET"]} for p, _ in paths
                            ],
                            "toolOverrides": [
                                {
                                    "path": p,
                                    "method": "GET",
                                    "name": n,
                                    "description": n.replace("_", " "),
                                }
                                for p, n in paths
                            ],
                        },
                    }
                }
            },
            credentialProviderConfigurations=[
                {"credentialProviderType": "GATEWAY_IAM_ROLE"}
            ],
        )
        save("order_target", r["targetId"])


def knowledge_base():
    s3 = session.client("s3")
    bucket = PREFIX + "-catalog-" + account
    if "bucket" not in state:
        s3.create_bucket(Bucket=bucket)
        save("bucket", bucket)
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
    s3.upload_file(str(ROOT / "product_catalog.txt"), bucket, "product_catalog.txt")
    kb_role = role(
        "knowledge-base",
        "bedrock.amazonaws.com",
        [
            allow(
                ["bedrock:InvokeModel"],
                f"arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v2:0",
            ),
            allow(["s3:ListBucket"], f"arn:aws:s3:::{bucket}"),
            allow(["s3:GetObject"], f"arn:aws:s3:::{bucket}/*"),
            allow(
                ["aoss:APIAccessAll"], f"arn:aws:aoss:{REGION}:{account}:collection/*"
            ),
        ],
    )
    aoss = session.client("opensearchserverless")
    name = PREFIX + "-kb"
    if "collection_id" not in state:
        for kind, policy in [
            (
                "encryption",
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": ["collection/" + name],
                        }
                    ],
                    "AWSOwnedKey": True,
                },
            ),
            (
                "network",
                [
                    {
                        "Rules": [
                            {
                                "ResourceType": "collection",
                                "Resource": ["collection/" + name],
                            }
                        ],
                        "AllowFromPublic": True,
                    }
                ],
            ),
        ]:
            try:
                aoss.create_security_policy(
                    name=name, type=kind, policy=json.dumps(policy)
                )
            except aoss.exceptions.ConflictException:
                pass
        principal = identity["Arn"]
        if ":assumed-role/" in principal:
            principal = (
                f"arn:aws:iam::{account}:role/"
                + principal.split(":assumed-role/")[1].rsplit("/", 1)[0]
            )
        try:
            aoss.create_access_policy(
                name=name,
                type="data",
                policy=json.dumps(
                    [
                        {
                            "Rules": [
                                {
                                    "ResourceType": "collection",
                                    "Resource": ["collection/" + name],
                                    "Permission": ["aoss:DescribeCollectionItems"],
                                },
                                {
                                    "ResourceType": "index",
                                    "Resource": ["index/" + name + "/*"],
                                    "Permission": [
                                        "aoss:CreateIndex",
                                        "aoss:DescribeIndex",
                                        "aoss:ReadDocument",
                                        "aoss:WriteDocument",
                                        "aoss:UpdateIndex",
                                    ],
                                },
                            ],
                            "Principal": [kb_role, principal],
                        }
                    ]
                ),
            )
        except aoss.exceptions.ConflictException:
            pass
        r = aoss.create_collection(
            name=name, type="VECTORSEARCH", standbyReplicas="DISABLED"
        )
        save("collection_id", r["createCollectionDetail"]["id"])
    while True:
        detail = aoss.batch_get_collection(ids=[state["collection_id"]])[
            "collectionDetails"
        ][0]
        print("Collection:", detail["status"], flush=True)
        if detail["status"] == "ACTIVE":
            break
        if detail["status"] == "FAILED":
            raise RuntimeError(str(detail))
        time.sleep(20)
    save("collection_arn", detail["arn"])
    endpoint = detail["collectionEndpoint"]
    if "index_ready" not in state:
        payload = {
            "settings": {"index.knn": True},
            "mappings": {
                "properties": {
                    "vector": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "engine": "faiss",
                            "space_type": "l2",
                        },
                    },
                    "text": {"type": "text"},
                    "metadata": {"type": "text", "index": False},
                }
            },
        }
        for attempt in range(20):
            request = AWSRequest(
                method="PUT",
                url=endpoint + "/catalog",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            SigV4Auth(
                session.get_credentials().get_frozen_credentials(), "aoss", REGION
            ).add_auth(request)
            response = requests.put(
                request.url,
                data=request.body,
                headers=dict(request.headers),
                timeout=30,
            )
            if response.ok or "resource_already_exists_exception" in response.text:
                break
            print(
                "Index waiting for policy propagation:",
                response.status_code,
                flush=True,
            )
            time.sleep(15)
        else:
            raise RuntimeError("Index creation failed: " + response.text)
        save("index_ready", True)
        time.sleep(30)
    bedrock = session.client("bedrock-agent")
    if "kb_id" not in state:
        r = bedrock.create_knowledge_base(
            name="CustomerSupportKBP02",
            roleArn=kb_role,
            knowledgeBaseConfiguration={
                "type": "VECTOR",
                "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": f"arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v2:0"
                },
            },
            storageConfiguration={
                "type": "OPENSEARCH_SERVERLESS",
                "opensearchServerlessConfiguration": {
                    "collectionArn": state["collection_arn"],
                    "vectorIndexName": "catalog",
                    "fieldMapping": {
                        "vectorField": "vector",
                        "textField": "text",
                        "metadataField": "metadata",
                    },
                },
            },
        )
        save("kb_id", r["knowledgeBase"]["knowledgeBaseId"])
    if "data_source_id" not in state:
        r = bedrock.create_data_source(
            knowledgeBaseId=state["kb_id"],
            name="product-catalog",
            dataSourceConfiguration={
                "type": "S3",
                "s3Configuration": {"bucketArn": f"arn:aws:s3:::{bucket}"},
            },
        )
        save("data_source_id", r["dataSource"]["dataSourceId"])
    if "ingestion_id" not in state:
        r = bedrock.start_ingestion_job(
            knowledgeBaseId=state["kb_id"], dataSourceId=state["data_source_id"]
        )
        save("ingestion_id", r["ingestionJob"]["ingestionJobId"])
    while True:
        r = bedrock.get_ingestion_job(
            knowledgeBaseId=state["kb_id"],
            dataSourceId=state["data_source_id"],
            ingestionJobId=state["ingestion_id"],
        )["ingestionJob"]
        print("Ingestion:", r["status"], flush=True)
        if r["status"] == "COMPLETE":
            break
        if r["status"] in ("FAILED", "STOPPED"):
            raise RuntimeError(str(r))
        time.sleep(15)
    (ROOT / "config.json").write_text(
        json.dumps(
            {
                "REGION": REGION,
                "GATEWAY_URL": state["gateway_url"],
                "KB_ID": state["kb_id"],
                "MEMORY_ID": state["memory_id"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    {"bootstrap": bootstrap, "knowledge-base": knowledge_base}[sys.argv[1]]()
