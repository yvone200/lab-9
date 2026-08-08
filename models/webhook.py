from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class WebhookSubscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    webhook_url: str
    event_type: str  # e.g., "document.enriched", "document.uploaded"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)