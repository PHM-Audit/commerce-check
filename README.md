# commerce-check

**Payload self-consistency checker** for agentic-commerce product feeds and agent orders — it rejects payloads that contradict themselves (currency pairs, negative amounts, inventory that disagrees with itself, totals that don't close), using no external state. Complements protocol-format validators (UCP conformance, JSON schema) on the numeric and cross-field layer they do not cover.

Scope boundary (credit: stillmarcus24, TAP#22): these are **payload self-consistency** checks, not fact checks — a payload that is internally consistent but describes an empty warehouse passes every rule here. Layer 2 (this filter) removes the malformed tail; it does not shrink layer 3 (world-verifying mechanisms such as notaries/escrow).

False-positive rate on non-injected traffic: 0/18 judgment units on UCP spec canonical payloads + 0/20 records on a live store catalog API (measured 2026-11-23, see `fp_final_1123.json`).

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
