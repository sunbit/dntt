"""View builders for the different tabs in the UI."""

from . import absences
from . import config
from . import month
from . import today
from . import week

__all__ = [
    "today",
    "week",
    "month",
    "absences",
    "config",
]
