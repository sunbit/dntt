from __future__ import annotations

from .models import AbsenceRule
from .models import Config
from .models import Entry
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Generic
from typing import Iterable
from typing import List
from typing import Protocol
from typing import Sequence
from typing import Tuple
from typing import TypeVar

_EPSILON = 1e-6


class EntryRetriever(Protocol):
    def entries_for_day(self, target: date) -> Sequence[Entry]:
        """Return all entries that belong to the provided day."""


class AbsenceRetriever(Protocol):
    def absences_for_day(self, target: date) -> Sequence[AbsenceRule]:
        """Return all absence rules that include the provided day."""


@dataclass(frozen=True)
class DayWorkSummary:
    """Computed metrics for a single day."""

    day: date
    expected: float
    worked: float
    remaining: float
    overworked: float
    is_workday: bool
    worked_day: bool
    absence_hours: float


@dataclass(frozen=True)
class RangeSummary:
    total_expected: float
    total_worked: float
    total_remaining: float
    total_overworked: float
    workdays: int
    worked_days: int


@dataclass(frozen=True)
class DayDetails:
    date: date
    entries: Tuple[Entry, ...]
    absences: Tuple[AbsenceRule, ...]
    summary: DayWorkSummary


@dataclass(frozen=True)
class WeekDetails:
    start: date
    end: date
    days: Tuple[DayDetails, ...]


@dataclass(frozen=True)
class MonthDetails:
    year: int
    month: int
    start: date
    end: date
    weeks: Tuple[WeekDetails, ...]


@dataclass(frozen=True)
class YearDetails:
    year: int
    start: date
    end: date
    months: Tuple[MonthDetails, ...]


TPeriod = TypeVar("TPeriod")


@dataclass(frozen=True)
class SummaryResult(Generic[TPeriod]):
    summary: RangeSummary
    period: TPeriod


@dataclass
class ConfigAbsenceRetriever:
    """Simple absence retriever that reads directly from a Config instance."""

    config: Config

    def absences_for_day(self, target: date) -> Sequence[AbsenceRule]:
        return [rule for rule in self.config.absences if rule.includes(target)]


def summarize_day(
    day: date,
    periods: Sequence[Entry],
    absences: Sequence[AbsenceRule],
    *,
    config: Config,
    now: datetime | None = None,
) -> DayWorkSummary:
    """
    Summarize a day worth of periods given the entries and absences for that date.

    The function is intentionally free of storage or UI concerns so it can be
    tested with ad-hoc periods and absence values.
    """
    is_workday = _is_config_workday(day, config)
    absence_credit = _absence_hours(absences, config) if is_workday else 0.0
    base_expected = float(config.hours_per_day) if is_workday else 0.0
    expected = max(base_expected - absence_credit, 0.0)
    worked = sum(entry.duration_hours(now=now) for entry in periods)
    remaining = max(expected - worked, 0.0)
    overworked = max(worked - expected, 0.0)
    worked_flag = worked > _EPSILON
    return DayWorkSummary(
        day=day,
        expected=expected,
        worked=worked,
        remaining=remaining,
        overworked=overworked,
        is_workday=is_workday,
        worked_day=worked_flag,
        absence_hours=absence_credit if is_workday else 0.0,
    )


def summarize_range(day_summaries: Sequence[DayWorkSummary]) -> RangeSummary:
    return RangeSummary(
        total_expected=sum(day.expected for day in day_summaries),
        total_worked=sum(day.worked for day in day_summaries),
        total_remaining=sum(day.remaining for day in day_summaries),
        total_overworked=sum(day.overworked for day in day_summaries),
        workdays=sum(1 for day in day_summaries if day.is_workday),
        worked_days=sum(1 for day in day_summaries if day.worked_day),
    )


def get_day_summary(
    start: date,
    end: date,
    *,
    entry_retriever: EntryRetriever,
    absence_retriever: AbsenceRetriever,
    config: Config,
    now: datetime | None = None,
) -> SummaryResult[DayDetails]:
    if start != end:
        raise ValueError("Day summaries require matching start and end dates")
    day_records = _build_day_details(
        start,
        end,
        entry_retriever=entry_retriever,
        absence_retriever=absence_retriever,
        config=config,
        now=now,
    )
    if not day_records:
        raise ValueError("No days available for provided range")
    day = day_records[0]
    return SummaryResult(summary=summarize_range([day.summary]), period=day)


def get_week_summary(
    start: date,
    end: date,
    *,
    entry_retriever: EntryRetriever,
    absence_retriever: AbsenceRetriever,
    config: Config,
    now: datetime | None = None,
) -> SummaryResult[WeekDetails]:
    days = _build_day_details(
        start,
        end,
        entry_retriever=entry_retriever,
        absence_retriever=absence_retriever,
        config=config,
        now=now,
    )
    week = WeekDetails(
        start=days[0].date if days else start,
        end=days[-1].date if days else end,
        days=tuple(days),
    )
    summary = summarize_range([day.summary for day in days])
    return SummaryResult(summary=summary, period=week)


def get_month_summary(
    start: date,
    end: date,
    *,
    entry_retriever: EntryRetriever,
    absence_retriever: AbsenceRetriever,
    config: Config,
    now: datetime | None = None,
) -> SummaryResult[MonthDetails]:
    days = _build_day_details(
        start,
        end,
        entry_retriever=entry_retriever,
        absence_retriever=absence_retriever,
        config=config,
        now=now,
    )
    weeks = tuple(_group_days_by_week(days))
    month = MonthDetails(
        year=start.year,
        month=start.month,
        start=days[0].date if days else start,
        end=days[-1].date if days else end,
        weeks=weeks,
    )
    summary = summarize_range([day.summary for day in days])
    return SummaryResult(summary=summary, period=month)


def get_year_summary(
    start: date,
    end: date,
    *,
    entry_retriever: EntryRetriever,
    absence_retriever: AbsenceRetriever,
    config: Config,
    now: datetime | None = None,
) -> SummaryResult[YearDetails]:
    days = _build_day_details(
        start,
        end,
        entry_retriever=entry_retriever,
        absence_retriever=absence_retriever,
        config=config,
        now=now,
    )
    months = tuple(_group_days_by_month(days))
    year_details = YearDetails(
        year=start.year,
        start=days[0].date if days else start,
        end=days[-1].date if days else end,
        months=months,
    )
    summary = summarize_range([day.summary for day in days])
    return SummaryResult(summary=summary, period=year_details)


def _build_day_details(
    start: date,
    end: date,
    *,
    entry_retriever: EntryRetriever,
    absence_retriever: AbsenceRetriever,
    config: Config,
    now: datetime | None,
) -> List[DayDetails]:
    results: List[DayDetails] = []
    today = date.today()
    for target in _iter_days(start, end):
        entries = _normalize_entries(entry_retriever.entries_for_day(target), target)
        absences = tuple(absence_retriever.absences_for_day(target))
        reference_now = now if (now is not None and target == today) else None
        summary = summarize_day(target, entries, absences, config=config, now=reference_now)
        results.append(DayDetails(date=target, entries=entries, absences=absences, summary=summary))
    return results


def _normalize_entries(entries: Sequence[Entry], target: date) -> Tuple[Entry, ...]:
    filtered = [entry for entry in entries if entry.start.date() == target]
    filtered.sort(key=lambda entry: entry.start)
    return tuple(filtered)


def _group_days_by_week(days: Sequence[DayDetails]) -> List[WeekDetails]:
    if not days:
        return []
    results: List[WeekDetails] = []
    current: List[DayDetails] = []
    current_iso: Tuple[int, int] | None = None
    for item in days:
        iso = item.date.isocalendar()
        iso_pair = (iso.year, iso.week)
        if current and iso_pair != current_iso:
            results.append(_make_week_details(current))
            current = [item]
        else:
            current.append(item)
        current_iso = iso_pair
    if current:
        results.append(_make_week_details(current))
    return results


def _group_days_by_month(days: Sequence[DayDetails]) -> List[MonthDetails]:
    if not days:
        return []
    results: List[MonthDetails] = []
    current: List[DayDetails] = []
    current_key: Tuple[int, int] | None = None
    for item in days:
        key = (item.date.year, item.date.month)
        if current and key != current_key:
            results.append(_make_month_details(current))
            current = [item]
        else:
            current.append(item)
        current_key = key
    if current:
        results.append(_make_month_details(current))
    return results


def _make_week_details(days: Sequence[DayDetails]) -> WeekDetails:
    return WeekDetails(start=days[0].date, end=days[-1].date, days=tuple(days))


def _make_month_details(days: Sequence[DayDetails]) -> MonthDetails:
    return MonthDetails(
        year=days[0].date.year,
        month=days[0].date.month,
        start=days[0].date,
        end=days[-1].date,
        weeks=tuple(_group_days_by_week(days)),
    )


def _iter_days(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _absence_hours(absences: Sequence[AbsenceRule], config: Config) -> float:
    credited = 0.0
    for rule in absences:
        credit_hours = rule.hours if rule.hours is not None else config.hours_per_day
        credited += float(credit_hours)
    return credited


def _is_config_workday(target: date, config: Config) -> bool:
    if config.workdays:
        return target.weekday() in config.workdays
    return True
