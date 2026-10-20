"""
main.py
Smart Campus Resource Booking System – Tkinter GUI entry point.
Richfield Graduate Institution – Programming 512 Assignment
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
import database as db
from models import create_user_from_dict, Lecturer, CampusAdministrator, SystemOperator
from booking_rules import get_policy_for_campus, list_all_policies


# ---------------------------------------------------------------------------
# Colour / style helpers
# ---------------------------------------------------------------------------
PRIMARY = "#1a365d"
ACCENT = "#2b6cb0"
BG = "#edf2f7"
CARD = "#ffffff"
SUCCESS = "#276749"
DANGER = "#c53030"
WARNING = "#c05600"


class SmartCampusApp(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("Smart Campus Resource Booking System – Richfield")
        self.geometry("980x680")
        self.minsize(860, 580)
        self.configure(bg=BG)

        # Current session state
        self.current_user = None
        self.active_campus_id = None
        self.active_campus_name = ""

        # Initialise database (creates tables + seed data on first run)
        db.initialise_database()

        # Style
        self._setup_styles()

        # Container for switching frames
        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)

        self.show_login()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("Accent.TButton", background=ACCENT, foreground="white")
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=26)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("TLabel", background=BG, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=PRIMARY)
        style.configure("SubHeader.TLabel", font=("Segoe UI", 12, "bold"), foreground=PRIMARY)

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # ------------------------------------------------------------------
    # LOGIN / REGISTER
    # ------------------------------------------------------------------
    def show_login(self):
        self.clear_container()
        self.current_user = None
        self.active_campus_id = None

        frame = tk.Frame(self.container, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="Smart Campus Resource Booking",
                 font=("Segoe UI", 20, "bold"), fg=PRIMARY, bg=BG).pack(pady=(0, 4))
        tk.Label(frame, text="Richfield Graduate Institution",
                 font=("Segoe UI", 11), fg="#4a5568", bg=BG).pack(pady=(0, 20))

        card = tk.Frame(frame, bg=CARD, padx=30, pady=25,
                        highlightbackground="#cbd5e0", highlightthickness=1)
        card.pack()

        tk.Label(card, text="Username", bg=CARD, anchor="w").pack(fill="x")
        self.login_user = tk.Entry(card, font=("Segoe UI", 11), width=28)
        self.login_user.pack(pady=(2, 10))

        tk.Label(card, text="Password", bg=CARD, anchor="w").pack(fill="x")
        self.login_pass = tk.Entry(card, font=("Segoe UI", 11), width=28, show="*")
        self.login_pass.pack(pady=(2, 15))

        btn_row = tk.Frame(card, bg=CARD)
        btn_row.pack()
        ttk.Button(btn_row, text="Login", command=self._do_login, width=12).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Register Lecturer", command=self.show_register, width=16).pack(side="left", padx=4)

        # Demo credentials hint
        hint = tk.Label(frame, text=(
            "Demo accounts:\n"
            "lecturer1 / pass123   |   admin_jhb / admin123   |   operator / op123"
        ), font=("Segoe UI", 9), fg="#718096", bg=BG, justify="left")
        hint.pack(pady=15)

        self.login_user.focus()
        self.bind("<Return>", lambda e: self._do_login())

    def _do_login(self):
        username = self.login_user.get().strip()
        password = self.login_pass.get()
        if not username or not password:
            messagebox.showwarning("Input required", "Please enter username and password.")
            return
        data = db.authenticate_user(username, password)
        if data is None:
            messagebox.showerror("Login failed", "Invalid username or password.")
            return
        self.current_user = create_user_from_dict(data)
        self.unbind("<Return>")
        self.show_campus_selection()

    def show_register(self):
        self.clear_container()
        frame = tk.Frame(self.container, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="Register as Lecturer",
                 font=("Segoe UI", 16, "bold"), fg=PRIMARY, bg=BG).pack(pady=(0, 15))

        card = tk.Frame(frame, bg=CARD, padx=30, pady=20,
                        highlightbackground="#cbd5e0", highlightthickness=1)
        card.pack()

        fields = {}
        for label, key in [("Full Name", "name"), ("Username", "user"),
                           ("Password", "pass"), ("Confirm Password", "confirm")]:
            tk.Label(card, text=label, bg=CARD, anchor="w").pack(fill="x")
            show = "*" if "pass" in key.lower() or key == "confirm" else ""
            e = tk.Entry(card, font=("Segoe UI", 11), width=28, show=show)
            e.pack(pady=(2, 8))
            fields[key] = e

        def submit():
            name = fields["name"].get().strip()
            user = fields["user"].get().strip()
            pw = fields["pass"].get()
            conf = fields["confirm"].get()
            if not all([name, user, pw]):
                messagebox.showwarning("Missing data", "All fields are required.")
                return
            if pw != conf:
                messagebox.showerror("Mismatch", "Passwords do not match.")
                return
            ok, msg = db.register_user(user, pw, name, role="lecturer")
            if ok:
                messagebox.showinfo("Success", msg)
                self.show_login()
            else:
                messagebox.showerror("Error", msg)

        btn_row = tk.Frame(card, bg=CARD)
        btn_row.pack(pady=8)
        ttk.Button(btn_row, text="Register", command=submit, width=12).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Back", command=self.show_login, width=10).pack(side="left", padx=4)

    # ------------------------------------------------------------------
    # CAMPUS SELECTION
    # ------------------------------------------------------------------
    def show_campus_selection(self):
        self.clear_container()
        frame = tk.Frame(self.container, bg=BG, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text=f"Welcome, {self.current_user.full_name}",
                 font=("Segoe UI", 16, "bold"), fg=PRIMARY, bg=BG).pack(anchor="w")
        tk.Label(frame, text=f"Role: {self.current_user.role.title()}",
                 font=("Segoe UI", 11), fg="#4a5568", bg=BG).pack(anchor="w", pady=(0, 15))

        tk.Label(frame, text="Select a campus to work with:",
                 font=("Segoe UI", 12, "bold"), fg=PRIMARY, bg=BG).pack(anchor="w")

        campuses = db.get_all_campuses()
        # Operator can work with any campus; admin is restricted
        if isinstance(self.current_user, CampusAdministrator) and self.current_user.campus_id:
            campuses = [c for c in campuses if c["campus_id"] == self.current_user.campus_id]

        list_frame = tk.Frame(frame, bg=BG)
        list_frame.pack(fill="both", expand=True, pady=10)

        for c in campuses:
            policy = get_policy_for_campus(c["campus_id"])
            summary = policy.policy_summary() if policy else ""
            card = tk.Frame(list_frame, bg=CARD, padx=15, pady=12,
                            highlightbackground="#cbd5e0", highlightthickness=1)
            card.pack(fill="x", pady=5)

            tk.Label(card, text=c["name"], font=("Segoe UI", 12, "bold"),
                     fg=PRIMARY, bg=CARD).pack(anchor="w")
            tk.Label(card, text=c.get("location", ""), font=("Segoe UI", 9),
                     fg="#718096", bg=CARD).pack(anchor="w")
            tk.Label(card, text=summary, font=("Segoe UI", 9),
                     fg=WARNING, bg=CARD).pack(anchor="w", pady=(4, 0))

            def make_cmd(cid, cname):
                return lambda: self._select_campus(cid, cname)

            ttk.Button(card, text="Select Campus",
                       command=make_cmd(c["campus_id"], c["name"])).pack(anchor="e", pady=(6, 0))

        ttk.Button(frame, text="Logout", command=self.show_login).pack(anchor="w", pady=10)

    def _select_campus(self, campus_id, campus_name):
        self.active_campus_id = campus_id
        self.active_campus_name = campus_name
        self.show_dashboard()

    # ------------------------------------------------------------------
    # DASHBOARD (role-aware)
    # ------------------------------------------------------------------
    def show_dashboard(self):
        self.clear_container()
        top = tk.Frame(self.container, bg=PRIMARY, padx=15, pady=10)
        top.pack(fill="x")

        tk.Label(top, text="Smart Campus Booking", font=("Segoe UI", 14, "bold"),
                 fg="white", bg=PRIMARY).pack(side="left")
        tk.Label(top, text=f"  |  {self.active_campus_name}",
                 font=("Segoe UI", 11), fg="#bee3f8", bg=PRIMARY).pack(side="left")

        right = tk.Frame(top, bg=PRIMARY)
        right.pack(side="right")
        tk.Label(right, text=f"{self.current_user.full_name} ({self.current_user.role})",
                 font=("Segoe UI", 10), fg="white", bg=PRIMARY).pack(side="left", padx=8)
        ttk.Button(right, text="Change Campus", command=self.show_campus_selection).pack(side="left", padx=4)
        ttk.Button(right, text="Logout", command=self.show_login).pack(side="left", padx=4)

        # Policy banner
        policy = get_policy_for_campus(self.active_campus_id)
        if policy:
            banner = tk.Frame(self.container, bg="#fefcbf", padx=12, pady=6)
            banner.pack(fill="x")
            tk.Label(banner, text=f"Active booking policy: {policy.policy_summary()}",
                     font=("Segoe UI", 9, "bold"), fg=WARNING, bg="#fefcbf").pack(anchor="w")

        # Navigation + content
        nav = tk.Frame(self.container, bg="#e2e8f0", padx=8, pady=8)
        nav.pack(fill="x")

        self.content = tk.Frame(self.container, bg=BG, padx=15, pady=10)
        self.content.pack(fill="both", expand=True)

        # Role-specific buttons
        buttons = []
        if isinstance(self.current_user, Lecturer):
            buttons = [
                ("Book Resource", self.ui_book_resource),
                ("My Bookings", self.ui_my_bookings),
                ("Resource Availability", self.ui_availability),
            ]
        elif isinstance(self.current_user, CampusAdministrator):
            buttons = [
                ("Manage Resources", self.ui_manage_resources),
                ("Campus Bookings", self.ui_campus_bookings),
                ("Campus Report", self.ui_campus_report),
                ("Resource Availability", self.ui_availability),
            ]
        elif isinstance(self.current_user, SystemOperator):
            buttons = [
                ("All Bookings", self.ui_all_bookings),
                ("Cross-Campus Report", self.ui_cross_report),
                ("Resource Availability", self.ui_availability),
                ("View Policies", self.ui_view_policies),
            ]

        for text, cmd in buttons:
            ttk.Button(nav, text=text, command=cmd).pack(side="left", padx=4)

        # Default view
        if buttons:
            buttons[0][1]()

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    # ------------------------------------------------------------------
    # LECTURER: Book Resource
    # ------------------------------------------------------------------
    def ui_book_resource(self):
        self._clear_content()
        tk.Label(self.content, text="Create a New Booking",
                 font=("Segoe UI", 14, "bold"), fg=PRIMARY, bg=BG).pack(anchor="w", pady=(0, 10))

        resources = db.get_resources_by_campus(self.active_campus_id)
        if not resources:
            tk.Label(self.content, text="No resources available at this campus.",
                     bg=BG, fg=DANGER).pack(anchor="w")
            return

        form = tk.Frame(self.content, bg=BG)
        form.pack(anchor="w")

        # Resource
        tk.Label(form, text="Resource:", bg=BG).grid(row=0, column=0, sticky="w", pady=4)
        res_var = tk.StringVar()
        res_names = {f"{r['name']} ({r['resource_type']})": r["resource_id"] for r in resources}
        res_combo = ttk.Combobox(form, textvariable=res_var, values=list(res_names.keys()),
                                 state="readonly", width=40)
        res_combo.grid(row=0, column=1, pady=4, padx=8)
        if res_names:
            res_combo.current(0)

        # Date
        tk.Label(form, text="Date (YYYY-MM-DD):", bg=BG).grid(row=1, column=0, sticky="w", pady=4)
        date_entry = tk.Entry(form, width=20)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.grid(row=1, column=1, sticky="w", pady=4, padx=8)

        # Start time
        tk.Label(form, text="Start time (HH:MM):", bg=BG).grid(row=2, column=0, sticky="w", pady=4)
        time_entry = tk.Entry(form, width=20)
        time_entry.insert(0, "09:00")
        time_entry.grid(row=2, column=1, sticky="w", pady=4, padx=8)

        # Duration
        policy = get_policy_for_campus(self.active_campus_id)
        max_dur = policy.max_duration_hours if policy else 2.0
        tk.Label(form, text=f"Duration (hours, max {max_dur}):", bg=BG).grid(row=3, column=0, sticky="w", pady=4)
        dur_entry = tk.Entry(form, width=20)
        dur_entry.insert(0, "1.0")
        dur_entry.grid(row=3, column=1, sticky="w", pady=4, padx=8)

        def submit():
            key = res_var.get()
            if not key:
                messagebox.showwarning("Select resource", "Please choose a resource.")
                return
            rid = res_names[key]
            date_str = date_entry.get().strip()
            time_str = time_entry.get().strip()
            try:
                duration = float(dur_entry.get().strip())
            except ValueError:
                messagebox.showerror("Invalid duration", "Duration must be a number.")
                return

            # Apply campus policy
            if policy:
                ok, msg = policy.validate(date_str, time_str, duration)
                if not ok:
                    messagebox.showerror("Policy violation", msg)
                    return

            ok, msg = self.current_user.create_booking(
                rid, self.active_campus_id, date_str, time_str, duration
            )
            if ok:
                messagebox.showinfo("Success", msg)
                self.ui_my_bookings()
            else:
                messagebox.showerror("Booking failed", msg)

        ttk.Button(form, text="Create Booking", command=submit).grid(row=4, column=1, sticky="w", pady=12, padx=8)

    # ------------------------------------------------------------------
    # LECTURER: My Bookings
    # ------------------------------------------------------------------
    def ui_my_bookings(self):
        self._clear_content()
        tk.Label(self.content, text="My Bookings",
                 font=("Segoe UI", 14, "bold"), fg=PRIMARY, bg=BG).pack(anchor="w", pady=(0, 8))

        filter_frame = tk.Frame(self.content, bg=BG)
        filter_frame.pack(anchor="w", pady=4)
        status_var = tk.StringVar(value="all")
        for val, label in [("all", "All"), ("active", "Active"), ("cancelled", "Cancelled")]:
            ttk.Radiobutton(filter_frame, text=label, variable=status_var, value=val,
                            command=lambda: self._refresh_my_bookings(tree, status_var.get())
                            ).pack(side="left", padx=6)

        cols = ("ID", "Resource", "Campus", "Date", "Start", "End", "Duration", "Status")
        tree = ttk.Treeview(self.content, columns=cols, show="headings", height=14)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=100, anchor="center")
        tree.column("Resource", width=160)
        tree.column("Campus", width=140)
        tree.pack(fill="both", expand=True, pady=6)

        def cancel_selected():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a booking to cancel.")
                return
            bid = int(tree.item(sel[0])["values"][0])
            if messagebox.askyesno("Confirm", "Cancel this booking?"):
                ok, msg = self.current_user.cancel_booking(bid)
                if ok:
                    messagebox.showinfo("Done", msg)
                    self._refresh_my_bookings(tree, status_var.get())
                else:
                    messagebox.showerror("Error", msg)

        ttk.Button(self.content, text="Cancel Selected Booking", command=cancel_selected).pack(anchor="w", pady=4)
        self._refresh_my_bookings(tree, "all")

    def _refresh_my_bookings(self, tree, status):
        tree.delete(*tree.get_children())
        st = None if status == "all" else status
        bookings = self.current_user.get_my_bookings(st)
        for b in bookings:
            tree.insert("", "end", values=(
                b["booking_id"], b["resource_name"], b["campus_name"],
                b["booking_date"], b["start_time"], b["end_time"],
                b["duration_hours"], b["status"]
            ))

    # ------------------------------------------------------------------
    # SHARED: Resource Availability
    # ------------------------------------------------------------------
    def ui_availability(self):
        self._clear_content()
        tk.Label(self.content, text="Resource Availability",
                 font=("Segoe UI", 14, "bold"), fg=PRIMARY, bg=BG).pack(anchor="w", pady=(0, 8))

        top = tk.Frame(self.content, bg=BG)
        top.pack(anchor="w", pady=4)
        tk.Label(top, text="Date (YYYY-MM-DD):", bg=BG).pack(side="left")
        date_entry = tk.Entry(top, width=14)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.pack(side="left", padx=6)

        resources = db.get_resources_by_campus(self.active_campus_id)
        res_frame = tk.Frame(self.content, bg=BG)
        res_frame.pack(fill="both", expand=True, pady=8)

        def refresh():
            for w in res_frame.winfo_children():
                w.destroy()
            date_str = date_entry.get().strip()
            for r in resources:
                card = tk.Frame(res_frame, bg=CARD, padx=12, pady=8,
                                highlightbackground="#cbd5e0", highlightthickness=1)
                card.pack(fill="x", pady=3)
                tk.Label(card, text=f"{r['name']}  ({r['resource_type']})",
                         font=("Segoe UI", 11, "bold"), fg=PRIMARY, bg=CARD).pack(anchor="w")
                bookings = db.get_active_bookings_for_resource_on_date(r["resource_id"], date_str)
                if not bookings:
                    tk.Label(card, text="Fully available", fg=SUCCESS, bg=CARD).pack(anchor="w")
                else:
                    slots = ", ".join(f"{b['start_time']}-{b['end_time']}" for b in bookings)
                    tk.Label(card, text=f"Booked: {slots}", fg=DANGER, bg=CARD).pack(anchor="w")

        ttk.Button(top, text="Check", command=refresh).pack(side="left", padx=4)
        refresh()

    # ------------------------------------------------------------------
    # ADMIN: Manage Resources
    # ------------------------------------------------------------------
    def ui_manage_resources(self):
        self._clear_content()
        tk.Label(self.content, text="Manage Campus Resources",
                 font=("Segoe UI", 14, "bold"), fg=PRIMARY, bg=BG).pack(anchor="w", pady=(0, 8))

        cols = ("ID", "Name", "Type", "Capacity", "Active", "Description")
        tree = ttk.Treeview(self.content, columns=cols, show="headings", height=12)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=90, anchor="center")
        tree.column("Name", width=160)
        tree.column("Description", width=220)
        tree.pack(fill="both", expand=True)

        def load():
            tree.delete(*tree.get_children())
            for r in db.get_resources_by_campus(self.active_campus_id, active_only=False):
                tree.insert("", "end", values=(
                    r["resource_id"], r["name"], r["resource_type"],
                    r["capacity"], "Yes" if r["is_active"] else "No",
                    r.get("description", "")
                ))

        btn_row = tk.Frame(self.content, bg=BG)
        btn_row.pack(anchor="w", pady=8)

        def add_res():
            dlg = ResourceDialog(self, "Add Resource")
            self.wait_window(dlg)
            if dlg.result:
                name, rtype, cap, desc = dlg.result
                ok, msg = self.current_user.add_resource(name, rtype, cap, desc)
                messagebox.showinfo("Result", msg) if ok else messagebox.showerror("Error", msg)
                load()

        def edit_res():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a resource first.")
                return
            vals = tree.item(sel[0])["values"]
            rid = int(vals[0])
            dlg = ResourceDialog(self, "Edit Resource",
                                 initial=(vals[1], vals[2], vals[3], vals[5]))
            self.wait_window(dlg)
            if dlg.result:
                name, rtype, cap, desc = dlg.result
                ok, msg = self.current_user.update_resource(rid, name, rtype, int(cap), desc)
                messagebox.showinfo("Result", msg) if ok else messagebox.showerror("Error", msg)
                load()

        def remove_res():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a resource first.")
                return
            rid = int(tree.item(sel[0])["values"][0])
            if messagebox.askyesno("Confirm", "Deactivate this resource?"):
                ok, msg = self.current_user.remove_resource(rid)
                messagebox.showinfo("Result", msg)
                load()

        ttk.Button(btn_row, text="Add Resource", command=add_res).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Edit Selected", command=edit_res).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Deactivate Selected", command=remove_res).pack(side="left", padx=4)
        load()

    # ------------------------------------------------------------------
    # ADMIN: Campus Bookings
    # ------------------------------------------------------------------
    def ui_campus_bookings(self):
        self._clear_content()
        tk.Label(self.content, text="Campus Bookings",
                 font=("Segoe UI", 14, "bold"), fg=PRIMARY, bg=BG).pack(anchor="w", pady=(0, 8))

        cols = ("ID", "Lecturer", "Resource", "Date", "Start", "End", "Duration", "Status")
        tree = ttk.Treeview(self.content, columns=cols, show="headings", height=16)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=100, anchor="center")
        tree.column("Lecturer", width=140)
        tree.column("Resource", width=150)
        tree.pack(fill="both", expand=True)

        bookings = self.current_user.get_campus_bookings()
        for b in bookings:
            tree.insert("", "end", values=(
                b["booking_id"], b["full_name"], b["resource_name"],
                b["booking_date"], b["start_time"], b["end_time"],
                b["duration_hours"], b["status"]
            ))

    # ------------------------------------------------------------------
    # ADMIN: Campus Report
    # ------------------------------------------------------------------
    def ui_campus_report(self):
        self._clear_content()
        tk.Label(self.content, text="Campus Usage Report",
                 font=("Segoe UI", 14, "bold"), fg=PRIMARY, bg=BG).pack(anchor="w", pady=(0, 10))

        rep = self.current_user.campus_report()
        card = tk.Frame(self.content, bg=CARD, padx=20, pady=15,
                        highlightbackground="#cbd5e0", highlightthickness=1)
        card.pack(anchor="w", fill="x")

        tk.Label(card, text=f"Campus: {self.active_campus_name}",
                 font=("Segoe UI", 12, "bold"), fg=PRIMARY, bg=CARD).pack(anchor="w")
        tk.Label(card, text=f"Total bookings: {rep['total_bookings']}", bg=CARD).pack(anchor="w", pady=2)
        tk.Label(card, text=f"Active bookings: {rep['active_bookings']}", bg=CARD).pack(anchor="w", pady=2)
        tk.Label(card, text=f"Average duration: {rep['average_duration']} hours", bg=CARD).pack(anchor="w", pady=2)

        tk.Label(card, text="Most frequently used resources:",
                 font=("Segoe UI", 10, "bold"), bg=CARD).pack(anchor="w", pady=(10, 4))
        if rep["top_resources"]:
            for item in rep["top_resources"]:
                tk.Label(card, text=f"  • {item['name']}: {item['count']} bookings",
                         bg=CARD).pack(anchor="w")
        else:
            tk.Label(card, text="  (no data yet)", bg=CARD, fg="#718096").pack(anchor="w")

    # ------------------------------------------------------------------
    # OPERATOR: All Bookings
    # ------------------------------------------------------------------
    def ui_all_bookings(self):
        self._clear_content()
        tk.Label(self.content, text="All Bookings (System-wide)",
                 font=("Segoe UI", 14, "bold"), fg=PRIMARY, bg=BG).pack(anchor="w", pady=(0, 8))

        cols = ("ID", "Lecturer", "Resource", "Campus", "Date", "Start", "End", "Status")
        tree = ttk.Treeview(self.content, columns=cols, show="headings", height=16)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=95, anchor="center")
        tree.column("Lecturer", width=130)
        tree.column("Resource", width=140)
        tree.column("Campus", width=140)
        tree.pack(fill="both", expand=True)

        for b in self.current_user.get_all_bookings():
            tree.insert("", "end", values=(
                b["booking_id"], b["full_name"], b["resource_name"],
                b["campus_name"], b["booking_date"], b["start_time"],
                b["end_time"], b["status"]
            ))

    # ------------------------------------------------------------------
    # OPERATOR: Cross-Campus Report
    # ------------------------------------------------------------------
    def ui_cross_report(self):
        self._clear_content()
        tk.Label(self.content, text="Cross-Campus Comparison Report",
                 font=("Segoe UI", 14, "bold"), fg=PRIMARY, bg=BG).pack(anchor="w", pady=(0, 10))

        reports = self.current_user.cross_campus_report()
        for rep in reports:
            card = tk.Frame(self.content, bg=CARD, padx=15, pady=10,
                            highlightbackground="#cbd5e0", highlightthickness=1)
            card.pack(fill="x", pady=5)
            tk.Label(card, text=rep["campus_name"],
                     font=("Segoe UI", 12, "bold"), fg=PRIMARY, bg=CARD).pack(anchor="w")
            tk.Label(card, text=(
                f"Policy: max {rep['max_duration']} h  |  "
                f"{rep['open_hour']:02d}:00–{rep['close_hour']:02d}:00"
            ), fg=WARNING, bg=CARD).pack(anchor="w")
            tk.Label(card, text=(
                f"Total bookings: {rep['total_bookings']}   |   "
                f"Active: {rep['active_bookings']}   |   "
                f"Avg duration: {rep['average_duration']} h"
            ), bg=CARD).pack(anchor="w", pady=2)
            if rep["top_resources"]:
                top = ", ".join(f"{t['name']} ({t['count']})" for t in rep["top_resources"][:3])
                tk.Label(card, text=f"Top resources: {top}", bg=CARD, fg="#4a5568").pack(anchor="w")

    # ------------------------------------------------------------------
    # OPERATOR: View Policies
    # ------------------------------------------------------------------
    def ui_view_policies(self):
        self._clear_content()
        tk.Label(self.content, text="Campus Booking Policies",
                 font=("Segoe UI", 14, "bold"), fg=PRIMARY, bg=BG).pack(anchor="w", pady=(0, 10))
        for summary in list_all_policies():
            card = tk.Frame(self.content, bg=CARD, padx=15, pady=10,
                            highlightbackground="#cbd5e0", highlightthickness=1)
            card.pack(fill="x", pady=4)
            tk.Label(card, text=summary, font=("Segoe UI", 11), bg=CARD, fg=PRIMARY).pack(anchor="w")


class ResourceDialog(tk.Toplevel):
    """Simple modal dialog for adding / editing a resource."""

    def __init__(self, parent, title, initial=None):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.resizable(False, False)
        self.grab_set()

        frm = tk.Frame(self, padx=20, pady=15)
        frm.pack()

        tk.Label(frm, text="Name:").grid(row=0, column=0, sticky="w", pady=4)
        self.name_e = tk.Entry(frm, width=30)
        self.name_e.grid(row=0, column=1, pady=4)

        tk.Label(frm, text="Type:").grid(row=1, column=0, sticky="w", pady=4)
        self.type_e = ttk.Combobox(frm, values=["Lab", "Room", "Equipment", "Other"],
                                   state="readonly", width=27)
        self.type_e.grid(row=1, column=1, pady=4)
        self.type_e.current(0)

        tk.Label(frm, text="Capacity:").grid(row=2, column=0, sticky="w", pady=4)
        self.cap_e = tk.Entry(frm, width=30)
        self.cap_e.insert(0, "1")
        self.cap_e.grid(row=2, column=1, pady=4)

        tk.Label(frm, text="Description:").grid(row=3, column=0, sticky="w", pady=4)
        self.desc_e = tk.Entry(frm, width=30)
        self.desc_e.grid(row=3, column=1, pady=4)

        if initial:
            self.name_e.insert(0, initial[0])
            self.type_e.set(initial[1])
            self.cap_e.delete(0, "end")
            self.cap_e.insert(0, str(initial[2]))
            self.desc_e.insert(0, initial[3] or "")

        btn = tk.Frame(frm)
        btn.grid(row=4, column=0, columnspan=2, pady=12)
        ttk.Button(btn, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btn, text="Cancel", command=self.destroy).pack(side="left", padx=4)

    def _save(self):
        name = self.name_e.get().strip()
        rtype = self.type_e.get()
        try:
            cap = int(self.cap_e.get().strip())
        except ValueError:
            messagebox.showerror("Invalid", "Capacity must be an integer.", parent=self)
            return
        if not name:
            messagebox.showerror("Invalid", "Name is required.", parent=self)
            return
        self.result = (name, rtype, cap, self.desc_e.get().strip())
        self.destroy()


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = SmartCampusApp()
    app.mainloop()
