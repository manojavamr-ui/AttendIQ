"""
╔══════════════════════════════════════════════════════╗
║        AttendIQ – Attendance Analytics System        ║
║        CP-032 | Level: Foundation | Domain: Education║
╚══════════════════════════════════════════════════════╝

Features:
  Core:
    1. Record daily attendance per subject
    2. Calculate attendance % per student per subject
    3. List students below 75% in any subject
    4. Classes needed to reach 75%
    5. Weekly attendance report
  Stretch:
    * Medical leave (does not count against student)
    * Predict students trending below 75%
"""

import json
import os
import sys
from datetime import datetime, timedelta, date
from collections import defaultdict

# ─────────────────────────────────────────────
#  ANSI COLOR HELPERS
# ─────────────────────────────────────────────
def _supports_color():
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

USE_COLOR = _supports_color()

class C:
    RESET   = "\033[0m"  if USE_COLOR else ""
    BOLD    = "\033[1m"  if USE_COLOR else ""
    DIM     = "\033[2m"  if USE_COLOR else ""
    RED     = "\033[91m" if USE_COLOR else ""
    GREEN   = "\033[92m" if USE_COLOR else ""
    YELLOW  = "\033[93m" if USE_COLOR else ""
    BLUE    = "\033[94m" if USE_COLOR else ""
    MAGENTA = "\033[95m" if USE_COLOR else ""
    CYAN    = "\033[96m" if USE_COLOR else ""
    WHITE   = "\033[97m" if USE_COLOR else ""

def colored(text, *codes):
    return "".join(codes) + str(text) + C.RESET

def red(t):     return colored(t, C.RED,     C.BOLD)
def green(t):   return colored(t, C.GREEN,   C.BOLD)
def yellow(t):  return colored(t, C.YELLOW,  C.BOLD)
def cyan(t):    return colored(t, C.CYAN,    C.BOLD)
def magenta(t): return colored(t, C.MAGENTA, C.BOLD)
def bold(t):    return colored(t, C.BOLD)
def dim(t):     return colored(t, C.DIM)

# ─────────────────────────────────────────────
#  DISPLAY HELPERS
# ─────────────────────────────────────────────
WIDTH = 70

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def hr(char="─", width=WIDTH):
    print(dim(char * width))

def banner():
    clear()
    print(cyan("╔" + "═" * (WIDTH - 2) + "╗"))
    title = "AttendIQ – Attendance Analytics & Prediction"
    pad   = (WIDTH - 2 - len(title)) // 2
    print(cyan("║") + " " * pad + bold(title) +
          " " * (WIDTH - 2 - pad - len(title)) + cyan("║"))
    print(cyan("╚" + "═" * (WIDTH - 2) + "╝"))

def section_header(title):
    print()
    print(cyan("┌─ ") + bold(title))
    hr("─")

def success(msg): print(green(f"  ✔  {msg}"))
def error(msg):   print(red(  f"  ✘  {msg}"))
def warn(msg):    print(yellow(f"  ⚠  {msg}"))
def info(msg):    print(cyan(  f"  ℹ  {msg}"))

def pct_color(pct):
    if pct is None:  return dim("   N/A")
    if pct >= 85:    return green( f"{pct:6.2f}%")
    if pct >= 75:    return yellow(f"{pct:6.2f}%")
    return red(f"{pct:6.2f}%")

def bar(pct, width=20):
    if pct is None:
        return dim("[" + "?" * width + "]")
    filled = int((pct / 100) * width)
    b = "█" * filled + "░" * (width - filled)
    if pct >= 85:  return green( "[" + b + "]")
    if pct >= 75:  return yellow("[" + b + "]")
    return red("[" + b + "]")

def pause():
    input(dim("\n  Press Enter to continue..."))

def ask(prompt, default=None):
    dflt = f" [{default}]" if default else ""
    val  = input(cyan(f"  > {prompt}{dflt}: ")).strip()
    return val if val else default

def ask_date(prompt, default=None):
    dflt_str = default or date.today().isoformat()
    while True:
        raw = ask(prompt, dflt_str)
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            error("Invalid date. Use YYYY-MM-DD format.")

def pick(options, prompt="Choose"):
    for i, opt in enumerate(options, 1):
        print(f"  {cyan(str(i) + '.')} {opt}")
    while True:
        raw = ask(prompt)
        if raw is None:
            return None
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        error(f"Enter a number between 1 and {len(options)}")

def confirm(msg):
    r = ask(f"{msg} (y/n)", "n")
    return r.lower().startswith("y")

# ─────────────────────────────────────────────
#  DATA MODEL
# ─────────────────────────────────────────────
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendiq_data.json")

class DB:
    """
    Persistent JSON data store.
    Schema:
      students:   [{"id": str, "name": str, "roll": str}]
      subjects:   [{"id": str, "name": str, "code": str}]
      attendance: {
        "YYYY-MM-DD": {
          "<subject_id>": {"<student_id>": "P"|"A"|"M"}
        }
      }
    """
    def __init__(self):
        self.students   = []
        self.subjects   = []
        self.attendance = {}

    # ── load / save ──────────────────────────
    def load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self.students   = raw.get("students",   [])
                self.subjects   = raw.get("subjects",   [])
                self.attendance = raw.get("attendance", {})
                return True
            except Exception:
                return False
        return False

    def save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "students":   self.students,
                "subjects":   self.subjects,
                "attendance": self.attendance,
            }, f, indent=2, ensure_ascii=False)

    # ── uid ──────────────────────────────────
    @staticmethod
    def uid():
        import random, string
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

    # ── student CRUD ─────────────────────────
    def add_student(self, name, roll):
        if any(s["roll"] == roll for s in self.students):
            return None, "Roll number already exists."
        s = {"id": self.uid(), "name": name, "roll": roll}
        self.students.append(s)
        self.save()
        return s, None

    def delete_student(self, sid):
        self.students = [s for s in self.students if s["id"] != sid]
        for day in self.attendance.values():
            for sub in day.values():
                sub.pop(sid, None)
        self.save()

    # ── subject CRUD ─────────────────────────
    def add_subject(self, name, code):
        code = code.upper()
        if any(s["code"] == code for s in self.subjects):
            return None, "Subject code already exists."
        s = {"id": self.uid(), "name": name, "code": code}
        self.subjects.append(s)
        self.save()
        return s, None

    def delete_subject(self, sid):
        self.subjects = [s for s in self.subjects if s["id"] != sid]
        for day in self.attendance.values():
            day.pop(sid, None)
        self.save()

    # ── attendance access ────────────────────
    def mark(self, date_str, subject_id, marks: dict):
        self.attendance.setdefault(date_str, {})
        self.attendance[date_str][subject_id] = marks
        self.save()

    def get_mark(self, date_str, subject_id, student_id):
        return self.attendance.get(date_str, {}).get(subject_id, {}).get(student_id)

    # ── seed demo data ───────────────────────
    def seed_demo(self):
        self.students = [
            {"id": "s1", "name": "Arjun Sharma",  "roll": "CS2101"},
            {"id": "s2", "name": "Priya Nair",    "roll": "CS2102"},
            {"id": "s3", "name": "Rahul Verma",   "roll": "CS2103"},
            {"id": "s4", "name": "Sneha Reddy",   "roll": "CS2104"},
            {"id": "s5", "name": "Vikram Patel",  "roll": "CS2105"},
            {"id": "s6", "name": "Meera Iyer",    "roll": "CS2106"},
        ]
        self.subjects = [
            {"id": "sub1", "name": "Data Structures",   "code": "CS301"},
            {"id": "sub2", "name": "Operating Systems", "code": "CS302"},
            {"id": "sub3", "name": "Database Systems",  "code": "CS303"},
            {"id": "sub4", "name": "Computer Networks", "code": "CS304"},
        ]
        # 24-character attendance strings, one char per class day
        patterns = {
            "s1": "PPPPPAPPPPPPPAPPPPPPPPA",   # good ~92%
            "s2": "PPPPAAAPPAAAAPPAAAAPPAA",    # at risk ~54%
            "s3": "PPPPPPPPPPPPPPPPPPPPPPPP",   # perfect 100%
            "s4": "PAPPPAPAPPPAPAPAPPPAPAAP",   # borderline ~71%
            "s5": "PPPAAAPPAAAAPAAAAAPAAAAA",   # severe ~33%
            "s6": "PPPPPAPPPPAAMMPPPPPPPPPP",   # has medical
        }
        today = date.today()
        day_index = 0
        for week_back in range(3, -1, -1):
            for weekday in range(6):  # Mon–Sat
                offset   = week_back * 7 + (5 - weekday)
                d        = today - timedelta(days=offset)
                date_str = d.isoformat()
                self.attendance[date_str] = {}
                for sub in self.subjects:
                    self.attendance[date_str][sub["id"]] = {}
                    for stu in self.students:
                        p    = patterns[stu["id"]]
                        mark = p[day_index % len(p)]
                        self.attendance[date_str][sub["id"]][stu["id"]] = mark
                day_index += 1
        self.save()


# ─────────────────────────────────────────────
#  BUSINESS LOGIC
# ─────────────────────────────────────────────
class Logic:
    def __init__(self, db: DB):
        self.db = db

    # ── Core Feature 2: attendance % ─────────
    def stats(self, student_id, subject_id):
        """
        Returns dict: total, present, absent, medical, effective, pct
        effective = total - medical  (medical leave excluded from denominator)
        pct       = present / effective * 100  (None if no classes held)
        """
        total = present = absent = medical = 0
        for day, subjects in self.db.attendance.items():
            if subject_id in subjects and student_id in subjects[subject_id]:
                mark = subjects[subject_id][student_id]
                total += 1
                if mark == "P":   present += 1
                elif mark == "A": absent  += 1
                elif mark == "M": medical += 1
        effective = total - medical
        pct = (present / effective * 100) if effective > 0 else None
        return dict(total=total, present=present, absent=absent,
                    medical=medical, effective=effective, pct=pct)

    # ── Core Feature 4: classes needed ───────
    def classes_needed(self, present, effective):
        """
        How many CONSECUTIVE classes must be attended to reach 75%?

        Solve for x:
            (present + x) / (effective + x) >= 0.75
            present + x >= 0.75*effective + 0.75*x
            0.25*x >= 0.75*effective - present
            x >= (0.75*effective - present) / 0.25

        Returns 0 if already >= 75%, positive int otherwise, None if no data.
        """
        if effective == 0:
            return None
        current_pct = present / effective * 100
        if current_pct >= 75:
            return 0
        numerator = (0.75 * effective) - present
        x = numerator / 0.25
        return max(0, int(x) + (1 if x % 1 else 0))   # math.ceil equivalent

    # ── Stretch: trend-based prediction ──────
    def predict(self, student_id, subject_id, future_classes=10):
        """
        Predict attendance % after `future_classes` more classes
        based on the student's rate over the last 14 recorded days.
        Returns (attendance_rate, predicted_pct).
        """
        dates = sorted(self.db.attendance.keys())[-14:]
        rp = rt = 0
        for d in dates:
            mark = self.db.attendance[d].get(subject_id, {}).get(student_id)
            if mark is not None and mark != "M":
                rt += 1
                if mark == "P":
                    rp += 1
        st   = self.stats(student_id, subject_id)
        rate = (rp / rt) if rt > 0 else (st["present"] / st["effective"] if st["effective"] else 0)
        future_present = round(rate * future_classes)
        new_eff  = st["effective"] + future_classes
        new_pres = st["present"]   + future_present
        pred_pct = (new_pres / new_eff * 100) if new_eff > 0 else None
        return rate, pred_pct

    # ── Core Feature 3: at-risk list ─────────
    def at_risk_students(self):
        """Returns all student×subject pairs below 75%."""
        result = []
        for stu in self.db.students:
            for sub in self.db.subjects:
                st = self.stats(stu["id"], sub["id"])
                if st["pct"] is not None and st["pct"] < 75:
                    needed = self.classes_needed(st["present"], st["effective"])
                    result.append(dict(
                        student=stu, subject=sub,
                        pct=st["pct"], present=st["present"],
                        effective=st["effective"], classes_needed=needed
                    ))
        return result

    # ── Stretch: predicted at-risk ────────────
    def predicted_at_risk(self, future_classes=10):
        """Students currently safe but predicted to drop below 75%."""
        result = []
        for stu in self.db.students:
            for sub in self.db.subjects:
                st = self.stats(stu["id"], sub["id"])
                if st["pct"] is None or st["pct"] < 75:
                    continue
                rate, pred = self.predict(stu["id"], sub["id"], future_classes)
                if pred is not None and pred < 75:
                    result.append(dict(
                        student=stu, subject=sub,
                        current_pct=st["pct"], predicted_pct=pred, rate=rate
                    ))
        return result


# ─────────────────────────────────────────────
#  APPLICATION / SCREENS
# ─────────────────────────────────────────────
class App:
    def __init__(self):
        self.db    = DB()
        self.logic = Logic(self.db)

    def run(self):
        if not self.db.load() or (not self.db.students and not self.db.subjects):
            banner()
            warn("No saved data found.")
            if confirm("Load demo data to explore the app?"):
                self.db.seed_demo()
                success("Demo data loaded (6 students, 4 subjects, 4 weeks).")
                pause()
        self.main_menu()

    # ═══════════════════════════════════════
    #  MAIN MENU
    # ═══════════════════════════════════════
    def main_menu(self):
        while True:
            banner()
            self._summary_bar()
            section_header("Main Menu")
            print(f"  {cyan('1.')} Mark Attendance                (Core Feature 1)")
            print(f"  {cyan('2.')} View Attendance %              (Core Feature 2)")
            print(f"  {cyan('3.')} Students Below 75% — At-Risk  (Core Feature 3)")
            print(f"  {cyan('4.')} Classes Needed to Reach 75%   (Core Feature 4)")
            print(f"  {cyan('5.')} Weekly Attendance Report       (Core Feature 5)")
            print(f"  {cyan('6.')} Shortage Prediction            (Stretch Feature)")
            print(f"  {cyan('7.')} Manage Students & Subjects")
            print(f"  {cyan('8.')} Export / Import Data")
            print(f"  {cyan('0.')} Exit")
            hr()
            choice = ask("Select option")
            if   choice == "1": self.screen_mark_attendance()
            elif choice == "2": self.screen_view_attendance()
            elif choice == "3": self.screen_at_risk()
            elif choice == "4": self.screen_classes_needed()
            elif choice == "5": self.screen_weekly_report()
            elif choice == "6": self.screen_prediction()
            elif choice == "7": self.screen_manage()
            elif choice == "8": self.screen_data()
            elif choice == "0":
                print(cyan("\n  Goodbye! Stay punctual. \n"))
                sys.exit(0)
            else:
                error("Invalid choice. Enter 0–8.")

    def _summary_bar(self):
        total     = len(self.db.students)
        risk_ids  = {item["student"]["id"] for item in self.logic.at_risk_students()}
        at_risk   = len(risk_ids)
        safe      = total - at_risk
        subj_cnt  = len(self.db.subjects)
        # count attendance days
        days_held = len(self.db.attendance)
        print(f"\n  Students: {bold(str(total))}   "
              f"Safe: {green(str(safe))}   "
              f"At Risk: {red(str(at_risk))}   "
              f"Subjects: {cyan(str(subj_cnt))}   "
              f"Days Recorded: {dim(str(days_held))}")
        hr("·")

    # ═══════════════════════════════════════
    #  SCREEN 1 — MARK ATTENDANCE
    # ═══════════════════════════════════════
    def screen_mark_attendance(self):
        banner()
        section_header("Mark Attendance — Core Feature 1")

        if not self.db.students:
            error("No students. Add students first (option 7)."); pause(); return
        if not self.db.subjects:
            error("No subjects. Add subjects first (option 7)."); pause(); return

        # Pick date
        att_date = ask_date("Date (YYYY-MM-DD)", date.today().isoformat())
        date_str  = att_date.isoformat()

        # Pick subject
        print()
        info(f"Select subject for {bold(att_date.strftime('%A, %d %b %Y'))}")
        sub_names = [f"{s['name']} ({s['code']})" for s in self.db.subjects]
        chosen    = pick(sub_names, "Subject number")
        if not chosen: return
        subject   = self.db.subjects[sub_names.index(chosen)]

        # Load existing marks for this date+subject
        existing = self.db.attendance.get(date_str, {}).get(subject["id"], {})
        marks    = {}

        banner()
        section_header(
            f"Mark Sheet — {subject['name']} ({subject['code']}) | "
            f"{att_date.strftime('%A, %d %b %Y')}"
        )

        print(f"\n  Mark options:  "
              f"{green('P')} = Present   "
              f"{red('A')} = Absent   "
              f"{yellow('M')} = Medical Leave")
        print(f"  Press Enter to keep the current mark shown in [brackets].")
        hr()
        print(f"  {'#':<4} {'Roll':<10} {'Name':<25}  Mark")
        hr()

        for i, stu in enumerate(self.db.students, 1):
            current = existing.get(stu["id"], "P")
            cur_disp = green("P") if current == "P" else (red("A") if current == "A" else yellow("M"))
            print(f"  {dim(str(i)):<4} {stu['roll']:<10} {stu['name']:<25}  "
                  f"[current: {cur_disp}]")

        print()
        hr()

        for i, stu in enumerate(self.db.students, 1):
            current = existing.get(stu["id"], "P")
            while True:
                raw = ask(f"  [{i:>2}] {stu['name']:<22}", current).upper()
                if raw in ("P", "A", "M"):
                    marks[stu["id"]] = raw
                    break
                error("Enter P (Present), A (Absent), or M (Medical).")

        # Summary before saving
        print()
        p_count = sum(1 for m in marks.values() if m == "P")
        a_count = sum(1 for m in marks.values() if m == "A")
        m_count = sum(1 for m in marks.values() if m == "M")
        hr()
        print(f"  Summary  →  Present: {green(str(p_count))}  "
              f"Absent: {red(str(a_count))}  "
              f"Medical: {yellow(str(m_count))}")
        hr()

        if confirm("Save this attendance?"):
            self.db.mark(date_str, subject["id"], marks)
            success(f"Attendance saved — {subject['name']} on {date_str}.")
        else:
            warn("Attendance NOT saved.")
        pause()

    # ═══════════════════════════════════════
    #  SCREEN 2 — VIEW ATTENDANCE %
    # ═══════════════════════════════════════
    def screen_view_attendance(self):
        banner()
        section_header("Attendance Percentages — Core Feature 2")

        if not self.db.students or not self.db.subjects:
            error("No data. Add students and subjects first."); pause(); return

        print(f"\n  View by:")
        print(f"  {cyan('1.')} All students (summary table)")
        print(f"  {cyan('2.')} Single student (detailed)")
        print(f"  {cyan('3.')} Single subject (all students)")
        choice = ask("Choose view")

        if   choice == "1": self._view_all_summary()
        elif choice == "2": self._view_single_student()
        elif choice == "3": self._view_single_subject()
        else: error("Invalid choice.")
        pause()

    def _view_all_summary(self):
        banner()
        section_header("All Students — Attendance Summary")
        col = 10
        # Header
        hdr = f"  {'#':<3} {'Name':<22} {'Roll':<10}"
        for sub in self.db.subjects:
            hdr += f"  {sub['code']:>{col}}"
        hdr += f"  {'Overall':>{col}}"
        print(hdr)
        hr()

        for i, stu in enumerate(self.db.students, 1):
            row = f"  {i:<3} {stu['name']:<22} {stu['roll']:<10}"
            pcts = []
            for sub in self.db.subjects:
                st = self.logic.stats(stu["id"], sub["id"])
                pcts.append(st["pct"])
                row += f"  {pct_color(st['pct']):>{col}}"
            valid = [p for p in pcts if p is not None]
            avg   = (sum(valid) / len(valid)) if valid else None
            row  += f"  {pct_color(avg):>{col}}"
            print(row)
        hr()
        print(f"\n  Legend:  {green('■')} >=85%  "
              f"{yellow('■')} 75-84% (Safe)  "
              f"{red('■')} <75% (At Risk)  |  Threshold: {bold('75%')}")

    def _view_single_student(self):
        banner()
        section_header("Student Detail")
        names  = [f"{s['name']} ({s['roll']})" for s in self.db.students]
        chosen = pick(names, "Student number")
        if not chosen: return
        stu = self.db.students[names.index(chosen)]

        print(f"\n  Student : {bold(stu['name'])}")
        print(f"  Roll No : {cyan(stu['roll'])}")
        hr()
        print(f"  {'Subject':<28} {'Code':<8} {'P':>5} {'Eff':>5} "
              f"{'Med':>5}  {'%':>8}  {'Bar (20)':22}  Needed to 75%")
        hr()

        for sub in self.db.subjects:
            st     = self.logic.stats(stu["id"], sub["id"])
            needed = self.logic.classes_needed(st["present"], st["effective"])
            if needed is None:   need_s = dim("   N/A")
            elif needed == 0:    need_s = green("  Safe")
            else:                need_s = yellow(f"  +{needed} cls")
            print(f"  {sub['name']:<28} {sub['code']:<8} "
                  f"{st['present']:>5} {st['effective']:>5} {st['medical']:>5}  "
                  f"{pct_color(st['pct']):>8}  {bar(st['pct'])}  {need_s}")
        hr()

    def _view_single_subject(self):
        banner()
        section_header("Subject Detail — All Students")
        sub_names = [f"{s['name']} ({s['code']})" for s in self.db.subjects]
        chosen    = pick(sub_names, "Subject number")
        if not chosen: return
        sub = self.db.subjects[sub_names.index(chosen)]

        print(f"\n  Subject : {bold(sub['name'])}  ({cyan(sub['code'])})")
        hr()
        print(f"  {'#':<3} {'Name':<22} {'Roll':<10} {'P':>5} {'Eff':>5} "
              f"{'Med':>5}  {'%':>8}  {'Bar':22}  Needed")
        hr()

        for i, stu in enumerate(self.db.students, 1):
            st     = self.logic.stats(stu["id"], sub["id"])
            needed = self.logic.classes_needed(st["present"], st["effective"])
            need_s = (green("Safe") if needed == 0 else
                      yellow(f"+{needed}") if needed is not None else dim("-"))
            print(f"  {i:<3} {stu['name']:<22} {stu['roll']:<10} "
                  f"{st['present']:>5} {st['effective']:>5} {st['medical']:>5}  "
                  f"{pct_color(st['pct']):>8}  {bar(st['pct'])}  {need_s}")
        hr()

    # ═══════════════════════════════════════
    #  SCREEN 3 — AT-RISK LIST (<75%)
    # ═══════════════════════════════════════
    def screen_at_risk(self):
        banner()
        section_header("Students Below 75% — Core Feature 3")

        risk = self.logic.at_risk_students()
        if not risk:
            success("No students are below 75% in any subject. Excellent!")
            pause(); return

        # Group by student
        by_student = defaultdict(list)
        for item in risk:
            by_student[item["student"]["id"]].append(item)

        print(f"\n  {red(bold(str(len(by_student)) + ' student(s)'))} "
              f"are below the 75% threshold.\n")
        hr()

        for stu_id, items in by_student.items():
            stu = items[0]["student"]
            print(f"  {bold(stu['name'])}  {dim(stu['roll'])}")
            for item in items:
                sub    = item["subject"]
                needed = item["classes_needed"]
                need_s = (yellow(f"Need +{needed} consecutive classes to recover")
                          if needed and needed > 0 else red("Very critical"))
                print(f"    {red('>>')} {sub['name']:<28} "
                      f"{pct_color(item['pct'])}  {bar(item['pct'], 15)}  {need_s}")
            print()
        hr()
        info("Formula: x >= (0.75 x effective - present) / 0.25")
        pause()

    # ═══════════════════════════════════════
    #  SCREEN 4 — CLASSES NEEDED
    # ═══════════════════════════════════════
    def screen_classes_needed(self):
        banner()
        section_header("Classes Needed to Reach 75% — Core Feature 4")
        info("Formula: x >= (0.75 x effective - present) / 0.25")
        info("Assumes student attends ALL remaining classes consecutively.")
        print()

        if not self.db.students or not self.db.subjects:
            error("No data available."); pause(); return

        col = 11
        # Header
        hdr = f"  {'#':<3} {'Name':<22} {'Roll':<10}"
        for sub in self.db.subjects:
            hdr += f"  {sub['code']:>{col}}"
        print(hdr)
        hr()

        for i, stu in enumerate(self.db.students, 1):
            row = f"  {i:<3} {stu['name']:<22} {stu['roll']:<10}"
            for sub in self.db.subjects:
                st     = self.logic.stats(stu["id"], sub["id"])
                needed = self.logic.classes_needed(st["present"], st["effective"])
                if needed is None:   cell = dim("     N/A")
                elif needed == 0:    cell = green("    Safe")
                else:                cell = yellow(f"  +{needed:>4} cls")
                row += f"  {cell:>{col}}"
            print(row)
        hr()
        print(f"\n  {green('Safe')} = already >=75%   {yellow('+N cls')} = consecutive classes needed   {dim('N/A')} = no data")
        pause()

    # ═══════════════════════════════════════
    #  SCREEN 5 — WEEKLY REPORT
    # ═══════════════════════════════════════
    def screen_weekly_report(self):
        banner()
        section_header("Weekly Attendance Report — Core Feature 5")

        if not self.db.students or not self.db.subjects:
            error("No data available."); pause(); return

        # Pick week start (default: this Monday)
        today  = date.today()
        monday = today - timedelta(days=today.weekday())
        wstart = ask_date("Week start Monday (YYYY-MM-DD)", monday.isoformat())
        days   = [(wstart + timedelta(days=i)) for i in range(7)]

        # Subject filter
        print()
        print(f"  {cyan('0.')} All subjects")
        for i, sub in enumerate(self.db.subjects, 1):
            print(f"  {cyan(str(i) + '.')} {sub['name']} ({sub['code']})")
        sub_choice = ask("Filter subject (0 for all)", "0")
        try:
            sidx = int(sub_choice)
        except ValueError:
            sidx = 0

        subjects = self.db.subjects if sidx == 0 else [self.db.subjects[sidx - 1]]

        banner()
        week_lbl = (f"{wstart.strftime('%d %b %Y')} – "
                    f"{days[-1].strftime('%d %b %Y')}")
        section_header(f"Weekly Report  |  {week_lbl}")

        for sub in subjects:
            print(f"\n  {bold(sub['name'])}  {dim('(' + sub['code'] + ')')}")

            # Day header
            hdr = f"  {'#':<3} {'Name':<22} {'Roll':<10}"
            for d in days:
                hdr += f"  {d.strftime('%a'):>5}"
            hdr += f"  {'Wk%':>7}  {'All%':>7}"
            print(hdr)
            hr()

            for i, stu in enumerate(self.db.students, 1):
                row = f"  {i:<3} {stu['name']:<22} {stu['roll']:<10}"
                wp = wa = 0
                for d in days:
                    mark = self.db.get_mark(d.isoformat(), sub["id"], stu["id"])
                    if   mark == "P": cell = green("  P");  wp += 1
                    elif mark == "A": cell = red("  A");    wa += 1
                    elif mark == "M": cell = yellow("  M")
                    else:             cell = dim("  -")
                    row += f"  {cell:>5}"

                # Weekly %
                we   = wp + wa
                wpct = (wp / we * 100) if we > 0 else None
                # Overall %
                st   = self.logic.stats(stu["id"], sub["id"])
                row += f"  {pct_color(wpct):>7}  {pct_color(st['pct']):>7}"
                print(row)
            hr()

        print(f"\n  {green('P')} Present  {red('A')} Absent  {yellow('M')} Medical  {dim('-')} No class")
        pause()

    # ═══════════════════════════════════════
    #  SCREEN 6 — SHORTAGE PREDICTION
    # ═══════════════════════════════════════
    def screen_prediction(self):
        banner()
        section_header("Shortage Prediction — Stretch Feature")
        info("Predicts future attendance based on rate from last 14 recorded days.")
        print()

        raw = ask("How many future classes to simulate", "10")
        try:
            future = max(1, int(raw))
        except ValueError:
            future = 10

        at_risk_now  = self.logic.at_risk_students()
        at_risk_pred = self.logic.predicted_at_risk(future)

        # Group current at-risk by student
        by_stu_now = defaultdict(list)
        for item in at_risk_now:
            by_stu_now[item["student"]["id"]].append(item)

        print(f"\n  Simulating {bold(str(future))} future classes at current rate.\n")
        hr()

        # ── Already at risk ──
        if by_stu_now:
            print(red(bold(f"  ALREADY BELOW 75%  ({len(by_stu_now)} student(s))")))
            hr()
            for stu_id, items in by_stu_now.items():
                stu = items[0]["student"]
                print(f"  {bold(stu['name'])}  {dim(stu['roll'])}")
                for item in items:
                    sub     = item["subject"]
                    _, pred = self.logic.predict(stu["id"], sub["id"], future)
                    pred_s  = (red(f"-> {pred:.1f}%") if pred and pred < 75 else
                               green(f"-> {pred:.1f}%") if pred else dim("-> N/A"))
                    print(f"    {red('>>')} {sub['name']:<28} "
                          f"Now: {pct_color(item['pct'])}  After {future} cls: {pred_s}")
                print()
        else:
            success("No students currently below 75%.")
            print()

        hr()
        # ── Predicted to drop ──
        if at_risk_pred:
            print(yellow(bold(f"  PREDICTED TO FALL BELOW 75%  ({len(at_risk_pred)} case(s))")))
            hr()
            for item in at_risk_pred:
                stu = item["student"]
                sub = item["subject"]
                rate_pct = item["rate"] * 100
                print(f"  {bold(stu['name'])}  {dim(stu['roll'])}")
                pred_str = f"{item['predicted_pct']:.1f}%"
                rate_str = f"{rate_pct:.0f}% attendance/class"
                print(f"    {yellow('>>')} {sub['name']:<28} "
                      f"Now: {pct_color(item['current_pct'])}  "
                      f"Predicted: {red(pred_str)}  "
                      f"Rate: {dim(rate_str)}")
            print()
        else:
            success(f"No currently-safe students predicted to drop in next {future} classes.")

        hr()
        pause()

    # ═══════════════════════════════════════
    #  SCREEN 7 — MANAGE STUDENTS & SUBJECTS
    # ═══════════════════════════════════════
    def screen_manage(self):
        while True:
            banner()
            section_header("Manage Students & Subjects")
            print(f"  {cyan('1.')} Students")
            print(f"  {cyan('2.')} Subjects")
            print(f"  {cyan('0.')} Back")
            choice = ask("Choose")
            if   choice == "1": self._manage_students()
            elif choice == "2": self._manage_subjects()
            elif choice == "0": break
            else: error("Invalid choice.")

    def _manage_students(self):
        while True:
            banner()
            section_header("Students")
            if self.db.students:
                print(f"\n  {'#':<3} {'Name':<25} {'Roll':<12} {'ID'}")
                hr()
                for i, s in enumerate(self.db.students, 1):
                    print(f"  {i:<3} {s['name']:<25} {s['roll']:<12} {dim(s['id'])}")
                hr()
            else:
                warn("No students yet.")

            print(f"\n  {cyan('A.')} Add   {cyan('D.')} Delete   {cyan('0.')} Back")
            choice = ask("Action").upper()

            if choice == "A":
                name = ask("Full name")
                roll = ask("Roll number")
                if name and roll:
                    _, err = self.db.add_student(name, roll)
                    if err: error(err)
                    else:   success(f"{name} added successfully.")
                else:
                    error("Both name and roll number are required.")
                pause()
            elif choice == "D":
                if not self.db.students:
                    error("No students to delete."); pause(); continue
                raw = ask("Student # to delete")
                try:
                    idx = int(raw) - 1
                    stu = self.db.students[idx]
                    if confirm(f"Delete {stu['name']}? All their records will be removed."):
                        self.db.delete_student(stu["id"])
                        success(f"{stu['name']} deleted.")
                except (ValueError, IndexError):
                    error("Invalid number.")
                pause()
            elif choice == "0":
                break

    def _manage_subjects(self):
        while True:
            banner()
            section_header("Subjects")
            if self.db.subjects:
                print(f"\n  {'#':<3} {'Name':<30} {'Code':<10} {'ID'}")
                hr()
                for i, s in enumerate(self.db.subjects, 1):
                    print(f"  {i:<3} {s['name']:<30} {s['code']:<10} {dim(s['id'])}")
                hr()
            else:
                warn("No subjects yet.")

            print(f"\n  {cyan('A.')} Add   {cyan('D.')} Delete   {cyan('0.')} Back")
            choice = ask("Action").upper()

            if choice == "A":
                name = ask("Subject name")
                code = ask("Subject code (e.g. CS301)")
                if name and code:
                    _, err = self.db.add_subject(name, code)
                    if err: error(err)
                    else:   success(f"{name} added successfully.")
                else:
                    error("Name and code are required.")
                pause()
            elif choice == "D":
                if not self.db.subjects:
                    error("No subjects to delete."); pause(); continue
                raw = ask("Subject # to delete")
                try:
                    idx = int(raw) - 1
                    sub = self.db.subjects[idx]
                    if confirm(f"Delete {sub['name']}? All its attendance records will be removed."):
                        self.db.delete_subject(sub["id"])
                        success(f"{sub['name']} deleted.")
                except (ValueError, IndexError):
                    error("Invalid number.")
                pause()
            elif choice == "0":
                break

    # ═══════════════════════════════════════
    #  SCREEN 8 — EXPORT / IMPORT
    # ═══════════════════════════════════════
    def screen_data(self):
        banner()
        section_header("Export / Import Data")
        print(f"  Current data file: {cyan(DATA_FILE)}")
        print()
        print(f"  {cyan('1.')} Export to JSON")
        print(f"  {cyan('2.')} Import from JSON")
        print(f"  {cyan('3.')} Reload demo data (overwrites current)")
        print(f"  {cyan('4.')} Clear ALL data")
        print(f"  {cyan('0.')} Back")
        choice = ask("Choose")

        if choice == "1":
            path = ask("Export file path", DATA_FILE.replace(".json", "_backup.json"))
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"students": self.db.students,
                               "subjects": self.db.subjects,
                               "attendance": self.db.attendance}, f, indent=2)
                success(f"Exported to: {path}")
            except Exception as e:
                error(f"Export failed: {e}")
            pause()

        elif choice == "2":
            path = ask("Import file path")
            if not path or not os.path.exists(path):
                error("File not found.")
            else:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    if "students" not in raw or "subjects" not in raw:
                        raise ValueError("Missing required keys.")
                    self.db.students   = raw["students"]
                    self.db.subjects   = raw["subjects"]
                    self.db.attendance = raw.get("attendance", {})
                    self.db.save()
                    success(f"Imported {len(self.db.students)} students, "
                            f"{len(self.db.subjects)} subjects.")
                except Exception as e:
                    error(f"Import failed: {e}")
            pause()

        elif choice == "3":
            if confirm("Overwrite ALL current data with demo data?"):
                self.db.students   = []
                self.db.subjects   = []
                self.db.attendance = {}
                self.db.seed_demo()
                success("Demo data loaded.")
            pause()

        elif choice == "4":
            if confirm("Permanently CLEAR all students, subjects, and attendance?"):
                self.db.students   = []
                self.db.subjects   = []
                self.db.attendance = {}
                self.db.save()
                success("All data cleared.")
            pause()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        App().run()
    except KeyboardInterrupt:
        print(cyan("\n\n  Interrupted. Goodbye!\n"))
        sys.exit(0)
