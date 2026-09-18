# Customer Support Assistant

Udacity Assignment 02: a support assistant built with Strands and Amazon Bedrock
AgentCore. It tracks orders, processes refunds, retrieves catalog policies,
remembers customer preferences, calculates loyalty discounts, and reads a live
website through the Browser tool.

## Submission files

| File | Purpose |
| --- | --- |
| [main.py](main.py) | Completed runtime entrypoint, tools, memory hooks, and error handling |
| [config.json](config.json) | AWS configuration template |
| [requirements.txt](requirements.txt) | Runtime dependencies |
| [product_catalog.txt](product_catalog.txt) | Catalog and policy content for the Knowledge Base |
| [lambda/order_tracker.py](lambda/order_tracker.py) | Starter order-tracking Lambda |
| [lambda/refund_processor.py](lambda/refund_processor.py) | Starter refund Lambda |
| [lambda/lambda_schema](lambda/lambda_schema) | Refund tool schema for the Gateway |
| [REFLECTION.md](REFLECTION.md) | Design decision, testing challenge, and production consideration |

## Test results

All six required scenarios passed on September 18, 2026, India time
(September 17 in the UTC records). These are saved results from one deployed
runtime in `us-east-1`; the JSON files include the requests, responses, and
tool conversations.

| Test | Result | Output | Screenshot |
| --- | --- | --- | --- |
| 1. Order tracking | UPS, TRK987654321, SHIPPED | [Order](submission/outputs/order.json) | [Panel](submission/screenshots/01_order.jpg) |
| 2. Refund | API and Lambda tools returned valid JSON; APPROVED, $139.99, 3-5 business days | [Refund](submission/outputs/refund.json) | [Panel](submission/screenshots/02_refund.jpg) |
| 3. RAG | Platinum benefits: free same-day shipping, 15% discount, priority support | [RAG](submission/outputs/rag.json) | [Panel](submission/screenshots/03_rag.jpg) |
| 4. Memory | Jane and her preference for concise replies recalled in a new session | [Session A](submission/outputs/memory_a.json), [Session B](submission/outputs/memory_b.json) | [A](submission/screenshots/04_memory_a.jpg), [B](submission/screenshots/04_memory_b.jpg) |
| 5. Discount | 4,000 points redeemed, 10% Gold discount, $99 total, 349 points remaining | [Calculation](submission/outputs/discount.json) | [Panel](submission/screenshots/05_discount.jpg) |
| 6. Browser | Live Udacity page title retrieved | [Browser](submission/outputs/browser.json) | [Panel](submission/screenshots/06_browser.jpg) |

The outcome screenshots show saved runtime responses without a cursor.
The [runtime screenshot](submission/screenshots/runtime_ready.jpg) is an AWS
console crop. The [uploaded-source check](submission/outputs/source_verification.json)
confirms that the deployed `main.py` matches this repository.

Actual `agentcore invoke` output is included for
[order tracking](submission/outputs/agentcore_invoke.txt) and
[RAG](submission/outputs/agentcore_rag.txt), with
[order command metadata](submission/outputs/agentcore_invoke.json) and
[RAG command metadata](submission/outputs/agentcore_rag.json). Both commands
completed with exit code 0.

### Reviewer corrections

- [Missing Knowledge Base](submission/outputs/rag_guard.json): an empty `KB_ID`
  returns a descriptive configuration message.
- [Unavailable Gateway](submission/outputs/gateway_failure.json): a closed test
  endpoint returns retry instructions and administrator guidance.
- [Runtime logs](submission/outputs/runtime_logs.json): Gateway discovery,
  connection failures, and memory event persistence are recorded.

Memory indexing was asynchronous: the
[initial recall](submission/outputs/memory_b_initial.json) did not find the
customer context; the later session succeeded. The browser recovered from one
invalid session name before reading the title. Both are retained in the records.

## Setup

Use Python 3.13 and install `requirements.txt`. Follow the course Environment
Setup to create the Lambda functions, REST API, MCP Gateway, Knowledge Base,
and AgentCore Memory in `us-east-1`. Sync `product_catalog.txt` to the Knowledge
Base. Fill in the Gateway URL, Knowledge Base ID, and generated Memory ID in
`config.json` before deployment.

Install the deployment CLI with
`pip install bedrock-agentcore-starter-toolkit==0.3.12`, then run
`agentcore configure --entrypoint main.py` and `agentcore deploy` using the
course settings and an execution role with access to the configured services.
For Test 4, use the same customer ID and different session IDs, allowing time
for memory extraction and indexing between requests.

The course specifies the Udacity sandbox. Its `aoss:CreateSecurityPolicy`
permission was denied, so the complete test run used the authorized personal
AWS account. This differs from the sandbox setup instruction; no sandbox IAM
permissions were changed. All temporary test resources were removed, with
[20 absence checks](submission/outputs/cleanup_verification.json). The blank
configuration requires new resources before redeployment.

Udacity re-review is pending; this revision has not been uploaded to the portal.
