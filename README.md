# AI Support Agent

September 17 reviewer corrections are documented in [REVISION_NOTES.md](REVISION_NOTES.md).
The revised source passes 33 local tests, including a real failed MCP connection.
The scenario records below are historical evidence. The revised source has not
yet been deployed or reviewed by Udacity. Test 3 was run against a real Knowledge
Base in the personal AWS account; its recorded ARN identifies that KB, rather
than an AgentCore Runtime. AWS sign-in must be restored for fresh deployment tests.

A cloud-native customer support platform built with the **Strands SDK** and **Amazon Bedrock AgentCore Runtime**, orchestrated with **Amazon Nova 2 Lite**. The agent integrates real-time order tracking, transactional refund processing via Model Context Protocol (MCP) Gateway microservices, semantic knowledge base retrieval (RAG) over Amazon OpenSearch Serverless, long-term cross-session memory, deterministic financial code execution, and headless browser automation.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph ClientLayer["Client & Session Management"]
        User["Customer Request"] --> Runtime["AgentCore Runtime (invoke)"]
    end

    subgraph AgentCore["Agent Reasoning Core"]
        Runtime --> Agent["Strands Agent Engine<br/>(Amazon Nova 2 Lite)"]
        MemoryHook["MemoryHook (Lifecycle Hook Provider)"] <--> Agent
    end

    subgraph ToolEcosystem["Federated Tool Integrations"]
        Agent -->|"MCP Streamable HTTP"| Gateway["AgentCore Gateway"]
        Gateway -->|"REST /api/orders"| LambdaOrder["Order Tracker Lambda"]
        Gateway -->|"Direct Tool Lambda"| LambdaRefund["Refund Processor Lambda"]

        Agent -->|"Vector Retrieve API"| BedrockKB["Bedrock Knowledge Base<br/>(OpenSearch Serverless)"]
        Agent -->|"Sandboxed Python"| CodeInterpreter["AgentCore Code Interpreter<br/>(Loyalty Math)"]
        Agent -->|"Playwright Automation"| BrowserTool["AgentCore Browser<br/>(DOM Inspection)"]
        MemoryHook -->|"Fact Extraction"| AgentMemory["AgentCore Memory Service<br/>(Cross-Session Context)"]
    end

    subgraph Observability["Monitoring & Governance"]
        Agent -.-> CloudWatch["Amazon CloudWatch<br/>(Logs, Metrics & Alarms)"]
    end
```

Detailed architectural specifications, sequencing diagrams, and interface contracts are documented in [docs/architecture.md](docs/architecture.md).

---

## Core Capabilities

1. **Order Tracking**: Inquires live shipment details (carrier, tracking number, estimated delivery) via an MCP Gateway routing to an Amazon API Gateway REST endpoint.
2. **Refund Processing**: Validates purchase records and issues transactional refunds with generated refund IDs and processing timelines via direct Gateway Lambda invocation.
3. **Knowledge Base Retrieval (RAG)**: Queries vector embeddings in OpenSearch Serverless through Amazon Bedrock Knowledge Base to answer customer inquiries regarding loyalty tier benefits, return windows, and product policies.
4. **Cross-Session Memory**: Maintains long-term customer context (name, communication preferences, historical interactions) across distinct sessions using Bedrock AgentCore Memory.
5. **Deterministic Discount Calculation**: Executes isolated Python programs in AgentCore Code Interpreter to guarantee exact decimal arithmetic for loyalty point redemption and tiered discount calculations, preventing LLM hallucination in financial transactions.
6. **Live Browser Automation**: Navigates external websites, inspects DOM elements, and extracts live webpage metadata using Playwright-backed browser actions.

---

## Execution Panels & Test Showcase

Below are panels displaying saved test results across the six capability domains.
The original trace files in `examples/traces/` identify the run dates and account
ARNs. These panels do not represent fresh executions of the September 17 revision.

### 1. Order Tracking
- **Objective**: Retrieve status and carrier tracking for order `ORD-001`.
- **Backend Tool**: `order_tracker` Lambda via Gateway MCP.
- **Verification**: Successfully resolved carrier (**UPS**), tracking number (**TRK987654321**), and estimated delivery date (**September 17, 2026**).

![Order Tracking](docs/images/01_order.jpg)

---

### 2. Refund Processing
- **Objective**: Process a return and refund for order `ORD-002`.
- **Backend Tools**: `order_tracker` (order validation) and `refund_processor` (refund execution).
- **Verification**: Successfully validated order record, generated unique refund ID, marked status as **APPROVED**, and confirmed refund delivery within 3–5 business days.

![Refund Processing](docs/images/02_refund.jpg)

---

### 3. Knowledge Base Retrieval (RAG)
- **Objective**: Inquire about Platinum member loyalty perks without hallucination.
- **Backend Tool**: `search_knowledge_base` querying Amazon Bedrock Knowledge Base (OpenSearch Serverless vector index).
- **Verification**: Accurately retrieved all three Platinum benefits: **free same-day shipping**, **15% discount on all purchases**, and **24/7 priority support access**.

![Knowledge Base Retrieval](docs/images/03_rag.jpg)

---

### 4. Cross-Session Long-Term Memory
- **Objective**: Recall customer name and response preferences across completely distinct runtime sessions.
- **Backend Tool**: `AgentCore Memory` with `MemoryHook`.
- **Session A**: Customer introduces herself as Jane and requests concise, bulleted responses.
- **Session B**: In a new session, customer asks what the agent remembers. The agent recalls her name and immediately applies her concise response formatting preference.

| Session A: Intake | Session B: Recall |
|---|---|
| ![Session A](docs/images/04_memory_a.jpg) | ![Session B](docs/images/04_memory_b.jpg) |

---

### 5. Loyalty Discount Calculation (Code Interpreter)
- **Objective**: Calculate discount for a Gold member with 4,250 points on a $150 standard order.
- **Backend Tool**: `calculate_loyalty_discount` via AgentCore Code Interpreter.
- **Business Logic**: 500-point blocks ($5/block) capped at 50% order value; 10% Gold tier discount applied to remaining subtotal.
- **Verification**: 4,000 points redeemed ($40.00 discount), remaining subtotal $110.00, Gold 10% discount ($11.00), **Final Total: $99.00**, and **349 remaining points**.

![Loyalty Discount Calculation](docs/images/05_discount.jpg)

---

### 6. Browser Automation
- **Objective**: Navigate to an external URL and retrieve page title content.
- **Backend Tool**: `AgentCore Browser` with Playwright navigation and DOM text extraction.
- **Verification**: Navigated to external URL and extracted the document title: `"Learn the Latest Tech Skills; Advance Your Career | Udacity"`.

![Browser Automation](docs/images/06_browser.jpg)

---

## Repository Structure

```text
.
├── main.py                     # Support agent implementation with Strands SDK & AgentCore
├── config.json                 # Environment and AWS resource configuration
├── requirements.txt            # Production Python package dependencies
├── pyproject.toml              # Build system specification & test dependencies
├── product_catalog.txt         # Catalog and policy fixtures for Knowledge Base ingestion
├── LICENSE                     # MIT License
├── README.md                   # Project documentation and architectural overview
├── docs/
│   ├── architecture.md         # Detailed system design, data flow, and component specifications
│   ├── design_decisions.md     # Engineering decisions, arithmetic boundary isolation, and security
│   └── images/                 # Saved outcome panel screenshots
├── lambda/
│   ├── order_tracker.py        # REST API Lambda handling order queries
│   ├── refund_processor.py     # MCP tool Lambda processing refunds and return labels
│   └── lambda_schema           # Tool definition schemas for refund Lambda
├── tests/
│   └── test_agent.py           # Existing local behavior tests
├── examples/
│   └── traces/                 # Verbatim execution JSON and text conversation traces
└── scripts/
    ├── run_scenario.py         # Scenario runner for invoking agent tools
    └── verify_traces.py        # Automated trace verification script
```

---

## Local Development & Testing

### Prerequisites
- Python 3.13+
- Active AWS credentials with Bedrock access (or mock environment for local tests)

### Installation
```bash
# Clone the repository
git clone https://github.com/Nitin-Mane/AI-Support-Agent.git
cd AI-Support-Agent

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install pytest anyio
```

### Running the Test Suite
The repository includes 33 local tests covering discount arithmetic, memory hooks,
Knowledge Base configuration guards, response enforcement, entrypoint validation,
Gateway failures and connection lifetime. Cloud services are replaced with test
doubles in this suite. The separate failure-check script also exercises a real
MCP connection against a deliberately closed localhost port.

```bash
pytest tests/
```

Measured result (full output in [examples/revision/pytest.txt](examples/revision/pytest.txt)):
```text
33 passed, 1 dependency deprecation warning
```

Run the actual connection failure checks with:

```bash
python scripts/verify_review_failures.py
```

![Reviewer correction outcomes](examples/revision/corrections_outcome.jpg)

---

## Key Engineering Decisions

- **Deterministic Financial Arithmetic**: Financial loyalty calculations are strictly executed in an isolated Python Code Interpreter sandbox rather than letting the LLM compute totals, preventing multi-step rounding errors.
- **Defensive Memory Hooks**: Memory retrieval occurs prior to model invocation (`MessageAddedEvent`), while persistence (`AfterInvocationEvent`) is non-blocking to prevent memory service latency from degrading response time.
- **Gateway failure handling**: The transport remains open throughout the agent turn. If connection or discovery fails, or no tools are returned, the request stops with a useful retry message and diagnostic server logging.

For deeper technical analysis, refer to [docs/design_decisions.md](docs/design_decisions.md) and the [Engineering Reflection](REFLECTION.md).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
