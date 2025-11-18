from __future__ import annotations

from ..theme import LIGHT_GRAY
from ..theme import PRIMARY_BLACK
from datetime import date
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:  # pragma: no cover
    from ...app import TrackerApp


def absence_labels_for_day(app: TrackerApp, target_day: date) -> list[str]:
    labels: list[str] = []
    for rule in app.config.absences:
        if rule.includes(target_day):
            credit_hours = rule.hours if rule.hours is not None else app.config.hours_per_day
            reason = rule.reason or "Absence"
            labels.append(f"{reason} - {credit_hours} h")
    return labels


def build_absence_chip(
    label: str,
    *,
    centered: bool = False,
    bgcolor: str = LIGHT_GRAY,
) -> ft.Control:
    return ft.Container(
        padding=4,
        bgcolor=bgcolor,
        border_radius=8,
        content=ft.Text(
            label,
            size=12,
            color=PRIMARY_BLACK,
            text_align=ft.TextAlign.CENTER if centered else ft.TextAlign.LEFT,
        ),
    )


def absence_badges_for_day(app: TrackerApp, day: date) -> list[ft.Control]:
    labels = absence_labels_for_day(app, day)
    return [build_absence_chip(label, bgcolor=LIGHT_GRAY) for label in labels]


__all__ = [
    "absence_badges_for_day",
    "absence_labels_for_day",
    "build_absence_chip",
]
