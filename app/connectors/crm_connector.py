"""
CRM connector – reads customer data from customers.json.

Supports filtering by status, plan, and a simple name search so the LLM
can ask questions like "show me all active enterprise customers".
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class CRMConnector(BaseConnector):
    source_name = "crm"
    data_type = "tabular_crm"

    def _load(self) -> List[Dict[str, Any]]:
        path = Path(settings.DATA_DIR) / "customers.json"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def fetch(
        self,
        status: Optional[str] = None,
        plan: Optional[str] = None,
        name_search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Fetch and filter customer records.

        Args:
            status: Filter by account status (active | inactive | churned).
            plan: Filter by subscription plan (free | starter | pro | enterprise).
            name_search: Case-insensitive substring match on the customer name.
            sort_by: Field to sort results by.  Defaults to created_at.
            sort_desc: When True, newest records come first.

        Returns:
            Filtered and sorted list of customer dicts.
        """
        logger.info(
            "CRM fetch | status=%s plan=%s name_search=%s sort_by=%s desc=%s",
            status, plan, name_search, sort_by, sort_desc,
        )

        records = self._load()

        # Apply filters one by one so it's easy to read and follow
        if status:
            records = [r for r in records if r.get("status") == status]

        if plan:
            records = [r for r in records if r.get("plan") == plan]

        if name_search:
            needle = name_search.lower()
            records = [r for r in records if needle in r.get("name", "").lower()]

        # Sort – fall back gracefully if the requested field doesn't exist
        records.sort(key=lambda r: r.get(sort_by, ""), reverse=sort_desc)

        logger.info("CRM fetch returned %d records", len(records))
        return records

    def llm_schema(self) -> Dict[str, Any]:
        """OpenAI function-calling schema for querying the CRM data source."""
        return {
            "name": "get_crm_customers",
            "description": (
                "Retrieve customer records from the CRM system. "
                "Use this when the user asks about customers, accounts, subscriptions, or churn."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "inactive", "churned"],
                        "description": "Filter customers by their account status.",
                    },
                    "plan": {
                        "type": "string",
                        "enum": ["free", "starter", "pro", "enterprise"],
                        "description": "Filter customers by their subscription plan.",
                    },
                    "name_search": {
                        "type": "string",
                        "description": "Case-insensitive substring to search within customer names.",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["created_at", "name", "mrr_usd"],
                        "description": "Field to sort results by.  Defaults to created_at.",
                    },
                    "sort_desc": {
                        "type": "boolean",
                        "description": "Sort descending (newest first) when true.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return.  Defaults to 10 for voice contexts.",
                    },
                },
                "required": [],
            },
        }
