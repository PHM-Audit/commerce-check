#!/usr/bin/env python3
"""PHM commerce feed/order validator -- deterministic physics/fact-consistency
checks for agentic-commerce product feeds and agent orders.

Complements protocol-format validators (UCP conformance, JSON schema):
checks the NUMERIC and CROSS-FIELD consistency layer they do not cover.

Zero dependencies. Deterministic. Offline subset of PHM engine.
"""
from dataclasses import dataclass, asdict
from typing import Any

ISO4217 = {"USD","EUR","GBP","CNY","JPY","KRW","CAD","AUD","SGD","HKD","CHF","SEK","NOK","DKK","NZD","MXN","BRL","INR","PLN","CZK","HUF","ILS","SAR","AED","THB","MYR","IDR","PHP","TWD","VND","ZAR","TRY","RON","RUB","UAH","CLP","COP","EGP","NGN","PKR","BDT","LKR","KES","MOP","ARS","CLF","ISK","BGN","HRK","RSD","QAR","KWD","BHD","OMR","JOD"}
QUNITS = {"each","kg","g","lb","oz","l","ml","m","cm","mm","pack","dozen","pair","set","box","bottle","can"}

@dataclass
class Violation:
    rule: str
    severity: str   # FAIL / WARN
    field: str
    detail: str
    product_id: str = ""

def _v(rule, sev, field, detail, pid=""):
    return Violation(rule, sev, field, detail, pid)

def check_product(p: dict) -> list:
    """One product/variant record from a commerce feed."""
    out = []
    pid = str(p.get("id", p.get("product_id", "?")))
    # price
    price = p.get("price", p.get("amount"))
    cur = p.get("currency")
    if price is None:
        out.append(_v("PRICE_MISSING", "FAIL", "price", "no price field", pid))
    else:
        if not isinstance(price, (int, float)):
            out.append(_v("PRICE_TYPE", "FAIL", "price", f"non-numeric price: {price!r}", pid))
        else:
            if price < 0:
                out.append(_v("PRICE_NEGATIVE", "FAIL", "price", f"negative price {price}", pid))
            if price == 0 and p.get("availability", {}).get("available", True):
                out.append(_v("PRICE_ZERO", "WARN", "price", "zero price while marked available", pid))
    if cur is not None:
        if cur not in ISO4217:
            out.append(_v("CURRENCY_INVALID", "FAIL", "currency", f"non-ISO-4217 currency {cur!r}", pid))
    # minor unit sanity: prices in cents that are floats like 19.99 signal unit mixup
    if isinstance(price, float) and not float(price).is_integer() and p.get("_unit") == "cents":
        out.append(_v("MINOR_UNIT_SUSPECT", "WARN", "price", "fractional value in minor-unit field (unit mixup?)", pid))
    # inventory cross-check
    qty = p.get("quantity", p.get("inventory", {}).get("quantity") if isinstance(p.get("inventory"), dict) else None)
    avail = p.get("availability", {}).get("available")
    if avail is True and qty is not None and qty <= 0:
        out.append(_v("AVAILABLE_BUT_EMPTY", "FAIL", "availability",
                      f"marked available but quantity={qty} (agent will order what cannot ship)", pid))
    if avail is False and qty is not None and qty > 0:
        out.append(_v("HIDDEN_STOCK", "WARN", "availability", f"unavailable but quantity={qty} (intentional?)", pid))
    # quantity unit
    qu = p.get("quantity_unit", p.get("unit"))
    if qu is not None and qu not in QUNITS:
        out.append(_v("QUNIT_INVALID", "WARN", "quantity_unit", f"non-standard sale basis {qu!r}", pid))
    # unit_price cross-field (UCP spec MUST: unit_price.currency == price.currency)
    up = p.get("unit_price")
    if isinstance(up, dict):
        if up.get("currency") and cur and up["currency"] != cur:
            out.append(_v("CURRENCY_MISMATCH", "FAIL", "unit_price.currency",
                          f"unit_price.currency={up['currency']} != price.currency={cur} (UCP MUST rule)", pid))
        upv = up.get("amount", up.get("value"))
        if upv is not None and price is not None and upv < 0:
            out.append(_v("UNIT_PRICE_NEGATIVE", "FAIL", "unit_price", f"negative unit price {upv}", pid))
    # weight/dimension sanity (shipping math depends on these)
    w = p.get("weight")
    if isinstance(w, dict):
        v, u = w.get("value"), (w.get("unit") or "").lower()
        if v is not None and v <= 0:
            out.append(_v("WEIGHT_NONPOSITIVE", "FAIL", "weight", f"weight {v} {u} <= 0", pid))
        if u and u not in {"g","kg","lb","oz"}:
            out.append(_v("WEIGHT_UNIT", "WARN", "weight.unit", f"uncommon weight unit {u!r}", pid))
    return out

def check_order(order: dict, feed: dict = None) -> list:
    """One agent order: arithmetic closure + feed cross-check."""
    out = []
    oid = str(order.get("id", "?"))
    items = order.get("items", order.get("line_items", []))
    subtotal = 0.0
    currency = order.get("currency")
    for i, it in enumerate(items):
        iid = str(it.get("product_id", it.get("id", f"item{i}")))
        price = it.get("unit_price", it.get("price"))
        q = it.get("quantity", 1)
        if not isinstance(price, (int, float)) or not isinstance(q, (int, float)) or q <= 0:
            out.append(_v("ORDER_ITEM_MALFORMED", "FAIL", f"items[{i}]", f"price={price!r} qty={q!r}", oid))
            continue
        if price < 0:
            out.append(_v("ORDER_NEGATIVE_PRICE", "FAIL", f"items[{i}]", f"negative unit price {price}", oid))
        subtotal += price * q
        # cross-check against feed
        if feed:
            fp = feed.get(iid) or feed.get(str(i.get("id", "")))
            if fp is not None and isinstance(fp, dict):
                fp_price = fp.get("price", fp.get("amount"))
                if isinstance(fp_price, (int, float)) and abs(fp_price - price) > 1e-9:
                    out.append(_v("ORDER_PRICE_MISMATCH", "FAIL", f"items[{i}].price",
                                  f"order price {price} != feed price {fp_price} (agent was fed wrong price)", oid))
                fcur = fp.get("currency")
                if fcur and currency and fcur != currency:
                    out.append(_v("ORDER_CURRENCY_MISMATCH", "FAIL", "currency",
                                  f"order {currency} vs feed {fcur}", oid))
    # arithmetic closure
    st = order.get("subtotal")
    if st is not None and abs(float(st) - subtotal) > 0.01:
        out.append(_v("SUBTOTAL_MISMATCH", "FAIL", "subtotal",
                      f"declared {st} != computed {round(subtotal,2)}", oid))
    total = order.get("total")
    ship = float(order.get("shipping", 0) or 0)
    disc = float(order.get("discount", 0) or 0)
    if total is not None:
        expect = subtotal + ship - disc
        if abs(float(total) - expect) > 0.01:
            out.append(_v("TOTAL_NOT_CLOSED", "FAIL", "total",
                          f"total {total} != subtotal({subtotal})+ship({ship})-disc({disc})={round(expect,2)}", oid))
    return out

def verdict(vs) -> str:
    return "FAIL" if any(x.severity == "FAIL" for x in vs) else ("WARN" if vs else "PASS")

def check_feed(products: list) -> dict:
    """Batch: feed-level product scan."""
    all_vs = []
    for p in products:
        all_vs += check_product(p)
    return {"verdict": verdict(all_vs),
            "checked": len(products),
            "violations": [asdict(x) for x in all_vs]}

def check_order_vs_feed(order: dict, products: list) -> dict:
    feed = {str(p.get("id", p.get("product_id"))): p for p in products}
    vs = check_order(order, feed)
    return {"verdict": verdict(vs), "violations": [asdict(x) for x in vs]}
