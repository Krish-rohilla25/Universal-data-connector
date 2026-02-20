"""
Voice optimisation service.

Turns raw data records into voice-ready summaries.  The goal is to give the
LLM a single, natural-language sentence it can read out verbatim, plus the
raw records so it can answer follow-up questions.

Design decision: we don't strip out the raw records – we just add the summary.
That way the LLM can choose how much detail to use depending on context.
"""

from typing import Any, Dict, List, Optional


def build_voice_summary(
    source: str,
    data_type: str,
    returned: int,
    total: int,
    applied_filters: Dict[str, Any] = None,
) -> str:
    """Compose a short, natural sentence summarising the query result.

    This sentence is placed in the DataMeta.voice_summary field so the LLM
    can use it as a ready-made spoken opener.

    Examples:
        "Showing the 5 most recent open high-priority support tickets out of 12 total."
        "Here are 10 active CRM customers out of 23 matching your filter."
        "Daily active users: average 542 over the last 7 days."

    Args:
        source: Data source name (crm | support | analytics).
        data_type: Detected data type label.
        returned: Number of records being returned.
        total: Total records matching the query before pagination.
        applied_filters: Dict of filters that were applied.

    Returns:
        A single human-readable sentence.
    """
    filters = applied_filters or {}

    # Support tickets
    if source == "support":
        status_phrase = f"{filters['status']} " if "status" in filters else ""
        priority_phrase = f"{filters['priority']}-priority " if "priority" in filters else ""
        noun = "ticket" if returned == 1 else "tickets"
        if total == returned:
            return f"Here are {returned} {priority_phrase}{status_phrase}support {noun}."
        return (
            f"Showing the {returned} most recent {priority_phrase}{status_phrase}"
            f"support {noun} out of {total} total."
        )

    # CRM customers
    if source == "crm":
        status_phrase = f"{filters['status']} " if "status" in filters else ""
        plan_phrase = f"{filters['plan']}-plan " if "plan" in filters else ""
        noun = "customer" if returned == 1 else "customers"
        if total == returned:
            return f"Here are {returned} {plan_phrase}{status_phrase}{noun}."
        return (
            f"Showing {returned} of {total} {plan_phrase}{status_phrase}{noun}."
        )

    # Analytics – aggregated summary (single record)
    # The caller puts the aggregated values into applied_filters so we can speak them
    if source == "analytics" and data_type == "aggregated":
        metric_name = filters.get("metric", "the requested metric").replace("_", " ")
        avg = filters.get("_avg")
        low = filters.get("_min")
        high = filters.get("_max")
        days = filters.get("_days", "")
        period = f" over the last {days} days" if days else ""
        if avg is not None:
            return (
                f"Here's the summary for {metric_name}{period}: "
                f"average {avg:,.0f}, lowest {low:,.0f}, highest {high:,.0f}."
            )
        return f"Here is the aggregated summary for {metric_name}{period}."

    # Analytics – raw time-series rows
    if source == "analytics":
        metric_phrase = f"for {filters['metric']} " if "metric" in filters else ""
        noun = "data point" if returned == 1 else "data points"
        if total == returned:
            return f"Here are {returned} {noun} {metric_phrase}from the analytics system."
        return f"Showing the {returned} most recent {noun} {metric_phrase}out of {total} total."

    # Generic fallback
    return f"Returning {returned} of {total} records from the {source} data source."


def summarize_if_large(records: List[Dict[str, Any]], threshold: int = 10) -> List[Dict[str, Any]]:
    """Legacy helper kept for backward compatibility with the original router stub.

    The preferred approach is to use apply_voice_limits() + build_voice_summary()
    but this function is retained so callers that import it directly continue to work.
    """
    # We no longer collapse records into a single summary dict because that
    # breaks downstream parsing.  Instead we just pass the slice through.
    return records
