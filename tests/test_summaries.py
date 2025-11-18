from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from do_nothing_time_tracker.models import AbsenceRule
from do_nothing_time_tracker.models import Config
from do_nothing_time_tracker.models import Entry
from do_nothing_time_tracker.summaries import DayWorkSummary
from do_nothing_time_tracker.summaries import get_month_summary
from do_nothing_time_tracker.summaries import get_week_summary
from do_nothing_time_tracker.summaries import get_year_summary
from do_nothing_time_tracker.summaries import RangeSummary
from do_nothing_time_tracker.summaries import summarize_day
from do_nothing_time_tracker.summaries import summarize_range
from itertools import count
from typing import Callable
from typing import Dict
from typing import List
from typing import Sequence
from typing import Tuple

import pytest

WORKDAY = date(2025, 1, 6)  # Monday
WEEKEND_DAY = date(2025, 1, 5)  # Sunday
ENTRY_START_TIME = time(9, 0)
ENTRY_ID_COUNTER = count()

NOW_OPEN_1H30_WORKDAY = datetime.combine(WORKDAY, time(12, 30))
NOW_OPEN_1H30_WEEKEND = datetime.combine(WEEKEND_DAY, time(12, 30))
NOW_OPEN_8H30_WORKDAY = datetime.combine(WORKDAY, time(21, 30))
NOW_OPEN_8H30_WEEKEND = datetime.combine(WEEKEND_DAY, time(21, 30))
NOW_OPEN_2H_WORKDAY = datetime.combine(WORKDAY, time(20, 0))
NOW_OPEN_2H_WEEKEND = datetime.combine(WEEKEND_DAY, time(20, 0))
NOW_OPEN_1H_WORKDAY = datetime.combine(WORKDAY, time(18, 0))
NOW_OPEN_HALF_WEEKEND = datetime.combine(WEEKEND_DAY, time(13, 0))
NOW_OPEN_4H_WORKDAY = datetime.combine(WORKDAY, time(22, 0))
TEST_CONFIG = Config(hours_per_day=8, workdays=[0, 1, 2, 3, 4])


def _absence_rules_for_day(target: date, hours: float) -> List[AbsenceRule]:
    if hours <= 0:
        return []
    credit_hours = float(hours)
    return [AbsenceRule(start=target, end=target, hours=credit_hours, reason="Test")]


class FakeEntryRetriever:
    def __init__(self, entries: Dict[date, List[Entry]]) -> None:
        self.entries = entries

    def entries_for_day(self, target: date) -> List[Entry]:
        return list(self.entries.get(target, []))


class FakeAbsenceRetriever:
    def __init__(self, absences: Dict[date, List[AbsenceRule]] | None = None) -> None:
        self.absences = absences or {}

    def absences_for_day(self, target: date) -> List[AbsenceRule]:
        return list(self.absences.get(target, []))


def _next_id(prefix: str) -> str:
    return f"{prefix}-{next(ENTRY_ID_COUNTER)}"


def closed_entries(*hours_values: float, day: date = WORKDAY) -> List[Entry]:
    start = datetime.combine(day, ENTRY_START_TIME)
    entries: List[Entry] = []
    for hours in hours_values:
        end = start + timedelta(hours=hours)
        entries.append(Entry(id=_next_id("closed"), start=start, end=end))
        start = end + timedelta(minutes=5)
    return entries


def open_period(hours: float, now: datetime) -> Entry:
    start = now - timedelta(hours=hours)
    return Entry(id=_next_id("open"), start=start, end=None)


def build_entries(
    *,
    closed_hours: Sequence[float] | None = None,
    open_hours: Sequence[float] | None = None,
    now: datetime | None = None,
    day: date = WORKDAY,
) -> Callable[[], Tuple[List[Entry], datetime | None]]:
    closed_list = list(closed_hours or [])
    open_list = list(open_hours or [])
    if open_list:
        if now is None:
            raise ValueError("Open entries require a reference 'now' datetime")
        if len(open_list) > 1:
            raise ValueError("Tests only expect one open entry per scenario")

    def _builder() -> Tuple[List[Entry], datetime | None]:
        entries = closed_entries(*closed_list, day=day)
        for hours in open_list:
            entries.append(open_period(hours, now))
        return entries, now

    return _builder


@dataclass(frozen=True)
class DayScenario:
    id: str
    is_workday: bool
    absence: float
    builder: Callable[[], Tuple[List[Entry], datetime | None]]
    expected: float
    worked: float
    remaining: float
    overworked: float


DAY_SCENARIOS: List[DayScenario] = [
    # 1.1 No entries
    DayScenario(
        "case01_no_entries_workday_no_absence",
        True,
        0,
        build_entries(day=WORKDAY),
        8,
        0,
        8,
        0,
    ),
    DayScenario(
        "case02_no_entries_workday_full_absence",
        True,
        8,
        build_entries(day=WORKDAY),
        0,
        0,
        0,
        0,
    ),
    DayScenario(
        "case03_no_entries_workday_partial_absence",
        True,
        4,
        build_entries(day=WORKDAY),
        4,
        0,
        4,
        0,
    ),
    DayScenario(
        "case04_no_entries_weekend",
        False,
        0,
        build_entries(day=WEEKEND_DAY),
        0,
        0,
        0,
        0,
    ),
    # 1.2 Single closed 1h30
    DayScenario(
        "case05_closed_1h30_workday_no_absence",
        True,
        0,
        build_entries(closed_hours=[1.5], day=WORKDAY),
        8,
        1.5,
        6.5,
        0,
    ),
    DayScenario(
        "case06_closed_1h30_workday_full_absence",
        True,
        8,
        build_entries(closed_hours=[1.5], day=WORKDAY),
        0,
        1.5,
        0,
        1.5,
    ),
    DayScenario(
        "case07_closed_1h30_workday_partial_absence",
        True,
        4,
        build_entries(closed_hours=[1.5], day=WORKDAY),
        4,
        1.5,
        2.5,
        0,
    ),
    DayScenario(
        "case08_closed_1h30_weekend",
        False,
        0,
        build_entries(closed_hours=[1.5], day=WEEKEND_DAY),
        0,
        1.5,
        0,
        1.5,
    ),
    # 1.3 Single open 1h30
    DayScenario(
        "case09_open_1h30_workday_no_absence",
        True,
        0,
        build_entries(open_hours=[1.5], now=NOW_OPEN_1H30_WORKDAY, day=WORKDAY),
        8,
        1.5,
        6.5,
        0,
    ),
    DayScenario(
        "case10_open_1h30_workday_full_absence",
        True,
        8,
        build_entries(open_hours=[1.5], now=NOW_OPEN_1H30_WORKDAY, day=WORKDAY),
        0,
        1.5,
        0,
        1.5,
    ),
    DayScenario(
        "case11_open_1h30_workday_partial_absence",
        True,
        4,
        build_entries(open_hours=[1.5], now=NOW_OPEN_1H30_WORKDAY, day=WORKDAY),
        4,
        1.5,
        2.5,
        0,
    ),
    DayScenario(
        "case12_open_1h30_weekend",
        False,
        0,
        build_entries(open_hours=[1.5], now=NOW_OPEN_1H30_WEEKEND, day=WEEKEND_DAY),
        0,
        1.5,
        0,
        1.5,
    ),
    # 1.4 Single period 8h30 (closed + open)
    DayScenario(
        "case13_closed_8h30_workday_no_absence",
        True,
        0,
        build_entries(closed_hours=[8.5], day=WORKDAY),
        8,
        8.5,
        0,
        0.5,
    ),
    DayScenario(
        "case14_closed_8h30_workday_full_absence",
        True,
        8,
        build_entries(closed_hours=[8.5], day=WORKDAY),
        0,
        8.5,
        0,
        8.5,
    ),
    DayScenario(
        "case15_closed_8h30_workday_partial_absence",
        True,
        4,
        build_entries(closed_hours=[8.5], day=WORKDAY),
        4,
        8.5,
        0,
        4.5,
    ),
    DayScenario(
        "case16_closed_8h30_weekend",
        False,
        0,
        build_entries(closed_hours=[8.5], day=WEEKEND_DAY),
        0,
        8.5,
        0,
        8.5,
    ),
    DayScenario(
        "case17_open_8h30_workday_no_absence",
        True,
        0,
        build_entries(open_hours=[8.5], now=NOW_OPEN_8H30_WORKDAY, day=WORKDAY),
        8,
        8.5,
        0,
        0.5,
    ),
    DayScenario(
        "case18_open_8h30_workday_full_absence",
        True,
        8,
        build_entries(open_hours=[8.5], now=NOW_OPEN_8H30_WORKDAY, day=WORKDAY),
        0,
        8.5,
        0,
        8.5,
    ),
    DayScenario(
        "case19_open_8h30_workday_partial_absence",
        True,
        4,
        build_entries(open_hours=[8.5], now=NOW_OPEN_8H30_WORKDAY, day=WORKDAY),
        4,
        8.5,
        0,
        4.5,
    ),
    DayScenario(
        "case20_open_8h30_weekend",
        False,
        0,
        build_entries(open_hours=[8.5], now=NOW_OPEN_8H30_WEEKEND, day=WEEKEND_DAY),
        0,
        8.5,
        0,
        8.5,
    ),
    # 1.5 Two closed entries (5h+3h and 5h+4h)
    DayScenario(
        "case21_two_closed_5h3h_workday_no_absence",
        True,
        0,
        build_entries(closed_hours=[5, 3], day=WORKDAY),
        8,
        8,
        0,
        0,
    ),
    DayScenario(
        "case22_two_closed_5h3h_workday_full_absence",
        True,
        8,
        build_entries(closed_hours=[5, 3], day=WORKDAY),
        0,
        8,
        0,
        8,
    ),
    DayScenario(
        "case23_two_closed_5h3h_workday_partial_absence",
        True,
        4,
        build_entries(closed_hours=[5, 3], day=WORKDAY),
        4,
        8,
        0,
        4,
    ),
    DayScenario(
        "case24_two_closed_5h3h_weekend",
        False,
        0,
        build_entries(closed_hours=[5, 3], day=WEEKEND_DAY),
        0,
        8,
        0,
        8,
    ),
    DayScenario(
        "case25_two_closed_5h4h_workday_no_absence",
        True,
        0,
        build_entries(closed_hours=[5, 4], day=WORKDAY),
        8,
        9,
        0,
        1,
    ),
    DayScenario(
        "case26_two_closed_5h4h_workday_full_absence",
        True,
        8,
        build_entries(closed_hours=[5, 4], day=WORKDAY),
        0,
        9,
        0,
        9,
    ),
    DayScenario(
        "case27_two_closed_5h4h_workday_partial_absence",
        True,
        4,
        build_entries(closed_hours=[5, 4], day=WORKDAY),
        4,
        9,
        0,
        5,
    ),
    DayScenario(
        "case28_two_closed_5h4h_weekend",
        False,
        0,
        build_entries(closed_hours=[5, 4], day=WEEKEND_DAY),
        0,
        9,
        0,
        9,
    ),
    # 1.6 Mixed closed + open
    DayScenario(
        "case29_mixed_3h_closed_2h_open_workday_no_absence",
        True,
        0,
        build_entries(closed_hours=[3], open_hours=[2], now=NOW_OPEN_2H_WORKDAY, day=WORKDAY),
        8,
        5,
        3,
        0,
    ),
    DayScenario(
        "case30_mixed_2h_closed_1h_open_workday_partial_absence",
        True,
        4,
        build_entries(closed_hours=[2], open_hours=[1], now=NOW_OPEN_1H_WORKDAY, day=WORKDAY),
        4,
        3,
        1,
        0,
    ),
    DayScenario(
        "case31_mixed_1h_closed_0h30_open_weekend",
        False,
        0,
        build_entries(
            closed_hours=[1],
            open_hours=[0.5],
            now=NOW_OPEN_HALF_WEEKEND,
            day=WEEKEND_DAY,
        ),
        0,
        1.5,
        0,
        1.5,
    ),
    DayScenario(
        "case32_mixed_7h_closed_2h_open_workday_no_absence",
        True,
        0,
        build_entries(closed_hours=[7], open_hours=[2], now=NOW_OPEN_2H_WORKDAY, day=WORKDAY),
        8,
        9,
        0,
        1,
    ),
    DayScenario(
        "case33_mixed_3h_closed_4h_open_workday_partial_absence",
        True,
        4,
        build_entries(closed_hours=[3], open_hours=[4], now=NOW_OPEN_4H_WORKDAY, day=WORKDAY),
        4,
        7,
        0,
        3,
    ),
    DayScenario(
        "case34_mixed_5h_closed_2h_open_weekend",
        False,
        0,
        build_entries(closed_hours=[5], open_hours=[2], now=NOW_OPEN_2H_WEEKEND, day=WEEKEND_DAY),
        0,
        7,
        0,
        7,
    ),
    # 1.7 Full absence but still working
    DayScenario(
        "case35_full_absence_but_worked",
        True,
        8,
        build_entries(closed_hours=[3], day=WORKDAY),
        0,
        3,
        0,
        3,
    ),
]


def _assert_day_summary(
    summary: DayWorkSummary,
    expected: float,
    worked: float,
    remaining: float,
    overworked: float,
) -> None:
    assert summary.expected == pytest.approx(expected)
    assert summary.worked == pytest.approx(worked)
    assert summary.remaining == pytest.approx(remaining)
    assert summary.overworked == pytest.approx(overworked)


@pytest.mark.parametrize("scenario", DAY_SCENARIOS, ids=lambda sc: sc.id)
def test_day_scenarios(scenario: DayScenario) -> None:
    target_day = WORKDAY if scenario.is_workday else WEEKEND_DAY
    entries, now = scenario.builder()
    summary = summarize_day(
        target_day,
        entries,
        _absence_rules_for_day(target_day, scenario.absence),
        config=TEST_CONFIG,
        now=now,
    )
    _assert_day_summary(
        summary,
        scenario.expected,
        scenario.worked,
        scenario.remaining,
        scenario.overworked,
    )
    assert summary.is_workday == scenario.is_workday
    assert summary.worked_day == (scenario.worked > 0)


def make_day(
    *,
    target_day: date,
    worked_hours: float,
    is_workday: bool,
    absence: float = 0.0,
) -> DayWorkSummary:
    entries = closed_entries(worked_hours, day=target_day) if worked_hours > 0 else []
    if is_workday and target_day.weekday() >= 5:
        raise ValueError("Expected a weekday target when is_workday=True")
    if not is_workday and target_day.weekday() < 5:
        raise ValueError("Expected a weekend target when is_workday=False")
    return summarize_day(
        target_day,
        entries,
        _absence_rules_for_day(target_day, absence),
        config=TEST_CONFIG,
    )


def _assert_range_summary(
    summary: RangeSummary,
    *,
    expected: float,
    worked: float,
    remaining: float,
    overworked: float,
    workdays: int,
    worked_days: int,
) -> None:
    assert summary.total_expected == pytest.approx(expected)
    assert summary.total_worked == pytest.approx(worked)
    assert summary.total_remaining == pytest.approx(remaining)
    assert summary.total_overworked == pytest.approx(overworked)
    assert summary.workdays == workdays
    assert summary.worked_days == worked_days


def test_range_perfect_week() -> None:
    days: List[DayWorkSummary] = []
    for offset in range(5):
        day = WORKDAY + timedelta(days=offset)
        days.append(make_day(target_day=day, worked_hours=8, is_workday=True))
    days.append(make_day(target_day=WORKDAY + timedelta(days=5), worked_hours=0, is_workday=False))
    days.append(make_day(target_day=WORKDAY + timedelta(days=6), worked_hours=0, is_workday=False))

    summary = summarize_range(days)
    _assert_range_summary(
        summary,
        expected=40,
        worked=40,
        remaining=0,
        overworked=0,
        workdays=5,
        worked_days=5,
    )


def test_range_under_and_over_balanced_week() -> None:
    days: List[DayWorkSummary] = [
        make_day(target_day=WORKDAY, worked_hours=6, is_workday=True),
        make_day(target_day=WORKDAY + timedelta(days=1), worked_hours=10, is_workday=True),
    ]
    for offset in range(2, 5):
        days.append(
            make_day(
                target_day=WORKDAY + timedelta(days=offset),
                worked_hours=8,
                is_workday=True,
            )
        )
    days.append(make_day(target_day=WORKDAY + timedelta(days=5), worked_hours=0, is_workday=False))
    days.append(make_day(target_day=WORKDAY + timedelta(days=6), worked_hours=0, is_workday=False))

    summary = summarize_range(days)
    _assert_range_summary(
        summary,
        expected=40,
        worked=40,
        remaining=2,
        overworked=2,
        workdays=5,
        worked_days=5,
    )


def test_range_with_full_absences_and_no_work() -> None:
    days: List[DayWorkSummary] = [
        make_day(target_day=WORKDAY, worked_hours=0, is_workday=True, absence=8),
        make_day(
            target_day=WORKDAY + timedelta(days=1),
            worked_hours=4,
            is_workday=True,
            absence=4,
        ),
    ]
    for offset in range(2, 5):
        days.append(
            make_day(
                target_day=WORKDAY + timedelta(days=offset),
                worked_hours=8,
                is_workday=True,
            )
        )
    days.append(make_day(target_day=WORKDAY + timedelta(days=5), worked_hours=0, is_workday=False))
    days.append(make_day(target_day=WORKDAY + timedelta(days=6), worked_hours=0, is_workday=False))

    summary = summarize_range(days)
    _assert_range_summary(
        summary,
        expected=28,
        worked=28,
        remaining=0,
        overworked=0,
        workdays=5,
        worked_days=4,
    )


def test_range_with_weekend_work() -> None:
    days: List[DayWorkSummary] = [
        make_day(target_day=WORKDAY + timedelta(days=offset), worked_hours=8, is_workday=True)
        for offset in range(5)
    ]
    days.append(make_day(target_day=WORKDAY + timedelta(days=5), worked_hours=5, is_workday=False))
    days.append(make_day(target_day=WORKDAY + timedelta(days=6), worked_hours=0, is_workday=False))

    summary = summarize_range(days)
    _assert_range_summary(
        summary,
        expected=40,
        worked=45,
        remaining=0,
        overworked=5,
        workdays=5,
        worked_days=6,
    )


def test_range_with_full_absence_but_work_done() -> None:
    days: List[DayWorkSummary] = [
        make_day(target_day=WORKDAY, worked_hours=3, is_workday=True, absence=8),
    ]
    for offset in range(1, 5):
        days.append(
            make_day(
                target_day=WORKDAY + timedelta(days=offset),
                worked_hours=8,
                is_workday=True,
            )
        )
    days.append(make_day(target_day=WORKDAY + timedelta(days=5), worked_hours=0, is_workday=False))
    days.append(make_day(target_day=WORKDAY + timedelta(days=6), worked_hours=0, is_workday=False))

    summary = summarize_range(days)
    _assert_range_summary(
        summary,
        expected=32,
        worked=35,
        remaining=0,
        overworked=3,
        workdays=5,
        worked_days=5,
    )


def test_get_week_summary_structure() -> None:
    week_start = WORKDAY
    entries: Dict[date, List[Entry]] = {}
    for i in range(5):
        day = week_start + timedelta(days=i)
        entries[day] = closed_entries(8, day=day)
    entry_retriever = FakeEntryRetriever(entries)
    absence_retriever = FakeAbsenceRetriever()
    result = get_week_summary(
        week_start,
        week_start + timedelta(days=6),
        entry_retriever=entry_retriever,
        absence_retriever=absence_retriever,
        config=TEST_CONFIG,
    )
    summary = result.summary
    _assert_range_summary(
        summary,
        expected=40,
        worked=40,
        remaining=0,
        overworked=0,
        workdays=5,
        worked_days=5,
    )
    assert len(result.period.days) == 7
    assert result.period.days[0].summary.worked == pytest.approx(8)


def test_get_month_summary_perfect_month() -> None:
    month_start = date(2025, 1, 1)
    _, days_in_month = monthrange(month_start.year, month_start.month)
    entries: Dict[date, List[Entry]] = {}
    for offset in range(days_in_month):
        day = month_start + timedelta(days=offset)
        if day.weekday() < 5:
            entries[day] = closed_entries(8, day=day)
    entry_retriever = FakeEntryRetriever(entries)
    absence_retriever = FakeAbsenceRetriever()
    result = get_month_summary(
        month_start,
        month_start + timedelta(days=days_in_month - 1),
        entry_retriever=entry_retriever,
        absence_retriever=absence_retriever,
        config=TEST_CONFIG,
    )
    summary = result.summary
    workdays = sum(1 for d in entries if d.weekday() < 5)
    _assert_range_summary(
        summary,
        expected=workdays * 8,
        worked=workdays * 8,
        remaining=0,
        overworked=0,
        workdays=workdays,
        worked_days=workdays,
    )
    assert result.period.weeks
    assert sum(len(week.days) for week in result.period.weeks) == days_in_month


def test_get_year_summary_balanced_under_and_over() -> None:
    year = 2025
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    entries: Dict[date, List[Entry]] = {}
    workday_index = 0
    per_day_hours: List[float] = []
    current = year_start
    while current <= year_end:
        if current.weekday() < 5:
            if workday_index < 200:
                hours = 8
            elif workday_index < 230:
                hours = 7
            else:
                hours = 9
            entries[current] = closed_entries(hours, day=current)
            workday_index += 1
            per_day_hours.append(hours)
        current += timedelta(days=1)
    entry_retriever = FakeEntryRetriever(entries)
    absence_retriever = FakeAbsenceRetriever()
    result = get_year_summary(
        year_start,
        year_end,
        entry_retriever=entry_retriever,
        absence_retriever=absence_retriever,
        config=TEST_CONFIG,
    )
    summary = result.summary
    expected_hours = len(per_day_hours) * TEST_CONFIG.hours_per_day
    worked_hours = sum(per_day_hours)
    remaining_hours = sum(max(TEST_CONFIG.hours_per_day - hours, 0) for hours in per_day_hours)
    overworked_hours = sum(max(hours - TEST_CONFIG.hours_per_day, 0) for hours in per_day_hours)
    _assert_range_summary(
        summary,
        expected=expected_hours,
        worked=worked_hours,
        remaining=remaining_hours,
        overworked=overworked_hours,
        workdays=len(per_day_hours),
        worked_days=len(per_day_hours),
    )
    assert result.period.months
