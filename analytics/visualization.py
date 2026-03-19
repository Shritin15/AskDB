from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class VizDecision:
    kind: str  # "metric" | "bar" | "line" | "table"
    x: Optional[str] = None
    y: Optional[str] = None


def rows_to_df(columns: list[str], rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=columns)


def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def _try_parse_datetime(series: pd.Series) -> pd.Series:
    # coerce errors -> NaT so we can detect if most values are parseable
    return pd.to_datetime(series, errors="coerce")


def decide_viz(df: pd.DataFrame) -> VizDecision:
    if df is None or df.empty:
        return VizDecision(kind="table")

    # Single cell -> metric if numeric
    if df.shape == (1, 1) and _is_numeric(df.iloc[:, 0]):
        return VizDecision(kind="metric", y=df.columns[0])

    # One row, multiple cols: if there is exactly one numeric col, show metrics-style table
    # We'll just use table for simplicity.
    if df.shape[0] == 1 and df.shape[1] > 1:
        return VizDecision(kind="table")

    # Two columns: try bar or line
    if df.shape[1] == 2:
        c1, c2 = df.columns[0], df.columns[1]

        # If second is numeric and first looks like datetime -> line
        if _is_numeric(df[c2]):
            parsed = _try_parse_datetime(df[c1])
            if parsed.notna().mean() >= 0.8:  # mostly dates
                return VizDecision(kind="line", x=c1, y=c2)
            # else treat first as category -> bar
            return VizDecision(kind="bar", x=c1, y=c2)

    # Default
    return VizDecision(kind="table")