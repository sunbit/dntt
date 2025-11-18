from __future__ import annotations

from ..theme import BORDER_GRAY
from ..theme import PRIMARY_BLACK
from ..theme import SECONDARY_GRAY
from . import absence_helpers
from . import entry_controls
from datetime import date
from typing import Optional
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:  # pragma: no cover
    from ...app import TrackerApp
    from ...models import Entry


def build_day_card(app: TrackerApp, day: date, entries: Optional[list[Entry]] = None) -> ft.Control:
    base_entries = entries if entries is not None else app.state.entries_for_day(day)
    day_entries = entry_controls.entries_with_draft(app, day, base_entries)
    title = ft.Text(day.strftime("%A %d %b"), weight=ft.FontWeight.W_600, size=17)
    badge_controls = absence_helpers.absence_badges_for_day(app, day)
    add_btn = ft.TextButton(
        "+ add entry",
        on_click=lambda _: entry_controls.start_new_entry(app, day),
        style=ft.ButtonStyle(padding=0, color=PRIMARY_BLACK),
    )
    if day_entries:
        entry_controls_list = [
            entry_controls.entry_control(app, item, is_last=idx == len(day_entries) - 1)
            for idx, item in enumerate(day_entries)
        ]
    else:
        entry_controls_list = [ft.Text("No entries", italic=True, size=12, color=SECONDARY_GRAY)]

    header_row = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[title, add_btn],
    )

    absences_row = (
        ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=4,
            wrap=True,
            controls=badge_controls,
        )
        if badge_controls
        else None
    )

    entry_column = ft.Column(spacing=0, tight=True, controls=entry_controls_list)
    bordered_entries = ft.Container(
        alignment=ft.alignment.center,
        content=ft.Container(
            width=520,
            padding=8,
            border=ft.border.all(1, BORDER_GRAY),
            border_radius=8,
            content=entry_column,
        ),
    )

    return ft.Container(
        padding=8,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Container(
                    alignment=ft.alignment.center,
                    content=ft.Container(width=520, content=header_row),
                ),
                *(
                    [
                        ft.Container(
                            alignment=ft.alignment.center,
                            content=ft.Container(width=520, content=absences_row),
                        )
                    ]
                    if absences_row
                    else []
                ),
                bordered_entries,
            ],
        ),
    )


__all__ = ["build_day_card"]
