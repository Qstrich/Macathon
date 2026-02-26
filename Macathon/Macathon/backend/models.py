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
  detail_cached: Optional[bool] = None  # True if meeting detail is in cache (motion count/topics known)


class MeetingDetail(BaseModel):
  meeting_code: str
  title: str
  date: str
  source_url: Optional[HttpUrl] = None
  motions: List[Motion]


class HealthResponse(BaseModel):
  status: str
  message: str


class RefreshResponse(BaseModel):
  meetings_count: int


class PrewarmResponse(BaseModel):
  prewarmed: int


class ContentReportRequest(BaseModel):
  meeting_code: str
  motion_id: Optional[int] = None
  reason: str  # "incorrect_information" | "inappropriate" | "other"
  comment: Optional[str] = None


class CategoryStats(BaseModel):
  category: str
  decisions: int


class RegionStats(BaseModel):
  region: str
  decisions: int


class StatusStats(BaseModel):
  status: str
  decisions: int


class MeetingStats(BaseModel):
  meeting_code: str
  date: str
  total_decisions: int


class StatsResponse(BaseModel):
  by_category: List[CategoryStats]
  by_region: List[RegionStats]
  by_status: List[StatusStats]
  by_meeting: List[MeetingStats]


class MotionReportSummary(BaseModel):
  meeting_code: str
  motion_id: int
  incorrect_reports: int


class ReportsSummaryResponse(BaseModel):
  by_motion: List[MotionReportSummary]

