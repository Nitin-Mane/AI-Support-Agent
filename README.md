# Customer Support Assistant

[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](requirements.txt) [![Amazon Bedrock AgentCore](https://img.shields.io/badge/AWS-Bedrock%20AgentCore-FF9900)](#architecture) [![Recorded live tests: 6/6](https://img.shields.io/badge/Recorded%20live%20tests-6%2F6%20passed-2E7D32)](#test-results) [![MIT License](https://img.shields.io/badge/License-MIT-2563EB)](LICENSE)

A customer support assistant for Udacity Assignment 02, built with Python,
Strands, and Amazon Bedrock AgentCore. One conversation can track an order,
process a refund, retrieve catalog policies, remember customer preferences,
calculate loyalty discounts, or read a live website.

## About

The project connects a conversational assistant to the backend services needed
for common support requests. Each integration has a defined role: the Gateway
handles order and refund tools, the Knowledge Base supplies policy facts, memory
hooks recover customer context, and Code Interpreter performs the arithmetic.

The implementation pays particular attention to the final customer response.
Calculated values are preserved, missing configuration produces a useful message,
and Gateway failures return recovery guidance with details in the runtime logs.

## Documentation

| Guide | Contents |
| --- | --- |
| [AWS architecture](AWS_ARCHITECTURE.md) | Service roles, system diagram, request flow, RAG, memory, configuration, and deployment considerations |
| [Test evidence](TEST_EVIDENCE.md) | Screenshots, conversation records, reviewer corrections, and rubric coverage |
| [Engineering reflection](REFLECTION.md) | Design decision, live-testing challenge, and production consideration |

## Architecture

AgentCore Runtime hosts the asynchronous Strands application with Amazon Nova
2 Lite. Its MCP Gateway exposes an API Gateway order target and a direct refund
Lambda target. Bedrock Knowledge Base retrieval uses a catalog in S3 and an
OpenSearch Serverless vector index. AgentCore Memory, Code Interpreter, and
Browser supply the remaining capabilities.

See the [AWS guide](AWS_ARCHITECTURE.md#system-design) for the architecture diagram
and integration details.

## Project status

The required implementation and all six live scenarios were completed on
September 18, 2026, India time. The two reviewer corrections were also verified
on the deployed runtime. Udacity re-review remains pending; the revised package
has not been uploaded to the portal.

Test resources were removed after evidence capture. This repository contains
recorded results and a blank configuration template, so new resources are needed
before redeployment. The test badge represents that completed run.

## Repository contents

| Resource | Purpose |
| --- | --- |
| [main.py](main.py) | Runtime entrypoint, tools, memory hooks, and response validation |
| [config.json](config.json) | Region, Gateway URL, Knowledge Base ID, and Memory ID template |
| [requirements.txt](requirements.txt) | Pinned runtime dependencies |
| [product_catalog.txt](product_catalog.txt) | Catalog and policy source for the Knowledge Base |
| [Order Lambda](lambda/order_tracker.py), [refund Lambda](lambda/refund_processor.py) | Unchanged course-provided backend fixtures |
| [Gateway schema](lambda/lambda_schema) | Tool definitions for the direct refund target |
| [Evidence guide](TEST_EVIDENCE.md) | Required screenshots and full test records |

## Getting started

Use Python 3.13 and complete the course Environment Setup in `us-east-1`.

```powershell
git clone https://github.com/Nitin-Mane/AI-Support-Agent.git
cd AI-Support-Agent
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install bedrock-agentcore-starter-toolkit==0.3.12
```

Sync the catalog, fill in `config.json`, and use the Python starter toolkit to
configure and deploy `main.py`. The [AWS guide](AWS_ARCHITECTURE.md#configuration-and-deployment)
explains configuration and resource permissions. Follow the course commands for
the six tests and retain both sessions for the memory test.

## Test results

| Scenario | Recorded outcome |
| --- | --- |
| Order tracking | SHIPPED, UPS, TRK987654321 |
| Refund | Valid API/Lambda responses, APPROVED, $139.99 |
| Knowledge retrieval | Platinum same-day shipping, 15% discount, priority support |
| Cross-session memory | Jane and her preference for concise responses recalled |
| Loyalty calculation | 4,000 points redeemed, $99 total, 349 points remaining |
| Browser | Live Udacity page title retrieved |

The [evidence guide](TEST_EVIDENCE.md) embeds every required outcome panel and
links the original conversations, CLI output, and failure checks. The full run
used the authorized personal AWS account after sandbox permissions blocked
vector-store provisioning; the [AWS guide](AWS_ARCHITECTURE.md#account-choice-cleanup-and-production)
records that account choice and the cleanup.

## License

Licensed under the [MIT License](LICENSE). This is a coursework implementation
using starter fixtures; production controls are discussed in the architecture
guide and reflection.
