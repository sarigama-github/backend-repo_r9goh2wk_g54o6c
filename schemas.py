"""
Database Schemas for Medical Tourism Platform (Bangalore Focus)

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercase of the class name.

Use these schemas with the provided database helpers:
- create_document(collection_name, data)
- get_documents(collection_name, filter_dict, limit)
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal, Dict
from datetime import datetime

# ----------------------------- Core Users -----------------------------
class Patient(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = Field("en", description="Preferred language code")
    password_hash: str
    passport_number: Optional[str] = None
    medical_history: Optional[str] = None
    is_verified: bool = True

class Hospital(BaseModel):
    name: str
    type: Literal["multi-specialty", "specialty", "clinic"] = "multi-specialty"
    address: str
    city: str = "Bengaluru"
    state: str = "Karnataka"
    country: str = "India"
    accreditation: Optional[str] = None
    specialties: List[str] = []
    rating: float = 4.5
    reviews_count: int = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    emergency_helpline: Optional[str] = None
    website: Optional[str] = None
    images: List[str] = []

class Doctor(BaseModel):
    name: str
    hospital_id: str
    specialty: str
    experience_years: int = 5
    rating: float = 4.6
    languages: List[str] = ["en", "hi", "kn"]
    credentials: List[str] = []
    bio: Optional[str] = None
    consultation_fee: float = 1000.0

class Treatment(BaseModel):
    name: str
    category: Literal[
        "cardiac", "orthopedic", "dental", "cosmetic", "fertility", "oncology", "neuro", "general"
    ] = "general"
    description: Optional[str] = None
    average_cost_inr_min: float
    average_cost_inr_max: float
    typical_stay_days: int = 3
    success_rate: Optional[float] = Field(None, ge=0, le=100)
    hospitals: List[str] = []  # hospital_ids that offer

# ----------------------------- Operational -----------------------------
class Appointment(BaseModel):
    patient_id: str
    doctor_id: str
    hospital_id: str
    datetime_iso: str
    type: Literal["in_person", "teleconsult"] = "in_person"
    status: Literal["pending", "confirmed", "completed", "cancelled"] = "pending"
    notes: Optional[str] = None

class TravelRequest(BaseModel):
    patient_id: str
    services: List[str] = ["visa_guidance", "airport_pickup", "accommodation"]
    travel_dates: Dict[str, Optional[str]] = {"arrival": None, "departure": None}
    passengers: int = 1
    budget_inr: Optional[float] = None
    notes: Optional[str] = None

class Document(BaseModel):
    patient_id: str
    filename: str
    content_type: str
    encrypted_b64: str
    size_bytes: int

class ChatMessage(BaseModel):
    room_id: str
    sender_id: str
    sender_role: Literal["patient", "hospital", "facilitator", "admin"] = "patient"
    content: str
    type: Literal["text", "file"] = "text"

class Review(BaseModel):
    patient_id: str
    hospital_id: Optional[str] = None
    doctor_id: Optional[str] = None
    rating: float = Field(..., ge=1, le=5)
    title: Optional[str] = None
    comment: Optional[str] = None

class AnalyticsEvent(BaseModel):
    user_id: Optional[str] = None
    event: str
    properties: Dict[str, str] = {}
    ts: datetime = Field(default_factory=datetime.utcnow)

# Dashboard role user for hospitals/facilitators
class Staff(BaseModel):
    name: str
    email: EmailStr
    role: Literal["hospital_admin", "coordinator", "facilitator", "analyst"] = "coordinator"
    org_id: Optional[str] = None  # hospital id or facilitator org id
    password_hash: str
