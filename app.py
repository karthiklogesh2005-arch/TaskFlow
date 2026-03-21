"""TaskFlow main application window.

This module contains the calendar, task management, and birthday management UI.
Login is handled from `login_page.py`, and persistence is handled by `db.py`.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from typing import Callable

import customtkinter as ctk
from tkinter import Listbox, messagebox

from db import DatabaseService
from login_page import LoginPage
from notification import send_notification

# Global UI theme colors.
DARK_BG = "#10151d"
DARK_PANEL = "#151d2b"
DARK_CARD = "#1b2434"
CYAN = "#47d7ff"

COLOR_NAME_TO_HEX = {
    "Cyan": "#47d7ff",
    "Blue": "#60a5fa",
    "Green": "#34d399",
    "Amber": "#f59e0b",
    "Red": "#f87171",
    "Pink": "#e879f9",
    "Yellow": "#fbbf24",
}
AVAILABLE_COLORS = list(COLOR_NAME_TO_HEX.keys())
SCHEDULE_OPTIONS = ["Date & Time", "Timer"]


class TaskFlowApp(ctk.CTk):
    """Main CustomTkinter application window for TaskFlow."""

    def __init__(self, db_service: DatabaseService, username: str) -> None:
        super().__init__()
        self.db = db_service
        self.username = username

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(f"TaskFlow Planner - {username}")
        self.geometry("1120x700")
        self.configure(fg_color=DARK_BG)

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month

        prefs = self.db.get_preferences(username)
        self.task_color = prefs["task_color"]
        self.birthday_color = prefs["birthday_color"]

        self.tasks: list[dict] = []
        self.birthdays: list[dict] = []
        self.active_mode = "calendar"
        self.listbox_items: list = []
        self.notified_today: set[str] = set()

        self._load_data()
        self._build_layout()
        self.show_calendar_view()
        self._background_tick()

    def _load_data(self) -> None:
        """Load user data from MongoDB."""
        self.tasks = self.db.get_tasks(self.username)
        self.birthdays = self.db.get_birthdays(self.username)

    def _normalize_notification_at(self, item: dict, date_key: str) -> datetime:
        """Return notification datetime for a record, supporting legacy rows."""
        if item.get("notification_at"):
            return datetime.fromisoformat(item["notification_at"])
        return datetime.combine(date.fromisoformat(item[date_key]), datetime.min.time())

    def _font(self, size: int = 14, weight: str = "normal") -> ctk.CTkFont:
        return ctk.CTkFont(family="Times New Roman", size=size, weight=weight)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=230, fg_color=DARK_PANEL, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.sidebar, text="TaskFlow", text_color=CYAN, font=self._font(size=28, weight="bold")).grid(
            row=0, column=0, padx=18, pady=(24, 18), sticky="w"
        )

        for row, (label, command) in enumerate(
            [("Calendar", self.show_calendar_view), ("Tasks", self.show_tasks_view), ("Birthdays", self.show_birthdays_view)],
            start=1,
        ):
            ctk.CTkButton(
                self.sidebar,
                text=label,
                command=command,
                height=42,
                font=self._font(size=18, weight="bold"),
                text_color=CYAN,
                fg_color="#2563eb",
                hover_color="#1d4ed8",
            ).grid(row=row, column=0, padx=18, pady=7, sticky="ew")

        self.main = ctk.CTkFrame(self, fg_color=DARK_BG, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

    def _clear_main(self) -> None:
        for child in self.main.winfo_children():
            child.destroy()

    def show_calendar_view(self) -> None:
        self.active_mode = "calendar"
        self._load_data()
        self._clear_main()

        wrap = ctk.CTkFrame(self.main, fg_color=DARK_BG)
        wrap.grid(row=0, column=0, sticky="nsew", padx=16, pady=14)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(1, weight=1)

        nav = ctk.CTkFrame(wrap, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        nav.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(nav, text="<", width=42, command=self.prev_month, font=self._font(size=18, weight="bold"), text_color=CYAN).grid(
            row=0, column=0, padx=(0, 8)
        )

        self.month_label = ctk.CTkLabel(nav, text="", text_color=CYAN, font=self._font(size=28, weight="bold"))
        self.month_label.grid(row=0, column=1)

        ctk.CTkButton(nav, text=">", width=42, command=self.next_month, font=self._font(size=18, weight="bold"), text_color=CYAN).grid(
            row=0, column=2, padx=(8, 8)
        )
        ctk.CTkButton(nav, text="Today", width=90, command=self.go_today, font=self._font(size=14, weight="bold"), text_color=CYAN).grid(
            row=0, column=3
        )
        ctk.CTkButton(
            nav,
            text="Summary",
            width=110,
            command=self.send_month_summary,
            font=self._font(size=14, weight="bold"),
            text_color=CYAN,
        ).grid(row=0, column=4, padx=(8, 0))

        self.calendar_frame = ctk.CTkFrame(wrap, fg_color=DARK_PANEL)
        self.calendar_frame.grid(row=1, column=0, sticky="nsew")
        self.calendar_frame.grid_columnconfigure(tuple(range(7)), weight=1)
        self.calendar_frame.grid_rowconfigure(tuple(range(7)), weight=1)

        self.refresh_calendar()

    def refresh_calendar(self) -> None:
        if not hasattr(self, "calendar_frame"):
            return

        self._load_data()
        for child in self.calendar_frame.winfo_children():
            child.destroy()

        self.month_label.configure(text=f"{calendar.month_name[self.current_month]} {self.current_year}")
        for col, day_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            ctk.CTkLabel(self.calendar_frame, text=day_name, text_color=CYAN, font=self._font(size=15, weight="bold")).grid(
                row=0, column=col, padx=6, pady=(8, 2), sticky="nsew"
            )

        for week_idx, week in enumerate(calendar.monthcalendar(self.current_year, self.current_month), start=1):
            for day_idx, day_num in enumerate(week):
                day_card = ctk.CTkFrame(self.calendar_frame, fg_color=DARK_CARD, corner_radius=8, border_width=1, border_color="#2b3a52")
                day_card.grid(row=week_idx, column=day_idx, padx=4, pady=4, sticky="nsew")
                if day_num == 0:
                    ctk.CTkLabel(day_card, text="", fg_color="transparent").pack(expand=True)
                    continue

                current_day = date(self.current_year, self.current_month, day_num)
                ctk.CTkLabel(day_card, text=str(day_num), text_color=CYAN, font=self._font(size=15, weight="bold")).pack(anchor="nw", padx=8, pady=(6, 0))

                for task in self._tasks_on_date(current_day):
                    ctk.CTkLabel(day_card, text=f"● {task['title']}", text_color=self.task_color, font=self._font(size=11, weight="bold")).pack(anchor="w", padx=8)

                for bday in self._birthdays_on_date(current_day):
                    ctk.CTkLabel(day_card, text=f"★ {bday['name']}", text_color=self.birthday_color, font=self._font(size=11, weight="bold")).pack(anchor="w", padx=8)

    def _tasks_on_date(self, target: date) -> list[dict]:
        return [task for task in self.tasks if date.fromisoformat(task["due_date"]) == target]

    def _birthdays_on_date(self, target: date) -> list[dict]:
        return [b for b in self.birthdays if b["day"] == target.day and b["month"] == target.month]

    def _month_tasks(self) -> list[dict]:
        """Return tasks due in the currently displayed month."""
        return [
            task
            for task in self.tasks
            if (due_date := date.fromisoformat(task["due_date"])).year == self.current_year
            and due_date.month == self.current_month
        ]

    def _month_birthdays(self) -> list[dict]:
        """Return birthdays that recur in the currently displayed month."""
        return [birthday for birthday in self.birthdays if birthday["month"] == self.current_month]

    def send_month_summary(self) -> None:
        """Send a detailed notification containing all month tasks and birthdays."""
        self._load_data()
        month_title = f"{calendar.month_name[self.current_month]} {self.current_year}"
        task_entries = sorted(self._month_tasks(), key=lambda item: self._normalize_notification_at(item, "due_date"))
        birthday_entries = sorted(
            self._month_birthdays(),
            key=lambda item: (item["day"], self._next_birthday_notification(item).time()),
        )

        lines = [f"Summary for {month_title}"]

        if task_entries:
            lines.append("Tasks:")
            for task in task_entries:
                due_at = self._normalize_notification_at(task, "due_date")
                lines.append(f"- {task['title']}: {due_at.strftime('%d %b %Y %H:%M')}")
        else:
            lines.append("Tasks: none")

        if birthday_entries:
            lines.append("Birthdays:")
            for birthday in birthday_entries:
                reminder_at = self._next_birthday_notification(birthday)
                lines.append(f"- {birthday['name']}: {reminder_at.strftime('%d %b %Y %H:%M')}")
        else:
            lines.append("Birthdays: none")

        send_notification(f"Monthly Summary - {month_title}", "\n".join(lines))

    def _color_name_from_hex(self, value: str) -> str:
        """Return display color name from its hex value."""
        for name, hex_value in COLOR_NAME_TO_HEX.items():
            if hex_value.lower() == value.lower():
                return name
        return "Cyan"

    def _show_list_view(self, title: str, add_command: Callable[[], None], delete_command: Callable[[], None], color_apply_command: Callable[[], None], color_var: ctk.StringVar) -> None:
        self._clear_main()
        wrap = ctk.CTkFrame(self.main, fg_color=DARK_BG)
        wrap.grid(row=0, column=0, sticky="nsew", padx=16, pady=14)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(wrap, text=title, text_color=CYAN, font=self._font(size=27, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))

        ribbon = ctk.CTkFrame(wrap, fg_color=DARK_PANEL)
        ribbon.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(ribbon, text="Add", command=add_command, width=110, text_color=CYAN, font=self._font(size=14, weight="bold")).pack(side="left", padx=(10, 8), pady=10)
        ctk.CTkButton(
            ribbon,
            text="Delete",
            command=delete_command,
            width=110,
            text_color=CYAN,
            font=self._font(size=14, weight="bold"),
            fg_color="#b91c1c",
            hover_color="#991b1b",
        ).pack(side="left", padx=(0, 14), pady=10)

        ctk.CTkLabel(ribbon, text="Display Color:", text_color=CYAN, font=self._font(size=14, weight="bold")).pack(side="left")
        ctk.CTkOptionMenu(ribbon, values=AVAILABLE_COLORS, variable=color_var, width=130, font=self._font(size=12), text_color=CYAN).pack(side="left", padx=(8, 8))
        ctk.CTkButton(ribbon, text="Apply Color", command=color_apply_command, width=120, text_color=CYAN, font=self._font(size=13, weight="bold")).pack(side="left", padx=(0, 8), pady=10)

        list_frame = ctk.CTkFrame(wrap, fg_color=DARK_PANEL)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        self.item_listbox = Listbox(
            list_frame,
            bg="#0f172a",
            fg=CYAN,
            selectbackground="#1d4ed8",
            selectforeground="#ecfeff",
            font=("Times New Roman", 15),
            borderwidth=0,
            highlightthickness=0,
        )
        self.item_listbox.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)

    def show_tasks_view(self) -> None:
        self.active_mode = "tasks"
        self._load_data()
        self.task_color_var = ctk.StringVar(value=self._color_name_from_hex(self.task_color))
        self._show_list_view("Tasks - Closest Due Dates", self.open_add_task_dialog, self.delete_selected_task, self.apply_task_color, self.task_color_var)
        self._refresh_task_listbox()

    def show_birthdays_view(self) -> None:
        self.active_mode = "birthdays"
        self._load_data()
        self.bday_color_var = ctk.StringVar(value=self._color_name_from_hex(self.birthday_color))
        self._show_list_view("Birthdays - Upcoming", self.open_add_birthday_dialog, self.delete_selected_birthday, self.apply_birthday_color, self.bday_color_var)
        self._refresh_birthday_listbox()

    def apply_task_color(self) -> None:
        self.task_color = COLOR_NAME_TO_HEX.get(self.task_color_var.get(), "#47d7ff")
        self.db.set_task_color(self.username, self.task_color)
        self.refresh_calendar()

    def apply_birthday_color(self) -> None:
        self.birthday_color = COLOR_NAME_TO_HEX.get(self.bday_color_var.get(), "#60a5fa")
        self.db.set_birthday_color(self.username, self.birthday_color)
        self.refresh_calendar()

    def _next_birthday_date(self, bday_date: date) -> date:
        today = date.today()
        next_date = date(today.year, bday_date.month, bday_date.day)
        if next_date < today:
            next_date = date(today.year + 1, bday_date.month, bday_date.day)
        return next_date

    def _next_birthday_notification(self, item: dict) -> datetime:
        """Return the next scheduled birthday notification datetime."""
        scheduled = self._normalize_notification_at(item, "birthday")
        now = datetime.now()
        year = now.year
        candidate = scheduled.replace(year=year)
        if candidate < now:
            candidate = candidate.replace(year=year + 1)
        return candidate

    def _refresh_task_listbox(self) -> None:
        self._load_data()
        self.item_listbox.delete(0, "end")
        self.listbox_items = []

        if not self.tasks:
            self.item_listbox.insert("end", "No tasks added yet.")
            return

        ordered = sorted(self.tasks, key=lambda t: (t["due_date"], t["title"].lower()))
        for task in ordered:
            due = date.fromisoformat(task["due_date"])
            due_in = (due - date.today()).days
            notify_at = self._normalize_notification_at(task, "due_date").strftime("%d %b %Y %H:%M")
            self.item_listbox.insert("end", f"{task['title']} | {task['due_date']} | notify {notify_at} | due in {due_in} day(s)")
            self.listbox_items.append(task["_id"])

    def _refresh_birthday_listbox(self) -> None:
        self._load_data()
        self.item_listbox.delete(0, "end")
        self.listbox_items = []

        if not self.birthdays:
            self.item_listbox.insert("end", "No birthdays added yet.")
            return

        ordered = sorted(self.birthdays, key=lambda b: self._next_birthday_date(date.fromisoformat(b["birthday"])))
        for b in ordered:
            born = date.fromisoformat(b["birthday"])
            next_date = self._next_birthday_date(born)
            days_left = (next_date - date.today()).days
            notify_at = (
                self._next_birthday_notification(b).strftime("%d %b %Y %H:%M")
                if b.get("notification_mode", "datetime") == "datetime"
                else self._normalize_notification_at(b, "birthday").strftime("%d %b %Y %H:%M")
            )
            self.item_listbox.insert("end", f"{b['name']} | {born.strftime('%d %b')} | notify {notify_at} | in {days_left} day(s)")
            self.listbox_items.append(b["_id"])

    def _date_dropdowns(self, parent: ctk.CTkToplevel, label: str, default: date, min_year: int, max_year: int):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=18, pady=6)
        ctk.CTkLabel(frame, text=label, text_color=CYAN, font=self._font(size=14, weight="bold")).pack(anchor="w")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        day_var = ctk.StringVar(value=str(default.day))
        month_var = ctk.StringVar(value=str(default.month))
        year_var = ctk.StringVar(value=str(default.year))

        ctk.CTkOptionMenu(row, values=[str(d) for d in range(1, 32)], variable=day_var, width=100, text_color=CYAN, font=self._font()).pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(row, values=[str(m) for m in range(1, 13)], variable=month_var, width=100, text_color=CYAN, font=self._font()).pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(row, values=[str(y) for y in range(min_year, max_year + 1)], variable=year_var, width=120, text_color=CYAN, font=self._font()).pack(side="left")

        def get_date() -> date:
            return date(int(year_var.get()), int(month_var.get()), int(day_var.get()))

        return get_date

    def _datetime_dropdowns(
        self,
        parent: ctk.CTkFrame,
        label: str,
        default: datetime,
        min_year: int,
        max_year: int,
    ):
        """Create day/month/year/hour/minute selectors and return a getter."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=18, pady=6)
        ctk.CTkLabel(frame, text=label, text_color=CYAN, font=self._font(size=14, weight="bold")).pack(anchor="w")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))

        day_var = ctk.StringVar(value=str(default.day))
        month_var = ctk.StringVar(value=str(default.month))
        year_var = ctk.StringVar(value=str(default.year))
        hour_var = ctk.StringVar(value=f"{default.hour:02d}")
        minute_var = ctk.StringVar(value=f"{default.minute:02d}")

        for values, variable, width in [
            ([str(d) for d in range(1, 32)], day_var, 70),
            ([str(m) for m in range(1, 13)], month_var, 70),
            ([str(y) for y in range(min_year, max_year + 1)], year_var, 90),
            ([f"{h:02d}" for h in range(24)], hour_var, 70),
            ([f"{m:02d}" for m in range(60)], minute_var, 70),
        ]:
            ctk.CTkOptionMenu(
                row,
                values=values,
                variable=variable,
                width=width,
                text_color=CYAN,
                font=self._font(),
            ).pack(side="left", padx=(0, 8))

        def get_datetime() -> datetime:
            return datetime(
                int(year_var.get()),
                int(month_var.get()),
                int(day_var.get()),
                int(hour_var.get()),
                int(minute_var.get()),
            )

        return get_datetime

    def _timer_inputs(self, parent: ctk.CTkFrame, label: str):
        """Create timer selectors and return a getter producing a future datetime."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=18, pady=6)
        ctk.CTkLabel(frame, text=label, text_color=CYAN, font=self._font(size=14, weight="bold")).pack(anchor="w")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))

        day_var = ctk.StringVar(value="0")
        hour_var = ctk.StringVar(value="0")
        minute_var = ctk.StringVar(value="5")

        ctk.CTkOptionMenu(row, values=[str(d) for d in range(0, 31)], variable=day_var, width=90, text_color=CYAN, font=self._font()).pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(row, values=[str(h) for h in range(0, 24)], variable=hour_var, width=90, text_color=CYAN, font=self._font()).pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(row, values=[str(m) for m in range(0, 60)], variable=minute_var, width=90, text_color=CYAN, font=self._font()).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(row, text="days / hours / minutes", text_color=CYAN, font=self._font(size=12)).pack(side="left")

        def get_timer_datetime() -> datetime:
            delta = timedelta(days=int(day_var.get()), hours=int(hour_var.get()), minutes=int(minute_var.get()))
            if delta.total_seconds() <= 0:
                raise ValueError("Timer must be greater than zero.")
            return datetime.now() + delta

        return get_timer_datetime

    def _build_schedule_selector(
        self,
        parent: ctk.CTkToplevel,
        title: str,
        default_dt: datetime,
        min_year: int,
        max_year: int,
    ):
        """Build scheduling mode controls and return selected datetime getter."""
        schedule_var = ctk.StringVar(value=SCHEDULE_OPTIONS[0])

        ctk.CTkLabel(parent, text=title, text_color=CYAN, font=self._font(size=15, weight="bold")).pack(anchor="w", padx=18, pady=(8, 4))
        segmented = ctk.CTkSegmentedButton(parent, values=SCHEDULE_OPTIONS, variable=schedule_var)
        segmented.pack(fill="x", padx=18, pady=(0, 8))

        mode_frame = ctk.CTkFrame(parent, fg_color="transparent")
        mode_frame.pack(fill="x")

        datetime_frame = ctk.CTkFrame(mode_frame, fg_color="transparent")
        timer_frame = ctk.CTkFrame(mode_frame, fg_color="transparent")

        get_datetime = self._datetime_dropdowns(datetime_frame, "Select date and time", default_dt, min_year, max_year)
        get_timer_datetime = self._timer_inputs(timer_frame, "Set timer for desktop notification")

        def refresh_mode() -> None:
            datetime_frame.pack_forget()
            timer_frame.pack_forget()
            if schedule_var.get() == "Date & Time":
                datetime_frame.pack(fill="x")
            else:
                timer_frame.pack(fill="x")

        segmented.configure(command=lambda _value: refresh_mode())
        refresh_mode()

        def get_schedule() -> tuple[str, datetime]:
            if schedule_var.get() == "Timer":
                return "timer", get_timer_datetime()
            return "datetime", get_datetime()

        return get_schedule

    def open_add_task_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Task")
        dialog.geometry("560x420")
        dialog.configure(fg_color=DARK_PANEL)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Task Name", text_color=CYAN, font=self._font(size=15, weight="bold")).pack(anchor="w", padx=18, pady=(16, 4))
        title_entry = ctk.CTkEntry(dialog, width=420, font=self._font())
        title_entry.pack(padx=18)

        now = datetime.now()
        get_schedule = self._build_schedule_selector(dialog, "Notification Schedule", now + timedelta(minutes=5), now.year - 1, now.year + 5)

        def save_task() -> None:
            title = title_entry.get().strip()
            if not title:
                messagebox.showerror("Invalid data", "Task name cannot be empty.")
                return
            try:
                notification_mode, notification_at = get_schedule()
            except ValueError:
                messagebox.showerror("Invalid schedule", "Please select a valid date/time or a timer greater than zero.")
                return
            self.db.add_task(self.username, title, notification_at.date(), notification_at, notification_mode)
            dialog.destroy()
            self.refresh_calendar()
            if self.active_mode == "tasks":
                self._refresh_task_listbox()

        ctk.CTkButton(dialog, text="Save Task", command=save_task, text_color=CYAN, font=self._font(size=14, weight="bold")).pack(pady=16)

    def open_add_birthday_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Birthday")
        dialog.geometry("560x420")
        dialog.configure(fg_color=DARK_PANEL)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Person Name", text_color=CYAN, font=self._font(size=15, weight="bold")).pack(anchor="w", padx=18, pady=(16, 4))
        name_entry = ctk.CTkEntry(dialog, width=420, font=self._font())
        name_entry.pack(padx=18)

        now = datetime.now()
        get_schedule = self._build_schedule_selector(dialog, "Birthday Reminder Schedule", now + timedelta(minutes=5), now.year - 100, now.year + 5)

        def save_birthday() -> None:
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Invalid data", "Name cannot be empty.")
                return
            try:
                notification_mode, notification_at = get_schedule()
            except ValueError:
                messagebox.showerror("Invalid schedule", "Please select a valid date/time or a timer greater than zero.")
                return
            self.db.add_birthday(self.username, name, notification_at.date(), notification_at, notification_mode)
            dialog.destroy()
            self.refresh_calendar()
            if self.active_mode == "birthdays":
                self._refresh_birthday_listbox()

        ctk.CTkButton(dialog, text="Save Birthday", command=save_birthday, text_color=CYAN, font=self._font(size=14, weight="bold")).pack(pady=16)

    def _selected_real_id(self):
        selection = self.item_listbox.curselection()
        if not selection:
            return None
        pos = selection[0]
        return self.listbox_items[pos] if pos < len(self.listbox_items) else None

    def delete_selected_task(self) -> None:
        task_id = self._selected_real_id()
        if task_id is None:
            messagebox.showwarning("Select task", "Please select a task to delete.")
            return
        self.db.delete_task(self.username, task_id)
        self._refresh_task_listbox()
        self.refresh_calendar()

    def delete_selected_birthday(self) -> None:
        bday_id = self._selected_real_id()
        if bday_id is None:
            messagebox.showwarning("Select birthday", "Please select a birthday to delete.")
            return
        self.db.delete_birthday(self.username, bday_id)
        self._refresh_birthday_listbox()
        self.refresh_calendar()

    def _check_notifications(self) -> None:
        self._load_data()
        now = datetime.now()
        today = now.date()

        for task in self.tasks:
            due_at = self._normalize_notification_at(task, "due_date")
            if due_at <= now and task.get("last_notified_on") != today.isoformat():
                key = f"task:{task['_id']}:{today.isoformat()}"
                if key not in self.notified_today:
                    send_notification(
                        "Task Reminder",
                        f"{task['title']} is scheduled for {due_at.strftime('%d %b %Y %H:%M')}.",
                    )
                    self.notified_today.add(key)
                    self.db.mark_task_notified(self.username, task["_id"], today)

        for item in self.birthdays:
            notification_mode = item.get("notification_mode", "datetime")
            reminder_at = self._next_birthday_notification(item) if notification_mode == "datetime" else self._normalize_notification_at(item, "birthday")
            if reminder_at <= now and item.get("last_notified_on") != today.isoformat():
                key = f"birthday:{item['_id']}:{today.isoformat()}"
                if key not in self.notified_today:
                    send_notification(
                        "Birthday Reminder",
                        f"{item['name']} has a birthday reminder for {reminder_at.strftime('%d %b %Y %H:%M')}.",
                    )
                    self.notified_today.add(key)
                    self.db.mark_birthday_notified(self.username, item["_id"], today)

        today_prefix = today.isoformat()
        self.notified_today = {k for k in self.notified_today if today_prefix in k}

    def _background_tick(self) -> None:
        self._check_notifications()
        self.after(60000, self._background_tick)

    def prev_month(self) -> None:
        self.current_month, self.current_year = (12, self.current_year - 1) if self.current_month == 1 else (self.current_month - 1, self.current_year)
        self.refresh_calendar()

    def next_month(self) -> None:
        self.current_month, self.current_year = (1, self.current_year + 1) if self.current_month == 12 else (self.current_month + 1, self.current_year)
        self.refresh_calendar()

    def go_today(self) -> None:
        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.refresh_calendar()


def main() -> None:
    """Start app with login-first flow."""
    db_service = DatabaseService()

    def launch_main(username: str) -> None:
        app = TaskFlowApp(db_service, username)
        app.mainloop()

    login = LoginPage(db_service, launch_main)
    login.mainloop()


if __name__ == "__main__":
    main()
