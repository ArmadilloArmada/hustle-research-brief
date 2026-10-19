"""Collect structured pricing / feed rows from config sources."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

PRICE_RE = re.compile(
    r"(?i)(?:USD\s*)?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
    r"|(?:(?:from|starting at|starts at)\s*)\$?\s*(\d+(?:\.\d{2})?)"
)
PLAN_HINT_RE = re.compile(
    r"(?i)\b(free|hobby|starter|basic|pro|plus|business|team|enterprise|"
    r"personal|premium|unlimited|standard)\b"
)

DEMO_ROWS: list[dict[str, Any]] = [
    {
        "source_name": "Notion",
        "product": "Notion",
        "source_type": "pricing_page",
        "url": "https://www.notion.so/pricing",
        "plan_hint": "Free",
        "price_raw": "$0",
        "price_numeric": "0",
        "currency": "USD",
        "signal": "Free plan listed on pricing page",
        "collected_at": "",
        "status": "demo",
    },
    {
        "source_name": "Notion",
        "product": "Notion",
        "source_type": "pricing_page",
        "url": "https://www.notion.so/pricing",
        "plan_hint": "Plus",
        "price_raw": "$10",
        "price_numeric": "10",
        "currency": "USD",
        "signal": "Plus plan ~$10/user/mo (demo fixture)",
        "collected_at": "",
        "status": "demo",
    },
    {
        "source_name": "Linear",
        "product": "Linear",
        "source_type": "pricing_page",
        "url": "https://linear.app/pricing",
        "plan_hint": "Free",
        "price_raw": "$0",
        "price_numeric": "0",
        "currency": "USD",
        "signal": "Free plan listed on pricing page",
        "collected_at": "",
        "status": "demo",
    },
    {
        "source_name": "Linear",
        "product": "Linear",
        "source_type": "pricing_page",
        "url": "https://linear.app/pricing",
        "plan_hint": "Standard",
        "price_raw": "$10",
        "price_numeric": "10",
        "currency": "USD",
        "signal": "Standard plan ~$10/user/mo (demo fixture)",
        "collected_at": "",
        "status": "demo",
    },
    {
        "source_name": "Loom",
        "product": "Loom",
        "source_type": "pricing_page",
        "url": "https://www.loom.com/pricing",
        "plan_hint": "Business",
        "price_raw": "$18",
        "price_numeric": "18",
        "currency": "USD",
        "signal": "Business plan listed (demo fixture)",
        "collected_at": "",
        "status": "demo",
    },
    {
        "source_name": "Product Hunt Launch Digest",
        "product": "Product Hunt",
        "source_type": "rss",
        "url": "https://www.producthunt.com/feed",
        "plan_hint": "",
        "price_raw": "",
        "price_numeric": "",
        "currency": "",
        "signal": "RSS item: example launch headline (demo fixture)",
        "collected_at": "",
        "status": "demo",
    },
]


CSV_FIELDS = [
    "source_name",
    "product",
    "source_type",
    "url",
    "plan_hint",
    "price_raw",
    "price_numeric",
    "currency",
    "signal",
    "collected_at",
    "status",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stamp_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ts = _now_iso()
    out: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        r["collected_at"] = ts
        out.append(r)
    return out


def collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return structured rows from demo fixtures or live sources."""
    if config.get("demo"):
        return _stamp_rows([dict(r) for r in DEMO_ROWS])

    fetch_cfg = config.get("fetch") or {}
    timeout = float(fetch_cfg.get("timeout_seconds", 25))
    user_agent = fetch_cfg.get(
        "user_agent",
        "hustle-research-brief/0.1 (research; respectful)",
    )
    max_bytes = int(fetch_cfg.get("max_bytes", 500_000))

    rows: list[dict[str, Any]] = []
    sources = config.get("sources") or []
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": user_agent, "Accept": "*/*"},
    ) as client:
        for source in sources:
            rows.extend(_collect_source(client, source, max_bytes))

    if not rows:
        # Fallback so dry-run still ships a SKU artifact if all fetches fail.
        fallback = _stamp_rows([dict(r) for r in DEMO_ROWS])
        for r in fallback:
            r["status"] = "fallback_demo"
            r["signal"] = f"[live fetch empty] {r['signal']}"
        return fallback
    return rows


def _collect_source(
    client: httpx.Client,
    source: dict[str, Any],
    max_bytes: int,
) -> list[dict[str, Any]]:
    name = str(source.get("name") or "unknown")
    product = str(source.get("product") or name)
    url = str(source.get("url") or "")
    source_type = str(source.get("type") or "pricing_page").lower()
    if not url:
        return [
            {
                "source_name": name,
                "product": product,
                "source_type": source_type,
                "url": "",
                "plan_hint": "",
                "price_raw": "",
                "price_numeric": "",
                "currency": "",
                "signal": "missing url in config",
                "collected_at": _now_iso(),
                "status": "error",
            }
        ]

    try:
        resp = client.get(url)
        body = resp.content[:max_bytes]
        text = body.decode(resp.encoding or "utf-8", errors="replace")
        if resp.status_code >= 400:
            return [
                {
                    "source_name": name,
                    "product": product,
                    "source_type": source_type,
                    "url": url,
                    "plan_hint": "",
                    "price_raw": "",
                    "price_numeric": "",
                    "currency": "",
                    "signal": f"HTTP {resp.status_code}",
                    "collected_at": _now_iso(),
                    "status": "error",
                }
            ]
        if source_type == "rss":
            return _parse_rss(name, product, url, text)
        return _parse_pricing_page(name, product, url, text)
    except Exception as exc:  # noqa: BLE001 — surface fetch errors as rows
        return [
            {
                "source_name": name,
                "product": product,
                "source_type": source_type,
                "url": url,
                "plan_hint": "",
                "price_raw": "",
                "price_numeric": "",
                "currency": "",
                "signal": f"fetch failed: {exc}",
                "collected_at": _now_iso(),
                "status": "error",
            }
        ]


def _parse_pricing_page(
    name: str,
    product: str,
    url: str,
    html: str,
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    host = urlparse(url).netloc
    ts = _now_iso()
    rows: list[dict[str, Any]] = []

    # Walk overlapping windows so plan labels near prices are captured.
    for match in PRICE_RE.finditer(text):
        amount = match.group(1) or match.group(2) or ""
        amount_clean = amount.replace(",", "")
        start = max(0, match.start() - 80)
        end = min(len(text), match.end() + 80)
        window = text[start:end]
        plan = ""
        plan_m = PLAN_HINT_RE.search(window)
        if plan_m:
            plan = plan_m.group(1).title()
        rows.append(
            {
                "source_name": name,
                "product": product,
                "source_type": "pricing_page",
                "url": url,
                "plan_hint": plan,
                "price_raw": f"${amount_clean}",
                "price_numeric": amount_clean,
                "currency": "USD",
                "signal": window[:160],
                "collected_at": ts,
                "status": "ok",
            }
        )

    # Deduplicate identical (plan, price) pairs; keep first few signals.
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key = (row["plan_hint"].lower(), row["price_numeric"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
        if len(deduped) >= 8:
            break

    if not deduped:
        snippet = text[:200] if text else f"no extractable text from {host}"
        deduped.append(
            {
                "source_name": name,
                "product": product,
                "source_type": "pricing_page",
                "url": url,
                "plan_hint": "",
                "price_raw": "",
                "price_numeric": "",
                "currency": "",
                "signal": snippet,
                "collected_at": ts,
                "status": "ok_no_price",
            }
        )
    return deduped


def _parse_rss(
    name: str,
    product: str,
    url: str,
    text: str,
) -> list[dict[str, Any]]:
    feed = feedparser.parse(text)
    ts = _now_iso()
    rows: list[dict[str, Any]] = []
    for entry in (feed.entries or [])[:10]:
        title = str(getattr(entry, "title", "") or "").strip()
        link = str(getattr(entry, "link", "") or url).strip()
        summary = str(getattr(entry, "summary", "") or "").strip()
        summary = " ".join(BeautifulSoup(summary, "html.parser").get_text(" ").split())
        signal = title
        if summary:
            signal = f"{title} — {summary[:120]}"
        rows.append(
            {
                "source_name": name,
                "product": product,
                "source_type": "rss",
                "url": link,
                "plan_hint": "",
                "price_raw": "",
                "price_numeric": "",
                "currency": "",
                "signal": signal[:240],
                "collected_at": ts,
                "status": "ok",
            }
        )
    if not rows:
        rows.append(
            {
                "source_name": name,
                "product": product,
                "source_type": "rss",
                "url": url,
                "plan_hint": "",
                "price_raw": "",
                "price_numeric": "",
                "currency": "",
                "signal": "empty RSS feed",
                "collected_at": ts,
                "status": "ok_empty",
            }
        )
    return rows
