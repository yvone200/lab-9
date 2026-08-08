# models/audit.py
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    patient_id: Optional[int] = Field(default=None, foreign_key="patient.id")
    action: str  # e.g., "CREATE", "READ", "UPDATE", "DELETE"
    endpoint: str
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)