from __future__ import annotations

from .layout import build_app_header
from .theme import APP_BG
from .theme import APP_FONT
from .theme import APP_FONT_ASSET
from .theme import APP_FONT_FILE
from .theme import BORDER_GRAY
from .theme import HERO_IMAGE_FILE
from .theme import PRIMARY_BLACK
from .theme import SECONDARY_GRAY
from .theme import text_style
from .theme import WHITE
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:  # pragma: no cover - only imported for typing
    from ..app import TrackerApp


def setup_page(app: TrackerApp, tab_definitions: list[tuple[str, ft.Control]]) -> ft.Tabs:
    page = app.page
    page.title = "Do Nothing Time Tracker"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.window.height = 1000
    page.window.width = 900
    if hasattr(page.window, "center"):
        page.window.center()
    if hasattr(page, "window_bgcolor"):
        page.window_bgcolor = APP_BG
    _ensure_assets()
    page.fonts = {
        APP_FONT: APP_FONT_ASSET,
    }
    page.theme = ft.Theme(
        color_scheme=_color_scheme(),
        font_family=APP_FONT,
        text_theme=_text_theme(),
        scrollbar_theme=_scrollbar_theme(),
    )
    page.bgcolor = APP_BG
    page.padding = 0

    tabs_navigation = ft.Tabs(
        selected_index=app._active_tab_index,
        expand=True,
        tabs=[ft.Tab(text=label) for label, _ in tab_definitions],
        tab_alignment=ft.TabAlignment.CENTER,
        on_change=app._handle_tab_change,
    )
    tabs_navigation.tab_text_style = text_style()
    appbar_header = ft.Container(
        margin=ft.margin.symmetric(horizontal=-16),
        content=build_app_header(app, navigation=tabs_navigation),
    )
    page.appbar = ft.AppBar(
        bgcolor=APP_BG,
        toolbar_height=350,
        center_title=False,
        elevation=2,
        leading=ft.Container(width=0),
        leading_width=0,
        title=appbar_header,
    )
    return tabs_navigation


def _ensure_assets() -> None:
    if not APP_FONT_FILE.exists():
        raise FileNotFoundError(f"Custom font file not found at {APP_FONT_FILE}")
    if not HERO_IMAGE_FILE.exists():
        raise FileNotFoundError(f"Hero image not found at {HERO_IMAGE_FILE}")


def _color_scheme() -> ft.ColorScheme:
    return ft.ColorScheme(
        primary=PRIMARY_BLACK,
        on_primary=WHITE,
        secondary=PRIMARY_BLACK,
        on_secondary=WHITE,
        surface=APP_BG,
        on_surface=PRIMARY_BLACK,
        background=APP_BG,
        on_background=PRIMARY_BLACK,
        outline=BORDER_GRAY,
    )


def _text_theme() -> ft.TextTheme:
    return ft.TextTheme(
        display_large=text_style(),
        display_medium=text_style(),
        display_small=text_style(),
        headline_large=text_style(),
        headline_medium=text_style(),
        headline_small=text_style(),
        title_large=text_style(weight=ft.FontWeight.W_600),
        title_medium=text_style(weight=ft.FontWeight.W_500),
        title_small=text_style(weight=ft.FontWeight.W_500),
        label_large=text_style(),
        label_medium=text_style(),
        label_small=text_style(),
        body_large=text_style(),
        body_medium=text_style(),
        body_small=text_style(),
    )


def _scrollbar_theme() -> ft.ScrollbarTheme:
    return ft.ScrollbarTheme(
        track_visibility=False,
        thumb_visibility=True,
        thickness=5,
        radius=20,
        main_axis_margin=4,
        cross_axis_margin=6,
        thumb_color={
            ft.ControlState.DEFAULT: SECONDARY_GRAY,
            ft.ControlState.HOVERED: PRIMARY_BLACK,
        },
    )


__all__ = ["setup_page"]
