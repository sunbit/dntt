from __future__ import annotations

from .components import summary_card
from .theme import HEADER_BG
from .theme import HERO_IMAGE_ASSET
from .theme import PRIMARY_BLACK
from .theme import SECONDARY_GRAY
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from ..app import TrackerApp


def build_app_header(app: TrackerApp, navigation: ft.Control | None = None) -> ft.Control:
    title = ft.Text("Do nothing.", size=40, weight=ft.FontWeight.W_600, color=PRIMARY_BLACK)
    subtitle = ft.Text("But Keep Track of It.", size=20, color=SECONDARY_GRAY)
    title_block = ft.Column(
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.END,
        controls=[title, subtitle],
    )
    image = ft.Image(src=HERO_IMAGE_ASSET, width=118, height=130, fit=ft.ImageFit.CONTAIN)
    hero_container = ft.Container(
        padding=ft.padding.only(top=10, right=8, bottom=4, left=0),
        alignment=ft.alignment.top_left,
        content=image,
        expand=1,
        col={"xs": 12, "md": 5},
    )
    text_container = ft.Container(
        alignment=ft.alignment.top_right,
        padding=ft.padding.only(right=100, top=50),
        content=title_block,
        expand=1,
        col={"xs": 12, "md": 7},
    )
    header_row = ft.ResponsiveRow(
        spacing=0,
        run_spacing=0,
        controls=[hero_container, text_container],
        columns=12,
    )
    cards = ft.Container(
        padding=ft.padding.symmetric(horizontal=20, vertical=20),
        content=ft.ResponsiveRow(
            spacing=30,
            run_spacing=30,
            controls=[
                summary_card(
                    "Current week",
                    app.week_value_text,
                    app.week_progress_text,
                    app.week_remaining_text,
                    highlight=True,
                ),
                summary_card(
                    "Current month",
                    app.month_value_text,
                    app.month_progress_text,
                    app.month_remaining_text,
                ),
                summary_card(
                    "Current year",
                    app.year_value_text,
                    app.year_progress_text,
                    app.year_remaining_text,
                ),
            ],
        ),
    )
    navigation_section: list[ft.Control] = []
    if navigation is not None:
        navigation_section.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                content=navigation,
            )
        )
    return ft.Container(
        bgcolor=HEADER_BG,
        padding=ft.padding.symmetric(horizontal=0),
        content=ft.Column(
            spacing=0,
            controls=[
                header_row,
                cards,
                *navigation_section,
            ],
        ),
    )


__all__ = ["build_app_header"]
