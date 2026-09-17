# Udacity rubric and reviewer recheck

Checked against the live classroom rubric, Environment Setup, Instructions, and
the review of submission **4823700** on September 17, with the live rubric checked again on September 18, 2026.
The classroom still reports two specifications requiring changes. This document
maps the revised work to those requests; it does not claim a new Udacity grade.

## Reviewer changes

| Requested correction | Revised implementation | Measured evidence |
| --- | --- | --- |
| Missing or blank `KB_ID` must return a descriptive message | `search_knowledge_base` checks missing, empty and whitespace-only values before calling AWS | [Local checks](../examples/revision/failure_checks.json); [deployed empty-KB response](../examples/cloud_final/rag_guard.json) |
| Gateway failures must be logged and give a useful, safe reply | `invoke` catches connection/discovery failures, logs diagnostics, returns `GATEWAY_UNAVAILABLE`, and keeps the transport active throughout successful tool use | [Deployed dummy-URL test](../examples/cloud_final/gateway_failure.json); [CloudWatch logs](../examples/cloud_final/runtime_logs.json) |
| Gateway test responses must be well formed | Successful API order lookup and Lambda refund results are nonempty JSON; the Lambda proxy body also parses as JSON | [Fresh refund trace](../examples/cloud_final/refund.json); [response audit](../examples/cloud_final/verification.json) |

## Every rubric criterion

### 1. Cloud runtime

- `BedrockAgentCoreApp` is created at module level.
- `invoke` is asynchronous and decorated with `@app.entrypoint`.
- The executable entry point calls `app.run()`.
- The fresh `agentcore invoke` order command and its terminal output are in
  [agentcore_invoke.txt](../examples/cloud_final/agentcore_invoke.txt), with
  timestamp, runtime ARN, source hash and exit code in
  [agentcore_invoke.json](../examples/cloud_final/agentcore_invoke.json).

The CLI check and all six positive scenarios use the same complete personal-account
runtime, `udacity_support_p02_rag_final-J3LfIlBY56`, version 1. The uploaded source
hash matches current `main.py`. Versions 2 and 3 are intentional configuration
failure tests; version 4 restores the valid configuration before cleanup.

### 2. MCP Gateway

- `MCPClient` connects using Streamable HTTP.
- `invoke` discovers tools with `list_tools_sync()` and adds them to the agent.
- The MCP transport remains open while the agent invokes those tools.
- The fresh refund trace includes successful `order-tracker___get_order`
  from the API target and `refund-processor___initiate_refund` from Lambda.
- Their outputs are valid, nonempty JSON and not error results.
- Successful discovery and the intentional connection failure are logged.

Evidence: [refund.json](../examples/cloud_final/refund.json),
[verification.json](../examples/cloud_final/verification.json), and
[runtime_logs.json](../examples/cloud_final/runtime_logs.json).
The deliberate dummy-Gateway error is kept in a separate negative-test record.

### 3. Knowledge Base RAG

- `search_knowledge_base` uses the `@tool` decorator.
- Its docstring explains when the agent should use it.
- It checks configuration before attempting retrieval.
- It calls the Bedrock Retrieve API.
- It joins retrieved text chunks into one formatted string.
- Local tests cover missing settings, successful retrieval, and empty results;
  the deployed missing-setting check returns the required configuration message.

**Successful deployed RAG is verified:** Instructions Test 3 returned free
same-day shipping, a 15% discount and priority customer support from the catalog.
[rag.json](../examples/cloud_final/rag.json) identifies the actual AgentCore
Runtime and includes its request, tool messages, response and source hash.
[agentcore_rag.txt](../examples/cloud_final/agentcore_rag.txt) provides successful
CLI output. The catalog ingestion completed without failed documents.

The sandbox permission denial was not bypassed. The user-authorized personal
account was used for all six final scenarios. A separate provisioning signing
issue was corrected by including the required payload-hash header;
[provisioning diagnostics](../examples/cloud_final/provisioning_diagnostics.json)
and the reusable [index helper](../scripts/create_catalog_index.py) document it.

### 4. Cross-session memory

- `get_namespaces` reads strategy types and supports `namespaceTemplates` and
  the legacy `namespaces` field.
- `MemoryHook` extends `HookProvider` and registers callbacks.
- Retrieval searches every strategy namespace, tags returned memories by type,
  and prepends them to the user message.
- Persistence extracts the user query and assistant response and calls
  `memory_client.create_event()`.
- Fresh sessions A and B use the same customer ID and distinct runtime session
  IDs. Session B recalls Jane and her concise-response preference after the
  extracted records become retrievable.

Evidence: [memory_a.json](../examples/cloud_final/memory_a.json) and
[memory_b.json](../examples/cloud_final/memory_b.json).
An early unsuccessful recall is preserved in `memory_b_initial.json`.

### 5. Code Interpreter

- `calculate_loyalty_discount` uses `@tool`.
- The generated self-contained Python code implements redemption, tier rates
  and earnings with decimal arithmetic.
- Execution uses `code_session(REGION).invoke("executeCode", ...)` with
  `clearContext=True`.
- Interpreter failure returns a tier-only calculation with points unchanged.
- Results include `points_redeemed`, `tier_discount_pct`, `final_total` and
  `remaining_points`.

Evidence: [discount.json](../examples/cloud_final/discount.json) records
actual Code Interpreter execution: 4,000 points redeemed, 10% Gold tier rate,
$99 final total and 349 points remaining. The local suite covers the fallback.

### 6. Browser

- `AgentCoreBrowser` is instantiated with the AWS region.
- Its browser tool is added to the agent.
- The fresh trace shows navigation to the requested Udacity website and a title
  read from the live page. It recovered from one session-name validation error.

Evidence: [browser.json](../examples/cloud_final/browser.json).
The Instructions page's command requests Udacity, although its expected-result
sentence says Amazon.com. The command is followed, and the actual title is
recorded without substituting a title from a different website.

### 7. Reflection

- [REFLECTION.md](../REFLECTION.md) contains 290 body words (excluding headings), within 200-400.
- It explains choosing Code Interpreter for loyalty calculations.
- It describes observed arithmetic drift and the response enforcement fix.
- It discusses authentication, authorization, refund idempotency and memory
  retention as production considerations.

The reviewer accepted this criterion. Word count and structural checks are in
[rubric_recheck.json](../examples/cloud_final/rubric_recheck.json).

## Instruction and setup checklist

- [x] Tasks 1-6: app, clients, namespace helper, memory hooks, RAG tool, calculator
  and entry point implemented. No `pass` statements remain in `main.py`.
- [x] Task 8: reflection included.
- [x] Starter Lambda files retained without modification.
- [x] Fresh order, refund, memory, discount and browser outputs included.
- [x] Both reviewer corrections tested in the cloud.
- [x] Fresh CLI invocation evidence included.
- [x] Outcome screenshots captured without a cursor.
- [x] Task 7: all six required scenarios passed through the complete deployed agent.
- [x] All four configuration values were present in the actual uploaded deployment,
  including a synced Knowledge Base. See `uploaded_config` in
  [source_verification.json](../examples/cloud_final/source_verification.json).
  The packaged configuration remains a template because resources were deleted
  after testing; historical IDs must not be reused.
- [ ] Revised project submitted and accepted by Udacity.

The required region is `us-east-1`. The September 17 run used the Udacity sandbox;
the complete September 18 run used the expressly authorized personal account
`166977155856` after sandbox vector-store permissions were denied. This is a
disclosed deviation from the classroom's sandbox setup instruction. No sandbox
IAM policies were changed.

Structured Pydantic validation is already implemented for discount output.
Conversation summarization and domain personalization are optional suggestions,
not missing grading requirements.

## Verification and files to submit

Run `python -m pytest tests -q` for local behavior checks and
`python scripts/verify_cloud_revision.py` to audit the saved fresh cloud records.
The latter reads evidence files; it does not perform new AWS invocations.

The revision ZIP includes the implementation, configuration template, dependency
files, original Lambda functions and schema, catalog, reflection, this checklist,
test records and screenshots. Credential files, deployment scratch directories
and virtual environments are excluded. Do not describe the package as fully
verified from the local suite alone. The separate cloud audit now confirms all
six scenarios, source identity, CLI output and reviewer corrections; Udacity
acceptance still requires re-review.
