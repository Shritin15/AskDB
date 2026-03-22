from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class VizDecision:
    kind: str  # "metric" | "bar" | "line" | "pie" | "scatter" | "table"
    x: Optional[str] = None
    y: Optional[str] = None


def rows_to_df(columns: list[str], rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=columns)


def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def _looks_like_date(series: pd.Series) -> bool:
    """Heuristic: does this column look like a year/date string?"""
    try:
        parsed = pd.to_datetime(series, errors="coerce")
        if parsed.notna().mean() >= 0.7:
            return True
    except Exception:
        pass
    # Year-like integers (1990-2030)
    if _is_numeric(series):
        vals = series.dropna()
        if len(vals) > 0 and vals.between(1900, 2100).mean() >= 0.7:
            return True
    # String that looks like year: "2013", "2013-01", etc.
    if series.dtype == object:
        sample = series.dropna().astype(str).head(10)
        year_like = sample.str.match(r"^\d{4}").mean()
        if year_like >= 0.7:
            return True
    return False


def _looks_like_category(series: pd.Series) -> bool:
    """Low cardinality text = category."""
    if series.dtype == object:
        n_unique = series.nunique()
        return n_unique <= 50
    return False


def decide_viz(df: pd.DataFrame) -> VizDecision:
    if df is None or df.empty:
        return VizDecision(kind="table")

    cols = list(df.columns)
    n_rows, n_cols = df.shape

    # ── Single cell ──────────────────────────────────────────────────────────
    if n_rows == 1 and n_cols == 1 and _is_numeric(df.iloc[:, 0]):
        return VizDecision(kind="metric", y=cols[0])

    # ── Single row, multiple numeric cols → metric row ───────────────────────
    if n_rows == 1:
        return VizDecision(kind="table")

    # ── Two-column results ───────────────────────────────────────────────────
    if n_cols == 2:
        c1, c2 = cols[0], cols[1]
        c1_num = _is_numeric(df[c1])
        c2_num = _is_numeric(df[c2])

        # Both numeric → scatter
        if c1_num and c2_num:
            return VizDecision(kind="scatter", x=c1, y=c2)

        # col1=label/date, col2=numeric
        if not c1_num and c2_num:
            # Time series → line
            if _looks_like_date(df[c1]):
                return VizDecision(kind="line", x=c1, y=c2)
            # Many categories → bar
            n_unique = df[c1].nunique()
            if n_unique <= 20:
                return VizDecision(kind="bar", x=c1, y=c2)
            return VizDecision(kind="bar", x=c1, y=c2)

        # col1=numeric, col2=label — flip for better display
        if c1_num and not c2_num:
            return VizDecision(kind="bar", x=c2, y=c1)

    # ── Three+ columns ───────────────────────────────────────────────────────
    if n_cols >= 3:
        # Find text and numeric columns
        text_cols = [c for c in cols if not _is_numeric(df[c])]
        num_cols  = [c for c in cols if _is_numeric(df[c])]
        if text_cols and num_cols:
            # Use first text col as x, first numeric as y
            return VizDecision(kind="bar", x=text_cols[0], y=num_cols[0])

    return VizDecision(kind="table")
