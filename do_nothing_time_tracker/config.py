from __future__ import annotations

from .models import AbsenceRule
from .models import Config
from .models import SummaryExpectedMode
from datetime import date
from pathlib import Path

import json

DEFAULT_DATA_DIR = Path("data")


class ConfigService:
    """Loads and exposes workday configuration."""

    def __init__(self, path: Path | str = "config.json") -> None:
        self.path = Path(path)

    def default_data_dir(self) -> Path:
        return self.normalize_data_dir(DEFAULT_DATA_DIR)

    def normalize_data_dir(self, value: Path | str) -> Path:
        path = Path(value).expanduser()
        return path.resolve()

    def resolve_data_dir(self, config: Config) -> Path:
        if config.data_dir:
            return self.normalize_data_dir(config.data_dir)
        return self.default_data_dir()

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

        data_dir_raw = payload.get("data_dir")
        data_dir = self.normalize_data_dir(data_dir_raw) if data_dir_raw else None

        return Config(
            hours_per_day=hours_per_day,
            workdays=list(workdays),
            absences=absences,
            summary_expected_mode=summary_mode,
            data_dir=data_dir,
        )

    def save(self, config: Config) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = serialize_config(config, default_data_dir=self.default_data_dir())
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)


def serialize_config(config: Config, *, default_data_dir: Path | None = None) -> dict:
    payload = {
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
    if config.data_dir:
        resolved_value = Path(config.data_dir).expanduser().resolve()
        default_value = default_data_dir.resolve() if default_data_dir else None
        if default_value is None or resolved_value != default_value:
            payload["data_dir"] = str(resolved_value)
    return payload
