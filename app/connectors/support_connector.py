"""
Support ticket connector – reads ticket data from support_tickets.json.

Supports filtering by status, priority, and customer_id so the LLM can
answer questions like "are there any open high-priority tickets right now?".
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class SupportConnector(BaseConnector):
    source_name = "support"
    data_type = "tabular_support"

    def _load(self) -> List[Dict[str, Any]]:
        path = Path(settings.DATA_DIR) / "support_tickets.json"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def fetch(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        customer_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Fetch and filter support ticket records.

        Args:
            status: Filter by ticket status (open | in_progress | closed).
            priority: Filter by priority level (low | medium | high).
            customer_id: Return only tickets belonging to this customer.
            sort_by: Field to sort results by.  Defaults to created_at.
            sort_desc: When True, most-recently-created tickets come first.

        Returns:
            Filtered and sorted list of ticket dicts.
        """
        logger.info(
            "Support fetch | status=%s priority=%s customer_id=%s sort_by=%s desc=%s",
            status, priority, customer_id, sort_by, sort_desc,
        )

        records = self._load()

        if status:
            records = [r for r in records if r.get("status") == status]

        if priority:
            records = [r for r in records if r.get("priority") == priority]

        if customer_id is not None:
            records = [r for r in records if r.get("customer_id") == customer_id]

        records.sort(key=lambda r: r.get(sort_by, ""), reverse=sort_desc)

        logger.info("Support fetch returned %d records", len(records))
        return records

    def llm_schema(self) -> Dict[str, Any]:
        """OpenAI function-calling schema for querying the support ticket system."""
        return {
            "name": "get_support_tickets",
            "description": (
                "Retrieve support tickets from the help-desk system. "
                "Use this when the user asks about issues, tickets, bugs, or customer complaints."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["open", "in_progress", "closed"],
                        "description": "Filter tickets by their current status.",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Filter tickets by priority.",
                    },
                    "customer_id": {
                        "type": "integer",
                        "description": "Return only tickets for this specific customer.",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["created_at", "updated_at", "priority"],
                        "description": "Field to sort results by.  Defaults to created_at.",
                    },
                    "sort_desc": {
                        "type": "boolean",
                        "description": "Sort descending (newest first) when true.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return.",
                    },
                },
                "required": [],
            },
        }
