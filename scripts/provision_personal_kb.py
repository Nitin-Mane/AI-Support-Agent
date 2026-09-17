import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

ROOT = Path(__file__).resolve().parents[1]
REGION = "us-east-1"
PREFIX = "udacity-p02-rag"
STATE_PATH = ROOT / ".local/personal_kb_resources.json"
state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}

creds = json.loads((ROOT / ".local/personal_user_credentials.json").read_text())
session = boto3.Session(region_name=REGION, **creds)
identity = session.client("sts").get_caller_identity()
account = identity["Account"]
caller_arn = identity["Arn"]
print(f"Authenticated as {caller_arn} (Account {account})")

def save(key, value):
    state[key] = value
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))
    print(f"  [SAVED] {key}", flush=True)
    return value

def allow(actions, resources):
    return {"Effect": "Allow", "Action": actions, "Resource": resources}

def setup_kb():
    s3 = session.client("s3")
    iam = session.client("iam")
    aoss = session.client("opensearchserverless")
    bedrock = session.client("bedrock-agent")

    bucket = f"{PREFIX}-catalog-{account}"
    if "bucket" not in state:
        print("1. Creating S3 bucket...")
        try:
            s3.create_bucket(Bucket=bucket)
        except s3.exceptions.BucketAlreadyOwnedByYou:
            pass
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        save("bucket", bucket)
    
    if "catalog_uploaded" not in state:
        print("Uploading product_catalog.txt to S3...")
        s3.upload_file(str(ROOT / "product_catalog.txt"), state["bucket"], "product_catalog.txt")
        save("catalog_uploaded", True)

    role_name = f"{PREFIX}-role"
    if "kb_role" not in state:
        print("2. Creating KB IAM Role...")
        try:
            role_arn = iam.get_role(RoleName=role_name)["Role"]["Arn"]
        except iam.exceptions.NoSuchEntityException:
            role_arn = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"Service": "bedrock.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }]
                })
            )["Role"]["Arn"]
        
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=PREFIX,
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    allow(["bedrock:InvokeModel"], f"arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v2:0"),
                    allow(["s3:ListBucket"], f"arn:aws:s3:::{state['bucket']}"),
                    allow(["s3:GetObject"], f"arn:aws:s3:::{state['bucket']}/*"),
                    allow(["aoss:APIAccessAll"], f"arn:aws:aoss:{REGION}:{account}:collection/*"),
                ]
            })
        )
        save("kb_role", role_arn)
        time.sleep(10)

    # Index is already confirmed created
    save("index_ready", True)

    if "kb_id" not in state:
        print("5. Creating Bedrock Knowledge Base...")
        r = bedrock.create_knowledge_base(
            name="CustomerSupportKBP02",
            roleArn=state["kb_role"],
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

    while True:
        kb_info = bedrock.get_knowledge_base(knowledgeBaseId=state["kb_id"])["knowledgeBase"]
        kb_status = kb_info["status"]
        print(f"Knowledge Base Status: {kb_status}", flush=True)
        if kb_status == "ACTIVE":
            break
        if kb_status in ("FAILED", "DELETING"):
            raise RuntimeError(f"Knowledge Base failed: {kb_info}")
        time.sleep(10)

    if "data_source_id" not in state:
        print("6. Creating Bedrock Data Source...")
        r = bedrock.create_data_source(
            knowledgeBaseId=state["kb_id"],
            name="product-catalog",
            dataSourceConfiguration={
                "type": "S3",
                "s3Configuration": {"bucketArn": f"arn:aws:s3:::{state['bucket']}"},
            },
        )
        save("data_source_id", r["dataSource"]["dataSourceId"])

    if "ingestion_id" not in state:
        print("7. Starting Ingestion Sync Job...")
        r = bedrock.start_ingestion_job(
            knowledgeBaseId=state["kb_id"],
            dataSourceId=state["data_source_id"]
        )
        save("ingestion_id", r["ingestionJob"]["ingestionJobId"])

    while True:
        r = bedrock.get_ingestion_job(
            knowledgeBaseId=state["kb_id"],
            dataSourceId=state["data_source_id"],
            ingestionJobId=state["ingestion_id"],
        )["ingestionJob"]
        print("Ingestion Job Status:", r["status"], flush=True)
        if r["status"] == "COMPLETE":
            break
        if r["status"] in ("FAILED", "STOPPED"):
            raise RuntimeError(f"Ingestion failed: {r}")
        time.sleep(15)

    print("\nKnowledge Base setup is COMPLETE!")
    print(f"KB_ID: {state['kb_id']}")
    return state["kb_id"]

def teardown_kb():
    s3 = session.client("s3")
    iam = session.client("iam")
    aoss = session.client("opensearchserverless")
    bedrock = session.client("bedrock-agent")
    name = f"{PREFIX}-store"

    print("Beginning Teardown of Temporary RAG Resources...")
    if "kb_id" in state:
        try:
            print(f"Deleting Knowledge Base {state['kb_id']}...")
            bedrock.delete_knowledge_base(knowledgeBaseId=state["kb_id"])
        except Exception as e:
            print("KB deletion error:", e)

    if "collection_id" in state:
        try:
            print(f"Deleting Collection {state['collection_id']}...")
            aoss.delete_collection(id=state["collection_id"])
        except Exception as e:
            print("Collection deletion error:", e)

    for kind in ["encryption", "network", "data"]:
        try:
            if kind == "data":
                aoss.delete_access_policy(name=name, type=kind)
            else:
                aoss.delete_security_policy(name=name, type=kind)
            print(f"Deleted {kind} policy")
        except Exception as e:
            print(f"Delete policy {kind} error:", e)

    if "bucket" in state:
        try:
            print(f"Emptying and deleting S3 bucket {state['bucket']}...")
            resp = s3.list_objects_v2(Bucket=state["bucket"])
            for obj in resp.get("Contents", []):
                s3.delete_object(Bucket=state["bucket"], Key=obj["Key"])
            s3.delete_bucket(Bucket=state["bucket"])
            print("S3 bucket deleted")
        except Exception as e:
            print("S3 bucket deletion error:", e)

    role_name = f"{PREFIX}-role"
    try:
        iam.delete_role_policy(RoleName=role_name, PolicyName=PREFIX)
        iam.delete_role(RoleName=role_name)
        print("IAM role deleted")
    except Exception as e:
        print("IAM role deletion error:", e)

    try:
        user_name = "udacity-p02-rag-user"
        keys = iam.list_access_keys(UserName=user_name)["AccessKeyMetadata"]
        for k in keys:
            iam.delete_access_key(UserName=user_name, AccessKeyId=k["AccessKeyId"])
        iam.detach_user_policy(UserName=user_name, PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess")
        iam.delete_user(UserName=user_name)
        print("IAM user deleted")
    except Exception as e:
        print("IAM user delete error:", e)

    try:
        iam.delete_role_policy(RoleName="udacity-p02-rag-deployer-role", PolicyName="udacity-p02-rag")
    except Exception:
        pass
    try:
        iam.detach_role_policy(RoleName="udacity-p02-rag-deployer-role", PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess")
        iam.delete_role(RoleName="udacity-p02-rag-deployer-role")
    except Exception:
        pass

    state["cleaned_up_at"] = time.time()
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))
    print("Teardown COMPLETE!")

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "setup"
    if action == "setup":
        setup_kb()
    elif action == "teardown":
        teardown_kb()
