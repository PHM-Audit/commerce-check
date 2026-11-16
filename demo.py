#!/usr/bin/env python3
"""Demo: clean vs injected-contradiction feed + wrong-price agent order.
Run: python3 demo.py  (zero dependencies)
Self-authored fixtures -- not independent benchmarks.
Corresponds to UCP issue #1098 (Universal-Commerce-Protocol/ucp).
"""
import json
from commerce import check_feed, check_order_vs_feed

clean_feed = [
  {"id": "SKU-001", "title": "USB-C cable", "price": 999, "currency": "USD",
   "availability": {"available": True}, "quantity": 250, "quantity_unit": "each"},
  {"id": "SKU-002", "title": "Desk lamp", "price": 3450, "currency": "USD",
   "availability": {"available": False}, "quantity": 0, "quantity_unit": "each"},
]
print("CLEAN FEED:", check_feed(clean_feed)["verdict"], "(expect PASS, 0 findings)")

dirty_feed = [
  {"id": "SKU-101", "price": -150, "currency": "usd", "availability": {"available": True}, "quantity": 0},
  {"id": "SKU-102", "price": 8999, "currency": "XX", "unit_price": {"amount": 8999, "currency": "EUR"}, "weight": {"value": 0, "unit": "kg"}},
  {"id": "SKU-103", "price": 99999.5, "_unit": "cents", "availability": {"available": True}, "quantity": -5},
]
r = check_feed(dirty_feed)
print("INJECTED FEED:", r["verdict"], f"({len(r['violations'])} findings, expect 8)")
for v in r["violations"]:
    print(f"  [{v['severity']}] {v['rule']}: {v['detail'][:70]}")

order = {"id": "ORD-001", "currency": "USD",
  "items": [{"id": "SKU-001", "price": 999, "quantity": 2}, {"id": "SKU-001", "price": 8999, "quantity": 1}],
  "subtotal": 9998, "shipping": 500, "discount": 0, "total": 10998}
r3 = check_order_vs_feed(order, clean_feed)
print("WRONG-PRICE ORDER:", r3["verdict"], f"({len(r3['violations'])} findings)")
for v in r3["violations"]:
    print(f"  [{v['severity']}] {v['rule']}: {v['detail'][:80]}")
