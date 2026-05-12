import sqlite3
import re

LESSON_TIMES = {
    "1": "08:30-09:50", "2": "10:00-11:20", "3": "12:00-13:20", "4": "13:30-14:50",
    "5": "15:10-16:30", "6": "16:40-18:00", "7": "18:10-19:30", "8": "19:40-21:00"
}

DAYS_ORDER = {
    "Понеділок": 1, "Вівторок": 2, "Середа": 3, 
    "Четвер": 4, "П'ятниця": 5, "Субота": 6, "Неділя": 7
}

def init_db():
    conn = sqlite3.connect('university.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS schedule 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT, day_of_week TEXT, 
                  lesson_time TEXT, teacher TEXT, location TEXT, is_cancelled INTEGER DEFAULT 0, lesson_type TEXT)""")
    conn.commit()
    conn.close()

def get_db_schedule():
    conn = sqlite3.connect('university.db')
    cursor = conn.cursor()
    cursor.execute("SELECT day_of_week, lesson_time, subject, teacher, location, is_cancelled, lesson_type FROM schedule")
    rows = cursor.fetchall()
    conn.close()
    return sorted(rows, key=lambda x: (DAYS_ORDER.get(x[0], 99), x[1]))

def clear_completely():
    conn = sqlite3.connect('university.db')
    conn.execute("DELETE FROM schedule")
    conn.commit()
    conn.close()

def delete_all_in_day(day):
    conn = sqlite3.connect('university.db')
    day_clean = day.strip().capitalize()
    conn.execute("DELETE FROM schedule WHERE day_of_week = ?", (day_clean,))
    conn.commit()
    conn.close()

def smart_delete(subject, day):
    conn = sqlite3.connect('university.db')
    day_clean = day.strip().capitalize()
    conn.execute("DELETE FROM schedule WHERE subject LIKE ? AND day_of_week = ?", (f"%{subject}%", day_clean))
    conn.commit()
    conn.close()

def smart_cancel(subject, day):
    conn = sqlite3.connect('university.db')
    day_clean = day.strip().capitalize()
    search = str(subject).strip()
    if search == "13": search = "13:30"
    if search == "15": search = "15:10"
    
    query = "UPDATE schedule SET is_cancelled = 1 WHERE (subject LIKE ? OR lesson_time LIKE ?) AND day_of_week = ?"
    conn.execute(query, (f"%{search}%", f"%{search}%", day_clean))
    conn.commit()
    conn.close()

def smart_uncancel(subject, day):
    conn = sqlite3.connect('university.db')
    day_clean = day.strip().capitalize()
    query = "UPDATE schedule SET is_cancelled = 0 WHERE (subject LIKE ? OR lesson_time LIKE ?) AND day_of_week = ?"
    conn.execute(query, (f"%{subject}%", f"%{subject}%", day_clean))
    conn.commit()
    conn.close()

def add_lesson(subject, day, time_input, teacher=None, location=None, lesson_type=None):
    conn = sqlite3.connect('university.db')
    
    formatted_type = ""
    if lesson_type and lesson_type.strip().lower() != "none":
        clean_type = lesson_type.replace("(", "").replace(")", "").strip().capitalize()
        formatted_type = f"({clean_type})"

    t_str = str(time_input).lower()
    num_map = {"перша": "1", "друга": "2", "третя": "3", "четверта": "4", "п'ята": "5", "шоста": "6", "сьома": "7", "восьма": "8"}
    pair_num = num_map.get(t_str, t_str)
    final_time = LESSON_TIMES.get(pair_num, time_input)
    
    clean_subject = re.sub(r'\(.*?\)', '', subject).strip()
    
    conn.execute('''INSERT INTO schedule (subject, day_of_week, lesson_time, teacher, location, is_cancelled, lesson_type)
                    VALUES (?, ?, ?, ?, ?, 0, ?)''', 
                 (clean_subject, day.strip().capitalize(), final_time, teacher, location, formatted_type))
    conn.commit()
    conn.close()

def format_schedule_text():
    rows = get_db_schedule()
    if not rows: return "Розклад порожній 📭"
    res = "📅 *ТВІЙ ПОВНИЙ РОЗКЛАД:*\n"
    current_day = ""
    for r in rows:
        day, time, subject, teacher, loc, cancelled, l_type = r
        if day != current_day:
            res += f"\n----------------------------------\n*{day}*\n"
            current_day = day
        type_str = f" {l_type}" if l_type and l_type != "None" else ""
        status = " (СКАСОВАНО) ❌" if cancelled == 1 else ""
        res += f"• {subject}{type_str} {time}{status}\n"
        if cancelled == 0:
            res += f"   👨‍🏫 {teacher if teacher else 'Не вказано'} | 📍 {loc if loc else 'ауд. ?'}\n"
    return res + "\n----------------------------------"
