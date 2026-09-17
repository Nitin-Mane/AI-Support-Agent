# Reflection

A key design decision was to keep loyalty arithmetic outside the language model.
The discount tool sends a self-contained Python program to AgentCore Code
Interpreter and uses decimal arithmetic for currency. Points are redeemed in
500-point blocks, capped at half the order value. The tier discount then applies
to the remaining subtotal. The final response preserves the tool's structured
values so the model cannot silently recalculate the quote. If the interpreter
is unavailable, the result explicitly identifies a tier-only estimate and leaves
the points balance unchanged.

Live testing showed why this boundary matters. For a Gold customer with 4,250
points and a $150 order, the interpreter correctly returned a $99 total, but the
model initially described a $95 total. The conversation trace made the source of
the error clear: the tool was correct, while the final explanation applied the
tier discount to the original order value. A regression test reproduced the
disagreement. The response handling was then changed to preserve the calculator
output, including the 349 remaining points. Retrieval failures receive similar
treatment: when the Knowledge Base is unavailable, the agent must say that it
cannot verify the policy instead of inventing benefits.

For production, the largest change would be authorization at the backend boundary.
The assignment's Gateway uses no inbound authorizer, and its Lambda functions
operate on demonstration records. A production deployment would authenticate each
customer, derive identity from the authenticated session, check order ownership
inside the service, and make refund requests idempotent. Memory would also need
retention and deletion controls. Finally, deployment checks should verify service
permissions before creating infrastructure: the sandbox's OpenSearch restriction
prevented Knowledge Base setup, so successful local tests alone could not establish
submission readiness.
