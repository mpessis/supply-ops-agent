"""Three baked-in realistic supply-side incidents."""

from __future__ import annotations

from typing import Any

INCIDENTS: list[dict[str, Any]] = [
    {
        "id": "INC-001",
        "partner": "Partner Bravo",
        "domain": "bravo-network.com",
        "type": "bid_rate_drop",
        "summary": "Bid rate dropped ~40% starting 2026-03-18 (day 5). "
                   "Root cause: two undeclared seller IDs (seller-099, seller-100) "
                   "appeared in bid streams but are missing from bravo-network.com/ads.txt. "
                   "DSPs are filtering bids from unauthorized sellers per IAB ads.txt spec.",
        "severity": "high",
        "detected": "2026-03-18",
        "status": "open",
        "signals": [
            "bid_rate: 55% → 33%",
            "win_rate: 12% → 8.4%",
            "ads.txt: 2 undeclared sellers detected",
        ],
        "recommended_actions": [
            "Add seller-099 and seller-100 to bravo-network.com/ads.txt",
            "Verify new seller IDs correspond to legitimate exchange seats",
            "Re-crawl ads.txt after update and monitor bid recovery",
        ],
    },
    {
        "id": "INC-002",
        "partner": "Partner Delta",
        "domain": "delta-digital.com",
        "type": "ivt_spike",
        "summary": "Sophisticated Invalid Traffic (SIVT) spiked to ~18% on days 10-12 "
                   "(2026-03-23 to 2026-03-25), well above the 5% alert threshold. "
                   "Traffic returned to baseline after day 12, suggesting a short burst "
                   "of bot activity or a compromised supply path.",
        "severity": "high",
        "detected": "2026-03-23",
        "resolved": "2026-03-26",
        "status": "resolved",
        "signals": [
            "sivt_pct: 2% baseline → 18% peak",
            "givt_pct: stable at ~3.5%",
            "Duration: 3 days",
        ],
        "recommended_actions": [
            "Review traffic source logs for days 10-12",
            "Check for data-center IP clusters in bid requests",
            "Notify MRC-accredited verification vendor for post-incident review",
        ],
    },
    {
        "id": "INC-003",
        "partner": "Partner Foxtrot",
        "domain": "foxtrot-tv.com",
        "type": "demand_drop",
        "summary": "Two major DSP buyers pulled back spend starting 2026-03-21 (day 8). "
                   "Combined daily spend from affected buyers dropped ~85%. "
                   "Remaining DSPs maintained normal spend levels.",
        "severity": "medium",
        "detected": "2026-03-21",
        "status": "open",
        "signals": [
            "Affected DSP spend: -85%",
            "Unaffected DSP spend: stable",
            "No corresponding IVT or ads.txt issues detected",
        ],
        "recommended_actions": [
            "Contact affected DSP account managers for buyer-side blocklist changes",
            "Check if brand safety category reclassification occurred",
            "Review deal ID / PMP status for affected buyers",
        ],
    },
]


def get_incidents_for_partner(partner: str) -> list[dict[str, Any]]:
    return [inc for inc in INCIDENTS if inc["partner"] == partner]


def get_incident_by_id(incident_id: str) -> dict[str, Any] | None:
    for inc in INCIDENTS:
        if inc["id"] == incident_id:
            return inc
    return None
