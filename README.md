# commerce-check

Deterministic **fact-consistency checker** for agentic-commerce product feeds and agent orders. Complements protocol-format validators (UCP conformance, JSON schema) by checking the numeric and cross-field consistency layer they do not cover.

## What it catches (schema validators don't)

- `unit_price.currency != price.currency` (UCP spec MUST rule, shopping/catalog)
- `availability.available=true` with `inventory.quantity <= 0` (agent orders what cannot ship)
- Negative/zero prices, non-ISO-4217 currency, non-positive weights
- Wrong-price agent orders (order price vs feed cross-check)
- Arithmetic non-closure (subtotal/total)

## Run

```bash
python3 demo.py   # zero dependencies, offline
```

Self-authored fixtures, not independent benchmarks.

## Context

Filed as issue #1098 in Universal-Commerce-Protocol/ucp proposing a "fact-consistency" dimension for the conformance suite.

Part of the PHM deterministic-validation family: merged into Microsoft PyRIT mainline (PhysicsConsistencyScorer), Dify official Marketplace, MCP Registry.

MIT license. Zero dependencies.
