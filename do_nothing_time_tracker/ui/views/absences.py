from __future__ import annotations

from ...models import AbsenceRule
from ..theme import BORDER_GRAY
from ..theme import LIGHT_GRAY
from ..theme import PRIMARY_BLACK
from ..theme import SECONDARY_GRAY
from ..theme import text_style
from ..theme import WHITE
from datetime import date
from typing import Callable
from typing import Optional
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:  # pragma: no cover - only for static analysis
    from ...app import TrackerApp


def build(app: TrackerApp) -> ft.Container:
    add_btn = ft.TextButton(
        "Add absence",
        icon="add",
        on_click=lambda event: _on_add_absence_click(app, event),
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, PRIMARY_BLACK),
            padding=ft.padding.symmetric(horizontal=16, vertical=6),
            shape=ft.RoundedRectangleBorder(radius=8),
            color=PRIMARY_BLACK,
            text_style=text_style(weight=ft.FontWeight.W_500),
        ),
    )
    helper = ft.Text(
        "Review and adjust planned absences.",
        size=12,
        color=SECONDARY_GRAY,
        text_align=ft.TextAlign.CENTER,
    )
    app.absences_list_column = ft.Column(spacing=0, expand=True)
    content_controls: list[ft.Control] = [
        ft.Container(alignment=ft.alignment.center, content=helper),
        ft.Container(alignment=ft.alignment.center, content=add_btn),
        ft.Container(
            alignment=ft.alignment.center,
            content=ft.Container(width=640, content=app.absences_list_column),
        ),
    ]
    column = ft.Column(
        expand=True,
        spacing=16,
        controls=content_controls,
        scroll=ft.ScrollMode.ADAPTIVE,
    )
    return ft.Container(padding=10, expand=True, content=column)


def refresh_tab(app: TrackerApp) -> None:
    if not isinstance(app.absences_list_column, ft.Column):
        return
    if not app.config.absences:
        app.absences_list_column.controls = [
            ft.Container(
                alignment=ft.alignment.center,
                padding=20,
                content=ft.Text("No absences configured.", italic=True, color=SECONDARY_GRAY),
            )
        ]
        return
    indexed_absences = list(enumerate(app.config.absences))
    indexed_absences.sort(
        key=lambda item: (
            item[1].start,
            item[1].end or item[1].start,
            item[1].reason,
        )
    )
    rows = [_absence_row(app, position, idx, rule) for position, (idx, rule) in enumerate(indexed_absences)]
    table = ft.Container(
        border=ft.border.all(1, BORDER_GRAY),
        border_radius=12,
        bgcolor=WHITE,
        content=ft.Column(
            spacing=0,
            controls=[_absence_table_header(), *rows],
        ),
    )
    app.absences_list_column.controls = [table]


def _on_add_absence_click(app: TrackerApp, _: ft.ControlEvent) -> None:
    _open_absence_editor(app)


def _on_edit_absence_click(app: TrackerApp, event: ft.ControlEvent) -> None:
    index = _index_from_control(event)
    if index is not None:
        _open_absence_editor(app, index)


def _on_delete_absence_click(app: TrackerApp, event: ft.ControlEvent) -> None:
    index = _index_from_control(event)
    if index is not None:
        _delete_absence(app, index)


def _absence_table_header() -> ft.Control:
    return ft.Container(
        padding=ft.padding.symmetric(vertical=10, horizontal=12),
        bgcolor=LIGHT_GRAY,
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                _absence_table_cell("Dates", expand=2, emphasize=True),
                _absence_table_cell("Reason", expand=3, emphasize=True),
                _absence_table_cell(
                    "Days",
                    width=70,
                    align=ft.alignment.center_right,
                    emphasize=True,
                ),
                _absence_table_cell(
                    "Hours",
                    width=110,
                    align=ft.alignment.center_right,
                    emphasize=True,
                ),
                _absence_table_cell(
                    "Actions",
                    width=90,
                    align=ft.alignment.center_right,
                    emphasize=True,
                ),
            ],
        ),
    )


def _absence_row(app: TrackerApp, position: int, config_index: int, rule: AbsenceRule) -> ft.Control:
    range_text = _format_absence_range(rule)
    day_count = _absence_day_count(rule)
    total_hours = _absence_total_hours(app, rule, day_count)
    hours_text = f"{_format_hours_value(total_hours)} h"
    if rule.hours is None:
        hours_text += " · full day" + ("s" if day_count != 1 else "")
    days_text = f"{day_count} day" + ("s" if day_count != 1 else "")
    reason_text = rule.reason or "Absence"
    row_bg = WHITE if position % 2 == 0 else "#F7F7F7"
    top_border = ft.border.BorderSide(1, BORDER_GRAY) if position > 0 else None
    return ft.Container(
        bgcolor=row_bg,
        padding=ft.padding.symmetric(vertical=10, horizontal=12),
        border=ft.border.only(top=top_border) if top_border else None,
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                _absence_table_cell(range_text, expand=2),
                _absence_table_cell(reason_text, expand=3),
                _absence_table_cell(days_text, width=70, align=ft.alignment.center_right),
                _absence_table_cell(hours_text, width=110, align=ft.alignment.center_right),
                ft.Container(
                    width=90,
                    alignment=ft.alignment.center_right,
                    content=ft.Row(
                        spacing=4,
                        controls=[
                            _absence_action_icon(
                                app,
                                "edit",
                                "Edit absence",
                                str(config_index),
                                _on_edit_absence_click,
                            ),
                            _absence_action_icon(
                                app,
                                "delete",
                                "Delete absence",
                                str(config_index),
                                _on_delete_absence_click,
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )


def _absence_table_cell(
    text: str,
    *,
    expand: int | None = None,
    width: float | None = None,
    align: ft.alignment.Alignment = ft.alignment.center_left,
    emphasize: bool = False,
) -> ft.Control:
    return ft.Container(
        expand=expand,
        width=width,
        alignment=align,
        content=ft.Text(
            text,
            size=13,
            color=PRIMARY_BLACK,
            weight=ft.FontWeight.W_600 if emphasize else ft.FontWeight.W_400,
            max_lines=3,
            overflow=ft.TextOverflow.ELLIPSIS,
        ),
    )


def _absence_action_icon(
    app: TrackerApp,
    icon: str,
    tooltip: str,
    data: str,
    handler: Callable[[TrackerApp, ft.ControlEvent], None],
) -> ft.IconButton:
    return ft.IconButton(
        icon=icon,
        tooltip=tooltip,
        data=data,
        icon_color=PRIMARY_BLACK,
        icon_size=18,
        on_click=lambda event: handler(app, event),
        style=ft.ButtonStyle(
            padding=ft.padding.all(6),
            shape=ft.RoundedRectangleBorder(radius=6),
        ),
    )


def _format_absence_range(rule: AbsenceRule) -> str:
    start_text = rule.start.strftime("%b %d, %Y")
    if not rule.end or rule.end == rule.start:
        return start_text
    end_text = rule.end.strftime("%b %d, %Y")
    return f"{start_text} →\n{end_text}"


def _absence_day_count(rule: AbsenceRule) -> int:
    if not rule.end or rule.end <= rule.start:
        return 1
    return (rule.end - rule.start).days + 1


def _absence_total_hours(app: TrackerApp, rule: AbsenceRule, day_count: int | None = None) -> float:
    per_day = rule.hours if rule.hours is not None else app.config.hours_per_day
    count = day_count if day_count is not None else _absence_day_count(rule)
    return float(per_day) * count


def _format_hours_value(value: float) -> str:
    rounded = round(value, 3)
    if abs(rounded - round(rounded)) < 1e-6:
        return str(int(round(rounded)))
    trimmed = f"{rounded:.2f}".rstrip("0").rstrip(".")
    return trimmed


def _index_from_control(event: ft.ControlEvent) -> Optional[int]:
    try:
        return int(event.control.data)
    except (TypeError, ValueError):
        return None


def _open_absence_editor(app: TrackerApp, index: Optional[int] = None) -> None:
    dialog = _ensure_absence_editor(app)
    app._absence_editor_index = index
    rule = app.config.absences[index] if index is not None else None
    start_value = rule.start.isoformat() if rule else ""
    end_value = rule.end.isoformat() if rule and rule.end else ""
    reason_value = rule.reason if rule else ""
    hours_value = (
        str(rule.hours)
        if rule and rule.hours is not None
        else (str(app.config.hours_per_day) if app.config.hours_per_day else "")
    )
    if app._absence_start_field:
        app._absence_start_field.value = start_value
    if app._absence_end_field:
        app._absence_end_field.value = end_value
    if app._absence_reason_field:
        app._absence_reason_field.value = reason_value
    if app._absence_hours_field:
        app._absence_hours_field.value = hours_value
    if app._absence_editor_title:
        app._absence_editor_title.value = "Edit absence" if index is not None else "New absence"
    if dialog not in app.page.overlay:
        app.page.overlay.append(dialog)
    dialog.open = True
    app.page.update()


def _ensure_absence_editor(app: TrackerApp) -> ft.AlertDialog:
    if app._absence_editor_dialog is not None:
        return app._absence_editor_dialog

    app._absence_start_field = ft.TextField(hint_text="YYYY-MM-DD", expand=True, dense=True)
    app._absence_end_field = ft.TextField(hint_text="YYYY-MM-DD", expand=True, dense=True)
    app._absence_reason_field = ft.TextField(
        hint_text="Vacation, holiday, etc.",
        multiline=True,
        min_lines=2,
        max_lines=4,
        expand=True,
        dense=True,
    )
    app._absence_hours_field = ft.TextField(
        hint_text="Leave blank for full day off",
        width=180,
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.InputFilter(regex_string=r"[0-9]*", allow=True),
        dense=True,
        text_align=ft.TextAlign.RIGHT,
    )
    app._absence_editor_title = ft.Text("")

    _ensure_start_date_picker(app)
    _ensure_end_date_picker(app)

    content_rows = [
        _absence_editor_row(
            "Start date",
            _date_input_group(app, app._absence_start_field, _show_start_date_picker),
        ),
        _absence_editor_row(
            "End date",
            _date_input_group(app, app._absence_end_field, _show_end_date_picker),
        ),
        ft.Container(
            padding=ft.padding.only(left=156, bottom=4),
            content=ft.Text(
                "Only set an end date for multi-day absences. The end date is inclusive.",
                size=11,
                color=SECONDARY_GRAY,
                italic=True,
            ),
        ),
        _absence_editor_row("Reason", app._absence_reason_field),
        _absence_editor_row(
            "Hours credited",
            ft.Container(width=200, content=app._absence_hours_field),
        ),
    ]

    actions = [
        ft.TextButton("Cancel", on_click=lambda event: _cancel_absence_editor(app, event)),
        ft.FilledButton("Save", on_click=lambda event: _save_absence_from_editor(app, event)),
    ]

    dialog = ft.AlertDialog(
        modal=True,
        title=app._absence_editor_title,
        content=ft.Container(
            width=520,
            content=ft.Column(
                spacing=16,
                controls=content_rows,
            ),
        ),
        actions=actions,
    )
    app._absence_editor_dialog = dialog
    return dialog


def _absence_editor_row(label: str, input_control: ft.Control) -> ft.Control:
    return ft.Container(
        content=ft.Row(
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=140,
                    alignment=ft.alignment.center_right,
                    content=ft.Text(label, size=13, color=SECONDARY_GRAY),
                ),
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.center_left,
                    content=input_control,
                ),
            ],
        )
    )


def _date_input_group(
    app: TrackerApp, field: ft.TextField, handler: Callable[[TrackerApp, ft.ControlEvent], None]
) -> ft.Control:
    field.expand = True
    return ft.Row(
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(expand=True, content=field),
            ft.IconButton(
                icon="calendar_today",
                tooltip="Pick date",
                on_click=lambda event: handler(app, event),
                icon_size=20,
                style=ft.ButtonStyle(
                    padding=ft.padding.all(6),
                    shape=ft.RoundedRectangleBorder(radius=6),
                ),
            ),
        ],
    )


def _cancel_absence_editor(app: TrackerApp, _: ft.ControlEvent) -> None:
    app._absence_editor_index = None
    _close_absence_editor(app)


def _save_absence_from_editor(app: TrackerApp, _: ft.ControlEvent) -> None:
    try:
        if not all(
            [
                app._absence_start_field,
                app._absence_end_field,
                app._absence_reason_field,
                app._absence_hours_field,
            ]
        ):
            raise ValueError("Editor fields not initialized.")
        start_value = (app._absence_start_field.value or "").strip()
        end_raw = (app._absence_end_field.value or "").strip()
        reason_value = (app._absence_reason_field.value or "").strip()
        if not start_value:
            raise ValueError("Start date is required.")
        start_date = date.fromisoformat(start_value)
        end_date = date.fromisoformat(end_raw) if end_raw else None
        if end_date and end_date < start_date:
            raise ValueError("End date cannot be before start date.")
        hours_raw = (app._absence_hours_field.value or "").strip()
        hours_value = int(hours_raw) if hours_raw else None
        updated = AbsenceRule(start=start_date, end=end_date, reason=reason_value, hours=hours_value)
        if app._absence_editor_index is None:
            app.config.absences.append(updated)
        else:
            app.config.absences[app._absence_editor_index] = updated
        app._absence_editor_index = None
        _persist_absences(app)
        _close_absence_editor(app)
        app.refresh_all()
    except Exception as exc:  # noqa: BLE001
        app._show_message(str(exc))


def _show_start_date_picker(app: TrackerApp, _: ft.ControlEvent) -> None:
    picker = _ensure_start_date_picker(app)
    default_value = _parse_date_value(app._absence_start_field.value if app._absence_start_field else None)
    picker.value = default_value or date.today()
    picker.open = True
    picker.update()


def _show_end_date_picker(app: TrackerApp, _: ft.ControlEvent) -> None:
    picker = _ensure_end_date_picker(app)
    default_value = _parse_date_value(app._absence_end_field.value if app._absence_end_field else None)
    if not default_value and app._absence_start_field:
        default_value = _parse_date_value(app._absence_start_field.value)
    picker.value = default_value or date.today()
    picker.open = True
    picker.update()


def _ensure_start_date_picker(app: TrackerApp) -> ft.DatePicker:
    if app._start_date_picker is None:
        app._start_date_picker = ft.DatePicker(on_change=lambda event: _handle_start_date_picked(app, event))
    if app._start_date_picker not in app.page.overlay:
        app.page.overlay.append(app._start_date_picker)
    return app._start_date_picker


def _ensure_end_date_picker(app: TrackerApp) -> ft.DatePicker:
    if app._end_date_picker is None:
        app._end_date_picker = ft.DatePicker(on_change=lambda event: _handle_end_date_picked(app, event))
    if app._end_date_picker not in app.page.overlay:
        app.page.overlay.append(app._end_date_picker)
    return app._end_date_picker


def _handle_start_date_picked(app: TrackerApp, event: ft.ControlEvent) -> None:
    if app._absence_start_field and event.control.value:
        app._absence_start_field.value = event.control.value.strftime("%Y-%m-%d")
        app._absence_start_field.update()


def _handle_end_date_picked(app: TrackerApp, event: ft.ControlEvent) -> None:
    if app._absence_end_field and event.control.value:
        app._absence_end_field.value = event.control.value.strftime("%Y-%m-%d")
        app._absence_end_field.update()


def _parse_date_value(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _delete_absence(app: TrackerApp, index: int) -> None:
    if index < 0 or index >= len(app.config.absences):
        return
    del app.config.absences[index]
    _persist_absences(app)
    app.refresh_all()


def _persist_absences(app: TrackerApp) -> None:
    app._persist_absences()


def _close_absence_editor(app: TrackerApp) -> None:
    if app._absence_editor_dialog and app._absence_editor_dialog.open:
        app._absence_editor_dialog.open = False
        app.page.update()


__all__ = ["build", "refresh_tab"]
