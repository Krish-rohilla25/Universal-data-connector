"""Pydantic model for analytics / metrics records."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyticsRecord(BaseModel):
    """A single daily metric data point."""

    metric: str = Field(..., description="Name of the metric (daily_active_users | new_signups | churn_rate | revenue_usd)")
    date: str = Field(..., description="Date the measurement was taken (YYYY-MM-DD)")
    value: float = Field(..., description="Numeric value of the metric on this date")


class AnalyticsSummary(BaseModel):
    """Aggregated view of a metric over a date range, used for voice responses."""

    metric: str
    period_start: str
    period_end: str
    average: float
    minimum: float
    maximum: float
    total_data_points: int
