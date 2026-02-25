from datetime import date
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class Motion(BaseModel):
  id: int
  title: str
  summary: str
  status: str  # PASSED | FAILED | DEFERRED | AMENDED
  category: str
  impact_tags: List[str]
  full_text: Optional[str] = None


class MeetingOverview(BaseModel):
  meeting_code: str  # e.g., "2026.CC04" or a slug
  title: str
  date: str
  topics: List[str]
  motion_count: int
  region: Optional[str] = None


class MeetingDetail(BaseModel):
  meeting_code: str
  title: str
  date: str
  source_url: Optional[HttpUrl] = None
  motions: List[Motion]


class HealthResponse(BaseModel):
  status: str
  message: str

