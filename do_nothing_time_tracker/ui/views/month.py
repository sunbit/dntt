from __future__ import annotations

from ...summaries import get_month_summary
from ..components import set_summary_sentence
from .day_cards import build_day_card
from .today import goto_today
from calendar import monthrange
from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from ...app import TrackerApp


def build(app: TrackerApp) -> ft.Container:
    prev_month_btn = ft.IconButton(icon="chevron_left", on_click=lambda event: shift_month(app, -1, event))
    next_month_btn = ft.IconButton(icon="chevron_right", on_click=lambda event: shift_month(app, 1, event))
    today_month_btn = ft.TextButton("Go to current month", on_click=lambda event: goto_today(app, event))

    header = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=12,
        controls=[prev_month_btn, app.month_title_text, next_month_btn],
    )

    content_controls: list[ft.Control] = [
        header,
        ft.Container(alignment=ft.alignment.center, content=today_month_btn),
        ft.Container(
            alignment=ft.alignment.center,
            padding=ft.padding.only(top=10),
            content=app.month_summary_card,
        ),
        app.month_weeks_column,
    ]

    column = ft.Column(
        expand=True,
        spacing=10,
        controls=content_controls,
        scroll=ft.ScrollMode.ADAPTIVE,
    )
    return ft.Container(padding=10, expand=True, content=column)


def refresh(app: TrackerApp, now: datetime) -> None:
    year = app.selected_date.year
    month = app.selected_date.month
    month_start = date(year, month, 1)
    app.month_title_text.value = f"{month_start.strftime('%B %Y')}"
    _, days_in_month = monthrange(month_start.year, month_start.month)
    month_end = month_start + timedelta(days=days_in_month - 1)
    month_result = get_month_summary(
        month_start,
        month_end,
        entry_retriever=app.state,
        absence_retriever=app.absence_retriever,
        config=app.config,
        now=now,
    )
    week_details = month_result.period.weeks
    if not week_details:
        app.month_weeks_column.controls = [ft.Text("No days available for this month.", italic=True)]
    else:
        week_controls = [month_week_block(app, summary) for summary in week_details]
        app.month_weeks_column.controls = week_controls
    month_summary = month_result.summary
    set_summary_sentence(
        app.month_tab_summary_text,
        month_summary.total_worked,
        month_summary.total_expected,
    )


def month_week_block(app: TrackerApp, summary) -> ft.Control:
    title = ft.Text(
        f"Week of {summary.start.strftime('%b %d')} -  {summary.end.strftime('%b %d')}",
        weight=ft.FontWeight.W_500,
        size=15,
    )
    day_controls = [
        build_day_card(app, day_summary.date, entries=list(day_summary.entries))
        for day_summary in summary.days
    ]
    line_width = app.page.width * 0.8 if getattr(app.page, "width", None) else 600
    separator = ft.Container(
        alignment=ft.alignment.center,
        padding=ft.padding.symmetric(vertical=6),
        content=ft.Container(width=line_width, height=2, bgcolor="#333333"),
    )
    return ft.Container(
        padding=8,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Container(alignment=ft.alignment.center, content=title),
                ft.Column(spacing=8, controls=day_controls),
                separator,
            ],
        ),
    )


def shift_month(app: TrackerApp, delta: int, _: ft.ControlEvent | None = None) -> None:
    year = app.selected_date.year
    month = app.selected_date.month + delta
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1
    max_day = monthrange(year, month)[1]
    day = min(app.selected_date.day, max_day)
    app.selected_date = date(year, month, day)
    app.refresh_all()


__all__ = ["build", "refresh", "shift_month"]
