from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.aggregation import NormalizedDaily, aggregate_weekly, raw_hash


def row(day: date, platform: str, spend: str, installs: str) -> NormalizedDaily:
    return NormalizedDaily(
        date=day,
        platform=platform,
        account_id="account",
        campaign="campaign",
        spend=Decimal(spend),
        installs=Decimal(installs),
        raw_hash=raw_hash({"date": day.isoformat(), "platform": platform}),
    )


def test_week_bucketing_uses_monday_to_sunday_from_base_date() -> None:
    weeks = aggregate_weekly(
        [
            row(date(2025, 12, 29), "meta", "10", "5"),
            row(date(2026, 1, 4), "meta", "20", "10"),
            row(date(2026, 1, 5), "meta", "30", "15"),
        ],
        date(2025, 12, 29),
        date(2026, 1, 5),
    )

    assert weeks[0]["weekNumber"] == 1
    assert weeks[0]["weekStart"] == "2025-12-29"
    assert weeks[0]["weekEnd"] == "2026-01-04"
    assert weeks[0]["meta"]["spend"] == 30.0
    assert weeks[0]["meta"]["installs"] == 15
    assert weeks[1]["weekNumber"] == 2
    assert weeks[1]["weekStart"] == "2026-01-05"
    assert weeks[1]["meta"]["spend"] == 30.0


def test_cpd_is_null_when_installs_are_zero() -> None:
    weeks = aggregate_weekly(
        [row(date(2025, 12, 29), "google", "50", "0")],
        date(2025, 12, 29),
        date(2026, 1, 4),
    )

    assert weeks[0]["google"]["cpd"] is None
    assert weeks[0]["total"]["cpd"] is None


def test_total_cpd_uses_summed_spend_over_summed_installs() -> None:
    weeks = aggregate_weekly(
        [
            row(date(2025, 12, 29), "meta", "10", "2"),
            row(date(2025, 12, 30), "tiktok", "20", "8"),
        ],
        date(2025, 12, 29),
        date(2026, 1, 4),
    )

    assert weeks[0]["total"]["spend"] == 30.0
    assert weeks[0]["total"]["installs"] == 10
    assert weeks[0]["total"]["cpd"] == 3.0

