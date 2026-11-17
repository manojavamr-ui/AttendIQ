# AttendIQ – Implementation Plan

## Overview
A single-page web application for attendance analytics and shortage prediction. Built with HTML, CSS (Vanilla), and JavaScript. All data stored in localStorage for persistence.

## Features

### Core Features
1. **Record daily attendance** – Mark Present/Absent/Medical Leave per subject per student per date
2. **Calculate attendance %** – Per student, per subject, in real-time
3. **Below 75% list** – Color-coded alert dashboard
4. **Classes needed to reach 75%** – Computed projection shown per student
5. **Weekly report** – Tabular report for any chosen week

### Stretch Features
- Medical leave days that don't count against the student
- Prediction: students trending below 75% based on current attendance rate

## Pages / Sections
- **Dashboard** – Summary cards, at-risk students
- **Mark Attendance** – Date picker + subject picker, mark each student
- **Student View** – Per-student detailed breakdown
- **Reports** – Weekly attendance table + PDF/print option
- **Settings** – Add/remove subjects, students

## Tech Stack
- HTML5 + Vanilla CSS (glassmorphism dark theme)
- Vanilla JavaScript (ES6+)
- Chart.js (CDN) for attendance trend charts
- localStorage for persistence
- Google Fonts: Inter

## Color Palette
- Background: #0f0f1a (deep navy)
- Accent: #6c63ff (violet)
- Danger: #ff4f6a (red-pink)
- Warning: #ffb347 (amber)
- Success: #4ade80 (green)
- Glass: rgba(255,255,255,0.05)
