"""Pydantic model for support ticket records."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class SupportTicket(BaseModel):
    """A single support ticket record as stored in support_tickets.json."""

    ticket_id: int = Field(..., description="Unique ticket identifier")
    customer_id: int = Field(..., description="ID of the customer who opened the ticket")
    subject: str = Field(..., description="Short one-line description of the issue")
    priority: str = Field(..., description="Ticket priority (low | medium | high)")
    created_at: str = Field(..., description="ISO 8601 timestamp when the ticket was created")
    updated_at: Optional[str] = Field(None, description="ISO 8601 timestamp of the last update")
    status: str = Field(..., description="Ticket status (open | in_progress | closed)")
    assigned_agent: Optional[str] = Field(None, description="Agent currently handling the ticket, if any")
