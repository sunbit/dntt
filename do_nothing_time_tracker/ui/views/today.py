from __future__ import annotations

from ...summaries import get_day_summary
from ..components import set_summary_sentence
from ..theme import BORDER_GRAY
from ..theme import PRIMARY_BLACK
from ..theme import text_style
from ..theme import WHITE
from . import absence_helpers
from . import entry_controls
from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:  # pragma: no cover - runtime import avoided
    from ...app import TrackerApp


def build(app: TrackerApp) -> ft.Container:
    prev_btn = ft.IconButton(
        icon="chevron_left",
        tooltip="Previous day",
        on_click=lambda event: shift_day(app, -1, event),
    )
    next_btn = ft.IconButton(
        icon="chevron_right",
        tooltip="Next day",
        on_click=lambda event: shift_day(app, 1, event),
    )
    today_btn = ft.TextButton(
        "Go to today",
        on_click=lambda event: goto_today(app, event),
        style=ft.ButtonStyle(text_style=text_style()),
    )

    app.clock_in_button.on_click = lambda event: handle_clock_in(app, event)
    app.clock_in_button.style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=8),
        text_style=text_style(color=WHITE),
    )
    app.clock_out_button.on_click = lambda event: handle_clock_out(app, event)
    app.clock_out_button.style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=8),
        text_style=text_style(color=WHITE),
    )
    add_manual_btn = ft.TextButton(
        "+ add manual entry",
        on_click=lambda _: entry_controls.start_new_entry(app, app.selected_date),
        style=ft.ButtonStyle(color=PRIMARY_BLACK, text_style=text_style()),
    )

    entries_section = ft.Column(
        spacing=4,
        controls=[
            ft.Container(height=20),
            ft.Container(
                alignment=ft.alignment.center,
                content=ft.Text(
                    "Entries",
                    size=22,
                    weight=ft.FontWeight.W_500,
                    text_align=ft.TextAlign.CENTER,
                ),
            ),
            ft.Container(
                alignment=ft.alignment.center,
                content=ft.Container(
                    width=520,
                    padding=4,
                    border=ft.border.all(1, BORDER_GRAY),
                    border_radius=6,
                    content=app.today_entries_column,
                ),
            ),
            ft.Container(alignment=ft.alignment.center, padding=4, content=add_manual_btn),
        ],
    )

    absences_block = ft.Column(
        controls=[
            ft.Container(height=20),
            ft.Container(
                alignment=ft.alignment.center,
                content=ft.Text(
                    "Absences",
                    size=22,
                    weight=ft.FontWeight.W_500,
                    text_align=ft.TextAlign.CENTER,
                ),
            ),
            ft.Container(
                alignment=ft.alignment.center,
                padding=4,
                content=app.absences_column,
            ),
        ]
    )

    content_controls: list[ft.Control] = [
        ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            controls=[prev_btn, app.today_title, next_btn],
        ),
        ft.Container(alignment=ft.alignment.center, content=today_btn),
        ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
            controls=[app.clock_in_button, app.clock_out_button],
        ),
        ft.Container(
            alignment=ft.alignment.center,
            padding=ft.padding.only(top=10),
            content=app.today_summary_card,
        ),
        entries_section,
        absences_block,
    ]

    column = ft.Column(
        expand=True,
        spacing=10,
        controls=content_controls,
        scroll=ft.ScrollMode.ADAPTIVE,
    )
    return ft.Container(padding=10, expand=False, content=column)


def refresh(app: TrackerApp, now: datetime) -> None:
    entries = app.state.entries_for_day(app.selected_date)
    if app.editing_entry_id:
        exists_in_state = app.state.find_entry(app.editing_entry_id) is not None
        if not exists_in_state and not entry_controls.is_draft_entry(app, app.editing_entry_id):
            app.editing_entry_id = None
    today = date.today()
    reference_now = now if app.selected_date == today else None
    day_result = get_day_summary(
        app.selected_date,
        app.selected_date,
        entry_retriever=app.state,
        absence_retriever=app.absence_retriever,
        config=app.config,
        now=reference_now,
    )
    day_summary = day_result.period.summary
    worked_hours = day_summary.worked
    expected_today = day_summary.expected

    app.today_title.value = app.selected_date.strftime("%A, %B %d, %Y")

    open_entry = app.state.open_entry()
    app.clock_in_button.disabled = open_entry is not None
    app.clock_out_button.disabled = open_entry is None

    set_summary_sentence(app.day_summary_text, worked_hours, expected_today)

    visible_entries = entry_controls.entries_with_draft(app, app.selected_date, entries)
    entry_controls_list = [
        entry_controls.entry_control(app, entry, is_last=idx == len(visible_entries) - 1)
        for idx, entry in enumerate(visible_entries)
    ]
    if not entry_controls_list:
        entry_controls_list = [ft.Text("Nothing logged yet.", italic=True)]
    app.today_entries_column.controls = entry_controls_list

    refresh_absences(app)


def refresh_absences(app: TrackerApp) -> None:
    target_day = app.selected_date
    todays_absence_labels = absence_helpers.absence_labels_for_day(app, target_day)
    if not todays_absence_labels:
        app.absences_column.controls = [
            ft.Text(
                "No absences planned for this day.",
                italic=True,
                text_align=ft.TextAlign.CENTER,
            )
        ]
        return
    app.absences_column.controls = [
        absence_helpers.build_absence_chip(label, centered=True) for label in todays_absence_labels
    ]


def shift_day(app: TrackerApp, delta: int, _: ft.ControlEvent | None = None) -> None:
    app.selected_date += timedelta(days=delta)
    app.refresh_all()


def goto_today(app: TrackerApp, _: ft.ControlEvent | None = None) -> None:
    app.selected_date = date.today()
    app.refresh_all()


def handle_clock_in(app: TrackerApp, _: ft.ControlEvent | None = None) -> None:
    try:
        app.state.clock_in()
        goto_today(app)
    except ValueError as exc:
        app._show_message(str(exc))


def handle_clock_out(app: TrackerApp, _: ft.ControlEvent | None = None) -> None:
    try:
        app.state.clock_out()
        goto_today(app)
    except ValueError as exc:
        app._show_message(str(exc))


__all__ = [
    "build",
    "refresh",
    "refresh_absences",
    "shift_day",
    "goto_today",
    "handle_clock_in",
    "handle_clock_out",
]
