from __future__ import annotations

from ...models import Entry
from ..components import format_duration
from ..theme import LIGHT_GRAY
from ..theme import PRIMARY_BLACK
from ..theme import SECONDARY_GRAY
from ..theme import WHITE
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import Optional
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:  # pragma: no cover - import for typing only
    from ...app import TrackerApp


def start_new_entry(app: TrackerApp, target_day: date) -> None:
    discard_draft_entry(app)
    start_dt, end_dt = default_entry_bounds(app, target_day)
    app._draft_entry = Entry.new(start=start_dt).with_updates(end=end_dt)
    app.editing_entry_id = app._draft_entry.id
    app.refresh_all()


def default_entry_bounds(app: TrackerApp, day: date) -> tuple[datetime, datetime]:
    default_start_time = time(hour=9)
    start_dt = datetime.combine(day, default_start_time)
    workday_hours = app.config.hours_per_day or 8
    default_duration = timedelta(hours=workday_hours if workday_hours > 0 else 8)
    end_dt = start_dt + default_duration
    if end_dt.date() != day:
        end_dt = datetime.combine(day, time(hour=23, minute=59))
    return start_dt, end_dt


def entries_with_draft(app: TrackerApp, day: date, base_entries: list[Entry]) -> list[Entry]:
    entries = list(base_entries)
    if app._draft_entry and app._draft_entry.start.date() == day:
        if all(p.id != app._draft_entry.id for p in entries):
            entries.append(app._draft_entry)
    entries.sort(key=lambda p: p.start)
    return entries


def discard_draft_entry(app: TrackerApp) -> None:
    if app._draft_entry is None:
        return
    if app.editing_entry_id == app._draft_entry.id:
        app.editing_entry_id = None
    app._draft_entry = None


def is_draft_entry(app: TrackerApp, entry_id: Optional[str]) -> bool:
    return bool(app._draft_entry and entry_id and app._draft_entry.id == entry_id)


def entry_control(app: TrackerApp, entry: Entry, *, is_last: bool = False) -> ft.Control:
    if app.editing_entry_id == entry.id:
        return editing_entry_control(app, entry)

    now = datetime.now()
    reference_now = now if (entry.is_open and entry.start.date() == date.today()) else None
    duration = entry.duration_hours(now=reference_now)
    headline = ft.Text(
        f"{entry.start.strftime('%H:%M')} → {entry.end.strftime('%H:%M') if entry.end else '…'}",
        size=13,
        weight=ft.FontWeight.W_500,
        color=PRIMARY_BLACK,
    )
    duration_text = ft.Text(format_duration(duration), size=13, color=SECONDARY_GRAY)
    trailing_controls: list[ft.Control] = []
    if entry.is_open:
        trailing_controls.extend(
            [
                ft.Container(
                    bgcolor=PRIMARY_BLACK,
                    padding=ft.padding.symmetric(horizontal=12, vertical=4),
                    border_radius=50,
                    content=ft.Text("OPEN", size=12, color=WHITE, weight=ft.FontWeight.W_600),
                ),
                ft.Container(width=50),
            ]
        )
    trailing_controls.append(duration_text)
    trailing_controls.append(
        ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=lambda e, p=entry: delete_entry(app, p),
            content=ft.Icon(name="close", size=16, color=PRIMARY_BLACK),
        )
    )
    trailing = ft.Row(
        spacing=2,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=trailing_controls,
    )

    return ft.Container(
        padding=ft.padding.only(top=2, bottom=2),
        on_click=lambda e, p=entry: enter_edit_mode(app, p),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                headline,
                trailing,
            ],
        ),
    )


def editing_entry_control(app: TrackerApp, entry: Entry) -> ft.Control:
    start_hour_field, start_min_field, start_inputs = time_input_controls(" ", entry.start.time())
    end_hour_field, end_min_field, end_inputs = time_input_controls(
        " ", entry.end.time() if entry.end else None, allow_blank=True
    )

    def handle_save(_: ft.ControlEvent) -> None:
        try:
            parsed_date = entry.start.date()
            start_time_value = read_time_inputs(start_hour_field, start_min_field)
            end_time_value = read_time_inputs(end_hour_field, end_min_field, allow_blank=True)
            start_dt = datetime.combine(parsed_date, start_time_value)
            end_dt = datetime.combine(parsed_date, end_time_value) if end_time_value else None
            if end_dt and end_dt <= start_dt:
                raise ValueError("End time must be after start time.")
            updated = entry.with_updates(start=start_dt, end=end_dt)
            open_entry = app.state.open_entry()
            if updated.is_open and open_entry and open_entry.id != updated.id:
                raise ValueError("Close the running entry before creating another open one.")
            app.state.save_entry(updated)
            if is_draft_entry(app, entry.id):
                app._draft_entry = None
            app.editing_entry_id = None
            app.refresh_all()
        except Exception as exc:  # noqa: BLE001
            app._show_message(str(exc))

    def handle_cancel(_: ft.ControlEvent) -> None:
        if is_draft_entry(app, entry.id):
            discard_draft_entry(app)
        app.editing_entry_id = None
        app.refresh_all()

    buttons = ft.Row(
        spacing=8,
        controls=[
            ft.FilledButton("Save", icon="check", on_click=handle_save),
            ft.OutlinedButton("Cancel", on_click=handle_cancel),
            ft.IconButton(
                icon="delete",
                tooltip="Delete",
                on_click=lambda e, p=entry: delete_entry(app, p),
            ),
        ],
    )

    return ft.Card(
        content=ft.Container(
            padding=12,
            bgcolor=LIGHT_GRAY,
            border_radius=8,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text(
                        entry.start.strftime("%A, %B %d"),
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Row(spacing=12, controls=[start_inputs, end_inputs]),
                    buttons,
                ],
            ),
        )
    )


def time_input_controls(
    label: str,
    initial: time | None,
    *,
    allow_blank: bool = False,
) -> tuple[ft.TextField, ft.TextField, ft.Control]:
    hour_value = f"{initial.hour:02d}" if initial else ""
    minute_value = f"{initial.minute:02d}" if initial else ""
    hour_label = f"{label} hour".strip()
    minute_label = f"{label} minute".strip()
    if allow_blank and initial is None:
        hour_label = ""
        minute_label = ""
    hour_field = ft.TextField(
        label=hour_label,
        value=hour_value,
        width=80,
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.InputFilter(regex_string=r"[0-9]*", allow=True),
    )
    minute_field = ft.TextField(
        label=minute_label,
        value=minute_value,
        width=100,
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.InputFilter(regex_string=r"[0-9]*", allow=True),
        hint_text=None if allow_blank else "00",
    )
    row = ft.Column(
        spacing=4,
        controls=[
            ft.Text(label, size=12, color=SECONDARY_GRAY),
            ft.Row(
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[hour_field, ft.Text(":"), minute_field],
            ),
        ],
    )
    return hour_field, minute_field, row


def read_time_inputs(
    hour_field: ft.TextField,
    minute_field: ft.TextField,
    *,
    allow_blank: bool = False,
) -> Optional[time]:
    hour_raw = (hour_field.value or "").strip()
    minute_raw = (minute_field.value or "").strip()
    if not hour_raw and not minute_raw:
        if allow_blank:
            return None
        raise ValueError("Time is required.")
    if not hour_raw or not minute_raw:
        raise ValueError("Provide both hour and minute.")
    hour = int(hour_raw)
    minute = int(minute_raw)
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError("Enter a valid 24h time.")
    return time(hour=hour, minute=minute)


def open_entry_editor(
    app: TrackerApp, entry: Optional[Entry] = None, default_date: Optional[date] = None
) -> None:
    if app._draft_entry is not None:
        discard_draft_entry(app)
        app.refresh_all()
    dialog = build_entry_editor(app, entry, default_date)
    app.page.dialog = dialog
    dialog.open = True
    app.page.update()


def build_entry_editor(
    app: TrackerApp, entry: Optional[Entry], default_date: Optional[date]
) -> ft.AlertDialog:
    default_start_dt = (
        entry.start if entry else datetime.combine(default_date or app.selected_date, time(hour=9))
    )
    target_date = default_start_dt.date()
    default_end_time = entry.end.time() if entry and entry.end else time(hour=17)

    date_field = ft.TextField(label="Date", value=target_date.isoformat())
    start_hour_field, start_min_field, start_inputs = time_input_controls("Start", default_start_dt.time())
    allow_open_end = entry is not None
    end_hour_field, end_min_field, end_inputs = time_input_controls(
        "End", default_end_time, allow_blank=allow_open_end
    )

    def handle_submit(_: ft.ControlEvent) -> None:
        try:
            parsed_date = date.fromisoformat(date_field.value)
            start_time_value = read_time_inputs(start_hour_field, start_min_field)
            end_time_value = read_time_inputs(end_hour_field, end_min_field, allow_blank=allow_open_end)
            start_dt = datetime.combine(parsed_date, start_time_value)
            end_dt = datetime.combine(parsed_date, end_time_value) if end_time_value else None
            if end_dt and end_dt <= start_dt:
                raise ValueError("End time must be after start time.")
            if not entry and end_dt is None:
                raise ValueError("Manual entries must have an end time.")
            updated = (
                entry.with_updates(start=start_dt, end=end_dt)
                if entry
                else Entry.new(start=start_dt).with_updates(end=end_dt)
            )
            open_entry = app.state.open_entry()
            if updated.is_open and open_entry and open_entry.id != updated.id:
                raise ValueError("Close the running entry before creating another open one.")
            app.state.save_entry(updated)
            app.page.dialog.open = False
            app.refresh_all()
        except Exception as exc:  # noqa: BLE001
            app._show_message(str(exc))

    actions = [
        ft.TextButton("Cancel", on_click=lambda _: close_dialog(app)),
        ft.FilledButton("Save", on_click=handle_submit),
    ]

    return ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit entry" if entry else "New entry"),
        content=ft.Column(spacing=12, controls=[date_field, start_inputs, end_inputs]),
        actions=actions,
    )


def close_dialog(app: TrackerApp) -> None:
    if app.page.dialog:
        app.page.dialog.open = False
        app.page.update()


def enter_edit_mode(app: TrackerApp, entry: Entry) -> None:
    if app._draft_entry and app._draft_entry.id != entry.id:
        discard_draft_entry(app)
    app.editing_entry_id = entry.id
    app.refresh_all()


def delete_entry(app: TrackerApp, entry: Entry) -> None:
    if is_draft_entry(app, entry.id):
        discard_draft_entry(app)
        app.refresh_all()
        return
    if app.editing_entry_id == entry.id:
        app.editing_entry_id = None
    app.state.delete_entry(entry.id)
    app.refresh_all()


__all__ = [
    "build_entry_editor",
    "close_dialog",
    "default_entry_bounds",
    "delete_entry",
    "discard_draft_entry",
    "editing_entry_control",
    "enter_edit_mode",
    "entries_with_draft",
    "entry_control",
    "is_draft_entry",
    "open_entry_editor",
    "read_time_inputs",
    "start_new_entry",
    "time_input_controls",
]
