"""
booking_rules.py
Campus-specific booking policies are deliberately separated from core logic
so that new campuses or rule changes require minimal code modifications.
"""

from datetime import datetime
from typing import Tuple, Dict, Optional
import database as db


class BookingPolicy:
    """
    Encapsulates the booking constraints for a single campus.
    New campuses can be supported by simply inserting a new row in the
    campuses table; this class reads the rules at runtime.
    """

    def __init__(self, campus: Dict):
        self.campus_id = campus["campus_id"]
        self.name = campus["name"]
        self.max_duration_hours = float(campus["max_duration_hours"])
        self.open_hour = int(campus["open_hour"])
        self.close_hour = int(campus["close_hour"])
        self.description = campus.get("description", "")

    def policy_summary(self) -> str:
        """Human-readable description of the active policy."""
        return (
            f"{self.name}: max {self.max_duration_hours} h per booking, "
            f"hours {self.open_hour:02d}:00 – {self.close_hour:02d}:00"
        )

    def validate(self, booking_date: str, start_time: str,
                 duration_hours: float) -> Tuple[bool, str]:
        """
        Apply all campus rules.
        Returns (is_valid, error_message).
        """
        # 1. Duration limit
        if duration_hours <= 0:
            return False, "Duration must be greater than zero."
        if duration_hours > self.max_duration_hours:
            return False, (
                f"Maximum allowed duration at {self.name} is "
                f"{self.max_duration_hours} hours."
            )

        # 2. Time format
        try:
            start_dt = datetime.strptime(f"{booking_date} {start_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return False, "Invalid date or start-time format (use YYYY-MM-DD and HH:MM)."

        # 3. Restricted booking hours
        start_hour = start_dt.hour
        end_dt = start_dt  # will be adjusted below
        from datetime import timedelta
        end_dt = start_dt + timedelta(hours=duration_hours)
        end_hour = end_dt.hour + (1 if end_dt.minute > 0 else 0)

        if start_hour < self.open_hour:
            return False, (
                f"Bookings at {self.name} may not start before "
                f"{self.open_hour:02d}:00."
            )
        if end_hour > self.close_hour or (end_dt.hour == self.close_hour and end_dt.minute > 0):
            return False, (
                f"Bookings at {self.name} must finish by "
                f"{self.close_hour:02d}:00."
            )

        # 4. No past bookings
        if start_dt < datetime.now():
            return False, "Cannot create a booking in the past."

        return True, "OK"


def get_policy_for_campus(campus_id: int) -> Optional[BookingPolicy]:
    """Factory that loads the policy for the given campus."""
    campus = db.get_campus_by_id(campus_id)
    if campus is None:
        return None
    return BookingPolicy(campus)


def list_all_policies() -> list:
    """Return a summary of every campus policy (useful for operator reports)."""
    campuses = db.get_all_campuses()
    return [BookingPolicy(c).policy_summary() for c in campuses]
