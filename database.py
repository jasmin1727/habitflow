import os
import sqlite3
from datetime import datetime, date, timedelta

DB_DIR = os.path.expanduser("~/.local/share/habitflow")
DEFAULT_DB_PATH = os.path.join(DB_DIR, "habitflow.db")


def get_db_connection(db_path=None):
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS habits (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'General',
        icon TEXT NOT NULL DEFAULT 'ph-check',
        target INTEGER NOT NULL DEFAULT 5,
        base_streak INTEGER DEFAULT 0,
        display_order INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS habit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id TEXT NOT NULL,
        log_date DATE NOT NULL,
        completed INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(habit_id) REFERENCES habits(id) ON DELETE CASCADE,
        UNIQUE(habit_id, log_date)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    # Check if empty, then seed defaults
    cursor.execute("SELECT COUNT(*) FROM habits")
    count = cursor.fetchone()[0]
    if count == 0:
        seed_defaults(conn)

    conn.commit()
    conn.close()


def seed_defaults(conn):
    cursor = conn.cursor()
    default_habits = [
        ('h1', 'Hydrate 2.5L Water', 'Health', 'ph-drop', 7, 12, 1),
        ('h2', '30m Zone-2 Cardio', 'Health', 'ph-person-simple-run', 5, 4, 2),
        ('h3', 'Deep Work (No Phone)', 'Work', 'ph-laptop', 5, 8, 3),
        ('h4', 'Mindful Meditation', 'Mind', 'ph-brain', 7, 6, 4),
        ('h5', 'Read 20 Pages', 'Mind', 'ph-book-open', 6, 9, 5)
    ]

    cursor.executemany("""
    INSERT INTO habits (id, name, category, icon, target, base_streak, display_order)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, default_habits)

    # Seed demo logs for the current week up to today
    today = date.today()
    # Monday of current week
    monday = today - timedelta(days=today.weekday())

    # Demo check patterns (Monday=0, Tuesday=1, etc.)
    # Match the aesthetic demo pattern from the original dashboard
    patterns = {
        'h1': [True, True, True, True, True, True, False],
        'h2': [True, True, False, True, True, False, False],
        'h3': [True, True, True, True, True, False, False],
        'h4': [True, True, True, False, True, True, False],
        'h5': [True, True, True, True, False, True, False]
    }

    current_day_idx = today.weekday()
    for habit_id, checks in patterns.items():
        for day_offset in range(7):
            if day_offset <= current_day_idx and checks[day_offset]:
                log_day = monday + timedelta(days=day_offset)
                cursor.execute("""
                INSERT OR IGNORE INTO habit_logs (habit_id, log_date, completed)
                VALUES (?, ?, 1)
                """, (habit_id, log_day.isoformat()))

    # Default theme
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('theme', 'dark')")


def get_week_dates(reference_date=None):
    if reference_date is None:
        reference_date = date.today()
    elif isinstance(reference_date, str):
        reference_date = date.fromisoformat(reference_date)

    monday = reference_date - timedelta(days=reference_date.weekday())
    days_short = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    days_full = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    today_iso = date.today().isoformat()

    week_info = []
    for i in range(7):
        current_d = monday + timedelta(days=i)
        iso = current_d.isoformat()
        week_info.append({
            'date': iso,
            'day_idx': i,
            'short': days_short[i],
            'full': days_full[i],
            'dateNum': current_d.day,
            'monthShort': current_d.strftime('%b'),
            'is_today': (iso == today_iso)
        })
    return week_info


def calculate_streak(cursor, habit_id, base_streak=0):
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Check if completed today or yesterday
    cursor.execute("SELECT completed FROM habit_logs WHERE habit_id = ? AND log_date = ? AND completed = 1", (habit_id, today.isoformat()))
    done_today = cursor.fetchone() is not None

    cursor.execute("SELECT completed FROM habit_logs WHERE habit_id = ? AND log_date = ? AND completed = 1", (habit_id, yesterday.isoformat()))
    done_yesterday = cursor.fetchone() is not None

    if not done_today and not done_yesterday:
        return 0

    # Start walking backwards
    cursor_date = today if done_today else yesterday
    run = 0

    while True:
        cursor.execute("SELECT completed FROM habit_logs WHERE habit_id = ? AND log_date = ? AND completed = 1", (habit_id, cursor_date.isoformat()))
        row = cursor.fetchone()
        if row:
            run += 1
            cursor_date = cursor_date - timedelta(days=1)
        else:
            break

    return base_streak + run


def get_dashboard_data(db_path=None, reference_date=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    week_dates = get_week_dates(reference_date)
    week_start_iso = week_dates[0]['date']
    week_end_iso = week_dates[6]['date']
    today_iso = date.today().isoformat()
    today_weekday = date.today().weekday()

    # Get habits
    cursor.execute("SELECT * FROM habits ORDER BY display_order ASC, created_at ASC")
    habit_rows = cursor.fetchall()

    # Get all logs for this week
    cursor.execute("""
        SELECT habit_id, log_date, completed
        FROM habit_logs
        WHERE log_date BETWEEN ? AND ? AND completed = 1
    """, (week_start_iso, week_end_iso))
    log_rows = cursor.fetchall()

    logs_map = {}
    for r in log_rows:
        logs_map[(r['habit_id'], r['log_date'])] = True

    habits_list = []
    total_habits = len(habit_rows)
    today_completed_count = 0
    total_possible_checks = 0
    total_actual_checks = 0

    for h in habit_rows:
        h_id = h['id']
        checks = []
        completed_this_week = 0

        for day in week_dates:
            is_checked = (h_id, day['date']) in logs_map
            checks.append(is_checked)
            if is_checked:
                completed_this_week += 1

        if (h_id, today_iso) in logs_map:
            today_completed_count += 1

        streak = calculate_streak(cursor, h_id, h['base_streak'])
        target = h['target']
        total_possible_checks += target
        total_actual_checks += completed_this_week

        habits_list.append({
            'id': h_id,
            'name': h['name'],
            'category': h['category'],
            'icon': h['icon'],
            'target': target,
            'baseStreak': h['base_streak'],
            'checks': checks,
            'streak': streak,
            'weeklyCount': completed_this_week,
            'targetPct': min(100, round((completed_this_week / target) * 100)) if target > 0 else 0
        })

    # KPIs
    today_pct = round((today_completed_count / total_habits) * 100) if total_habits > 0 else 0
    weekly_pct = min(100, round((total_actual_checks / total_possible_checks) * 100)) if total_possible_checks > 0 else 0

    # Best streak
    best_streak = 0
    best_habit_name = 'No active streaks yet'
    for h in habits_list:
        if h['streak'] > best_streak:
            best_streak = h['streak']
            best_habit_name = h['name']

    # Chart data per day
    chart_days = []
    perfect_days_count = 0
    day_perfections = []
    sum_chart_pct = 0
    best_chart_day = {'name': '—', 'pct': -1}

    for idx, day in enumerate(week_dates):
        day_date = day['date']
        completed_on_day = sum(1 for h in habits_list if h['checks'][idx])
        day_pct = round((completed_on_day / total_habits) * 100) if total_habits > 0 else 0
        sum_chart_pct += day_pct

        is_perfect = (total_habits > 0 and completed_on_day == total_habits)
        if is_perfect:
            perfect_days_count += 1
        day_perfections.append(is_perfect)

        if day_pct > best_chart_day['pct'] and day_pct > 0:
            best_chart_day = {'name': day['full'], 'pct': day_pct}

        chart_days.append({
            'date': day_date,
            'short': day['short'],
            'full': day['full'],
            'dateNum': day['dateNum'],
            'completed': completed_on_day,
            'total': total_habits,
            'pct': day_pct,
            'is_today': day['is_today']
        })

    chart_avg_pct = round(sum_chart_pct / 7) if total_habits > 0 else 0

    # Settings
    cursor.execute("SELECT key, value FROM settings")
    settings_rows = cursor.fetchall()
    settings_dict = {r['key']: r['value'] for r in settings_rows}

    conn.close()

    return {
        'habits': habits_list,
        'week_dates': week_dates,
        'today_weekday': today_weekday,
        'today_iso': today_iso,
        'kpis': {
            'today_count': f"{today_completed_count}/{total_habits}",
            'today_completed': today_completed_count,
            'today_total': total_habits,
            'today_pct': today_pct,
            'weekly_pct': weekly_pct,
            'weekly_actual': total_actual_checks,
            'weekly_possible': total_possible_checks,
            'top_streak': best_streak,
            'top_streak_habit': best_habit_name,
            'perfect_days': perfect_days_count,
            'day_perfections': day_perfections
        },
        'chart': {
            'days': chart_days,
            'avg_pct': chart_avg_pct,
            'peak_text': f"Peak: {best_chart_day['name']} ({best_chart_day['pct']}%)" if best_chart_day['pct'] > 0 else "Peak day: —"
        },
        'settings': settings_dict
    }


def toggle_habit_check(habit_id, date_str, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT completed FROM habit_logs WHERE habit_id = ? AND log_date = ?", (habit_id, date_str))
    row = cursor.fetchone()

    new_state = False
    if row is None:
        cursor.execute("INSERT INTO habit_logs (habit_id, log_date, completed) VALUES (?, ?, 1)", (habit_id, date_str))
        new_state = True
    else:
        if row['completed'] == 1:
            cursor.execute("DELETE FROM habit_logs WHERE habit_id = ? AND log_date = ?", (habit_id, date_str))
            new_state = False
        else:
            cursor.execute("UPDATE habit_logs SET completed = 1 WHERE habit_id = ? AND log_date = ?", (habit_id, date_str))
            new_state = True

    conn.commit()
    conn.close()
    return new_state


def add_habit(name, category, icon, target, base_streak=0, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    habit_id = f"h_{int(datetime.now().timestamp() * 1000)}"
    cursor.execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM habits")
    next_order = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO habits (id, name, category, icon, target, base_streak, display_order)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (habit_id, name, category, icon, target, base_streak, next_order))

    conn.commit()
    conn.close()
    return habit_id


def delete_habit(habit_id, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM habit_logs WHERE habit_id = ?", (habit_id,))
    cursor.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit()
    conn.close()
    return True


def complete_all_for_date(date_str, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM habits")
    habits = cursor.fetchall()
    for h in habits:
        cursor.execute("""
            INSERT OR REPLACE INTO habit_logs (habit_id, log_date, completed)
            VALUES (?, ?, 1)
        """, (h['id'], date_str))
    conn.commit()
    conn.close()
    return True


def reset_to_demo_data(db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM habit_logs")
    cursor.execute("DELETE FROM habits")
    seed_defaults(conn)
    conn.commit()
    conn.close()
    return True


def save_setting(key, value, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()
    return True
