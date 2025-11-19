from __future__ import annotations

from .config import ConfigService
from .models import Config
from .models import Entry
from .models import SummaryExpectedMode
from .state import TrackerState
from .storage import AbsenceStorage
from .storage import EntryStorage
from .summaries import ConfigAbsenceRetriever
from .summaries import get_month_summary
from .summaries import get_week_summary
from .summaries import get_year_summary
from .summaries import RangeSummary
from .ui.components import format_duration
from .ui.components import sentence_card
from .ui.components import set_difference_text
from .ui.components import summary_sentence_text
from .ui.page_setup import setup_page
from .ui.theme import ASSETS_DIR
from .ui.views import absences as absences_view
from .ui.views import config as config_view
from .ui.views import month as month_view
from .ui.views import today as today_view
from .ui.views import week as week_view
from calendar import monthrange
from datetime import date
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Callable
from typing import Optional

import asyncio
import flet as ft


class TrackerApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.config_service = ConfigService()
        self.config: Config = self.config_service.load()
        self.data_dir: Path = self.config_service.resolve_data_dir(self.config)
        self._setup_storage()
        self.selected_date = date.today()

        # Controls we'll update later
        self.today_title = ft.Text(
            size=24,
            width=400,
            weight=ft.FontWeight.W_600,
            text_align=ft.TextAlign.CENTER,
        )
        self.week_value_text = ft.Text()
        self.week_progress_text = ft.Text()
        self.week_remaining_text = ft.Text()
        self.month_value_text = ft.Text()
        self.month_progress_text = ft.Text()
        self.month_remaining_text = ft.Text()
        self.year_value_text = ft.Text()
        self.year_progress_text = ft.Text()
        self.year_remaining_text = ft.Text()
        self.day_summary_text = summary_sentence_text()
        self.week_tab_summary_text = summary_sentence_text()
        self.month_tab_summary_text = summary_sentence_text()
        self.today_summary_card = sentence_card(self.day_summary_text)
        self.week_summary_card = sentence_card(self.week_tab_summary_text)
        self.month_summary_card = sentence_card(self.month_tab_summary_text)
        self.clock_in_button = ft.FilledButton("Clock in")
        self.clock_out_button = ft.FilledButton("Clock out")
        self.today_entries_column = ft.Column(spacing=0, tight=True, expand=True)
        self.absences_column = ft.Column(spacing=4)
        self.week_title_text = ft.Text(
            size=24,
            width=400,
            weight=ft.FontWeight.W_500,
            text_align=ft.TextAlign.CENTER,
        )
        self.week_days_column = ft.Column(spacing=8)
        self.month_title_text = ft.Text(
            size=24,
            width=400,
            weight=ft.FontWeight.W_500,
            text_align=ft.TextAlign.CENTER,
        )
        self.month_weeks_column = ft.Column(spacing=10)
        self.absences_list_column = ft.Column(spacing=8, tight=False, expand=False)
        self.config_hours_field: ft.TextField | None = None
        self.config_workday_checkboxes: list[ft.Checkbox] = []
        self.config_summary_mode_group: ft.RadioGroup | None = None
        self.config_status_text: ft.Text | None = None
        self.config_data_dir_field: ft.TextField | None = None
        self._summary_cache: dict[str, tuple[float, float] | None] = {
            "week": None,
            "month": None,
            "year": None,
        }
        self._ticker_task: asyncio.Task | None = None
        self.editing_entry_id: str | None = None
        self._draft_entry: Entry | None = None
        self._absence_editor_dialog: ft.AlertDialog | None = None
        self._absence_editor_index: Optional[int] = None
        self._absence_start_field: ft.TextField | None = None
        self._absence_end_field: ft.TextField | None = None
        self._absence_reason_field: ft.TextField | None = None
        self._absence_hours_field: ft.TextField | None = None
        self._absence_editor_title: ft.Text | None = None
        self._start_date_picker: ft.DatePicker | None = None
        self._end_date_picker: ft.DatePicker | None = None
        self._tab_content_container: ft.Container | None = None
        self._tab_views: list[ft.Control] = []
        self._tab_navigation: ft.Tabs | None = None
        self._active_tab_index = 0

    def mount(self) -> None:
        tab_definitions: list[tuple[str, ft.Control]] = [
            ("Today", today_view.build(self)),
            ("Week", week_view.build(self)),
            ("Month", month_view.build(self)),
            ("Absences", absences_view.build(self)),
            ("Config", config_view.build(self)),
        ]
        self._tab_views = [content for _, content in tab_definitions]
        self._active_tab_index = 0
        tabs_navigation = setup_page(self, tab_definitions)
        self._tab_navigation = tabs_navigation

        self.page.on_disconnect = self._handle_page_disconnect
        self._tab_content_container = ft.Container(
            expand=True,
            content=self._tab_views[self._active_tab_index],
        )
        self.page.add(self._tab_content_container)
        self.refresh_all()
        self._start_ticker()

    def _setup_storage(self) -> None:
        entries_dir = self.data_dir / "entries"
        absences_dir = self.data_dir / "absences"
        self.absence_storage = AbsenceStorage(base_dir=absences_dir)
        stored_absences = self.absence_storage.load_all()
        if stored_absences:
            self.config.absences = stored_absences
        else:
            self.config.absences = getattr(self.config, "absences", [])
            if self.config.absences:
                self._persist_absences()
        self.absence_retriever = ConfigAbsenceRetriever(self.config)
        self.state = TrackerState(EntryStorage(base_dir=entries_dir))

    # ------------------------------------------------------------------
    def refresh_all(self) -> None:
        now = datetime.now()
        today_view.refresh(self, now)
        week_view.refresh(self, now)
        month_view.refresh(self, now)
        self._update_appbar_summaries(now)
        absences_view.refresh_tab(self)
        self._refresh_config_tab()
        self.page.update()

    def _handle_tab_change(self, event: ft.ControlEvent) -> None:
        if not self._tab_views or self._tab_content_container is None:
            return
        selected_index = self._active_tab_index
        control = getattr(event, "control", None)
        if isinstance(control, ft.Tabs) and control.selected_index is not None:
            selected_index = control.selected_index
        elif self._tab_navigation is not None and self._tab_navigation.selected_index is not None:
            selected_index = self._tab_navigation.selected_index
        selected_index = max(0, min(len(self._tab_views) - 1, selected_index))
        if selected_index == self._active_tab_index:
            return
        self._active_tab_index = selected_index
        self._tab_content_container.content = self._tab_views[selected_index]
        self.page.update()

    def _refresh_config_tab(self) -> None:
        if self.config_hours_field is not None:
            self.config_hours_field.value = str(self.config.hours_per_day)
        if self.config_summary_mode_group is not None:
            self.config_summary_mode_group.value = self.config.summary_expected_mode.value
        if self.config_data_dir_field is not None:
            self.config_data_dir_field.value = str(self.data_dir)
        workdays = set(self.config.workdays)
        for checkbox in self.config_workday_checkboxes:
            checkbox.value = checkbox.data in workdays

    def _week_start_for(self, target: date) -> date:
        delta = target.weekday()
        return target - timedelta(days=delta)

    def _compute_week_summary(
        self, target_date: date, now: datetime, *, limit_end: date | None = None
    ) -> RangeSummary:
        week_start = self._week_start_for(target_date)
        week_end = week_start + timedelta(days=6)
        week_end = self._clamp_range_end(week_start, week_end, limit_end)
        result = get_week_summary(
            week_start,
            week_end,
            entry_retriever=self.state,
            absence_retriever=self.absence_retriever,
            config=self.config,
            now=now,
        )
        return result.summary

    def _compute_month_summary(
        self, target_date: date, now: datetime, *, limit_end: date | None = None
    ) -> RangeSummary:
        month_start = date(target_date.year, target_date.month, 1)
        _, days_in_month = monthrange(month_start.year, month_start.month)
        month_end = month_start + timedelta(days=days_in_month - 1)
        month_end = self._clamp_range_end(month_start, month_end, limit_end)
        result = get_month_summary(
            month_start,
            month_end,
            entry_retriever=self.state,
            absence_retriever=self.absence_retriever,
            config=self.config,
            now=now,
        )
        return result.summary

    def _compute_year_summary(
        self, year: int, now: datetime, *, limit_end: date | None = None
    ) -> RangeSummary:
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        year_end = self._clamp_range_end(year_start, year_end, limit_end)
        result = get_year_summary(
            year_start,
            year_end,
            entry_retriever=self.state,
            absence_retriever=self.absence_retriever,
            config=self.config,
            now=now,
        )
        return result.summary

    @staticmethod
    def _clamp_range_end(start: date, default_end: date, limit_end: date | None) -> date:
        if limit_end is None:
            return default_end
        if limit_end < start:
            return start
        return min(default_end, limit_end)

    def _update_appbar_summaries(self, now: datetime) -> None:
        anchor_date = date.today()
        week_summary = self._compute_week_summary(anchor_date, now)
        week_expected = self._resolve_expected_target(
            week_summary,
            lambda: self._compute_week_summary(anchor_date, now, limit_end=anchor_date),
        )
        self._maybe_update_summary_card(
            "week",
            week_summary.total_worked,
            week_expected,
            self.week_value_text,
            self.week_progress_text,
            self.week_remaining_text,
        )

        month_summary = self._compute_month_summary(anchor_date, now)
        month_expected = self._resolve_expected_target(
            month_summary,
            lambda: self._compute_month_summary(anchor_date, now, limit_end=anchor_date),
        )
        self._maybe_update_summary_card(
            "month",
            month_summary.total_worked,
            month_expected,
            self.month_value_text,
            self.month_progress_text,
            self.month_remaining_text,
        )

        year_summary = self._compute_year_summary(anchor_date.year, now)
        year_expected = self._resolve_expected_target(
            year_summary,
            lambda: self._compute_year_summary(anchor_date.year, now, limit_end=anchor_date),
        )
        self._maybe_update_summary_card(
            "year",
            year_summary.total_worked,
            year_expected,
            self.year_value_text,
            self.year_progress_text,
            self.year_remaining_text,
        )

    def _maybe_update_summary_card(
        self,
        key: str,
        actual: float,
        expected: float,
        value_control: ft.Text,
        progress_control: ft.Text,
        remaining_control: ft.Text,
    ) -> None:
        rounded = (round(actual, 4), round(expected, 4))
        if self._summary_cache.get(key) == rounded:
            return
        value_control.value = format_duration(actual)
        progress_control.value = format_duration(expected)
        set_difference_text(remaining_control, actual - expected, with_suffix=True)
        self._summary_cache[key] = rounded

    def _resolve_expected_target(
        self,
        full_summary: RangeSummary,
        limited_summary_factory: Callable[[], RangeSummary],
    ) -> float:
        if self.config.summary_expected_mode == SummaryExpectedMode.TO_DATE:
            return limited_summary_factory().total_expected
        return full_summary.total_expected

    # ------------------------------------------------------------------
    # Timer helpers
    async def _handle_page_disconnect(self, _: ft.ControlEvent) -> None:
        self._stop_ticker()

    def _start_ticker(self) -> None:
        if self._ticker_task is None and hasattr(self.page, "run_task"):
            self._ticker_task = self.page.run_task(self._ticker_loop)

    def _stop_ticker(self) -> None:
        if self._ticker_task is not None:
            self._ticker_task.cancel()
            self._ticker_task = None

    async def _ticker_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(60)
                self._on_timer_tick()
        except asyncio.CancelledError:
            return

    # ------------------------------------------------------------------
    # UI factories
    # Week helpers (legacy history controls removed)

    def _persist_absences(self) -> None:
        self.config.absences.sort(key=lambda r: (r.start, r.end or r.start, r.reason))
        self.absence_storage.save_rules(self.config.absences)

    def _on_timer_tick(self) -> None:
        today_view.refresh(self, datetime.now())
        self.page.update()

    def _show_message(self, message: str) -> None:
        self.page.snack_bar = ft.SnackBar(ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()


def run_app(page: ft.Page) -> None:
    TrackerApp(page).mount()


def main() -> None:
    ft.app(
        target=run_app,
        view=ft.AppView.FLET_APP,
        assets_dir=str(ASSETS_DIR),
    )


if __name__ == "__main__":
    main()
