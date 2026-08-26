from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CreateCustomerRequest(BaseModel):
    name: str
    address: str
    phone: str
    service_type: str


class CustomerResponse(BaseModel):
    id: UUID
    name: str
    address: str
    phone: str
    service_type: str
    created_at: datetime
