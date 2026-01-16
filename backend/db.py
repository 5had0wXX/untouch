import os
from typing import List

import asyncpg

from .models import Lead

DATABASE_URL = os.getenv("DATABASE_URL")

LEAD_QUERY = """
SELECT
  id,
  name,
  type,
  score,
  ST_Y(geom::geometry) AS lat,
  ST_X(geom::geometry) AS lng,
  updated_at::text AS date,
  summary,
  signals
FROM p3_leads
WHERE ST_DWithin(
  geom::geography,
  ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography,
  $3
)
ORDER BY score DESC
LIMIT 50;
"""


def meters_from_miles(miles: float) -> float:
  return miles * 1609.34


async def fetch_leads(lat: float, lng: float, radius_miles: float) -> List[Lead]:
  if not DATABASE_URL:
    return Lead.sample_data()

  conn = await asyncpg.connect(DATABASE_URL)
  try:
    rows = await conn.fetch(LEAD_QUERY, lng, lat, meters_from_miles(radius_miles))
    return [Lead.from_record(row) for row in rows]
  finally:
    await conn.close()


async def fetch_lead(lead_id: str) -> Lead | None:
  if not DATABASE_URL:
    return next((lead for lead in Lead.sample_data() if lead.id == lead_id), None)

  conn = await asyncpg.connect(DATABASE_URL)
  try:
    row = await conn.fetchrow(
      "SELECT id, name, type, score, ST_Y(geom::geometry) AS lat, ST_X(geom::geometry) AS lng, updated_at::text AS date, summary, signals FROM p3_leads WHERE id = $1",
      lead_id,
    )
    return Lead.from_record(row) if row else None
  finally:
    await conn.close()
