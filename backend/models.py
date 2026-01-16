from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class LeadSignals:
  newsHits: int
  powerOutages: int
  imageryFlags: List[str]
  zoningAlerts: int


@dataclass
class Lead:
  id: str
  name: str
  type: str
  score: int
  lat: float
  lng: float
  date: str
  summary: str
  signals: LeadSignals

  @staticmethod
  def from_record(record: Dict[str, Any]) -> "Lead":
    signals = record.get("signals") or {}
    return Lead(
      id=str(record["id"]),
      name=record["name"],
      type=record["type"],
      score=int(record["score"]),
      lat=float(record["lat"]),
      lng=float(record["lng"]),
      date=record["date"],
      summary=record.get("summary") or "",
      signals=LeadSignals(
        newsHits=signals.get("newsHits", 0),
        powerOutages=signals.get("powerOutages", 0),
        imageryFlags=signals.get("imageryFlags", []),
        zoningAlerts=signals.get("zoningAlerts", 0),
      ),
    )

  @staticmethod
  def sample_data() -> List["Lead"]:
    return [
      Lead(
        id="kc-1",
        name="KCI Logistics Campus",
        type="Intermodal",
        score=92,
        lat=39.3156,
        lng=-94.7139,
        date="2024-08-09",
        summary="Strong infrastructure access with underutilized parcels.",
        signals=LeadSignals(
          newsHits=12,
          powerOutages=3,
          imageryFlags=["Vacancy", "Heavy truck traffic"],
          zoningAlerts=2,
        ),
      ),
      Lead(
        id="kc-2",
        name="West Bottoms Revamp",
        type="Mixed-use",
        score=86,
        lat=39.1084,
        lng=-94.6036,
        date="2024-07-22",
        summary="Industrial corridor with renewal grants and active bids.",
        signals=LeadSignals(
          newsHits=8,
          powerOutages=1,
          imageryFlags=["Large vacant lot"],
          zoningAlerts=1,
        ),
      ),
      Lead(
        id="kc-3",
        name="Independence Rail Yard",
        type="Industrial",
        score=79,
        lat=39.0951,
        lng=-94.4211,
        date="2024-06-14",
        summary="Rail-adjacent site with large footprint and low utilization.",
        signals=LeadSignals(
          newsHits=5,
          powerOutages=0,
          imageryFlags=["Idle freight cars"],
          zoningAlerts=0,
        ),
      ),
    ]
