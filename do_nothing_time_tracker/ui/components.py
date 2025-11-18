from __future__ import annotations

from .theme import BORDER_GRAY
from .theme import PRIMARY_BLACK
from .theme import SUMMARY_HIGHLIGHT
from .theme import WHITE

import flet as ft


def summary_card(
    label: str,
    value_control: ft.Text,
    progress_control: ft.Text,
    remaining_control: ft.Text,
    *,
    highlight: bool = False,
) -> ft.Control:
    title = ft.Text(label, size=16, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER)
    value_control.size = 20
    value_control.weight = ft.FontWeight.W_600
    value_control.text_align = ft.TextAlign.CENTER
    progress_control.size = 20
    progress_control.weight = ft.FontWeight.W_600
    progress_control.text_align = ft.TextAlign.CENTER
    remaining_control.size = 14
    remaining_control.text_align = ft.TextAlign.CENTER
    bgcolor = SUMMARY_HIGHLIGHT if highlight else WHITE
    comparison_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=8,
        controls=[
            value_control,
            ft.Text("out of", size=14, color=PRIMARY_BLACK),
            progress_control,
        ],
    )
    return ft.Container(
        padding=12,
        border_radius=12,
        border=ft.border.all(1, BORDER_GRAY),
        bgcolor=bgcolor,
        col={"xs": 12, "md": 4},
        content=ft.Column(
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                title,
                comparison_row,
                remaining_control,
            ],
        ),
    )


def summary_sentence_text() -> ft.Text:
    return ft.Text(size=16, text_align=ft.TextAlign.CENTER)


def sentence_card(summary_text: ft.Text) -> ft.Control:
    return ft.Container(
        padding=16,
        border_radius=12,
        bgcolor=WHITE,
        width=520,
        content=ft.Column(
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                summary_text,
            ],
        ),
    )


def set_difference_text(control: ft.Text, diff_hours: float, *, with_suffix: bool = False) -> None:
    control.value = ""
    control.spans = difference_spans(diff_hours, with_suffix=with_suffix)


def difference_spans(diff_hours: float, *, with_suffix: bool = False) -> list[ft.TextSpan]:
    base_style = ft.TextStyle(size=14, color=PRIMARY_BLACK)
    emphasis_style = ft.TextStyle(size=20, weight=ft.FontWeight.W_600, color=PRIMARY_BLACK)
    if diff_hours > 1e-3:
        controls = [
            ft.TextSpan(format_duration(diff_hours), style=emphasis_style),
        ]
        if with_suffix:
            controls.append(ft.TextSpan(" overworked", style=base_style))
        return controls
    if diff_hours < -1e-3:
        controls = [
            ft.TextSpan(format_duration(abs(diff_hours)), style=emphasis_style),
        ]
        if with_suffix:
            controls.append(ft.TextSpan(" remaining", style=base_style))
        return controls
    return [ft.TextSpan("0h", style=emphasis_style)]


def set_summary_sentence(control: ft.Text, actual_hours: float, expected_hours: float) -> None:
    diff = actual_hours - expected_hours
    base_style = ft.TextStyle(size=14, color=PRIMARY_BLACK)
    emphasis_style = ft.TextStyle(size=20, weight=ft.FontWeight.W_600, color=PRIMARY_BLACK)
    spans: list[ft.TextSpan] = [
        ft.TextSpan("Worked ", style=base_style),
        ft.TextSpan(format_duration(actual_hours), style=emphasis_style),
        ft.TextSpan(" out of ", style=base_style),
        ft.TextSpan(format_duration(expected_hours), style=emphasis_style),
    ]
    if diff > 1e-3:
        spans.extend(
            [
                ft.TextSpan(", you overworked ", style=base_style),
                ft.TextSpan(format_duration(diff), style=emphasis_style),
            ]
        )
    elif diff < -1e-3:
        spans.extend(
            [
                ft.TextSpan(", still ", style=base_style),
                ft.TextSpan(format_duration(abs(diff)), style=emphasis_style),
                ft.TextSpan(" to go", style=base_style),
            ]
        )
    else:
        spans.append(ft.TextSpan(", perfect balance", style=base_style))
    control.value = ""
    control.spans = spans


def format_duration(hours: float) -> str:
    total_minutes = int(round(hours * 60))
    h, m = divmod(total_minutes, 60)
    parts: list[str] = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m:02d}m" if h else f"{m}m")
    if not parts:
        parts.append("0h")
    return " ".join(parts)


__all__ = [
    "difference_spans",
    "format_duration",
    "sentence_card",
    "set_difference_text",
    "set_summary_sentence",
    "summary_card",
    "summary_sentence_text",
]
