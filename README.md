# TaskFlow (CustomTkinter + MongoDB)

Dark-themed desktop planner with login, MongoDB persistence, task reminders, and recurring birthdays.

## What changed

- Added a **separate login page** (`login_page.py`) with:
  - Login
  - Register
- Added **separate MongoDB connectivity/data layer** (`db.py`) for:
  - user authentication
  - task CRUD
  - birthday CRUD
  - color preferences
- Added a dedicated `notification.py` module that sends desktop notifications through the `plyer` library.
- Main UI (`app.py`) now loads and saves all data using MongoDB instead of in-memory lists.

## Features

- Sidebar menu: **Calendar**, **Tasks**, **Birthdays**
- Calendar header includes a **Summary** button beside **Today** that sends a detailed monthly notification covering all tasks and birthdays in the visible month.
- Tasks:
  - single due date derived from either a chosen date/time or a timer
  - auto-removed after date passes
  - sorted by due date
- Birthdays:
  - recurring yearly on the calendar
  - sorted by next upcoming birthday
- Task and birthday creation each support two reminder options:
  - choose a full **day / month / year / time**
  - set a **timer** in days / hours / minutes
- Calendar displays task names and birthday names in different colors.
- Task and birthday marker colors are customizable and saved per user.
- Default marker colors follow the blue-cyan theme:
  - Tasks: `#47d7ff`
  - Birthdays: `#60a5fa`
- Desktop reminders are triggered from the selected schedule through `plyer`, so the app uses the platform notification system from one shared notification module.

## Requirements

```bash
pip install customtkinter pymongo plyer
```

Also ensure MongoDB is running (default URI used by app):

- `mongodb://localhost:27017`

## Run

```bash
python app.py
```

## File structure

- `app.py` - main TaskFlow window and login-first startup flow
- `login_page.py` - login/register UI
- `db.py` - MongoDB connectivity and all data operations
- `notification.py` - shared desktop notification helper powered by `plyer`
