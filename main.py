from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select, or_
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime
from typing import List

from database.session import get_session, create_tables
from models.user import User, UserCreate, UserResponse
from models.patient import Patient, PatientCreate, PatientUpdate
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_current_admin, get_current_doctor, get_receptionist_or_above
)

app = FastAPI(title="ClinicGuard API", version="1.0.0")
from models.audit import AuditLog

def log_patient_access(session: Session, user_id: int, action: str, endpoint: str, patient_id: Optional[int] = None, ip: Optional[str] = None):
    log = AuditLog(
        user_id=user_id,
        patient_id=patient_id,
        action=action,
        endpoint=endpoint,
        ip_address=ip
    )
    session.add(log)
    session.commit()


# Setup Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.on_event("startup")
def on_startup():
    create_tables()

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/register", status_code=201)
@limiter.limit("5/minute")
def register_user(
    request: Request,
    user_data: UserCreate,
    session: Session = Depends(get_session)
):
    if session.exec(select(User).where(User.username == user_data.username)).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    if session.exec(select(User).where(User.email == user_data.email)).first():
        raise HTTPException(status_code=409, detail="Email already exists")
    
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return {"message": "User created successfully", "user": db_user}

@app.post("/login")
@limiter.limit("5/minute")
def login_user(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")
    
    user.last_login = datetime.utcnow()
    session.commit()
    
    token = create_access_token({"sub": user.username})
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 30 * 60,
        "username": user.username,
        "role": user.role
    }

# ==================== PATIENT ENDPOINTS ====================

@app.post("/patients", status_code=201)
@limiter.limit("20/hour")
def create_patient(
    request: Request,
    patient_data: PatientCreate,
    current_user: User = Depends(get_receptionist_or_above),
    session: Session = Depends(get_session)
):
    if patient_data.doctor_id:
        doctor = session.get(User, patient_data.doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        if doctor.role not in ["admin", "doctor"]:
            raise HTTPException(status_code=400, detail="Assigned user must be a doctor")
            
    db_patient = Patient(**patient_data.dict(), created_by=current_user.id)
    session.add(db_patient)
    session.commit()
    session.refresh(db_patient)
    return db_patient

@app.get("/patients")
@limiter.limit("30/minute")
def list_patients(
    request: Request,
    current_user: User = Depends(get_receptionist_or_above),
    session: Session = Depends(get_session)
):
    query = select(Patient)
    if current_user.role == "doctor":
        query = query.where(Patient.doctor_id == current_user.id)
    return session.exec(query).all()

# --- Exercise 2: Unassigned Patients & Claim Workflow ---

@app.get("/patients/unassigned")
@limiter.limit("20/minute")
def list_unassigned_patients(
    request: Request,
    current_user: User = Depends(get_current_doctor),
    session: Session = Depends(get_session)
):
    return session.exec(select(Patient).where(Patient.doctor_id == None)).all()

@app.patch("/patients/{patient_id}/claim")
def claim_patient(
    patient_id: int,
    current_user: User = Depends(get_current_doctor),
    session: Session = Depends(get_session)
):
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    patient.doctor_id = current_user.id
    patient.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(patient)
    return {"message": "Patient claimed successfully", "patient": patient}

# --- Exercise 3: Secure Patient Search ---

@app.get("/patients/search")
@limiter.limit("20/minute")
def search_patients(
    request: Request,
    q: str,
    current_user: User = Depends(get_current_doctor),
    session: Session = Depends(get_session)
):
    query = select(Patient).where(
        or_(
            Patient.first_name.ilike(f"%{q}%"),
            Patient.last_name.ilike(f"%{q}%")
        )
    )
    if current_user.role == "doctor":
        query = query.where(Patient.doctor_id == current_user.id)
        
    return session.exec(query).all()

@app.get("/patients/{patient_id}")
@limiter.limit("30/minute")
def get_patient(
    request: Request,
    patient_id: int,
    current_user: User = Depends(get_receptionist_or_above),
    session: Session = Depends(get_session)
):
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if current_user.role == "doctor" and patient.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this patient record")
    return patient

@app.patch("/patients/{patient_id}")
def update_patient(
    patient_id: int,
    patient_update: PatientUpdate,
    current_user: User = Depends(get_current_doctor),
    session: Session = Depends(get_session)
):
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if current_user.role != "admin" and patient.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update your own patients")
    
    for key, value in patient_update.dict(exclude_unset=True).items():
        setattr(patient, key, value)
    
    patient.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(patient)
    return patient

@app.delete("/patients/{patient_id}")
def delete_patient(
    patient_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    session.delete(patient)
    session.commit()
    return {"message": "Patient record deleted"}

# ==================== ADMIN USER MANAGEMENT ====================

@app.get("/users", response_model=List[UserResponse])
def list_users(
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    return session.exec(select(User)).all()

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    new_role: str,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    if new_role not in ["admin", "doctor", "receptionist"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot change your own role")
    
    user.role = new_role
    session.commit()
    return {"message": f"User {user.username} role updated to {new_role}"}

@app.patch("/users/{user_id}/activate")
def toggle_user_activation(
    user_id: int,
    activate: bool,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate yourself")
    
    user.is_active = activate
    session.commit()
    return {"message": f"User {user.username} activation set to {activate}"}