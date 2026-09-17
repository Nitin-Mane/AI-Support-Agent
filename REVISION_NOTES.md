# September 17 reviewer corrections

Udacity submission 4823700, dated September 17, 2026, requires changes to two
specifications. Reviewer comments were read in Chrome and saved locally in
`assignment/reviewer_feedback/`. Deployment, Code Interpreter, memory, Browser
and reflection were accepted by the reviewer; they are retained.

| Correction | Result | Validation |
|---|---|---|
| Descriptive guard when `KB_ID` is absent or blank | The current `search_knowledge_base` checks `not KB_ID or not KB_ID.strip()` before calling AWS. Its message names the missing setting and asks for configuration. This guard was already present in the files when the review rework began. | Tests cover `None`, empty string, spaces and tabs/newlines, assert no Retrieve request occurs, and preserve the error rather than an invented policy answer. |
| Useful handling for Gateway failures | The configured MCP transport remains open while the agent runs. Startup/tool-discovery failures and empty tool lists stop execution with `GATEWAY_UNAVAILABLE`, a retry instruction and administrator checks. Successful discovery logs the number of tools. | Tests cover connection entry and discovery failures, timeout, connection error, other service error, empty discovery and tool execution while the connection remains open. |

The previous implementation logged Gateway failures but continued into the agent.
It also exited the MCP context before agent execution. Both behaviors were
reproduced by failing tests before the connection lifetime and error return were
corrected. Raw exception details and the endpoint URL are not returned to customers;
diagnostic exception traces are written to server logs.

## Measured verification

- Full local suite: **33 passed**, with one upstream Pydantic deprecation warning.
- A real `MCPClient` pointed at a closed localhost port returned the actionable
  Gateway error without starting a Bedrock invocation. See
  `examples/revision/failure_checks.json` and `gateway_failure.log`.
- [Correction outcome screenshot](examples/revision/corrections_outcome.jpg):
  a cursor-free crop of the locally displayed measured results.
- Missing, empty and whitespace-only KB settings returned the configuration
  message. These are intentional failure tests, not evidence of successful RAG.
- The saved refund trace contains successful responses from both the API-backed
  order tool and Lambda-backed refund tool. The trace audit also checks that their
  responses are nonempty and not error results.
- Tests and failure checks apply to the revised `main.py`; saved successful
  scenario records apply to their original run dates and earlier source versions.

## RAG and deployment evidence

The saved RAG record identifies a real Bedrock Knowledge Base in personal account
`166977155856`, tested on September 17. Its `runtime_arn` field contains a
Knowledge Base ARN, so it must not be described as proof of a deployed AgentCore
Runtime executing that test. Other saved successful records identify the original
Udacity sandbox AgentCore Runtime from September 15. The vector resources were
recorded as cleaned up; default configuration currently has no KB or Gateway URL.

At the time of this rework, all AWS browser tabs were signed out and each saved
credential set failed STS validation. The revised source has therefore **not been
redeployed**. Restoring AWS authentication is required before fresh cloud tests.
The reviewer corrections have been verified locally; Udacity acceptance remains
pending. No revised project was uploaded or submitted during this rework.

After authentication, recreate the test resources, generate their actual IDs,
deploy this source, rerun order/refund and the RAG query, and capture the real
outputs. Keep deliberate negative-test records separate from successful scenario
evidence. The instructor's sandbox account instruction and any personal-account
use must remain explicitly documented.
