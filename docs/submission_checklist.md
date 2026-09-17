# Udacity rubric and reviewer recheck

Checked against the live classroom rubric, Environment Setup, Instructions, and
the review of submission **4823700** on September 17, 2026.
The classroom still reports two specifications requiring changes. This document
maps the revised work to those requests; it does not claim a new Udacity grade.

## Reviewer changes

| Requested correction | Revised implementation | Measured evidence |
| --- | --- | --- |
| Missing or blank `KB_ID` must return a descriptive message | `search_knowledge_base` checks missing, empty and whitespace-only values before calling AWS | [Local checks](../examples/revision/failure_checks.json); [deployed empty-KB response](../examples/cloud_revision/rag.json) |
| Gateway failures must be logged and give a useful, safe reply | `invoke` catches connection/discovery failures, logs diagnostics, returns `GATEWAY_UNAVAILABLE`, and keeps the transport active throughout successful tool use | [Deployed dummy-URL test](../examples/cloud_revision/gateway_failure.json); [CloudWatch logs](../examples/cloud_revision/runtime_logs.json) |
| Gateway test responses must be well formed | Successful API order lookup and Lambda refund results are nonempty JSON; the Lambda proxy body also parses as JSON | [Fresh refund trace](../examples/cloud_revision/refund.json); [response audit](../examples/cloud_revision/verification.json) |

## Every rubric criterion

### 1. Cloud runtime

- `BedrockAgentCoreApp` is created at module level.
- `invoke` is asynchronous and decorated with `@app.entrypoint`.
- The executable entry point calls `app.run()`.
- The fresh `agentcore invoke` order command and its terminal output are in
  [agentcore_invoke.txt](../examples/cloud_revision/agentcore_invoke.txt), with
  timestamp, runtime ARN, source hash and exit code in
  [agentcore_invoke.json](../examples/cloud_revision/agentcore_invoke.json).

The CLI check uses a separate temporary sandbox runtime running the same revised
`main.py`. It supplements the earlier fresh SDK invocation records; it does not
replace or change their recorded runtime identifiers.

### 2. MCP Gateway

- `MCPClient` connects using Streamable HTTP.
- `invoke` discovers tools with `list_tools_sync()` and adds them to the agent.
- The MCP transport remains open while the agent invokes those tools.
- The fresh refund trace includes successful `order-tracker___get_order`
  from the API target and `refund-processor___initiate_refund` from Lambda.
- Their outputs are valid, nonempty JSON and not error results.
- Successful discovery and the intentional connection failure are logged.

Evidence: [refund.json](../examples/cloud_revision/refund.json),
[verification.json](../examples/cloud_revision/verification.json), and
[runtime_logs.json](../examples/cloud_revision/runtime_logs.json).
The deliberate dummy-Gateway error is kept in a separate negative-test record.

### 3. Knowledge Base RAG

- `search_knowledge_base` uses the `@tool` decorator.
- Its docstring explains when the agent should use it.
- It checks configuration before attempting retrieval.
- It calls the Bedrock Retrieve API.
- It joins retrieved text chunks into one formatted string.
- Local tests cover missing settings, successful retrieval, and empty results;
  the deployed missing-setting check returns the required configuration message.

**Remaining live gap:** Instructions Test 3 requires a successful Platinum query
through the deployed agent. This is blocked by sandbox OpenSearch permissions.
[rag_permission.json](../examples/cloud_revision/rag_permission.json) records
the denied `aoss:CreateSecurityPolicy` call. The older personal-account RAG trace
is a real retrieval result, but its ARN identifies a Knowledge Base rather than
an AgentCore Runtime; it is not counted as a fresh deployed-agent pass.

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

Evidence: [memory_a.json](../examples/cloud_revision/memory_a.json) and
[memory_b.json](../examples/cloud_revision/memory_b.json).
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

Evidence: [discount.json](../examples/cloud_revision/discount.json) records
actual Code Interpreter execution: 4,000 points redeemed, 10% Gold tier rate,
$99 final total and 349 points remaining. The local suite covers the fallback.

### 6. Browser

- `AgentCoreBrowser` is instantiated with the AWS region.
- Its browser tool is added to the agent.
- The fresh trace shows navigation to the requested Udacity website and a title
  read from the live page. It recovered from one session-name validation error.

Evidence: [browser.json](../examples/cloud_revision/browser.json).
The Instructions page's command requests Udacity, although its expected-result
sentence says Amazon.com. The command is followed, and the actual title is
recorded without substituting a title from a different website.

### 7. Reflection

- [REFLECTION.md](../REFLECTION.md) contains 293 body words, within 200-400.
- It explains choosing Code Interpreter for loyalty calculations.
- It describes observed arithmetic drift and the response enforcement fix.
- It discusses authentication, authorization, refund idempotency and memory
  retention as production considerations.

The reviewer accepted this criterion. Word count and structural checks are in
[rubric_recheck.json](../examples/revision/rubric_recheck.json).

## Instruction and setup checklist

- [x] Tasks 1-6: app, clients, namespace helper, memory hooks, RAG tool, calculator
  and entry point implemented. No `pass` statements remain in `main.py`.
- [x] Task 8: reflection included.
- [x] Starter Lambda files retained without modification.
- [x] Fresh order, refund, memory, discount and browser outputs included.
- [x] Both reviewer corrections tested in the cloud.
- [x] Fresh CLI invocation evidence included.
- [x] Outcome screenshots captured without a cursor.
- [ ] Task 7 fully complete: successful deployed RAG remains pending.
- [ ] All four live configuration values available for a complete deployment:
  `KB_ID` is unavailable in the sandbox. The packaged configuration is a template;
  resources were deleted after testing, so historical IDs must not be reused.
- [ ] Revised project submitted and accepted by Udacity.

The required region is `us-east-1`, and the fresh deployments use the Udacity
sandbox. Personal-account RAG was previously authorized by the user, but remains
a disclosed deviation from the classroom's sandbox setup instruction.

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
verified until the successful deployed RAG check is recorded.
