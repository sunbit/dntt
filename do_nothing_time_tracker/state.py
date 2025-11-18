from __future__ import annotations

from .models import Entry
from .storage import EntryStorage
from datetime import date
from datetime import datetime
from datetime import time
from typing import Dict
from typing import List
from typing import Optional


class TrackerState:
    def __init__(self, storage: EntryStorage) -> None:
        self.storage = storage
        self.entries_by_month: Dict[str, List[Entry]] = storage.load_all()
        self._close_overnight_entries()

    # ------------------------------------------------------------------
    # Entry queries
    def open_entry(self) -> Optional[Entry]:
        for entries in self.entries_by_month.values():
            for entry in entries:
                if entry.is_open:
                    return entry
        return None

    def entries_for_day(self, target: date) -> List[Entry]:
        key = EntryStorage.month_key_from_date(target)
        entries = [entry for entry in self.entries_by_month.get(key, []) if entry.start.date() == target]
        return sorted(entries, key=lambda entry: entry.start)

    def entries_for_month(self, year: int, month: int) -> List[Entry]:
        key = f"{year:04d}-{month:02d}"
        return list(self.entries_by_month.get(key, []))

    def find_entry(self, entry_id: str) -> Optional[Entry]:
        for entries in self.entries_by_month.values():
            for entry in entries:
                if entry.id == entry_id:
                    return entry
        return None

    # ------------------------------------------------------------------
    # Mutations
    def clock_in(self, timestamp: Optional[datetime] = None) -> Entry:
        now = timestamp or datetime.now()
        if self.open_entry() is not None:
            raise ValueError("Cannot clock in while another entry is open.")
        entry = Entry.new(start=now)
        self._add_entry(entry)
        return entry

    def clock_out(self, timestamp: Optional[datetime] = None) -> Entry:
        open_entry = self.open_entry()
        if open_entry is None:
            raise ValueError("No open entry to close.")
        end_time = timestamp or datetime.now()
        updated = open_entry.with_updates(end=end_time)
        self._replace_entry(updated)
        return updated

    def save_entry(self, entry: Entry) -> None:
        self._replace_entry(entry)

    def delete_entry(self, entry_id: str) -> bool:
        removed = False
        for key, entries in list(self.entries_by_month.items()):
            new_entries = [entry for entry in entries if entry.id != entry_id]
            if len(new_entries) != len(entries):
                self._persist_month(key, new_entries)
                removed = True
        return removed

    # ------------------------------------------------------------------
    # Internal helpers
    def _add_entry(self, entry: Entry) -> None:
        key = EntryStorage.month_key_from_date(entry.start.date())
        bucket = self.entries_by_month.setdefault(key, [])
        bucket.append(entry)
        self._persist_month(key, bucket)

    def _replace_entry(self, entry: Entry) -> None:
        # remove existing record (if any)
        found = False
        for key, bucket in list(self.entries_by_month.items()):
            for idx, existing in enumerate(bucket):
                if existing.id == entry.id:
                    del bucket[idx]
                    self._persist_month(key, bucket)
                    found = True
                    break
            if found:
                break
        # add to appropriate month bucket
        self._add_entry(entry)

    def _sorted_month(self, entries: List[Entry]) -> List[Entry]:
        return sorted(entries, key=lambda entry: entry.start)

    def _persist_month(self, key: str, entries: List[Entry]) -> None:
        sorted_entries = self._sorted_month(entries)
        self.entries_by_month[key] = sorted_entries
        self.storage.save_month(key, sorted_entries)

    def _close_overnight_entries(self) -> None:
        today = date.today()
        for key, entries in list(self.entries_by_month.items()):
            updated = False
            for idx, entry in enumerate(entries):
                if entry.is_open and entry.start.date() < today:
                    closing_point = datetime.combine(entry.start.date(), time(hour=23, minute=59))
                    entries[idx] = entry.with_updates(end=closing_point)
                    updated = True
            if updated:
                self.entries_by_month[key] = self._sorted_month(entries)
                self.storage.save_month(key, self.entries_by_month[key])
