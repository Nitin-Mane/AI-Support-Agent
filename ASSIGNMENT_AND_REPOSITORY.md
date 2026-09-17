# Assignment 02: AI Support Agent

## Verified course information

- Program: Future AWS Agent Engineer.
- Course: Building Agents with Amazon Bedrock AgentCore and Strands SDK.
- Project: AI Support Agent.
- Due date shown by Udacity: **September 20, 2026**. The page does not give a cutoff time or timezone.
- Submission: a ZIP archive, with a 500 MB uncompressed limit. A public GitHub repository is also offered by the upload form.
- Required region: `us-east-1`.
- Account selected for this work: the Udacity sandbox.

The original classroom text and source URLs are saved in `assignment/`.

## Required deliverables

| Deliverable | Required content |
|---|---|
| `main.py` | Module-level app, async entrypoint, Gateway MCP integration, RAG tool, memory hooks, discount calculation, browser tool |
| Test 1 | Order ORD-001: shipment status, UPS, TRK987654321, estimated delivery |
| Test 2 | ORD-002 refund: generated refund ID, APPROVED, 3–5 business days |
| Test 3 | Knowledge Base retrieval: Platinum benefits including same-day shipping, 15% discount and priority support |
| Test 4 | Two separate sessions for the same customer; recall Jane and the concise-response preference |
| Test 5 | Gold, 4,250 points, $150 standard order: redeemed points, discount percentage, total and remaining points |
| Test 6 | Live browser retrieval of the requested page title |
| Reflection | 200–400 words: one design decision, one encountered challenge and one production consideration |

## Official repository

- Source: https://github.com/udacity/cd14763-project-starter/
- Downloaded revision: `1b597d3269a5d60a9186cac5755aa27915b21713`.
- Untouched checkout: `upstream/`.

| Original file | Purpose |
|---|---|
| `README.md` | Project description, setup and testing guidance |
| `starter/main.py` | Eight unfinished implementation sections |
| `starter/pyproject.toml` | Starter dependency declaration |
| `starter/product_catalog.txt` | Fixture catalog, policies and loyalty rules for Knowledge Base ingestion |
| `starter/lambda/order_tracker.py` | REST proxy Lambda with three GET routes and fixture orders/customers |
| `starter/lambda/refund_processor.py` | Direct Gateway Lambda with refund, status and label operations |
| `starter/lambda/lambda_schema` | JSON tool schemas for the refund Lambda |
| `starter/README.md` | Explanation of the starter folder |
| `LICENSE.txt` | Original Udacity license |
| `CODEOWNERS` | Repository ownership metadata |

## Differences reconciled

1. The classroom mentions a `RUBRIC.md`, but this revision does not contain it. The live rubric is saved as `assignment/04_project_rubric.txt`.
2. The classroom specifies Python 3.13+, while the repository specifies 3.14+. This implementation uses Python 3.13, matching the classroom and the chosen managed runtime. The original manifest remains in `upstream/`.
3. The classroom's browser prompt requests Udacity, but its expected-result sentence says Amazon. The main evidence follows the actual prompt; an Amazon check can be added separately.
4. The repository README requests a CloudWatch alarm screenshot; the classroom rubric and submission checklist do not. Treat it as supplementary repository evidence and report its status separately.
5. The starter uses `namespaces`; the current rubric also accepts `namespaceTemplates`. The helper supports both.
6. The setup lists the Nova Lite model ID while the starter supplies the global Nova 2 Lite inference profile. A real request to `global.amazon.nova-2-lite-v1:0` succeeded in the selected sandbox.
7. The course explicitly requires the Python starter-toolkit CLI. Its deprecation notice does not change this assignment's workflow.
8. The product catalog and Lambda data are educational fixtures. Refund responses do not represent real payment transactions. Original fixture dates and content are preserved.

## Local file map

| Path | Purpose |
|---|---|
| `main.py` | Implemented support agent |
| `config.json` | Non-secret AWS resource identifiers; empty KB ID means the Knowledge Base is not provisioned |
| `requirements.txt`, `pyproject.toml` | Runtime dependencies and development setup |
| `lambda/` | Unmodified copies of supplied Lambda code and schemas |
| `product_catalog.txt` | Unmodified catalog for upload |
| `tests/test_agent.py` | Local behavior checks with external services replaced by test doubles |
| `scripts/provision.py` | Sandbox infrastructure setup and resource checkpointing |
| `scripts/prepare_runtime.py` | Runtime role and isolated deployment staging |
| `scripts/sandbox_command.py` | Runs commands with sandbox credentials, without changing personal AWS profiles |
| `deployment/` | Staged runtime files and generated deployment artifacts |
| `evidence/` | Actual test outputs and verification results |
| `SUBMISSION_STATUS.md` | Requirement-by-requirement pass and blocker summary |
| `project_outcome/` | Audited review ZIP, package audit and SHA-256 checksum |
| `.local/` | Private credentials and setup state; excluded from submission |

Local unit tests do not count as the six required deployed-agent conversation tests.
The raw classroom captures and original checkout remain in the workspace; the
review ZIP contains the implementation, project guide and evidence rather than
copies of course pages or installed dependencies.
# September 17 additions

| File or folder | Contents |
|---|---|
| `docs/COURSE_REVIEW.md` | Comparison with seven classroom RAG and web-search pages, code choices, exact source links and the remaining blocker. |
| `assignment/course_lessons/` | Local reference captures of the reviewed classroom pages; excluded from the review ZIP. |
| `evidence/screenshots/` | Eight outcome-only JPEG screenshots, evidence index and capture metadata. |
| `evidence/panels/` | Seven offline HTML documents displaying verbatim saved scenario responses with timestamps and source checksums. |
| `evidence/course_permission_check.json` | September 17 read-only service checks against the authorized Udacity sandbox. |
| `scripts/build_evidence_panels.py` | Recreates the HTML evidence documents from the original recorded outputs. |
