from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import List, Optional

from supabase import Client, create_client

from .models import MeetingDetail, MeetingOverview

logger = logging.getLogger("supabase")


class SupabaseConfigError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _get_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SupabaseConfigError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    return create_client(url, key)


def is_configured() -> bool:
    """Return True if Supabase env vars are present."""
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


def get_meetings_index() -> List[MeetingOverview]:
    """Fetch meeting index from Supabase."""
    client = _get_client()
    resp = client.table("meetings").select("*").execute()
    rows = resp.data or []
    meetings: List[MeetingOverview] = []
    for row in rows:
        try:
            meetings.append(MeetingOverview.model_validate(row))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to parse MeetingOverview row %s: %s", row, exc)
    return meetings


def save_meetings_index(meetings: List[MeetingOverview]) -> None:
    """Upsert the meeting index into Supabase."""
    if not meetings:
        return
    client = _get_client()
    payload = []
    now = datetime.now(timezone.utc).isoformat()
    for m in meetings:
        data = m.model_dump()
        data.setdefault("updated_at", now)
        payload.append(data)
    client.table("meetings").upsert(payload).execute()


def get_meeting_detail(meeting_code: str) -> Optional[MeetingDetail]:
    """Fetch a single MeetingDetail from Supabase, if present."""
    client = _get_client()
    resp = client.table("meeting_details").select("*").eq("meeting_code", meeting_code).maybe_single().execute()
    row = resp.data
    if not row:
        return None

    detail_data = row.get("detail") or row
    try:
        # detail column may be stored as JSON string in some setups
        if isinstance(detail_data, str):
            detail_data = json.loads(detail_data)
        return MeetingDetail.model_validate(detail_data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse MeetingDetail for %s from Supabase: %s", meeting_code, exc)
        return None


def save_meeting_detail(detail: MeetingDetail) -> None:
    """Upsert a MeetingDetail into Supabase."""
    client = _get_client()
    payload = {
        "meeting_code": detail.meeting_code,
        "detail": json.loads(detail.model_dump_json()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    client.table("meeting_details").upsert(payload).execute()

