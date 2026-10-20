"""
models.py
Object-oriented user hierarchy demonstrating inheritance and encapsulation.
"""

from typing import Optional, List, Dict
import database as db


class User:
    """Base user class with common authentication attributes (encapsulation)."""

    def __init__(self, user_id: int, username: str, full_name: str,
                 role: str, campus_id: Optional[int] = None):
        self._user_id = user_id
        self._username = username
        self._full_name = full_name
        self._role = role
        self._campus_id = campus_id

    # Encapsulated properties
    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def full_name(self) -> str:
        return self._full_name

    @property
    def role(self) -> str:
        return self._role

    @property
    def campus_id(self) -> Optional[int]:
        return self._campus_id

    def can_book(self) -> bool:
        """Override in subclasses."""
        return False

    def can_manage_resources(self) -> bool:
        return False

    def can_view_all_campuses(self) -> bool:
        return False

    def can_generate_reports(self) -> bool:
        return False

    def __str__(self):
        return f"{self._full_name} ({self._role})"


class Lecturer(User):
    """Academic staff member who books resources."""

    def __init__(self, user_id: int, username: str, full_name: str,
                 campus_id: Optional[int] = None):
        super().__init__(user_id, username, full_name, "lecturer", campus_id)

    def can_book(self) -> bool:
        return True

    def get_my_bookings(self, status: Optional[str] = None) -> List[Dict]:
        return db.get_bookings_for_user(self._user_id, status)

    def create_booking(self, resource_id: int, campus_id: int,
                       booking_date: str, start_time: str,
                       duration_hours: float):
        return db.create_booking(
            resource_id, self._user_id, campus_id,
            booking_date, start_time, duration_hours
        )

    def cancel_booking(self, booking_id: int):
        return db.cancel_booking(booking_id, self._user_id, is_admin=False)


class CampusAdministrator(User):
    """Manages resources and views bookings for a specific campus."""

    def __init__(self, user_id: int, username: str, full_name: str,
                 campus_id: int):
        super().__init__(user_id, username, full_name, "admin", campus_id)

    def can_manage_resources(self) -> bool:
        return True

    def can_generate_reports(self) -> bool:
        return True  # campus-level only

    def get_campus_bookings(self, status: Optional[str] = None) -> List[Dict]:
        if self._campus_id is None:
            return []
        return db.get_bookings_for_campus(self._campus_id, status)

    def add_resource(self, name: str, resource_type: str,
                     capacity: int = 1, description: str = ""):
        if self._campus_id is None:
            return False, "No campus assigned."
        return db.add_resource(self._campus_id, name, resource_type, capacity, description)

    def update_resource(self, resource_id: int, name: str, resource_type: str,
                        capacity: int, description: str, is_active: int = 1):
        return db.update_resource(resource_id, name, resource_type, capacity, description, is_active)

    def remove_resource(self, resource_id: int):
        return db.delete_resource(resource_id)

    def campus_report(self) -> Dict:
        if self._campus_id is None:
            return {}
        return db.campus_report(self._campus_id)


class SystemOperator(User):
    """Institutional management with system-wide access."""

    def __init__(self, user_id: int, username: str, full_name: str):
        super().__init__(user_id, username, full_name, "operator", None)

    def can_view_all_campuses(self) -> bool:
        return True

    def can_generate_reports(self) -> bool:
        return True

    def can_manage_resources(self) -> bool:
        # Operator can view but primary management is by campus admins
        return False

    def get_all_bookings(self, status: Optional[str] = None) -> List[Dict]:
        return db.get_all_bookings(status)

    def cross_campus_report(self) -> List[Dict]:
        return db.cross_campus_report()


def create_user_from_dict(data: Dict) -> User:
    """Factory that returns the correct subclass based on role."""
    role = data["role"]
    if role == "lecturer":
        return Lecturer(
            data["user_id"], data["username"], data["full_name"],
            data.get("campus_id")
        )
    elif role == "admin":
        return CampusAdministrator(
            data["user_id"], data["username"], data["full_name"],
            data.get("campus_id")
        )
    elif role == "operator":
        return SystemOperator(
            data["user_id"], data["username"], data["full_name"]
        )
    else:
        return User(
            data["user_id"], data["username"], data["full_name"],
            role, data.get("campus_id")
        )
