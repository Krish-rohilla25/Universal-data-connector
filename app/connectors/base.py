"""
Abstract base class for all data connectors.

Every connector must implement:
- fetch(**kwargs)  – returns raw list of records (filtered as requested)
- data_type        – a string label describing the schema (for the LLM)
- llm_schema       – an OpenAI-compatible function-calling schema dict

Keeping these on the base class means the router can call any connector
uniformly without caring about which data source it's talking to.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseConnector(ABC):
    """Common interface that all data source connectors must satisfy."""

    # Subclasses override these class-level attributes
    source_name: str = "unknown"
    data_type: str = "unknown"

    @abstractmethod
    def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        """Retrieve records from the underlying data source.

        Subclasses should accept keyword arguments that map to the query
        parameters defined in their llm_schema (filters, sorts, etc.).

        Returns:
            A list of raw record dicts.  The caller is responsible for
            applying voice / pagination rules on top.
        """
        ...

    @abstractmethod
    def llm_schema(self) -> Dict[str, Any]:
        """Return an OpenAI function-calling compatible schema for this connector.

        The schema describes what parameters the LLM can pass when it wants to
        query this data source.  This is surfaced via the /llm/functions endpoint
        so the LLM can discover available tools at runtime.
        """
        ...
