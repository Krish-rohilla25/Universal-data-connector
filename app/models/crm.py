"""Pydantic model for CRM / customer records."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class Customer(BaseModel):
    """A single customer record as stored in customers.json."""

    customer_id: int = Field(..., description="Unique customer identifier")
    name: str = Field(..., description="Full name of the customer")
    email: str = Field(..., description="Customer email address")
    plan: Optional[str] = Field(None, description="Subscription plan (free | starter | pro | enterprise)")
    mrr_usd: Optional[float] = Field(None, description="Monthly recurring revenue in USD")
    created_at: str = Field(..., description="ISO 8601 timestamp when the customer was created")
    status: str = Field(..., description="Account status (active | inactive | churned)")
