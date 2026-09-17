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

## Fresh cloud verification, September 17

The Udacity sandbox session was refreshed and its account verified through STS.
New resources were created under `udacity-p02-rev2`. The corrected source was
deployed to runtime `udacity_support_p02_rev2-uE9Qrh46hn`. Its uploaded `main.py`
SHA-256 matches the current source and the local correction checks.

Five of six required live scenarios passed: order tracking, both API and Lambda
Gateway targets during refund processing, cross-session memory, Code Interpreter
discounts, and Browser page-title retrieval. The first memory recall attempts
returned no extracted records; a later independent session recalled Jane and her
concise-response preference after extraction and retrieval became available.
Browser navigation recovered from one invalid session-name argument before
returning the live Udacity title. These intermediate results are disclosed in
the fresh evidence rather than described as clean first-attempt passes.

The missing-KB guard passed in runtime version 1. A dummy Gateway URL deployed
in version 2 returned `GATEWAY_UNAVAILABLE` and a safe retry/administrator message.
CloudWatch recorded successful tool loading and the intentional failure.
Version 3 restored the valid Gateway and passed the final memory recall.
See [fresh verification results](examples/cloud_revision/verification.json).

Successful RAG retrieval remains pending. A fresh attempt to create the required
OpenSearch encryption policy was denied for `aoss:CreateSecurityPolicy` in sandbox
account `090165623118`. The personal AWS sign-in is still awaiting user completion;
the saved personal credentials are expired or invalid. No permissions were
bypassed. The earlier personal-account RAG record remains historical evidence.

The temporary deployment was removed after recording evidence; see the cleanup
records in `examples/cloud_revision`. Udacity acceptance remains pending, and no
revised submission was uploaded. Successful RAG must be retested through an
AgentCore Runtime after suitable AWS access is available.

## Rubric recheck and fresh CLI evidence

The live rubric, instructions, setup page and all reviewer sections were checked
again on September 17. No additional missing agent implementation was found.
The review still concerns the original submission and has not been regraded.
[The submission checklist](docs/submission_checklist.md) maps every requirement
to the revised code and evidence, distinguishing the RAG code criterion from
the remaining successful RAG scenario required by the instructions.

A separate temporary sandbox runtime executed the course order command through
`agentcore invoke`, with exit code 0, UPS and `TRK987654321` in its response.
Its uploaded source was verified against the current `main.py`. The command,
verbatim CLI output and metadata are in `examples/cloud_revision/agentcore_invoke.*`.
This closes the fresh CLI-evidence gap without relabeling the existing SDK traces.
The additional test resources were cleaned up after recording the result.

The full local suite again passed 33 tests with one dependency warning. The
reflection has 293 body words, both Lambda files match the preserved starter,
and no `pass` statements remain in the agent. Structural results are recorded
in `examples/revision/rubric_recheck.json`.

README now includes the deployment CLI installation and cloud setup workflow.
The unused memory display name was cleared from the configuration template to
avoid treating it as a real Memory ID. Memory persistence documentation now
accurately distinguishes the synchronous save hook from asynchronous extraction.
Successful deployed RAG remains pending; the package has not been resubmitted.
