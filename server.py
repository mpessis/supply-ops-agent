"""supply-ops-agent — Sell-side ad ops diagnostic MCP server.

A supply-side operations diagnostic agent built on AAMP standards,
extending the IAB Tech Lab seller agent framework with diagnostic tooling
for bid rate analysis, IVT detection, and ads.txt compliance.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from data.mock_data import (
    ADS_TXT_DB,
    PARTNER_DOMAINS,
    PARTNERS,
    generate_bid_data,
    generate_demand_data,
    generate_ivt_data,
)
from data.incidents import get_incidents_for_partner

mcp = FastMCP(
    "supply-ops-agent",
    instructions=(
        "Supply-side ad ops diagnostic assistant built on AAMP standards. "
        "Provides bid rate analysis, IVT detection, ads.txt compliance checks, "
        "demand analysis, and composite partner health scoring."
    ),
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

IVT_THRESHOLD_PCT: float = 5.0
BID_RATE_DROP_THRESHOLD_PCT: float = 20.0


def _resolve_partner(name: str) -> str | None:
    """Fuzzy-match a partner name (case-insensitive, partial match)."""
    lower = name.lower().strip()
    for p in PARTNERS:
        if lower in p.lower() or p.lower() in lower:
            return p
    return None


def _fmt(obj: Any) -> str:
    return json.dumps(obj, indent=2)


# ---------------------------------------------------------------------------
# Tool 1: diagnose_bid_rate
# ---------------------------------------------------------------------------

@mcp.tool()
def diagnose_bid_rate(partner: str, days: int = 7) -> str:
    """Diagnose bid rate health for a supply partner.

    Returns daily bid rates, flags anomalies vs baseline, and includes
    win rate and bid volume. Use this when investigating bid rate drops
    or checking bidding health.

    Args:
        partner: Partner name (e.g. "Partner Bravo" or just "Bravo").
        days: Number of recent days to analyze (default 7, max 30).
    """
    resolved = _resolve_partner(partner)
    if not resolved:
        return _fmt({"error": f"Unknown partner '{partner}'", "available": PARTNERS})

    days = min(max(days, 1), 30)
    all_data = generate_bid_data(resolved)
    recent = all_data[-days:]

    # Compute baseline from first 4 days (pre-incident window)
    baseline_window = all_data[:4]
    baseline_bid = sum(r["bid_rate_pct"] for r in baseline_window) / len(baseline_window)
    baseline_win = sum(r["win_rate_pct"] for r in baseline_window) / len(baseline_window)

    current_avg = sum(r["bid_rate_pct"] for r in recent) / len(recent)
    drop_pct = ((baseline_bid - current_avg) / baseline_bid) * 100

    anomalies: list[dict[str, Any]] = []
    for row in recent:
        day_drop = ((baseline_bid - row["bid_rate_pct"]) / baseline_bid) * 100
        if day_drop > BID_RATE_DROP_THRESHOLD_PCT:
            anomalies.append({
                "date": row["date"],
                "bid_rate_pct": row["bid_rate_pct"],
                "drop_from_baseline_pct": round(day_drop, 1),
            })

    incidents = get_incidents_for_partner(resolved)
    bid_incidents = [i for i in incidents if i["type"] == "bid_rate_drop"]

    return _fmt({
        "partner": resolved,
        "period_days": days,
        "baseline_bid_rate_pct": round(baseline_bid, 2),
        "baseline_win_rate_pct": round(baseline_win, 2),
        "current_avg_bid_rate_pct": round(current_avg, 2),
        "change_from_baseline_pct": round(-drop_pct, 2),
        "anomaly_days": anomalies,
        "daily_data": recent,
        "related_incidents": bid_incidents if bid_incidents else None,
    })


# ---------------------------------------------------------------------------
# Tool 2: check_ads_txt
# ---------------------------------------------------------------------------

@mcp.tool()
def check_ads_txt(domain: str) -> str:
    """Check ads.txt compliance for a publisher domain.

    Returns declared vs observed sellers, flags mismatches, and shows
    when any mismatch was first detected. Accepts a domain name or a
    partner name.

    Args:
        domain: Publisher domain (e.g. "bravo-network.com") or partner name.
    """
    # Try direct domain lookup
    lookup = domain.lower().strip()
    record = ADS_TXT_DB.get(lookup)

    # Try partner name → domain
    if not record:
        resolved = _resolve_partner(domain)
        if resolved and resolved in PARTNER_DOMAINS:
            lookup = PARTNER_DOMAINS[resolved]
            record = ADS_TXT_DB.get(lookup)

    if not record:
        return _fmt({
            "error": f"No ads.txt data for '{domain}'",
            "available_domains": list(ADS_TXT_DB.keys()),
        })

    return _fmt({
        "domain": lookup,
        "status": record["status"],
        "declared_sellers": record["declared_sellers"],
        "observed_sellers": record["observed_sellers"],
        "mismatches": record["mismatches"] if record["mismatches"] else "none",
        "last_crawl": record["last_crawl"],
        "summary": (
            f"MISMATCH: {len(record['mismatches'])} undeclared seller(s) detected"
            if record["mismatches"]
            else "All observed sellers are properly declared"
        ),
    })


# ---------------------------------------------------------------------------
# Tool 3: detect_ivt
# ---------------------------------------------------------------------------

@mcp.tool()
def detect_ivt(partner: str, days: int = 7) -> str:
    """Detect Invalid Traffic (IVT) for a supply partner.

    Returns daily IVT rates broken down by GIVT (General Invalid Traffic)
    and SIVT (Sophisticated Invalid Traffic). Flags spikes above the
    alert threshold.

    Args:
        partner: Partner name (e.g. "Partner Delta" or just "Delta").
        days: Number of recent days to analyze (default 7, max 30).
    """
    resolved = _resolve_partner(partner)
    if not resolved:
        return _fmt({"error": f"Unknown partner '{partner}'", "available": PARTNERS})

    days = min(max(days, 1), 30)
    all_data = generate_ivt_data(resolved)
    recent = all_data[-days:]

    baseline_window = all_data[:4]
    baseline_total = sum(r["total_ivt_pct"] for r in baseline_window) / len(baseline_window)

    spikes: list[dict[str, Any]] = []
    baseline_sivt = sum(r["sivt_pct"] for r in baseline_window) / len(baseline_window)
    for row in recent:
        sivt_spike = row["sivt_pct"] > max(IVT_THRESHOLD_PCT, baseline_sivt * 2)
        total_spike = row["total_ivt_pct"] > baseline_total * 2
        if sivt_spike or total_spike:
            spikes.append({
                "date": row["date"],
                "givt_pct": row["givt_pct"],
                "sivt_pct": row["sivt_pct"],
                "total_ivt_pct": row["total_ivt_pct"],
            })

    incidents = get_incidents_for_partner(resolved)
    ivt_incidents = [i for i in incidents if i["type"] == "ivt_spike"]

    avg_givt = round(sum(r["givt_pct"] for r in recent) / len(recent), 2)
    avg_sivt = round(sum(r["sivt_pct"] for r in recent) / len(recent), 2)

    return _fmt({
        "partner": resolved,
        "period_days": days,
        "threshold_pct": IVT_THRESHOLD_PCT,
        "baseline_total_ivt_pct": round(baseline_total, 2),
        "period_avg_givt_pct": avg_givt,
        "period_avg_sivt_pct": avg_sivt,
        "period_avg_total_ivt_pct": round(avg_givt + avg_sivt, 2),
        "spike_days": spikes,
        "daily_data": recent,
        "related_incidents": ivt_incidents if ivt_incidents else None,
    })


# ---------------------------------------------------------------------------
# Tool 4: analyze_demand
# ---------------------------------------------------------------------------

@mcp.tool()
def analyze_demand(partner: str, days: int = 7) -> str:
    """Analyze DSP demand trends for a supply partner.

    Returns per-buyer spend trends, identifies which buyers pulled back
    and when. Use this to investigate revenue drops or demand shifts.

    Args:
        partner: Partner name (e.g. "Partner Foxtrot" or just "Foxtrot").
        days: Number of recent days to analyze (default 7, max 30).
    """
    resolved = _resolve_partner(partner)
    if not resolved:
        return _fmt({"error": f"Unknown partner '{partner}'", "available": PARTNERS})

    days = min(max(days, 1), 30)
    all_data = generate_demand_data(resolved)

    # Group by DSP
    dsp_data: dict[str, list[dict[str, Any]]] = {}
    for row in all_data:
        dsp_data.setdefault(row["dsp"], []).append(row)

    dsp_summaries: list[dict[str, Any]] = []
    for dsp, rows in dsp_data.items():
        recent = rows[-days:]
        baseline = rows[:4]

        baseline_spend = sum(r["spend_usd"] for r in baseline) / len(baseline)
        recent_spend = sum(r["spend_usd"] for r in recent) / len(recent)
        change_pct = ((recent_spend - baseline_spend) / baseline_spend) * 100 if baseline_spend else 0

        avg_cpm = sum(r["cpm_usd"] for r in recent) / len(recent)

        dsp_summaries.append({
            "dsp": dsp,
            "baseline_daily_spend_usd": round(baseline_spend, 2),
            "recent_avg_daily_spend_usd": round(recent_spend, 2),
            "spend_change_pct": round(change_pct, 1),
            "avg_cpm_usd": round(avg_cpm, 2),
            "status": "pullback" if change_pct < -30 else ("growth" if change_pct > 15 else "stable"),
            "daily_data": recent,
        })

    pullbacks = [s for s in dsp_summaries if s["status"] == "pullback"]
    incidents = get_incidents_for_partner(resolved)
    demand_incidents = [i for i in incidents if i["type"] == "demand_drop"]

    return _fmt({
        "partner": resolved,
        "period_days": days,
        "dsp_count": len(dsp_summaries),
        "dsp_summaries": dsp_summaries,
        "pullbacks": pullbacks if pullbacks else "none",
        "related_incidents": demand_incidents if demand_incidents else None,
    })


# ---------------------------------------------------------------------------
# Tool 5: partner_health
# ---------------------------------------------------------------------------

@mcp.tool()
def partner_health(partner: str) -> str:
    """Get a composite health score for a supply partner.

    Combines bid rate, IVT, ads.txt, and demand signals into a single
    health assessment with per-dimension scores. Use this for a quick
    overview before diving into specific diagnostics.

    Args:
        partner: Partner name (e.g. "Partner Alpha" or just "Alpha").
    """
    resolved = _resolve_partner(partner)
    if not resolved:
        return _fmt({"error": f"Unknown partner '{partner}'", "available": PARTNERS})

    # Bid rate score (0-100)
    bid_data = generate_bid_data(resolved)
    recent_bids = bid_data[-7:]
    baseline_bids = bid_data[:4]
    baseline_rate = sum(r["bid_rate_pct"] for r in baseline_bids) / len(baseline_bids)
    current_rate = sum(r["bid_rate_pct"] for r in recent_bids) / len(recent_bids)
    bid_ratio = current_rate / baseline_rate if baseline_rate else 1
    bid_score = min(100, max(0, bid_ratio * 100))

    # IVT score (100 = clean, 0 = terrible)
    ivt_data = generate_ivt_data(resolved)
    recent_ivt = ivt_data[-7:]
    avg_ivt = sum(r["total_ivt_pct"] for r in recent_ivt) / len(recent_ivt)
    ivt_score = max(0, 100 - (avg_ivt * 10))

    # Ads.txt score
    domain = PARTNER_DOMAINS.get(resolved, "")
    ads_record = ADS_TXT_DB.get(domain, {})
    ads_score = 100.0 if ads_record.get("status") == "ok" else 40.0

    # Demand score
    demand_data = generate_demand_data(resolved)
    dsp_data: dict[str, list[dict[str, Any]]] = {}
    for row in demand_data:
        dsp_data.setdefault(row["dsp"], []).append(row)

    demand_ratios: list[float] = []
    for rows in dsp_data.values():
        baseline_spend = sum(r["spend_usd"] for r in rows[:4]) / 4
        recent_spend = sum(r["spend_usd"] for r in rows[-7:]) / 7
        ratio = recent_spend / baseline_spend if baseline_spend else 1
        demand_ratios.append(min(ratio, 1.5))
    demand_score = min(100, max(0, (sum(demand_ratios) / len(demand_ratios)) * 100)) if demand_ratios else 50

    # Composite
    weights = {"bid_rate": 0.30, "ivt": 0.25, "ads_txt": 0.20, "demand": 0.25}
    composite = (
        bid_score * weights["bid_rate"]
        + ivt_score * weights["ivt"]
        + ads_score * weights["ads_txt"]
        + demand_score * weights["demand"]
    )

    def _grade(score: float) -> str:
        if score >= 90:
            return "healthy"
        if score >= 70:
            return "warning"
        return "critical"

    incidents = get_incidents_for_partner(resolved)

    return _fmt({
        "partner": resolved,
        "domain": domain,
        "composite_score": round(composite, 1),
        "grade": _grade(composite),
        "dimensions": {
            "bid_rate": {"score": round(bid_score, 1), "grade": _grade(bid_score), "weight": weights["bid_rate"]},
            "ivt": {"score": round(ivt_score, 1), "grade": _grade(ivt_score), "weight": weights["ivt"]},
            "ads_txt": {"score": round(ads_score, 1), "grade": _grade(ads_score), "weight": weights["ads_txt"]},
            "demand": {"score": round(demand_score, 1), "grade": _grade(demand_score), "weight": weights["demand"]},
        },
        "active_incidents": [i for i in incidents if i.get("status") == "open"] or "none",
        "available_tools": [
            "diagnose_bid_rate — deep dive into bidding metrics",
            "check_ads_txt — ads.txt compliance check",
            "detect_ivt — invalid traffic detection",
            "analyze_demand — DSP demand trends",
        ],
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
