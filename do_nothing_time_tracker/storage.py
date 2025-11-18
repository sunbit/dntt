from __future__ import annotations

from .models import AbsenceRule
from .models import Entry
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict
from typing import Iterable
from typing import List

import json


@dataclass
class EntryStorage:
    base_dir: Path = Path("data/entries")

    def __post_init__(self) -> None:
        self.base_dir = Path(self.base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def month_key_from_date(target: date) -> str:
        return target.strftime("%Y-%m")

    @staticmethod
    def year_month_from_key(key: str) -> tuple[int, int]:
        year, month = key.split("-")
        return int(year), int(month)

    def _path_for_key(self, key: str) -> Path:
        return self.base_dir / f"{key}.json"

    def _path_for_date(self, target: date) -> Path:
        return self._path_for_key(self.month_key_from_date(target))

    def load_month(self, key: str) -> List[Entry]:
        path = self._path_for_key(key)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return [Entry.from_dict(item) for item in payload]

    def save_month(self, key: str, entries: List[Entry]) -> None:
        path = self._path_for_key(key)
        data = [entry.to_dict() for entry in entries]
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    def load_all(self) -> Dict[str, List[Entry]]:
        result: Dict[str, List[Entry]] = defaultdict(list)
        for path in sorted(self.base_dir.glob("*.json")):
            key = path.stem
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            result[key] = [Entry.from_dict(item) for item in payload]
        return result


def _to_payload(rule: AbsenceRule) -> dict:
    return {
        "start": rule.start.isoformat(),
        "end": rule.end.isoformat() if rule.end else None,
        "reason": rule.reason,
        "hours": rule.hours,
    }


def _from_payload(payload: dict) -> AbsenceRule:
    end_value = payload.get("end")
    return AbsenceRule(
        start=date.fromisoformat(payload["start"]),
        end=date.fromisoformat(end_value) if end_value else None,
        reason=payload.get("reason", ""),
        hours=payload.get("hours"),
    )


@dataclass
class AbsenceStorage:
    base_dir: Path = Path("data/absences")

    def __post_init__(self) -> None:
        self.base_dir = Path(self.base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for_year(self, year: int) -> Path:
        return self.base_dir / f"{year}.json"

    def load_year(self, year: int) -> List[AbsenceRule]:
        path = self._path_for_year(year)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return [_from_payload(item) for item in payload]

    def load_all(self) -> List[AbsenceRule]:
        rules: List[AbsenceRule] = []
        for path in sorted(self.base_dir.glob("*.json")):
            try:
                year = int(path.stem)
            except ValueError:
                continue
            rules.extend(self.load_year(year))
        rules.sort(key=lambda r: (r.start, r.end or r.start, r.reason))
        return rules

    def save_rules(self, rules: Iterable[AbsenceRule]) -> None:
        buckets: Dict[int, List[AbsenceRule]] = {}
        for rule in rules:
            buckets.setdefault(rule.start.year, []).append(rule)
        existing_years = {int(path.stem) for path in self.base_dir.glob("*.json") if path.stem.isdigit()}
        for year, year_rules in buckets.items():
            payload = [
                _to_payload(rule)
                for rule in sorted(year_rules, key=lambda r: (r.start, r.end or r.start, r.reason))
            ]
            with self._path_for_year(year).open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        for stale_year in existing_years - buckets.keys():
            stale_path = self._path_for_year(stale_year)
            if stale_path.exists():
                stale_path.unlink()


def _to_payload(rule: AbsenceRule) -> dict:
    return {
        "start": rule.start.isoformat(),
        "end": rule.end.isoformat() if rule.end else None,
        "reason": rule.reason,
        "hours": rule.hours,
    }


def _from_payload(payload: dict) -> AbsenceRule:
    end_value = payload.get("end")
    return AbsenceRule(
        start=date.fromisoformat(payload["start"]),
        end=date.fromisoformat(end_value) if end_value else None,
        reason=payload.get("reason", ""),
        hours=payload.get("hours"),
    )
