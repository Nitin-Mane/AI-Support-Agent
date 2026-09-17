# Knowledge Base setup is blocked by sandbox permissions

The project's Environment Setup specifies an Amazon Bedrock Knowledge Base backed by OpenSearch Serverless.
On September 15, 2026, the selected Udacity sandbox rejected the first OpenSearch
security-policy creation call with `AccessDeniedException`:

> No identity-based policy allows the aoss:CreateSecurityPolicy action.

An OpenSearch collection inventory was also denied (`aoss:ListCollections`).
The alternative S3 Vectors inventory was denied (`s3vectors:ListVectorBuckets`).
No workaround that changes or bypasses the sandbox's access controls was attempted.

The separate RAG lesson uses S3 Vectors. On September 17, both vector-store
inventory calls were denied again, and the Bedrock Knowledge Base list was empty.
See `COURSE_REVIEW.md` and `evidence/course_permission_check.json`. The S3 Vectors
console denial is captured in `evidence/screenshots/08_aws_s3_vectors_permission.jpg`.

## Information for Udacity support

Course: Building Agents with Amazon Bedrock AgentCore and Strands SDK.
Project: AI Support Agent (cd14763).
Region: us-east-1.
Sandbox role: voclabs.

Please check that the lab policy enables the documented Knowledge Base setup:
OpenSearch Serverless security/data policies, collection creation, index access,
Bedrock Knowledge Base and data-source creation, ingestion and retrieval, and
the associated project-scoped IAM/S3 operations. The IAM role should be reviewed
by the sandbox administrator; this document does not prescribe an unrestricted policy.

## Resume after the sandbox is corrected

1. Refresh the sandbox credentials if they have expired.
2. Recreate the cleaned-up backend with `.venv\Scripts\python.exe scripts\provision.py bootstrap`,
   then run `.venv\Scripts\python.exe scripts\provision.py knowledge-base`.
3. Confirm ingestion completes and `config.json` contains a real `KB_ID`.
4. Run `scripts\prepare_runtime.py`, then redeploy from `deployment/`.
5. Repeat Test 3 and preserve the actual retrieval output.
6. Rebuild the submission archive only after checking its evidence checklist.

This message has been prepared locally. It has not been sent to Udacity.
