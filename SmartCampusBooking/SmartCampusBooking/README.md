# Smart Campus Resource Booking System

**Programming 512 Assignment – Richfield Graduate Institution**

A fully functional Python desktop application that allows lecturers, campus administrators and system operators to manage shared academic resources across multiple campuses.

## Features

- **Three user roles** implemented with OOP (classes, inheritance, encapsulation):
  - **Lecturer** – register, log in, book resources, view/cancel own bookings
  - **Campus Administrator** – manage resources, view campus bookings, generate campus reports
  - **System Operator** – system-wide view, cross-campus comparison reports
- **At least three campuses** with distinct booking policies:
  - Johannesburg Main – max 2 h, 08:00–17:00
  - Cape Town Waterfront – max 4 h, 09:00–20:00
  - Durban North – max 1.5 h, 07:00–16:00
- Policies are loaded from the database and applied automatically (separated from core logic)
- **Tkinter GUI** – login, registration, campus selection, booking forms, reports, availability
- **SQLite persistence** – users, campuses, resources and bookings survive program restarts
- Overlap detection prevents double-bookings
- Input validation and clear error messages

## Requirements

- Python 3.8+
- Standard library only (tkinter, sqlite3, datetime) – no external packages needed

## How to Run

```bash
cd SmartCampusBooking
python main.py
```

On first launch the SQLite database is created automatically under `db/campus_booking.db` and seeded with sample campuses, resources and demo accounts.

## Demo Accounts

| Username    | Password  | Role                 |
|-------------|-----------|----------------------|
| lecturer1   | pass123   | Lecturer             |
| lecturer2   | pass123   | Lecturer             |
| admin_jhb   | admin123  | Campus Admin (JHB)   |
| admin_cpt   | admin123  | Campus Admin (CPT)   |
| admin_dbn   | admin123  | Campus Admin (DBN)   |
| operator    | op123     | System Operator      |

You can also register a new lecturer account from the login screen.

## Project Structure

```
SmartCampusBooking/
├── main.py              # Tkinter GUI application entry point
├── database.py          # SQLite layer (CRUD + reports)
├── models.py            # User class hierarchy (OOP)
├── booking_rules.py     # Campus-specific booking policies
├── db/                  # SQLite database (auto-created)
├── README.md
└── requirements.txt
```

## Design Notes

- **Booking rules** live in `booking_rules.py` and are driven by campus table columns, so new campuses or rule changes require only database inserts / updates.
- Resources have a unique constraint per campus; duplicate names are rejected.
- Soft-delete is used for resources so historical booking records remain intact.
- All timestamps are stored as ISO strings; overlap checks convert to minutes for accuracy.

## Author

Student submission for Programming 512 – Smart Campus Resource Booking System.
