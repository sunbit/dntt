from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

import uuid


@dataclass
class Entry:
    """Represents a tracked time entry between two datetimes."""

    id: str
    start: datetime
    end: Optional[datetime] = None

    @property
    def is_open(self) -> bool:
        return self.end is None

    @property
    def start_date(self) -> date:
        return self.start.date()

    def duration_hours(self, now: Optional[datetime] = None) -> float:
        """Returns the number of hours worked for this entry."""
        effective_end = self.end or now
        if not effective_end:
            return 0.0
        seconds = (effective_end - self.start).total_seconds()
        return max(seconds / 3600, 0.0)

    def with_updates(
        self,
        *,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Entry:
        return Entry(
            id=self.id,
            start=start or self.start,
            end=end if end is not None else self.end,
        )

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "id": self.id,
            "start": self.start.isoformat(timespec="minutes"),
            "end": self.end.isoformat(timespec="minutes") if self.end else None,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Optional[str]]) -> Entry:
        return cls(
            id=payload["id"],
            start=datetime.fromisoformat(payload["start"]),
            end=datetime.fromisoformat(payload["end"]) if payload.get("end") else None,
        )

    @classmethod
    def new(cls, start: datetime) -> Entry:
        return cls(id=str(uuid.uuid4()), start=start)


class SummaryExpectedMode(str, Enum):
    FULL_PERIOD = "full_period"
    TO_DATE = "to_date"


@dataclass
class Config:
    hours_per_day: int = 8
    workdays: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    absences: List[AbsenceRule] = field(default_factory=list)
    summary_expected_mode: SummaryExpectedMode = SummaryExpectedMode.FULL_PERIOD


@dataclass
class AbsenceRule:
    start: date
    end: Optional[date] = None
    reason: str = ""
    hours: Optional[int] = None

    def includes(self, target: date) -> bool:
        end_date = self.end or self.start
        return self.start <= target <= end_date


@dataclass
class DaySummary:
    day: date
    entries: List[Entry] = field(default_factory=list)
    expected_hours: float = 0.0

    def worked_hours(self, *, now: Optional[datetime] = None) -> float:
        return sum(entry.duration_hours(now=now) for entry in self.entries)


@dataclass
class WeekSummary:
    start: date
    end: date
    day_summaries: List[DaySummary]

    def total_hours(self, *, now: Optional[datetime] = None) -> float:
        return sum(day.worked_hours(now=now) for day in self.day_summaries)
