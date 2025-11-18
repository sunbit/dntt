from __future__ import annotations

from ..components import set_summary_sentence
from .day_cards import build_day_card
from .today import goto_today
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from ...app import TrackerApp


def build(app: TrackerApp) -> ft.Container:
    prev_week_btn = ft.IconButton(icon="chevron_left", on_click=lambda event: shift_week(app, -1, event))
    next_week_btn = ft.IconButton(icon="chevron_right", on_click=lambda event: shift_week(app, 1, event))
    today_week_btn = ft.TextButton("Go to current week", on_click=lambda event: goto_today(app, event))

    header = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=12,
        controls=[prev_week_btn, app.week_title_text, next_week_btn],
    )

    content_controls: list[ft.Control] = [
        header,
        ft.Container(alignment=ft.alignment.center, content=today_week_btn),
        ft.Container(
            alignment=ft.alignment.center,
            padding=ft.padding.only(top=10),
            content=app.week_summary_card,
        ),
        app.week_days_column,
    ]

    column = ft.Column(
        expand=True,
        spacing=10,
        controls=content_controls,
        scroll=ft.ScrollMode.ADAPTIVE,
    )
    return ft.Container(padding=10, expand=True, content=column)


def refresh(app: TrackerApp, now: datetime) -> None:
    week_start = app._week_start_for(app.selected_date)
    week_end = week_start + timedelta(days=4)
    app.week_title_text.value = f"Week of {week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"
    day_controls: list[ft.Control] = []
    for offset in range(5):
        day = week_start + timedelta(days=offset)
        day_controls.append(build_day_card(app, day))
    app.week_days_column.controls = day_controls
    week_summary = app._compute_week_summary(app.selected_date, now)
    set_summary_sentence(
        app.week_tab_summary_text,
        week_summary.total_worked,
        week_summary.total_expected,
    )


def shift_week(app: TrackerApp, delta: int, _: ft.ControlEvent | None = None) -> None:
    app.selected_date += timedelta(days=7 * delta)
    app.refresh_all()


__all__ = ["build", "refresh", "shift_week"]
