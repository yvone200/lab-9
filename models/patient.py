from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional

class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    date_of_birth: datetime
    phone: str = Field(index=True)
    email: Optional[str] = None
    address: Optional[str] = None
    medical_notes: Optional[str] = None
    
    doctor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_by: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PatientCreate(SQLModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    date_of_birth: datetime
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    medical_notes: Optional[str] = None
    doctor_id: Optional[int] = None

class PatientUpdate(SQLModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    date_of_birth: Optional[datetime] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    medical_notes: Optional[str] = None
    doctor_id: Optional[int] = None