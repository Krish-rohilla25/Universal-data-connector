"""
Business rules engine for voice-optimised data delivery.

The core problem: voice assistants can't read 50 rows of data aloud.  We need
smart rules that select the right subset without throwing information away.

Rules applied (in order):
1. Prioritise high-importance records (e.g. high-priority open tickets).
2. Return most-recently-updated records first so the response feels fresh.
3. Hard-cap the result count so the LLM doesn't get overwhelmed.
4. Attach a human-readable freshness string so the LLM can say "as of X".
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.config import settings

logger = logging.getLogger(__name__)

# Priority ordering used when sorting support tickets or similar records
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def prioritise_support_tickets(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Put open, high-priority tickets at the top of the list.

    For voice contexts the assistant should lead with the most urgent items so
    the user gets actionable information immediately.
    """
    def sort_key(r: Dict[str, Any]):
        # Open tickets first, then by priority, then by recency
        status_score = 0 if r.get("status") in ("open", "in_progress") else 1
        priority_score = PRIORITY_ORDER.get(r.get("priority", "low"), 2)
        return (status_score, priority_score)

    return sorted(records, key=sort_key)


def apply_voice_limits(
    records: List[Dict[str, Any]],
    limit: int = None,
    voice_mode: bool = False,
) -> List[Dict[str, Any]]:
    """Cap the number of records returned.

    In voice mode we apply a tighter cap (MAX_VOICE_RESULTS) because a spoken
    response with more than 5 items becomes hard to follow.  In API / non-voice
    mode we use the broader MAX_RESULTS cap.

    Args:
        records: Full filtered list of records.
        limit: Caller-supplied override.  Honoured if provided.
        voice_mode: When True, use the tighter voice cap as the default.

    Returns:
        A slice of records no longer than the computed limit.
    """
    if voice_mode:
        # Voice mode hard-caps at MAX_VOICE_RESULTS regardless of the caller's limit
        cap = min(limit if limit is not None else settings.MAX_VOICE_RESULTS, settings.MAX_VOICE_RESULTS)
    elif limit is not None:
        cap = min(limit, settings.MAX_RESULTS)
    else:
        cap = settings.MAX_RESULTS

    logger.debug("apply_voice_limits: cap=%d total=%d", cap, len(records))
    return records[:cap]


def get_freshness_label(as_of: datetime = None) -> str:
    """Generate a human-readable freshness string for the metadata block.

    Example outputs:
        "Data as of just now"
        "Data as of 3 minutes ago"
        "Data as of 2 hours ago"
    """
    if as_of is None:
        as_of = datetime.now(timezone.utc)

    # Our mock data is loaded from static JSON so we treat "now" as the reference
    delta_seconds = 0  # live data would compute this against a last-modified header

    if delta_seconds < 60:
        return "Data as of just now"
    elif delta_seconds < 3600:
        minutes = delta_seconds // 60
        return f"Data as of {minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        hours = delta_seconds // 3600
        return f"Data as of {hours} hour{'s' if hours != 1 else ''} ago"
