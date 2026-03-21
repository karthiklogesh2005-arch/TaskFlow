"""MongoDB connectivity and data operations for TaskFlow."""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Any

from pymongo import ASCENDING, MongoClient


class DatabaseService:
    """Handle authentication and CRUD operations backed by MongoDB."""

    DEFAULT_TASK_COLOR = "#47d7ff"
    DEFAULT_BIRTHDAY_COLOR = "#60a5fa"

    def __init__(self, uri: str = "mongodb://localhost:27017", db_name: str = "taskflow") -> None:
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.users = self.db["users"]
        self.tasks = self.db["tasks"]
        self.birthdays = self.db["birthdays"]
        self.preferences = self.db["preferences"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self.users.create_index([("username", ASCENDING)], unique=True)
        self.tasks.create_index([("username", ASCENDING), ("due_date", ASCENDING)])
        self.birthdays.create_index([("username", ASCENDING), ("month", ASCENDING), ("day", ASCENDING)])
        self.preferences.create_index([("username", ASCENDING)], unique=True)

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def register_user(self, username: str, password: str) -> bool:
        if self.users.find_one({"username": username}):
            return False
        self.users.insert_one({"username": username, "password_hash": self._hash_password(password)})
        self.preferences.update_one(
            {"username": username},
            {
                "$setOnInsert": {
                    "task_color": self.DEFAULT_TASK_COLOR,
                    "birthday_color": self.DEFAULT_BIRTHDAY_COLOR,
                }
            },
            upsert=True,
        )
        return True

    def authenticate_user(self, username: str, password: str) -> bool:
        user = self.users.find_one({"username": username})
        if not user:
            return False
        return user.get("password_hash") == self._hash_password(password)

    def prune_expired_tasks(self, username: str) -> None:
        self.tasks.delete_many({"username": username, "due_date": {"$lt": date.today().isoformat()}})

    def get_tasks(self, username: str) -> list[dict[str, Any]]:
        self.prune_expired_tasks(username)
        return list(self.tasks.find({"username": username}).sort("due_date", ASCENDING))

    def add_task(
        self,
        username: str,
        title: str,
        due_date: date,
        notification_at: datetime,
        notification_mode: str,
    ) -> None:
        self.tasks.insert_one(
            {
                "username": username,
                "title": title,
                "due_date": due_date.isoformat(),
                "notification_at": notification_at.isoformat(timespec="minutes"),
                "notification_mode": notification_mode,
                "last_notified_on": None,
            }
        )

    def delete_task(self, username: str, task_id: Any) -> None:
        self.tasks.delete_one({"username": username, "_id": task_id})

    def get_birthdays(self, username: str) -> list[dict[str, Any]]:
        return list(self.birthdays.find({"username": username}))

    def add_birthday(
        self,
        username: str,
        name: str,
        birthday: date,
        notification_at: datetime,
        notification_mode: str,
    ) -> None:
        self.birthdays.insert_one(
            {
                "username": username,
                "name": name,
                "birthday": birthday.isoformat(),
                "month": birthday.month,
                "day": birthday.day,
                "notification_at": notification_at.isoformat(timespec="minutes"),
                "notification_mode": notification_mode,
                "last_notified_on": None,
            }
        )

    def delete_birthday(self, username: str, birthday_id: Any) -> None:
        self.birthdays.delete_one({"username": username, "_id": birthday_id})

    def mark_task_notified(self, username: str, task_id: Any, notified_on: date) -> None:
        self.tasks.update_one(
            {"username": username, "_id": task_id},
            {"$set": {"last_notified_on": notified_on.isoformat()}},
        )

    def mark_birthday_notified(self, username: str, birthday_id: Any, notified_on: date) -> None:
        self.birthdays.update_one(
            {"username": username, "_id": birthday_id},
            {"$set": {"last_notified_on": notified_on.isoformat()}},
        )

    def get_preferences(self, username: str) -> dict[str, str]:
        pref = self.preferences.find_one({"username": username})
        if not pref:
            return {
                "task_color": self.DEFAULT_TASK_COLOR,
                "birthday_color": self.DEFAULT_BIRTHDAY_COLOR,
            }
        return {
            "task_color": pref.get("task_color", self.DEFAULT_TASK_COLOR),
            "birthday_color": pref.get("birthday_color", self.DEFAULT_BIRTHDAY_COLOR),
        }

    def set_task_color(self, username: str, color: str) -> None:
        self.preferences.update_one({"username": username}, {"$set": {"task_color": color}}, upsert=True)

    def set_birthday_color(self, username: str, color: str) -> None:
        self.preferences.update_one({"username": username}, {"$set": {"birthday_color": color}}, upsert=True)
