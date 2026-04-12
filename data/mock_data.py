"""Synthetic supply partner data for 30 days, 6 partners."""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

random.seed(42)

PARTNERS: list[str] = [
    "Partner Alpha",
    "Partner Bravo",
    "Partner Charlie",
    "Partner Delta",
    "Partner Echo",
    "Partner Foxtrot",
]

DSPS: list[str] = [
    "TradeDesk",
    "DV360",
    "Amazon DSP",
    "Xandr",
    "MediaMath",
    "Yahoo DSP",
]

START_DATE: date = date(2026, 3, 13)
NUM_DAYS: int = 30


def _jitter(base: float, pct: float = 0.08) -> float:
    return base * (1 + random.uniform(-pct, pct))


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


# ---------------------------------------------------------------------------
# Bid / win rate data
# ---------------------------------------------------------------------------

def _baseline_bid_rate(partner: str) -> float:
    """Baseline bid rate per partner (%)."""
    baselines = {
        "Partner Alpha": 62.0,
        "Partner Bravo": 55.0,
        "Partner Charlie": 48.0,
        "Partner Delta": 70.0,
        "Partner Echo": 38.0,
        "Partner Foxtrot": 60.0,
    }
    return baselines.get(partner, 50.0)


def _baseline_win_rate(partner: str) -> float:
    baselines = {
        "Partner Alpha": 14.0,
        "Partner Bravo": 12.0,
        "Partner Charlie": 18.0,
        "Partner Delta": 10.0,
        "Partner Echo": 22.0,
        "Partner Foxtrot": 15.0,
    }
    return baselines.get(partner, 15.0)


def generate_bid_data(partner: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base_bid = _baseline_bid_rate(partner)
    base_win = _baseline_win_rate(partner)
    base_volume = random.randint(800_000, 3_000_000)

    for day_offset in range(NUM_DAYS):
        d = START_DATE + timedelta(days=day_offset)
        bid_rate = _jitter(base_bid)
        win_rate = _jitter(base_win)
        volume = int(_jitter(base_volume, 0.12))

        # INCIDENT — Partner Bravo: bid rate drops 40% starting day 5
        if partner == "Partner Bravo" and day_offset >= 5:
            bid_rate = _jitter(base_bid * 0.60, 0.05)
            win_rate = _jitter(base_win * 0.70, 0.05)
            volume = int(volume * 0.65)

        rows.append({
            "date": d.isoformat(),
            "partner": partner,
            "bid_rate_pct": round(_clamp(bid_rate), 2),
            "win_rate_pct": round(_clamp(win_rate, 0, 100), 2),
            "bid_volume": volume,
        })
    return rows


# ---------------------------------------------------------------------------
# IVT data
# ---------------------------------------------------------------------------

def _baseline_givt(partner: str) -> float:
    return {"Partner Delta": 3.5}.get(partner, random.uniform(1.5, 3.0))


def _baseline_sivt(partner: str) -> float:
    return {"Partner Delta": 2.0}.get(partner, random.uniform(0.8, 2.5))


def generate_ivt_data(partner: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base_givt = _baseline_givt(partner)
    base_sivt = _baseline_sivt(partner)

    for day_offset in range(NUM_DAYS):
        d = START_DATE + timedelta(days=day_offset)
        givt = _jitter(base_givt)
        sivt = _jitter(base_sivt)

        # INCIDENT — Partner Delta: SIVT spike on days 10-12
        if partner == "Partner Delta" and 10 <= day_offset <= 12:
            sivt = _jitter(18.0, 0.06)

        rows.append({
            "date": d.isoformat(),
            "partner": partner,
            "givt_pct": round(_clamp(givt), 2),
            "sivt_pct": round(_clamp(sivt), 2),
            "total_ivt_pct": round(_clamp(givt + sivt), 2),
        })
    return rows


# ---------------------------------------------------------------------------
# Demand / DSP data
# ---------------------------------------------------------------------------

def generate_demand_data(partner: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # Assign 3-4 DSPs per partner
    rng = random.Random(hash(partner))
    partner_dsps = rng.sample(DSPS, k=rng.randint(3, 4))
    dsp_spend: dict[str, float] = {
        dsp: round(random.uniform(5_000, 50_000), 2) for dsp in partner_dsps
    }
    dsp_cpm: dict[str, float] = {
        dsp: round(random.uniform(4.0, 28.0), 2) for dsp in partner_dsps
    }

    for day_offset in range(NUM_DAYS):
        d = START_DATE + timedelta(days=day_offset)
        for dsp in partner_dsps:
            spend = _jitter(dsp_spend[dsp], 0.10)
            cpm = _jitter(dsp_cpm[dsp], 0.06)

            # INCIDENT — Partner Foxtrot: two DSPs pull back from day 8
            if partner == "Partner Foxtrot" and day_offset >= 8:
                if dsp in partner_dsps[:2]:
                    spend *= 0.15
                    cpm *= 0.80

            rows.append({
                "date": d.isoformat(),
                "partner": partner,
                "dsp": dsp,
                "spend_usd": round(max(spend, 0), 2),
                "cpm_usd": round(max(cpm, 0.5), 2),
                "impressions": int(spend / max(cpm / 1000, 0.001)),
            })
    return rows


# ---------------------------------------------------------------------------
# Ads.txt data
# ---------------------------------------------------------------------------

ADS_TXT_DB: dict[str, dict[str, Any]] = {
    "alpha-media.com": {
        "declared_sellers": ["seller-001", "seller-002", "seller-003"],
        "observed_sellers": ["seller-001", "seller-002", "seller-003"],
        "mismatches": [],
        "last_crawl": "2026-04-12",
        "status": "ok",
    },
    "bravo-network.com": {
        "declared_sellers": ["seller-010", "seller-011"],
        "observed_sellers": ["seller-010", "seller-011", "seller-099", "seller-100"],
        "mismatches": [
            {"seller_id": "seller-099", "type": "undeclared", "first_seen": "2026-03-18"},
            {"seller_id": "seller-100", "type": "undeclared", "first_seen": "2026-03-18"},
        ],
        "last_crawl": "2026-04-12",
        "status": "mismatch",
    },
    "charlie-pub.com": {
        "declared_sellers": ["seller-020", "seller-021", "seller-022"],
        "observed_sellers": ["seller-020", "seller-021", "seller-022"],
        "mismatches": [],
        "last_crawl": "2026-04-11",
        "status": "ok",
    },
    "delta-digital.com": {
        "declared_sellers": ["seller-030", "seller-031"],
        "observed_sellers": ["seller-030", "seller-031"],
        "mismatches": [],
        "last_crawl": "2026-04-12",
        "status": "ok",
    },
    "echo-media.com": {
        "declared_sellers": ["seller-040", "seller-041", "seller-042"],
        "observed_sellers": ["seller-040", "seller-041", "seller-042"],
        "mismatches": [],
        "last_crawl": "2026-04-10",
        "status": "ok",
    },
    "foxtrot-tv.com": {
        "declared_sellers": ["seller-050", "seller-051"],
        "observed_sellers": ["seller-050", "seller-051"],
        "mismatches": [],
        "last_crawl": "2026-04-12",
        "status": "ok",
    },
}

PARTNER_DOMAINS: dict[str, str] = {
    "Partner Alpha": "alpha-media.com",
    "Partner Bravo": "bravo-network.com",
    "Partner Charlie": "charlie-pub.com",
    "Partner Delta": "delta-digital.com",
    "Partner Echo": "echo-media.com",
    "Partner Foxtrot": "foxtrot-tv.com",
}
