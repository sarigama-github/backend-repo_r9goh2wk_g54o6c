import os
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64

from database import db, create_document, get_documents
from schemas import (
    Patient, Hospital, Doctor, Treatment, Appointment, TravelRequest,
    Document, ChatMessage, Review, AnalyticsEvent, Staff
)

APP_NAME = "MediBridge Bangalore API"

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------ Base Routes ------------------------
@app.get("/")
def root():
    return {"app": APP_NAME, "status": "ok"}

@app.get("/test")
def test_database():
    info = {
        "backend": "running",
        "database": "not connected" if db is None else "connected",
        "collections": []
    }
    try:
        if db is not None:
            info["collections"] = db.list_collection_names()
    except Exception as e:
        info["error"] = str(e)
    return info

# ------------------------ Seed sample data on first run ------------------------
@app.on_event("startup")
async def seed_sample():
    if db is None:
        return
    # Seed hospitals
    if "hospital" not in db.list_collection_names() or db.hospital.count_documents({}) == 0:
        create_document("hospital", Hospital(
            name="Narayana Health City",
            type="multi-specialty",
            address="Bommasandra, Bengaluru",
            city="Bengaluru",
            state="Karnataka",
            country="India",
            accreditation="NABH/JCI",
            specialties=["cardiac", "orthopedic", "oncology", "neuro"],
            rating=4.6,
            emergency_helpline="1800-123-4567",
            website="https://www.narayanahealth.org/",
            images=[]
        ))
        create_document("hospital", Hospital(
            name="Manipal Hospital Old Airport Road",
            type="multi-specialty",
            address="HAL Old Airport Rd, Bengaluru",
            city="Bengaluru",
            state="Karnataka",
            country="India",
            accreditation="NABH",
            specialties=["cardiac", "fertility", "orthopedic", "dental"],
            rating=4.5,
            emergency_helpline="080-2222-3333",
            website="https://www.manipalhospitals.com/",
            images=[]
        ))
    # Seed treatments
    if "treatment" not in db.list_collection_names() or db.treatment.count_documents({}) == 0:
        create_document("treatment", Treatment(
            name="CABG - Coronary Bypass", category="cardiac",
            average_cost_inr_min=250000, average_cost_inr_max=450000, typical_stay_days=7, success_rate=95.0
        ))
        create_document("treatment", Treatment(
            name="Total Knee Replacement", category="orthopedic",
            average_cost_inr_min=180000, average_cost_inr_max=350000, typical_stay_days=5
        ))
        create_document("treatment", Treatment(
            name="Dental Implants", category="dental",
            average_cost_inr_min=25000, average_cost_inr_max=60000, typical_stay_days=1
        ))

# ------------------------ Directory Data ------------------------
@app.get("/hospitals")
def list_hospitals(q: Optional[str] = None, specialty: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if q:
        filt["name"] = {"$regex": q, "$options": "i"}
    if specialty:
        filt["specialties"] = {"$in": [specialty]}
    hospitals = get_documents("hospital", filt)
    for h in hospitals:
        if "_id" in h:
            h["id"] = str(h.pop("_id"))
    return hospitals

@app.post("/hospitals")
def create_hospital(payload: Hospital):
    hid = create_document("hospital", payload)
    return {"id": hid}

@app.get("/doctors")
def list_doctors(hospital_id: Optional[str] = None, specialty: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if hospital_id:
        filt["hospital_id"] = hospital_id
    if specialty:
        filt["specialty"] = specialty
    docs = get_documents("doctor", filt)
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return docs

@app.post("/doctors")
def create_doctor(payload: Doctor):
    did = create_document("doctor", payload)
    return {"id": did}

@app.get("/treatments")
def list_treatments(category: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if category:
        filt["category"] = category
    ts = get_documents("treatment", filt)
    for t in ts:
        if "_id" in t:
            t["id"] = str(t.pop("_id"))
    return ts

@app.post("/treatments")
def create_treatment(payload: Treatment):
    tid = create_document("treatment", payload)
    return {"id": tid}

# ------------------------ AI-like Recommendation & Cost Estimator ------------------------
class RecommendRequest(BaseModel):
    treatment_category: str
    preference: Optional[str] = None  # cost | success | speed
    comorbidities: List[str] = []

class RecommendResponse(BaseModel):
    recommended_treatments: List[str]
    estimated_cost_inr: Dict[str, float]
    suggested_hospitals: List[str]

@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    treatments = get_documents("treatment", {"category": req.treatment_category})
    if not treatments:
        raise HTTPException(404, "No treatments found for category")
    est_min = min(t.get("average_cost_inr_min", 0) for t in treatments)
    est_max = max(t.get("average_cost_inr_max", 0) for t in treatments)
    adj = 1.0
    if req.preference == "cost":
        adj = 0.9
    elif req.preference == "success":
        adj = 1.1
    adj += 0.05 * len(req.comorbidities)
    hospitals = get_documents("hospital", {"specialties": {"$in": [req.treatment_category]}})
    return RecommendResponse(
        recommended_treatments=[t["name"] for t in treatments][:5],
        estimated_cost_inr={"min": round(est_min * adj, 2), "max": round(est_max * adj, 2)},
        suggested_hospitals=[h["name"] for h in hospitals][:5]
    )

# ------------------------ Appointments & Teleconsultations ------------------------
@app.post("/appointments")
def create_appointment(payload: Appointment):
    aid = create_document("appointment", payload)
    return {"id": aid}

# ------------------------ Travel & Concierge ------------------------
@app.post("/travel-requests")
def create_travel_request(payload: TravelRequest):
    tid = create_document("travelrequest", payload)
    return {"id": tid}

# ------------------------ Chat with Coordinators ------------------------
@app.post("/chat/send")
def send_message(payload: ChatMessage):
    mid = create_document("chatmessage", payload)
    return {"id": mid}

# ------------------------ Document Upload (Base64-encoded storage) ------------------------
@app.post("/documents/upload")
async def upload_document(patient_id: str, file: UploadFile = File(...)):
    content = await file.read()
    encrypted_b64 = base64.b64encode(content).decode("utf-8")
    doc = Document(
        patient_id=patient_id,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        encrypted_b64=encrypted_b64,
        size_bytes=len(content),
    )
    did = create_document("document", doc)
    return {"id": did}

# ------------------------ Reviews & Stories ------------------------
@app.post("/reviews")
def create_review(payload: Review):
    rid = create_document("review", payload)
    return {"id": rid}

@app.get("/reviews")
def list_reviews(hospital_id: Optional[str] = None, doctor_id: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if hospital_id:
        filt["hospital_id"] = hospital_id
    if doctor_id:
        filt["doctor_id"] = doctor_id
    revs = get_documents("review", filt)
    for r in revs:
        if "_id" in r:
            r["id"] = str(r.pop("_id"))
    return revs

# ------------------------ Analytics ------------------------
@app.post("/analytics")
def track_event(payload: AnalyticsEvent):
    eid = create_document("analyticsevent", payload)
    return {"id": eid}

# ------------------------ Utilities ------------------------
@app.get("/languages")
def languages():
    return {"supported": ["en", "ar", "fr", "ru", "es", "bn", "ne", "ml", "kn"], "default": "en"}

@app.get("/contact/whatsapp")
def whatsapp_link(phone_e164: str, text: Optional[str] = None):
    base = "https://wa.me/" + phone_e164.replace("+", "")
    if text:
        from urllib.parse import urlencode
        return {"url": base + "?" + urlencode({"text": text})}
    return {"url": base}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
