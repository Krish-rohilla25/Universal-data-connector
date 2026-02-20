"""
Data type identification service.

Looks at the structure of the first record in a dataset and returns a label
that helps the LLM understand what kind of data it's dealing with.  The LLM
can use this label to decide whether to read values out directly ("the MRR is
$1,200") or to describe the structure ("I have a list of 10 customers for you").
"""

from typing import Any, Dict, List


def identify_data_type(data: List[Dict[str, Any]]) -> str:
    """Infer the logical type of a dataset by inspecting its fields.

    This is intentionally simple – we look at the presence of well-known keys.
    In a real system this could be driven by a schema registry.

    Args:
        data: The list of records to inspect.

    Returns:
        A short label string: tabular_crm | tabular_support | time_series | aggregated | unknown | empty
    """
    if not data:
        return "empty"

    first = data[0]

    # Analytics connector returns an _aggregated flag when summarising
    if first.get("_aggregated"):
        return "aggregated"

    # Analytics raw rows have metric + date + value
    if "metric" in first and "date" in first and "value" in first:
        return "time_series"

    # Support tickets have a ticket_id
    if "ticket_id" in first:
        return "tabular_support"

    # CRM records have a customer_id
    if "customer_id" in first:
        return "tabular_crm"

    return "unknown"
