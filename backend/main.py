from typing import List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from .db import fetch_lead, fetch_leads
from .models import Lead

app = FastAPI(title="P3 Site Finder API")


class LeadResponse(BaseModel):
  id: str
  name: str
  type: str
  score: int
  lat: float
  lng: float
  date: str
  summary: str
  signals: dict

  @staticmethod
  def from_lead(lead: Lead) -> "LeadResponse":
    return LeadResponse(
      id=lead.id,
      name=lead.name,
      type=lead.type,
      score=lead.score,
      lat=lead.lat,
      lng=lead.lng,
      date=lead.date,
      summary=lead.summary,
      signals={
        "newsHits": lead.signals.newsHits,
        "powerOutages": lead.signals.powerOutages,
        "imageryFlags": lead.signals.imageryFlags,
        "zoningAlerts": lead.signals.zoningAlerts,
      },
    )


class GeocodeResponse(BaseModel):
  lat: float
  lng: float


class ChatRequest(BaseModel):
  query: str


class ChatResponse(BaseModel):
  response: str


@app.get("/api/leads", response_model=List[LeadResponse])
async def get_leads(
  lat: float = Query(...),
  lng: float = Query(...),
  radius: float = Query(10, ge=1, le=200),
) -> List[LeadResponse]:
  leads = await fetch_leads(lat=lat, lng=lng, radius_miles=radius)
  return [LeadResponse.from_lead(lead) for lead in leads]


@app.get("/api/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: str) -> LeadResponse:
  lead = await fetch_lead(lead_id)
  if not lead:
    raise HTTPException(status_code=404, detail="Lead not found")
  return LeadResponse.from_lead(lead)


@app.get("/api/geocode", response_model=GeocodeResponse)
async def geocode(address: str = Query(...)) -> GeocodeResponse:
  address = address.lower()
  if "kansas" in address or "kc" in address:
    return GeocodeResponse(lat=39.0997, lng=-94.5786)
  if "denver" in address:
    return GeocodeResponse(lat=39.7392, lng=-104.9903)
  return GeocodeResponse(lat=39.0997, lng=-94.5786)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
  leads = await fetch_leads(lat=39.0997, lng=-94.5786, radius_miles=30)
  if not leads:
    return ChatResponse(response="No leads found in the current radius.")
  top = leads[0]
  response = (
    "Top lead: "
    f"{top.name} ({top.type}) with score {top.score}. "
    "Signals highlight "
    f"{top.signals.newsHits} news hits and {top.signals.imageryFlags[0]} imagery."
  )
  return ChatResponse(response=response)
