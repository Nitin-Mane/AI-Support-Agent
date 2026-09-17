# RAG and web-search course review

Reviewed in the enrolled Udacity classroom on September 17, 2026.
Seven lesson pages were read, including their visible Python examples.
Reference captures with their exact source URLs are stored locally in
`assignment/course_lessons/`; these course copies are excluded from the submission ZIP.

## What applies to this project

| Course example | Project implementation and decision |
|---|---|
| A Strands `@tool` wraps `bedrock-agent-runtime.retrieve()` and joins retrieved text chunks. | `main.py:search_knowledge_base` follows this pattern, includes a usage docstring, handles absent configuration and empty results, and is registered in the agent's tools. |
| Policy questions must use retrieved material. | The support system prompt directs catalog, policy and loyalty questions to the Knowledge Base. The response guard prevents an unconfigured KB from becoming an invented policy answer. Live retrieval remains unverified. |
| RAG exercise creates a Bedrock Knowledge Base using Titan Text Embeddings v2 and S3 Vectors. | The **project Environment Setup** instead specifies an automatically created OpenSearch Serverless store. Keep that project setup as the deployment baseline. Either store still sits behind Bedrock Retrieve; replacing Retrieve with local text search would not meet the rubric. |
| KB ingestion must be synced; use the Knowledge Base ID rather than its ARN or data-source ID. | Provisioning waits for ingestion and writes the KB ID to configuration. That stage has not completed because the sandbox denied OpenSearch setup. |
| Runtime role needs `bedrock:Retrieve`. | The runtime deployment policy includes retrieval access. This does not grant the sandbox's provisioning role permission to create its vector store. |
| Browser is constructed inside each invocation and its `.browser` tool is registered. | `invoke` already instantiates `AgentCoreBrowser(region=REGION)` per request and passes `agent_core_browser.browser` to Strands. The recorded test includes successful navigation and title extraction. |
| Browser exercise uses `session_timeout=600` and a Wikivoyage-focused prompt. | These are useful choices for that travel exercise. The project currently uses the SDK timeout default and the project-requested Udacity URL. A shorter timeout can be adopted and retested in a future deployment. A prompt restriction alone should not be treated as enforced network access control. |
| General web-search lesson discusses search APIs, result snippets and citations. | A search-engine API is a separate capability from browsing. The assignment asks for AgentCore Browser evidence, so no external search provider or unrelated API key was added. |
| Agentic RAG can inspect inadequate results and reformulate a query. | The Strands agent can select the retrieval tool during its reasoning loop. There is no separately implemented relevance scorer or guaranteed retry policy; the package makes no claim that those advanced behaviors were tested. |

The lesson's WanderBot examples use `payload['message']`, travel documents and
container deployment. The support-agent starter uses `prompt`, a product catalog,
Gateway and Memory alongside its local tools. Copying the lesson's entire entrypoint
would remove required project behavior. The existing async support entrypoint is retained.

## Remaining RAG blocker

A fresh check of sandbox account `090165623118` in `us-east-1` at
`2026-09-17T01:59:38Z` returned:

- `s3vectors:ListVectorBuckets`: AccessDeniedException.
- `aoss:ListCollections`: AccessDeniedException.
- Bedrock Knowledge Base listing: allowed, with no Knowledge Bases returned.

See `evidence/course_permission_check.json` for the service responses and
`evidence/screenshots/08_aws_s3_vectors_permission.jpg` for the actual console panel.
Listing denial does not prove every create action is denied. The earlier OpenSearch
`CreateSecurityPolicy` denial is the direct evidence that the project's provisioning
path is blocked. No permission boundary was modified and no new cloud resources
were created during this review.

The S3 Vectors lesson therefore does not establish a working alternative in this
sandbox. Udacity needs to correct the lab permissions or supply an authorized KB.
After that, provision and sync the catalog, regenerate configuration, redeploy and
run the actual Platinum-benefits query before marking Test 3 passed.

## Lesson sources

- [RAG demonstration](https://learn.udacity.com/nd905?version=1.2.15&partKey=cd14763&lessonKey=a3886441-9fb9-4d38-84bf-2613b46e41e0&conceptKey=f17ef012-8a8f-4e2c-87a7-aa675a852c44)
- [RAG exercise](https://learn.udacity.com/nd905?version=1.2.15&partKey=cd14763&lessonKey=a3886441-9fb9-4d38-84bf-2613b46e41e0&conceptKey=013778a0-cd95-47d5-b223-cc203150e261)
- [RAG solution](https://learn.udacity.com/nd905?version=1.2.15&partKey=cd14763&lessonKey=a3886441-9fb9-4d38-84bf-2613b46e41e0&conceptKey=f7280e43-26e8-4baa-84c9-771d1f920b80)
- [Browser exercise](https://learn.udacity.com/nd905?version=1.2.15&partKey=cd14763&lessonKey=335de13d-b374-4a8d-b607-0165e16304f6&conceptKey=381fe27f-0f97-416f-b68a-38c5248a5b11)
- [Browser solution](https://learn.udacity.com/nd905?version=1.2.15&partKey=cd14763&lessonKey=335de13d-b374-4a8d-b607-0165e16304f6&conceptKey=591b39c5-f752-4067-8d9a-e55b60f13a6e)
- [Web Search Agents](https://learn.udacity.com/nd905?version=1.2.15&partKey=cd14763&lessonKey=ls15049&conceptKey=71a56c5a-738a-41a5-b14e-79c54aee72b6)
- [Agentic RAG](https://learn.udacity.com/nd905?version=1.2.15&partKey=cd14763&lessonKey=ls15053&conceptKey=4972c534-d05f-42b4-9fde-4ecb7ae4787a)

Optional future improvements from the exercise include an explicit retrieval limit
and returning each chunk's S3 source URI. They are not required by this rubric and
have not been added to the previously tested source during this evidence review.
