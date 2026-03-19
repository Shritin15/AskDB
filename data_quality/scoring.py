"""Confidence scoring for profiled data quality."""

from __future__ import annotations

from typing import Any


def confidence_from_profile(profile: dict[str, Any]) -> str:
    row_count = max(int(profile.get("row_count", 0)), 1)
    missing_total = sum(int(v) for v in profile.get("missing_values", {}).values())
    duplicate_groups = int(profile.get("duplicate_groups", 0))

    issue_ratio = (missing_total + duplicate_groups) / row_count

    if issue_ratio < 0.05:
        return "High"
    if issue_ratio < 0.2:
        return "Medium"
    return "Low"
