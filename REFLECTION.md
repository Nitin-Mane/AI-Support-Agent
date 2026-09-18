# Engineering Reflection

## Design decision

Loyalty discounts need consistent arithmetic. The discount tool runs a complete
Python calculation in AgentCore Code Interpreter, using Decimal and explicit
rounding. It redeems points in 500-point blocks, limits redemption to half the
order value, and applies the tier discount to the remaining subtotal. The final
reply keeps the tool's structured result so customers receive the same figures
that the calculation produced. If Code Interpreter is unavailable, the fallback
provides a tier-only estimate and does not redeem points.

## Challenge

One live test exposed a mismatch between the calculation and the reply. For a
Gold customer with 4,250 points and a $150 order, the tool returned $99, but the
model described a $95 total. It had applied the 10% discount to the original
order value instead of the $110 balance after point redemption. Checking the
tool conversation made the cause clear. Response validation now preserves the
calculator's JSON fields in the final answer. This showed why checking only the
tool result was insufficient: the customer-facing response also needed testing.

## Production consideration

Refunds need authenticated customer identity and protection against duplicate
requests. A production Gateway should validate bearer tokens, derive customer
identity from the authenticated session, and check that the customer owns the
order. Refund processing should accept an idempotency key so retries cannot
issue the same refund twice. Customer memory also needs a retention period and
a deletion process. These controls should be tested alongside the normal support
flows before connecting the assistant to real customer accounts.
