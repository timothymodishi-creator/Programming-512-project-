"""
database.py
SQLite persistence layer for the Smart Campus Resource Booking System.
Handles users, campuses, resources and bookings.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "campus_booking.db")


def get_connection():
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialise_database():
    """Create all required tables and seed initial data if the DB is empty."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            full_name   TEXT NOT NULL,
            role        TEXT NOT NULL CHECK(role IN ('lecturer', 'admin', 'operator')),
            campus_id   INTEGER,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campus_id) REFERENCES campuses(campus_id)
        )
    """)

    # Campuses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campuses (
            campus_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT UNIQUE NOT NULL,
            location    TEXT,
            max_duration_hours REAL NOT NULL DEFAULT 2.0,
            open_hour   INTEGER NOT NULL DEFAULT 8,
            close_hour  INTEGER NOT NULL DEFAULT 18,
            description TEXT
        )
    """)

    # Resources table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
            campus_id   INTEGER NOT NULL,
            name        TEXT NOT NULL,
            resource_type TEXT,
            capacity    INTEGER DEFAULT 1,
            description TEXT,
            is_active   INTEGER DEFAULT 1,
            UNIQUE(campus_id, name),
            FOREIGN KEY (campus_id) REFERENCES campuses(campus_id)
        )
    """)

    # Bookings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            campus_id   INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            start_time  TEXT NOT NULL,
            duration_hours REAL NOT NULL,
            end_time    TEXT NOT NULL,
            status      TEXT DEFAULT 'active' CHECK(status IN ('active', 'cancelled', 'completed')),
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resource_id) REFERENCES resources(resource_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (campus_id) REFERENCES campuses(campus_id)
        )
    """)

    conn.commit()

    # Seed data only if campuses table is empty
    cursor.execute("SELECT COUNT(*) FROM campuses")
    if cursor.fetchone()[0] == 0:
        _seed_data(cursor)
        conn.commit()

    conn.close()


def _seed_data(cursor):
    """Insert three campuses with different booking policies and sample data."""
    campuses = [
        # Campus 1: Johannesburg – short sessions, standard hours
        ("Johannesburg Main", "Johannesburg, Gauteng", 2.0, 8, 17,
         "Main campus – max 2 hours per booking, 08:00-17:00"),
        # Campus 2: Cape Town – longer sessions, later close
        ("Cape Town Waterfront", "Cape Town, Western Cape", 4.0, 9, 20,
         "Waterfront campus – max 4 hours, 09:00-20:00"),
        # Campus 3: Durban – very short, early close (priority on labs)
        ("Durban North", "Durban, KwaZulu-Natal", 1.5, 7, 16,
         "North campus – max 1.5 hours, 07:00-16:00"),
    ]
    cursor.executemany("""
        INSERT INTO campuses (name, location, max_duration_hours, open_hour, close_hour, description)
        VALUES (?, ?, ?, ?, ?, ?)
    """, campuses)

    # Sample resources per campus
    resources = [
        # Johannesburg (campus_id=1)
        (1, "Computer Lab A", "Lab", 30, "30-seat computer laboratory"),
        (1, "Computer Lab B", "Lab", 25, "25-seat computer laboratory"),
        (1, "Seminar Room 1", "Room", 20, "Seminar / tutorial room"),
        (1, "Multimedia Projector 1", "Equipment", 1, "Portable projector"),
        (1, "Presentation Suite", "Room", 40, "Large presentation venue"),
        # Cape Town (campus_id=2)
        (2, "Computer Lab C", "Lab", 35, "35-seat lab with dual monitors"),
        (2, "Lecture Theatre", "Room", 80, "Main lecture theatre"),
        (2, "Multimedia Projector 2", "Equipment", 1, "4K projector"),
        (2, "Meeting Room Blue", "Room", 12, "Small meeting room"),
        (2, "Innovation Hub", "Room", 25, "Collaborative workspace"),
        # Durban (campus_id=3)
        (3, "Computer Lab D", "Lab", 20, "20-seat programming lab"),
        (3, "Seminar Room 2", "Room", 15, "Small seminar room"),
        (3, "Portable Projector", "Equipment", 1, "Lightweight projector"),
        (3, "Boardroom", "Room", 10, "Executive boardroom"),
        (3, "Media Studio", "Room", 8, "Recording / media studio"),
    ]
    cursor.executemany("""
        INSERT INTO resources (campus_id, name, resource_type, capacity, description)
        VALUES (?, ?, ?, ?, ?)
    """, resources)

    # Default accounts (password is plain text for assignment simplicity)
    # In production one would hash passwords.
    users = [
        ("lecturer1", "pass123", "Dr. Thandi Nkosi", "lecturer", 1),
        ("lecturer2", "pass123", "Mr. Johan van der Berg", "lecturer", 2),
        ("admin_jhb", "admin123", "Admin Johannesburg", "admin", 1),
        ("admin_cpt", "admin123", "Admin Cape Town", "admin", 2),
        ("admin_dbn", "admin123", "Admin Durban", "admin", 3),
        ("operator", "op123", "System Operator", "operator", None),
    ]
    cursor.executemany("""
        INSERT INTO users (username, password, full_name, role, campus_id)
        VALUES (?, ?, ?, ?, ?)
    """, users)


# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Return user dict if credentials are valid, else None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, password)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def register_user(username: str, password: str, full_name: str,
                  role: str = "lecturer", campus_id: Optional[int] = None) -> Tuple[bool, str]:
    """Register a new user. Returns (success, message)."""
    if role not in ("lecturer", "admin", "operator"):
        return False, "Invalid role."
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, full_name, role, campus_id) VALUES (?, ?, ?, ?, ?)",
            (username, password, full_name, role, campus_id)
        )
        conn.commit()
        return True, "Registration successful."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Campus operations
# ---------------------------------------------------------------------------

def get_all_campuses() -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campuses ORDER BY name")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_campus_by_id(campus_id: int) -> Optional[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campuses WHERE campus_id = ?", (campus_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Resource operations
# ---------------------------------------------------------------------------

def get_resources_by_campus(campus_id: int, active_only: bool = True) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    if active_only:
        cursor.execute(
            "SELECT * FROM resources WHERE campus_id = ? AND is_active = 1 ORDER BY name",
            (campus_id,)
        )
    else:
        cursor.execute(
            "SELECT * FROM resources WHERE campus_id = ? ORDER BY name",
            (campus_id,)
        )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def add_resource(campus_id: int, name: str, resource_type: str,
                 capacity: int = 1, description: str = "") -> Tuple[bool, str]:
    """Add a resource. Detects duplicate name within the same campus."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO resources (campus_id, name, resource_type, capacity, description)
               VALUES (?, ?, ?, ?, ?)""",
            (campus_id, name.strip(), resource_type, capacity, description)
        )
        conn.commit()
        return True, "Resource added successfully."
    except sqlite3.IntegrityError:
        return False, "A resource with this name already exists at the campus."
    finally:
        conn.close()


def update_resource(resource_id: int, name: str, resource_type: str,
                    capacity: int, description: str, is_active: int = 1) -> Tuple[bool, str]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """UPDATE resources
               SET name = ?, resource_type = ?, capacity = ?, description = ?, is_active = ?
               WHERE resource_id = ?""",
            (name.strip(), resource_type, capacity, description, is_active, resource_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Resource not found."
        return True, "Resource updated."
    except sqlite3.IntegrityError:
        return False, "Duplicate resource name at this campus."
    finally:
        conn.close()


def delete_resource(resource_id: int) -> Tuple[bool, str]:
    """Soft-delete (deactivate) a resource so historical bookings remain intact."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE resources SET is_active = 0 WHERE resource_id = ?",
        (resource_id,)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    if affected:
        return True, "Resource deactivated."
    return False, "Resource not found."


def get_resource_by_id(resource_id: int) -> Optional[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM resources WHERE resource_id = ?", (resource_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Booking operations
# ---------------------------------------------------------------------------

def _times_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    """Return True if two time intervals (HH:MM strings) overlap."""
    def to_minutes(t):
        h, m = map(int, t.split(":"))
        return h * 60 + m
    s1, e1 = to_minutes(start1), to_minutes(end1)
    s2, e2 = to_minutes(start2), to_minutes(end2)
    return s1 < e2 and s2 < e1


def check_overlap(resource_id: int, booking_date: str,
                  start_time: str, end_time: str,
                  exclude_booking_id: Optional[int] = None) -> bool:
    """Return True if an overlapping active booking already exists."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT start_time, end_time FROM bookings
        WHERE resource_id = ? AND booking_date = ? AND status = 'active'
    """
    params = [resource_id, booking_date]
    if exclude_booking_id:
        query += " AND booking_id != ?"
        params.append(exclude_booking_id)
    cursor.execute(query, params)
    for row in cursor.fetchall():
        if _times_overlap(start_time, end_time, row["start_time"], row["end_time"]):
            conn.close()
            return True
    conn.close()
    return False


def create_booking(resource_id: int, user_id: int, campus_id: int,
                   booking_date: str, start_time: str,
                   duration_hours: float) -> Tuple[bool, str]:
    """Create a booking after validating rules and overlaps."""
    # Calculate end time
    try:
        start_dt = datetime.strptime(f"{booking_date} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(hours=duration_hours)
        end_time = end_dt.strftime("%H:%M")
    except ValueError:
        return False, "Invalid date or time format."

    # Overlap check
    if check_overlap(resource_id, booking_date, start_time, end_time):
        return False, "This resource is already booked for the selected time slot."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO bookings
           (resource_id, user_id, campus_id, booking_date, start_time,
            duration_hours, end_time, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
        (resource_id, user_id, campus_id, booking_date, start_time,
         duration_hours, end_time)
    )
    conn.commit()
    conn.close()
    return True, "Booking created successfully."


def cancel_booking(booking_id: int, user_id: int, is_admin: bool = False) -> Tuple[bool, str]:
    """Cancel a future booking. Lecturers can only cancel their own."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,))
    booking = cursor.fetchone()
    if not booking:
        conn.close()
        return False, "Booking not found."
    if booking["status"] != "active":
        conn.close()
        return False, "Booking is not active."
    if not is_admin and booking["user_id"] != user_id:
        conn.close()
        return False, "You can only cancel your own bookings."

    # Only allow cancellation of future bookings
    try:
        booking_dt = datetime.strptime(
            f"{booking['booking_date']} {booking['start_time']}", "%Y-%m-%d %H:%M"
        )
        if booking_dt < datetime.now():
            conn.close()
            return False, "Cannot cancel past or ongoing bookings."
    except ValueError:
        pass

    cursor.execute(
        "UPDATE bookings SET status = 'cancelled' WHERE booking_id = ?",
        (booking_id,)
    )
    conn.commit()
    conn.close()
    return True, "Booking cancelled."


def get_bookings_for_user(user_id: int, status: Optional[str] = None) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT b.*, r.name AS resource_name, c.name AS campus_name, u.full_name
        FROM bookings b
        JOIN resources r ON b.resource_id = r.resource_id
        JOIN campuses c ON b.campus_id = c.campus_id
        JOIN users u ON b.user_id = u.user_id
        WHERE b.user_id = ?
    """
    params = [user_id]
    if status:
        query += " AND b.status = ?"
        params.append(status)
    query += " ORDER BY b.booking_date DESC, b.start_time DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_bookings_for_campus(campus_id: int, status: Optional[str] = None) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT b.*, r.name AS resource_name, c.name AS campus_name, u.full_name
        FROM bookings b
        JOIN resources r ON b.resource_id = r.resource_id
        JOIN campuses c ON b.campus_id = c.campus_id
        JOIN users u ON b.user_id = u.user_id
        WHERE b.campus_id = ?
    """
    params = [campus_id]
    if status:
        query += " AND b.status = ?"
        params.append(status)
    query += " ORDER BY b.booking_date DESC, b.start_time DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_all_bookings(status: Optional[str] = None) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT b.*, r.name AS resource_name, c.name AS campus_name, u.full_name
        FROM bookings b
        JOIN resources r ON b.resource_id = r.resource_id
        JOIN campuses c ON b.campus_id = c.campus_id
        JOIN users u ON b.user_id = u.user_id
    """
    params = []
    if status:
        query += " WHERE b.status = ?"
        params.append(status)
    query += " ORDER BY b.booking_date DESC, b.start_time DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_active_bookings_for_resource_on_date(resource_id: int, booking_date: str) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM bookings
           WHERE resource_id = ? AND booking_date = ? AND status = 'active'
           ORDER BY start_time""",
        (resource_id, booking_date)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def campus_report(campus_id: int) -> Dict:
    """Generate campus-level statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    # Total bookings (all statuses)
    cursor.execute(
        "SELECT COUNT(*) FROM bookings WHERE campus_id = ?", (campus_id,)
    )
    total = cursor.fetchone()[0]

    # Active bookings
    cursor.execute(
        "SELECT COUNT(*) FROM bookings WHERE campus_id = ? AND status = 'active'",
        (campus_id,)
    )
    active = cursor.fetchone()[0]

    # Most frequently used resources
    cursor.execute("""
        SELECT r.name, COUNT(*) AS cnt
        FROM bookings b
        JOIN resources r ON b.resource_id = r.resource_id
        WHERE b.campus_id = ? AND b.status != 'cancelled'
        GROUP BY r.resource_id
        ORDER BY cnt DESC
        LIMIT 5
    """, (campus_id,))
    top_resources = [{"name": r[0], "count": r[1]} for r in cursor.fetchall()]

    # Average duration
    cursor.execute("""
        SELECT AVG(duration_hours) FROM bookings
        WHERE campus_id = ? AND status != 'cancelled'
    """, (campus_id,))
    avg_dur = cursor.fetchone()[0] or 0.0

    conn.close()
    return {
        "total_bookings": total,
        "active_bookings": active,
        "top_resources": top_resources,
        "average_duration": round(avg_dur, 2),
    }


def cross_campus_report() -> List[Dict]:
    """Comparative report across all campuses."""
    campuses = get_all_campuses()
    results = []
    for c in campuses:
        rep = campus_report(c["campus_id"])
        rep["campus_id"] = c["campus_id"]
        rep["campus_name"] = c["name"]
        rep["max_duration"] = c["max_duration_hours"]
        rep["open_hour"] = c["open_hour"]
        rep["close_hour"] = c["close_hour"]
        results.append(rep)
    return results
