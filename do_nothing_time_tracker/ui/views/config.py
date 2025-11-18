from __future__ import annotations

from ...models import SummaryExpectedMode
from ..theme import BORDER_GRAY
from ..theme import ERROR_RED
from ..theme import SECONDARY_GRAY
from ..theme import WHITE
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:  # pragma: no cover - only used for static checking
    from ...app import TrackerApp

WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

SUMMARY_MODE_OPTIONS = [
    (
        SummaryExpectedMode.FULL_PERIOD,
        "Full period target",
        "Compare work against the entire week, month, or year target \n when showing remaining or overworked hours.",
    ),
    (
        SummaryExpectedMode.TO_DATE,
        "Up-to-today target",
        "Only count expected hours up to today (including today's plan) \n so the app bar reflects what is left right now.",
    ),
]


def build(app: TrackerApp) -> ft.Container:
    app.config_hours_field = ft.TextField(
        label="Hours per workday",
        value=str(app.config.hours_per_day),
        width=220,
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.InputFilter(regex_string=r"[0-9]*", allow=True),
    )
    app.config_workday_checkboxes = [
        ft.Checkbox(label=name, value=index in app.config.workdays, data=index)
        for index, name in enumerate(WEEKDAY_NAMES)
    ]
    workday_section = ft.Container(
        padding=ft.padding.symmetric(vertical=4),
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Text("Workdays", size=14, weight=ft.FontWeight.W_500),
                ft.Text(
                    "Select the weekdays that count as working days.",
                    size=12,
                    color=SECONDARY_GRAY,
                ),
                ft.Row(
                    wrap=True,
                    spacing=18,
                    run_spacing=6,
                    controls=app.config_workday_checkboxes,
                ),
            ],
        ),
    )
    summary_mode_rows: list[ft.Control] = []
    for mode, title, description in SUMMARY_MODE_OPTIONS:
        summary_mode_rows.append(
            ft.Container(
                padding=ft.padding.symmetric(vertical=4),
                content=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Radio(value=mode.value),
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text(title, size=13, weight=ft.FontWeight.W_500),
                                ft.Text(description, size=12, color=SECONDARY_GRAY),
                            ],
                        ),
                    ],
                ),
            )
        )
    app.config_summary_mode_group = ft.RadioGroup(
        value=app.config.summary_expected_mode.value,
        content=ft.Column(spacing=0, controls=summary_mode_rows),
    )
    app.config_status_text = ft.Text("", size=12, color=SECONDARY_GRAY, text_align=ft.TextAlign.CENTER)
    buttons = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=12,
        controls=[
            ft.FilledButton(
                "Save configuration",
                icon="save",
                on_click=lambda event: _handle_save_config(app, event),
            ),
            ft.OutlinedButton(
                "Reset changes",
                icon="refresh",
                on_click=lambda event: _reset_config_form(app, event),
            ),
        ],
    )
    header = ft.Column(
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text(
                "Configuration",
                size=26,
                weight=ft.FontWeight.W_600,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
    )
    form_sections = [
        ft.Container(
            padding=ft.padding.all(20),
            bgcolor=WHITE,
            border=ft.border.all(1, BORDER_GRAY),
            border_radius=12,
            content=ft.Column(
                spacing=20,
                controls=[
                    ft.Column(
                        spacing=6,
                        controls=[
                            ft.Text(
                                "Work days configuration",
                                size=15,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                "How many hours do you work per day?",
                                size=12,
                                color=SECONDARY_GRAY,
                            ),
                        ],
                    ),
                    app.config_hours_field,
                    workday_section,
                ],
            ),
        ),
        ft.Container(
            padding=ft.padding.all(20),
            bgcolor=WHITE,
            border=ft.border.all(1, BORDER_GRAY),
            border_radius=12,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Column(
                        spacing=6,
                        controls=[
                            ft.Text(
                                "Summary target mode",
                                size=15,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                "Decide whether summaries expected hours and balance is computed up to period or up to today.",
                                size=12,
                                color=SECONDARY_GRAY,
                            ),
                        ],
                    ),
                    app.config_summary_mode_group,
                ],
            ),
        ),
    ]
    form = ft.Column(
        spacing=24,
        width=560,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            header,
            *form_sections,
            buttons,
            app.config_status_text,
        ],
    )
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=20, vertical=10),
        expand=True,
        content=ft.Column(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.ADAPTIVE,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=640,
                            alignment=ft.alignment.center,
                            padding=ft.padding.only(bottom=20),
                            content=form,
                        )
                    ],
                )
            ],
        ),
    )


def _handle_save_config(app: TrackerApp, _: ft.ControlEvent) -> None:
    if app.config_hours_field is None or app.config_summary_mode_group is None:
        return
    raw_hours = (app.config_hours_field.value or "").strip()
    if not raw_hours:
        _set_config_status(app, "Enter the number of hours per workday.", is_error=True)
        return
    try:
        hours_value = int(raw_hours)
    except ValueError:
        _set_config_status(app, "Hours per workday must be a whole number.", is_error=True)
        return
    if hours_value <= 0:
        _set_config_status(app, "Hours per workday must be greater than zero.", is_error=True)
        return

    selected_workdays = sorted(
        checkbox.data
        for checkbox in app.config_workday_checkboxes
        if checkbox.value and isinstance(checkbox.data, int)
    )
    mode_value = app.config_summary_mode_group.value or SummaryExpectedMode.FULL_PERIOD.value
    try:
        summary_mode = SummaryExpectedMode(mode_value)
    except ValueError:
        summary_mode = SummaryExpectedMode.FULL_PERIOD

    app.config.hours_per_day = hours_value
    app.config.workdays = selected_workdays
    app.config.summary_expected_mode = summary_mode

    try:
        app.config_service.save(app.config)
    except Exception as exc:  # noqa: BLE001
        _set_config_status(app, f"Failed to save: {exc}", is_error=True)
        return

    _set_config_status(app, "Configuration saved.", is_error=False)
    app.refresh_all()


def _reset_config_form(app: TrackerApp, _: ft.ControlEvent) -> None:
    app._refresh_config_tab()
    _set_config_status(app, "Changes reverted.", is_error=False)
    app.page.update()


def _set_config_status(app: TrackerApp, message: str, *, is_error: bool) -> None:
    if not app.config_status_text:
        return
    app.config_status_text.value = message
    app.config_status_text.color = ERROR_RED if is_error else SECONDARY_GRAY
    app.config_status_text.update()


__all__ = ["build"]
