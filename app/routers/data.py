"""
Data router – the main query interface for all three data sources.

Endpoint: GET /data/{source}

The {source} path parameter selects the connector (crm | support | analytics).
All other query parameters are forwarded to the connector's fetch() method as
keyword arguments.  This keeps the router thin – it only handles HTTP concerns
(validation, error responses, pagination envelope) and delegates data logic to
the connector + services layers.

The response always follows the DataResponse schema which the LLM can parse
to construct a spoken reply.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import JSONResponse

from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.connectors.analytics_connector import AnalyticsConnector
from app.models.common import DataResponse, DataMeta, PaginationInfo
from app.services.business_rules import (
    apply_voice_limits,
    prioritise_support_tickets,
    get_freshness_label,
)
from app.services.data_identifier import identify_data_type
from app.services.voice_optimizer import build_voice_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["Data"])

# Map of source name -> connector instance.
# Instantiated once at module load time so there's no overhead per request.
CONNECTOR_MAP = {
    "crm": CRMConnector(),
    "support": SupportConnector(),
    "analytics": AnalyticsConnector(),
}


@router.get(
    "/crm",
    response_model=DataResponse,
    summary="Query CRM customer data",
    description=(
        "Returns customer records with optional filtering by status, plan, and name. "
        "Results are capped for voice contexts.  Ideal for LLM function calling."
    ),
)
def get_crm_data(
    status: Optional[str] = Query(None, description="Filter by account status: active | inactive | churned"),
    plan: Optional[str] = Query(None, description="Filter by subscription plan: free | starter | pro | enterprise"),
    name_search: Optional[str] = Query(None, description="Substring search on customer name"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_desc: bool = Query(True, description="Sort descending when true"),
    limit: int = Query(10, ge=1, le=100, description="Max records to return"),
    voice_mode: bool = Query(False, description="Apply tighter limits suited for voice responses"),
):
    """Retrieve CRM customer records."""
    logger.info("GET /data/crm | status=%s plan=%s name=%s limit=%d voice=%s",
                status, plan, name_search, limit, voice_mode)

    connector = CONNECTOR_MAP["crm"]

    raw = connector.fetch(
        status=status,
        plan=plan,
        name_search=name_search,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )

    total = len(raw)
    applied_filters = {k: v for k, v in {"status": status, "plan": plan}.items() if v}

    paged = apply_voice_limits(raw, limit=limit, voice_mode=voice_mode)
    data_type = identify_data_type(paged)

    meta = DataMeta(
        source="crm",
        data_type=data_type,
        voice_summary=build_voice_summary("crm", data_type, len(paged), total, applied_filters),
        data_freshness=get_freshness_label(),
        applied_filters=applied_filters,
        pagination=PaginationInfo(
            total_records=total,
            returned_records=len(paged),
            page=1,
            page_size=limit,
            has_more=total > len(paged),
        ),
    )

    return DataResponse(data=paged, metadata=meta)


@router.get(
    "/support",
    response_model=DataResponse,
    summary="Query support ticket data",
    description=(
        "Returns support tickets with optional filtering by status, priority, and customer. "
        "High-priority open tickets are automatically promoted to the top of results."
    ),
)
def get_support_data(
    status: Optional[str] = Query(None, description="Filter by ticket status: open | in_progress | closed"),
    priority: Optional[str] = Query(None, description="Filter by priority: low | medium | high"),
    customer_id: Optional[int] = Query(None, description="Filter to tickets from a specific customer"),
    sort_desc: bool = Query(True, description="Sort descending (newest first) when true"),
    limit: int = Query(10, ge=1, le=100, description="Max records to return"),
    voice_mode: bool = Query(False, description="Apply tighter limits suited for voice responses"),
):
    """Retrieve support ticket records."""
    logger.info("GET /data/support | status=%s priority=%s cid=%s limit=%d voice=%s",
                status, priority, customer_id, limit, voice_mode)

    connector = CONNECTOR_MAP["support"]

    raw = connector.fetch(
        status=status,
        priority=priority,
        customer_id=customer_id,
        sort_desc=sort_desc,
    )

    total = len(raw)
    applied_filters = {k: v for k, v in {
        "status": status, "priority": priority, "customer_id": customer_id
    }.items() if v is not None}

    # Business rule: always put urgent open tickets at the front
    prioritised = prioritise_support_tickets(raw)
    paged = apply_voice_limits(prioritised, limit=limit, voice_mode=voice_mode)
    data_type = identify_data_type(paged)

    meta = DataMeta(
        source="support",
        data_type=data_type,
        voice_summary=build_voice_summary("support", data_type, len(paged), total, applied_filters),
        data_freshness=get_freshness_label(),
        applied_filters=applied_filters,
        pagination=PaginationInfo(
            total_records=total,
            returned_records=len(paged),
            page=1,
            page_size=limit,
            has_more=total > len(paged),
        ),
    )

    return DataResponse(data=paged, metadata=meta)


@router.get(
    "/analytics",
    response_model=DataResponse,
    summary="Query analytics metrics data",
    description=(
        "Returns time-series analytics records.  Set aggregate=true to receive a single "
        "min/max/average summary instead of raw rows – ideal for voice responses."
    ),
)
def get_analytics_data(
    metric: Optional[str] = Query(None, description="Metric name: daily_active_users | new_signups | churn_rate | revenue_usd"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD, inclusive)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD, inclusive)"),
    aggregate: bool = Query(False, description="Return a summary (avg/min/max) instead of raw rows"),
    limit: int = Query(10, ge=1, le=100, description="Max records to return"),
    voice_mode: bool = Query(False, description="Apply tighter limits suited for voice responses"),
):
    """Retrieve analytics / metrics records."""
    logger.info("GET /data/analytics | metric=%s from=%s to=%s agg=%s limit=%d voice=%s",
                metric, date_from, date_to, aggregate, limit, voice_mode)

    connector = CONNECTOR_MAP["analytics"]

    raw = connector.fetch(
        metric=metric,
        date_from=date_from,
        date_to=date_to,
        aggregate=aggregate,
    )

    total = len(raw)
    applied_filters = {k: v for k, v in {
        "metric": metric, "date_from": date_from, "date_to": date_to
    }.items() if v is not None}

    # Aggregated responses are always a single record – no further slicing needed
    paged = raw if aggregate else apply_voice_limits(raw, limit=limit, voice_mode=voice_mode)
    data_type = identify_data_type(paged)

    # For aggregated analytics, pull the numbers into applied_filters so the
    # voice optimizer can say something like "average 557, lowest 162, highest 948"
    if aggregate and paged:
        agg = paged[0]
        applied_filters["_avg"] = agg.get("average")
        applied_filters["_min"] = agg.get("minimum")
        applied_filters["_max"] = agg.get("maximum")
        applied_filters["_days"] = agg.get("total_data_points", "")

    meta = DataMeta(
        source="analytics",
        data_type=data_type,
        voice_summary=build_voice_summary("analytics", data_type, len(paged), total, applied_filters),
        data_freshness=get_freshness_label(),
        applied_filters={k: v for k, v in applied_filters.items() if not k.startswith("_")},
        pagination=PaginationInfo(
            total_records=total,
            returned_records=len(paged),
            page=1,
            page_size=limit if not aggregate else total,
            has_more=False if aggregate else total > len(paged),
        ),
    )

    return DataResponse(data=paged, metadata=meta)


@router.get(
    "/{source}",
    response_model=DataResponse,
    summary="Generic data source query (legacy route)",
    description="Fallback route that dispatches to the correct connector by name.",
    include_in_schema=False,  # Hide from docs to avoid confusion with named routes
)
def get_data_generic(
    source: str = Path(..., description="Data source: crm | support | analytics"),
    limit: int = Query(10, ge=1, le=100),
    voice_mode: bool = Query(False),
):
    """Generic dispatcher kept for backward compatibility."""
    if source not in CONNECTOR_MAP:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown data source '{source}'. Valid sources: {list(CONNECTOR_MAP.keys())}",
        )

    connector = CONNECTOR_MAP[source]
    raw = connector.fetch()
    total = len(raw)
    paged = apply_voice_limits(raw, limit=limit, voice_mode=voice_mode)
    data_type = identify_data_type(paged)

    meta = DataMeta(
        source=source,
        data_type=data_type,
        voice_summary=build_voice_summary(source, data_type, len(paged), total, {}),
        data_freshness=get_freshness_label(),
        applied_filters={},
        pagination=PaginationInfo(
            total_records=total,
            returned_records=len(paged),
            page=1,
            page_size=limit,
            has_more=total > len(paged),
        ),
    )

    return DataResponse(data=paged, metadata=meta)
