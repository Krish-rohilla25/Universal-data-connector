"""
Analytics connector – reads time-series metrics from analytics.json.

Supports filtering by metric name and date range, plus optional aggregation
(average/min/max) that collapses a long time-series into a single summary
number – ideal for voice responses where reading out 30 days of data would
be exhausting for the listener.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class AnalyticsConnector(BaseConnector):
    source_name = "analytics"
    data_type = "time_series"

    def _load(self) -> List[Dict[str, Any]]:
        path = Path(settings.DATA_DIR) / "analytics.json"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def fetch(
        self,
        metric: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        aggregate: bool = False,
        sort_desc: bool = True,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Fetch and (optionally) aggregate analytics records.

        Args:
            metric: Filter to a specific metric name (e.g. daily_active_users).
            date_from: ISO date string (YYYY-MM-DD) – include records on or after this date.
            date_to: ISO date string (YYYY-MM-DD) – include records on or before this date.
            aggregate: When True, collapse all matching rows into a single summary record
                       containing min/max/average.  Great for voice responses.
            sort_desc: When True, most-recent dates appear first.

        Returns:
            Either a list of raw metric records or a one-item list with the aggregated summary.
        """
        logger.info(
            "Analytics fetch | metric=%s date_from=%s date_to=%s aggregate=%s",
            metric, date_from, date_to, aggregate,
        )

        records = self._load()

        if metric:
            records = [r for r in records if r.get("metric") == metric]

        if date_from:
            records = [r for r in records if r.get("date", "") >= date_from]

        if date_to:
            records = [r for r in records if r.get("date", "") <= date_to]

        # Sort by date so pagination is meaningful
        records.sort(key=lambda r: r.get("date", ""), reverse=sort_desc)

        if aggregate and records:
            values = [r["value"] for r in records]
            metric_name = records[0]["metric"] if records else "unknown"
            summary = {
                "metric": metric_name,
                "period_start": min(r["date"] for r in records),
                "period_end": max(r["date"] for r in records),
                "average": round(sum(values) / len(values), 2),
                "minimum": round(min(values), 2),
                "maximum": round(max(values), 2),
                "total_data_points": len(records),
                "_aggregated": True,
            }
            logger.info("Analytics returning aggregated summary over %d points", len(records))
            return [summary]

        logger.info("Analytics fetch returned %d records", len(records))
        return records

    def llm_schema(self) -> Dict[str, Any]:
        """OpenAI function-calling schema for querying the analytics data source."""
        return {
            "name": "get_analytics_metrics",
            "description": (
                "Retrieve product analytics and business metrics. "
                "Use this when the user asks about usage trends, active users, "
                "revenue, signups, or any numeric KPI over time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "enum": ["daily_active_users", "new_signups", "churn_rate", "revenue_usd"],
                        "description": "Which metric to query.  Omit to return all metrics.",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start of date range in YYYY-MM-DD format (inclusive).",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End of date range in YYYY-MM-DD format (inclusive).",
                    },
                    "aggregate": {
                        "type": "boolean",
                        "description": (
                            "When true, return a single summary record with min/max/average "
                            "instead of the raw day-by-day data.  Set to true for voice responses."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return (applies before aggregation).",
                    },
                },
                "required": [],
            },
        }
