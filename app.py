#!/usr/bin/env python3
import os
import sys
import webview
import database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(BASE_DIR, "index.html")
ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.png")


class HabitFlowAPI:
    """Python API exposed directly to JavaScript via pywebview."""

    def __init__(self, db_path=None):
        self.db_path = db_path
        database.init_db(self.db_path)

    def get_dashboard_data(self, reference_date=None):
        return database.get_dashboard_data(self.db_path, reference_date)

    def toggle_habit_check(self, habit_id, date_str):
        return database.toggle_habit_check(habit_id, date_str, self.db_path)

    def add_habit(self, name, category, icon, target, base_streak=0):
        return database.add_habit(name, category, icon, target, base_streak, self.db_path)

    def delete_habit(self, habit_id):
        return database.delete_habit(habit_id, self.db_path)

    def complete_all_for_date(self, date_str):
        return database.complete_all_for_date(date_str, self.db_path)

    def reset_demo_data(self):
        return database.reset_to_demo_data(self.db_path)

    def save_setting(self, key, value):
        return database.save_setting(key, value, self.db_path)

    def get_notes(self, category=None, search=None):
        return database.get_notes(category, search, self.db_path)

    def add_note(self, title, category="Journal", cover_style="noir", icon="ph-book-bookmark", content=""):
        return database.add_note(title, category, cover_style, icon, content, self.db_path)

    def update_note(self, note_id, title, category="Journal", cover_style="noir", icon="ph-book-bookmark", content=""):
        return database.update_note(note_id, title, category, cover_style, icon, content, self.db_path)

    def delete_note(self, note_id):
        return database.delete_note(note_id, self.db_path)


def main():
    api = HabitFlowAPI()

    window = webview.create_window(
        title="HabitFlow — Minimal Habit & Streak Dashboard",
        url=INDEX_HTML,
        js_api=api,
        width=1440,
        height=900,
        min_size=(1024, 700),
        background_color="#0A0A0A",
        text_select=False,
        easy_drag=False
    )

    webview.start(
        gui="gtk",
        debug=False,
        http_server=True,
        icon=ICON_PATH if os.path.exists(ICON_PATH) else None
    )


if __name__ == "__main__":
    main()
