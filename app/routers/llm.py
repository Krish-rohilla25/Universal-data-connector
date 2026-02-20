"""
LLM function-calling interface router.

Endpoint: GET /llm/functions

Returns the list of all available function schemas in OpenAI function-calling
format.  An LLM can call this endpoint at the start of a session to discover
what data sources it can query and what parameters each one accepts.

This is the key piece that makes the Universal Data Connector work as an
LLM tool – the agent can inspect this endpoint and then call /data/* endpoints
to fetch the actual data.

Endpoint: POST /llm/call
Accepts a function_name + arguments dict and routes to the right connector.
This makes it trivial to integrate with OpenAI or Anthropic tool-use:
the LLM generates the call, your orchestration layer hits this endpoint,
and the structured DataResponse comes back for the LLM to summarise.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.connectors.analytics_connector import AnalyticsConnector
from app.models.common import DataResponse, DataMeta, PaginationInfo
from app.services.business_rules import apply_voice_limits, get_freshness_label, prioritise_support_tickets
from app.services.data_identifier import identify_data_type
from app.services.voice_optimizer import build_voice_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM Function Calling"])

# Connector pool – one instance each, shared across requests
_connectors = {
    "get_crm_customers": CRMConnector(),
    "get_support_tickets": SupportConnector(),
    "get_analytics_metrics": AnalyticsConnector(),
}

# Map function name -> source name label used in metadata
_source_labels = {
    "get_crm_customers": "crm",
    "get_support_tickets": "support",
    "get_analytics_metrics": "analytics",
}


class FunctionCallRequest(BaseModel):
    """Body schema for POST /llm/call.

    Mirrors the shape that OpenAI passes back after a function_call response,
    so your orchestration layer can forward it here with minimal translation.
    """

    function_name: str
    arguments: Dict[str, Any] = {}


@router.get(
    "/functions",
    summary="List available LLM function schemas",
    description=(
        "Returns the OpenAI-compatible function-calling schemas for all data connectors. "
        "Call this endpoint at the start of a session to populate the LLM's tools list."
    ),
)
def list_functions():
    """Return all connector schemas in OpenAI function-calling format."""
    schemas = [connector.llm_schema() for connector in _connectors.values()]
    logger.info("LLM /functions called – returning %d schemas", len(schemas))
    return {
        "functions": schemas,
        "usage_note": (
            "Call POST /llm/call with function_name + arguments to execute any of these functions. "
            "All responses follow the DataResponse schema with a voice_summary field."
        ),
    }


@router.post(
    "/call",
    response_model=DataResponse,
    summary="Execute a function call from an LLM",
    description=(
        "Accepts a function_name and arguments dict (as returned by the LLM's tool-use output) "
        "and returns a structured DataResponse.  The voice_summary field in metadata contains "
        "a ready-to-speak sentence the LLM can read out directly."
    ),
)
def execute_function_call(request: FunctionCallRequest):
    """Route an LLM function call to the appropriate connector and return data."""
    fn_name = request.function_name
    args = request.arguments

    logger.info("LLM /call | function=%s args=%s", fn_name, args)

    connector = _connectors.get(fn_name)
    if connector is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown function '{fn_name}'. "
                f"Valid functions: {list(_connectors.keys())}"
            ),
        )

    source = _source_labels[fn_name]
    limit = args.pop("limit", 10)
    voice_mode = args.pop("voice_mode", True)  # LLM calls default to voice mode
    aggregate = args.get("aggregate", False)

    # Fetch records, passing remaining args as connector filters
    raw = connector.fetch(**args)
    total = len(raw)

    # Apply business rules
    if source == "support":
        raw = prioritise_support_tickets(raw)

    paged = apply_voice_limits(raw, limit=limit, voice_mode=voice_mode)
    data_type = identify_data_type(paged)

    # Build the response envelope
    applied_filters = {k: v for k, v in args.items() if v is not None}

    # For aggregated analytics, enrich filters with real numbers for the voice summary
    if source == "analytics" and aggregate and paged:
        agg = paged[0]
        applied_filters["_avg"] = agg.get("average")
        applied_filters["_min"] = agg.get("minimum")
        applied_filters["_max"] = agg.get("maximum")
        applied_filters["_days"] = agg.get("total_data_points", "")

    meta = DataMeta(
        source=source,
        data_type=data_type,
        voice_summary=build_voice_summary(source, data_type, len(paged), total, applied_filters),
        data_freshness=get_freshness_label(),
        applied_filters={k: v for k, v in applied_filters.items() if not k.startswith("_")},
        pagination=PaginationInfo(
            total_records=total,
            returned_records=len(paged),
            page=1,
            page_size=limit,
            has_more=total > len(paged),
        ),
    )

    return DataResponse(data=paged, metadata=meta)
