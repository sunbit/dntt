from __future__ import annotations

from .models import AbsenceRule
from .models import Config
from .models import SummaryExpectedMode
from datetime import date
from pathlib import Path

import json


class ConfigService:
    """Loads and exposes workday configuration."""

    def __init__(self, path: Path | str = "config.json") -> None:
        self.path = Path(path)

    def load(self) -> Config:
        if not self.path.exists():
            return Config()

        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        absences = [
            AbsenceRule(
                start=date.fromisoformat(item["start"]),
                end=date.fromisoformat(item["end"]) if item.get("end") else None,
                reason=item.get("reason", ""),
                hours=item.get("hours"),
            )
            for item in payload.get("absences", payload.get("exceptions", []))
        ]

        hours_per_day = int(payload.get("hours_per_day", 8))
        workdays = payload.get("workdays") or [0, 1, 2, 3, 4]
        mode_raw = payload.get("summary_expected_mode", SummaryExpectedMode.FULL_PERIOD.value)
        try:
            summary_mode = SummaryExpectedMode(mode_raw)
        except ValueError:
            summary_mode = SummaryExpectedMode.FULL_PERIOD

        return Config(
            hours_per_day=hours_per_day,
            workdays=list(workdays),
            absences=absences,
            summary_expected_mode=summary_mode,
        )

    def save(self, config: Config) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = serialize_config(config)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)


def serialize_config(config: Config) -> dict:
    return {
        "hours_per_day": config.hours_per_day,
        "workdays": config.workdays,
        "summary_expected_mode": config.summary_expected_mode.value,
        "absences": [
            {
                "start": rule.start.isoformat(),
                "end": rule.end.isoformat() if rule.end else None,
                "reason": rule.reason,
                "hours": rule.hours,
            }
            for rule in config.absences
        ],
    }
