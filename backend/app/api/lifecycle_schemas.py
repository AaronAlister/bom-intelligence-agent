from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class LifecycleResponse(BaseModel):
    """Current lifecycle assessment for a component."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    component_id: int
    status: str
    risk: str

    eol_date: date | None
    last_buy_date: date | None

    created_at: datetime


class LifecycleHistoryResponse(BaseModel):
    """Lifecycle history for a component."""

    component_id: int
    records: list[LifecycleResponse]