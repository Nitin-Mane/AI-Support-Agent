# Engineering Design Decisions & Trade-Offs

This document records the architectural decisions, trade-offs, and failure investigations made during the engineering of the **AI Support Agent**.

---

## 1. Isolating Financial Arithmetic from Foundation Model Reasoning

### Context & Problem
During early integration testing with a Gold customer profile (4,250 points, $150 standard order), the underlying foundation model was tasked with both tool orchestration and final answer synthesis. While the backend tool correctly computed a **$99.00 final total** ($40 point redemption + 10% Gold tier discount on the $110 balance), the model's natural language summary hallucinated a **$95.00 total** by calculating the 10% tier discount against the pre-redemption $150 base.

### Engineering Resolution
To eliminate arithmetic drift and ensure regulatory/financial compliance:
1. **Sandboxed Execution**: All point redemption, discount tier percentage, and post-purchase point earning calculations are compiled into self-contained Python code and executed within the **AgentCore Code Interpreter** sandbox using the `Decimal` module with strict `ROUND_HALF_UP` rounding.
2. **Response Verification (`verified_response`)**: The agent's output layer inspects the conversation trajectory. If `calculate_loyalty_discount` was executed, the response parser enforces that the tool's verified structured JSON payload is preserved verbatim in the final response, overriding any conflicting arithmetic synthesized by the model.
3. **Graceful Fallback**: If the Code Interpreter sandbox is temporarily unreachable, the tool emits a deterministic `tier_only_fallback` estimate with 0 points redeemed and an explicit notice, ensuring no points are accidentally deducted without verified code execution.

---

## 2. Non-Blocking Event-Driven Memory Hooks

### Context & Problem
Session state and customer memory persistence should not block the real-time interaction loop. Under high latency or transient backend connectivity issues with the memory service, synchronous event commits could fail or drop user turns.

### Engineering Resolution
- The `MemoryHook` decouples context retrieval from persistence.
- Pre-turn context retrieval (`MessageAddedEvent`) queries semantic and preference namespaces with a tight `top_k=5` constraint.
- Post-turn event creation (`AfterInvocationEvent`) wraps the `create_event` call in defensive error boundaries. Transient write failures or delayed extraction pipelines log warnings without terminating the active turn or presenting an error to the end user.
- To prevent context contamination, the hook preserves the customer's raw input query and ensures that injected `Customer Context` prefixes are stripped before committing the interaction history back to the memory store.

---

## 3. Resilience Across Federated Microservices

### Context & Problem
In distributed cloud architectures, individual tool endpoints (such as Gateway MCP servers or OpenSearch vector clusters) may experience intermittent timeouts, network partition, or cold starts.

### Engineering Resolution
- **Gateway MCP Fallback**: If the Gateway MCP endpoint is unreachable, the agent catches the connection error, logs a warning, and initializes the Strands Agent with the remaining local tools (Knowledge Base, Code Interpreter, Browser).
- **Knowledge Base Factuality**: When vector search returns empty results or the knowledge base is unconfigured, the tool explicitly states that the catalog cannot be verified rather than allowing the model to hallucinate warranty or return policies.

---

## 4. Production Security & Identity Boundaries

For full production deployment, the following boundaries are enforced:
- **Principal Identity**: Customer identities (`customer_id`) are validated against alphanumeric regex constraints (`[A-Za-z0-9_.:-]{1,128}`) to protect against identifier injection attacks.
- **Idempotency**: All refund actions require deterministic order ID matching to ensure duplicate customer requests cannot trigger duplicate financial transactions.
- **Prompt Injection Defense**: Content extracted from external web pages via the browser tool or retrieved from the knowledge base is treated strictly as untrusted data strings.
