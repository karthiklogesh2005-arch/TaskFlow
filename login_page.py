"""Separate login UI for TaskFlow."""

from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from db import DatabaseService

DARK_BG = "#10151d"
DARK_PANEL = "#151d2b"
CYAN = "#47d7ff"


class LoginPage(ctk.CTk):
    """Login/registration page shown before the main TaskFlow window."""

    def __init__(self, db_service: DatabaseService, on_success) -> None:
        super().__init__()
        self.db_service = db_service
        self.on_success = on_success

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("TaskFlow Login")
        self.geometry("450x320")
        self.configure(fg_color=DARK_BG)

        panel = ctk.CTkFrame(self, fg_color=DARK_PANEL)
        panel.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            panel,
            text="TaskFlow Login",
            text_color=CYAN,
            font=ctk.CTkFont(family="Times New Roman", size=30, weight="bold"),
        ).pack(pady=(20, 16))

        self.username_entry = ctk.CTkEntry(panel, placeholder_text="Username", width=300)
        self.username_entry.pack(pady=8)

        self.password_entry = ctk.CTkEntry(panel, placeholder_text="Password", show="*", width=300)
        self.password_entry.pack(pady=8)

        button_row = ctk.CTkFrame(panel, fg_color="transparent")
        button_row.pack(pady=20)

        ctk.CTkButton(button_row, text="Login", command=self.login, text_color=CYAN).pack(side="left", padx=8)
        ctk.CTkButton(button_row, text="Register", command=self.register, text_color=CYAN).pack(side="left", padx=8)

    def login(self) -> None:
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showwarning("Missing fields", "Please enter username and password.")
            return

        if not self.db_service.authenticate_user(username, password):
            messagebox.showerror("Login failed", "Invalid username or password.")
            return

        self.destroy()
        self.on_success(username)

    def register(self) -> None:
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showwarning("Missing fields", "Please enter username and password.")
            return

        if not self.db_service.register_user(username, password):
            messagebox.showerror("Registration failed", "Username already exists.")
            return

        messagebox.showinfo("Success", "Account created. You can now login.")
