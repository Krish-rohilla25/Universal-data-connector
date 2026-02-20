"""
Shared Pydantic models used across all connectors and routers.

DataResponse is the standard envelope every endpoint returns.  It includes
pagination metadata plus a voice-friendly context string so the LLM can
incorporate "showing 3 of 47 results" into its spoken reply.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PaginationInfo(BaseModel):
    """Tracks where we are in a potentially large result set."""

    total_records: int = Field(..., description="Total records matching the query before pagination")
    returned_records: int = Field(..., description="Number of records actually returned in this response")
    page: int = Field(default=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Maximum records per page")
    has_more: bool = Field(..., description="True when there are additional pages")


class DataMeta(BaseModel):
    """Rich metadata attached to every response.

    This is the information the LLM needs to craft a helpful spoken summary,
    e.g. "Here are the 5 most recent open tickets out of 23 total."
    """

    source: str = Field(..., description="Which data source was queried (crm | support | analytics)")
    data_type: str = Field(..., description="Detected data type (tabular_crm | tabular_support | time_series | unknown)")
    voice_summary: str = Field(..., description="A ready-to-speak single sentence describing the result set")
    data_freshness: str = Field(..., description="Human-readable staleness indicator, e.g. 'Data as of 3 minutes ago'")
    applied_filters: Dict[str, Any] = Field(default_factory=dict, description="Filters that were applied to produce this result")
    pagination: PaginationInfo


class DataResponse(BaseModel):
    """Standard response envelope returned by all /data/* endpoints."""

    data: List[Any]
    metadata: DataMeta


class ErrorDetail(BaseModel):
    """Structured error body so clients can parse failures programmatically."""

    error: str
    detail: Optional[str] = None
