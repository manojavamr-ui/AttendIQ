# AttendIQ — Attendance Analytics & Shortage Prediction System
**CP-032 | Level: Foundation | Domain: Education & Campus**

A fully-featured, colorful **Python CLI application** that helps students and
faculty track attendance, detect shortages early, and predict future trends.

---

## How to Run

```bash
python attendiq.py
```

> **Requirements:** Python 3.8+  &nbsp;|&nbsp; No third-party packages needed (stdlib only)

The app will ask if you want to load **demo data** on first launch (6 students,
4 subjects, 4 weeks of attendance).

---

## Project Structure

```
attendiq_python/
├── attendiq.py        # Complete single-file application (~1000 lines)
└── attendiq_data.json # Auto-created on first save (all data stored here)
```

---

## Features

### Core Features (All 5 Compulsory)

| # | Feature | Menu Option |
|---|---------|-------------|
| 1 | Record daily attendance per subject (P / A / M) | Option 1 |
| 2 | Calculate attendance % per student per subject | Option 2 |
| 3 | List students below 75% in any subject | Option 3 |
| 4 | Calculate consecutive classes needed to reach 75% | Option 4 |
| 5 | Weekly attendance report (Mon–Sun, any week) | Option 5 |

### Stretch Features

| Feature | Detail |
|---------|--------|
| **Medical Leave** | Mark `M` — excluded from denominator, doesn't penalise student |
| **Shortage Prediction** | Trend-based: uses last-14-day rate to project future % | Option 6 |
| **Export / Import** | Save and load data as JSON | Option 8 |

---

## Formula Details

### Attendance Percentage
```
effective = total_classes - medical_leave_days
percentage = (present / effective) × 100
```

### Classes Needed to Reach 75%
Solve for x (consecutive classes to attend):
```
(present + x) / (effective + x) >= 0.75
=> x >= (0.75 × effective − present) / 0.25
```

### Prediction (Stretch)
```
rate        = classes_attended / total_classes  (last 14 days)
future_pct  = (present + rate × future_N) / (effective + future_N) × 100
```

---

## Data Storage

All data is saved in `attendiq_data.json` in the same folder.
JSON structure:
```json
{
  "students":   [{"id": "...", "name": "...", "roll": "..."}],
  "subjects":   [{"id": "...", "name": "...", "code": "..."}],
  "attendance": {
    "YYYY-MM-DD": {
      "<subject_id>": {"<student_id>": "P|A|M"}
    }
  }
}
```

---

## Interview Talking Points

- **Percentage calculations** — medical-aware denominator
- **Simple projection** — rate-based trend over 14 days
- **Filtering by condition** — `at_risk_students()` and `predicted_at_risk()`
- **Data persistence** — JSON file, no DB needed
- **OOP design** — `DB` (storage), `Logic` (calculations), `App` (UI) classes
