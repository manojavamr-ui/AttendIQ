/**
 * AttendIQ – app.js
 * Attendance Analytics & Shortage Prediction System
 *
 * Data model (stored in localStorage as "attendiq"):
 * {
 *   students: [{ id, name, roll }],
 *   subjects: [{ id, name, code }],
 *   attendance: {
 *     "YYYY-MM-DD": {
 *       "<subjectId>": { "<studentId>": "P"|"A"|"M" }
 *     }
 *   }
 * }
 */

/* =============================================
   STATE
   ============================================= */
let db = {
  students: [],
  subjects: [],
  attendance: {}
};

let subjectChartInst = null;
let studentRadarInst = null;

/* =============================================
   PERSISTENCE
   ============================================= */
function saveDB() {
  localStorage.setItem('attendiq', JSON.stringify(db));
}

function loadDB() {
  try {
    const raw = localStorage.getItem('attendiq');
    if (raw) db = JSON.parse(raw);
  } catch (_) {
    db = { students: [], subjects: [], attendance: {} };
  }
  // Seed demo data if empty
  if (!db.students.length && !db.subjects.length) seedDemo();
}

function seedDemo() {
  db.students = [
    { id: 's1', name: 'Arjun Sharma',  roll: 'CS2101' },
    { id: 's2', name: 'Priya Nair',    roll: 'CS2102' },
    { id: 's3', name: 'Rahul Verma',   roll: 'CS2103' },
    { id: 's4', name: 'Sneha Reddy',   roll: 'CS2104' },
    { id: 's5', name: 'Vikram Patel',  roll: 'CS2105' },
    { id: 's6', name: 'Meera Iyer',    roll: 'CS2106' },
  ];
  db.subjects = [
    { id: 'sub1', name: 'Data Structures',    code: 'CS301' },
    { id: 'sub2', name: 'Operating Systems',  code: 'CS302' },
    { id: 'sub3', name: 'Database Systems',   code: 'CS303' },
    { id: 'sub4', name: 'Computer Networks',  code: 'CS304' },
  ];

  // Generate 4 weeks of attendance data (Mon–Sat)
  const today = new Date();
  today.setHours(0,0,0,0);
  const patterns = {
    s1: [1,1,1,1,1,0,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,0,1],
    s2: [1,1,1,1,0,0,1,1,1,0,0,0,1,1,0,0,0,0,1,1,0,0,0,0],  // at risk
    s3: [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    s4: [1,0,1,1,1,0,1,0,1,1,1,0,1,0,1,0,1,1,1,0,1,0,1,0],  // borderline
    s5: [1,1,1,0,0,0,1,1,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0],  // severe
    s6: [1,1,1,1,1,0,1,1,1,1,0,0,'M','M',1,1,1,1,1,1,1,1,1,1], // medical
  };

  let dayIndex = 0;
  for (let w = 3; w >= 0; w--) {
    for (let d = 0; d < 6; d++) { // Mon-Sat
      const dt = new Date(today);
      dt.setDate(today.getDate() - (w * 7 + (5 - d)));
      const dateStr = dt.toISOString().slice(0, 10);
      db.attendance[dateStr] = {};
      db.subjects.forEach(sub => {
        db.attendance[dateStr][sub.id] = {};
        db.students.forEach(stu => {
          const p = patterns[stu.id];
          const val = p[dayIndex % p.length];
          db.attendance[dateStr][sub.id][stu.id] = val === 'M' ? 'M' : val ? 'P' : 'A';
        });
      });
      dayIndex++;
    }
  }
  saveDB();
}

/* =============================================
   HELPERS
   ============================================= */
function uid() {
  return '_' + Math.random().toString(36).slice(2, 9);
}

function avatarClass(index) {
  return 'avatar-' + (index % 8);
}

function initials(name) {
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

/** Returns attendance stats for a student in a subject */
function getStats(studentId, subjectId) {
  let total = 0, present = 0, medical = 0;
  Object.values(db.attendance).forEach(dayData => {
    if (dayData[subjectId]) {
      const mark = dayData[subjectId][studentId];
      if (mark !== undefined) {
        total++;
        if (mark === 'P') present++;
        if (mark === 'M') medical++;
      }
    }
  });
  // Medical leaves don't count in total
  const effective = total - medical;
  const pct = effective > 0 ? (present / effective) * 100 : null;
  return { total, present, medical, effective, pct };
}

/** How many consecutive classes must a student attend to reach 75%? */
function classesNeeded(present, effective) {
  if (effective === 0) return null;
  const pct = present / effective;
  if (pct >= 0.75) return 0;
  // (present + x) / (effective + x) >= 0.75
  // present + x >= 0.75 * effective + 0.75 * x
  // 0.25 * x >= 0.75 * effective - present
  // x >= (0.75 * effective - present) / 0.25
  const needed = Math.ceil((0.75 * effective - present) / 0.25);
  return Math.max(0, needed);
}

/** Predict future attendance based on recent trend (last 2 weeks) */
function predictPct(studentId, subjectId, futureClasses = 10) {
  const dates = Object.keys(db.attendance).sort();
  const recent = dates.slice(-14);
  let rPresent = 0, rTotal = 0;
  recent.forEach(d => {
    const mark = db.attendance[d]?.[subjectId]?.[studentId];
    if (mark !== undefined) {
      if (mark !== 'M') rTotal++;
      if (mark === 'P') rPresent++;
    }
  });
  const { present, effective } = getStats(studentId, subjectId);
  const rate = rTotal > 0 ? rPresent / rTotal : (present / (effective || 1));
  const futurePres = Math.round(rate * futureClasses);
  const newPct = effective + futureClasses > 0
    ? ((present + futurePres) / (effective + futureClasses)) * 100
    : null;
  return { rate, predictedPct: newPct };
}

function pctClass(pct) {
  if (pct === null) return '';
  if (pct >= 85) return 'pct-ok';
  if (pct >= 75) return 'pct-warn';
  return 'pct-bad';
}

function barClass(pct) {
  if (pct === null) return '';
  if (pct >= 85) return 'bar-ok';
  if (pct >= 75) return 'bar-warn';
  return 'bar-bad';
}

function formatDate(str) {
  const d = new Date(str + 'T00:00:00');
  return d.toLocaleDateString('en-IN', { weekday:'short', day:'2-digit', month:'short', year:'numeric' });
}

function getMonday(date) {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  d.setDate(diff);
  return d;
}

/* =============================================
   NAVIGATION
   ============================================= */
function navigate(sectionId) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('section-' + sectionId).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(b => {
    b.classList.toggle('active', b.dataset.section === sectionId);
  });
  // Close sidebar on mobile
  if (window.innerWidth < 900) {
    document.getElementById('sidebar').classList.remove('open');
  }

  if (sectionId === 'dashboard') renderDashboard();
  if (sectionId === 'students')  renderStudents();
  if (sectionId === 'mark')      initMarkSection();
  if (sectionId === 'report')    initReportSection();
  if (sectionId === 'settings')  renderSettings();
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

/* =============================================
   DASHBOARD
   ============================================= */
function renderDashboard() {
  // Header date
  document.getElementById('headerDate').textContent =
    new Date().toLocaleDateString('en-IN', { weekday:'long', day:'2-digit', month:'long', year:'numeric' });

  // Summary cards
  document.getElementById('totalStudents').textContent = db.students.length;

  // Calculate at-risk + avg
  let atRiskSet = new Set();
  let totalPct = 0, pctCount = 0;
  let totalClassesHeld = 0;

  db.subjects.forEach(sub => {
    const dates = Object.keys(db.attendance).filter(d => db.attendance[d][sub.id]);
    totalClassesHeld = Math.max(totalClassesHeld, dates.length);
    db.students.forEach(stu => {
      const stats = getStats(stu.id, sub.id);
      if (stats.pct !== null) {
        totalPct += stats.pct;
        pctCount++;
        if (stats.pct < 75) atRiskSet.add(stu.id);
      }
    });
  });

  document.getElementById('atRiskCount').textContent   = atRiskSet.size;
  document.getElementById('totalClasses').textContent  = totalClassesHeld;
  document.getElementById('avgAttendance').textContent = pctCount > 0
    ? Math.round(totalPct / pctCount) + '%' : '—';

  // At-risk list
  const atRiskEl = document.getElementById('atRiskList');
  document.getElementById('atRiskBadge').textContent = atRiskSet.size;
  if (atRiskSet.size === 0) {
    atRiskEl.innerHTML = `<div class="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
      <p>All students are above 75% — Great job! 🎉</p></div>`;
  } else {
    atRiskEl.innerHTML = [...atRiskSet].map(sid => {
      const stu = db.students.find(s => s.id === sid);
      if (!stu) return '';
      const idx = db.students.indexOf(stu);
      const badSubjects = db.subjects.filter(sub => {
        const stats = getStats(sid, sub.id);
        return stats.pct !== null && stats.pct < 75;
      });
      const pillsHtml = badSubjects.map(sub => {
        const stats = getStats(sid, sub.id);
        const needed = classesNeeded(stats.present, stats.effective);
        return `<span class="subject-pill danger">${sub.code}: ${stats.pct.toFixed(1)}%</span>`;
      }).join('');
      const worstStats = (() => {
        let worst = null, worstSub = null;
        db.subjects.forEach(sub => {
          const st = getStats(sid, sub.id);
          if (st.pct !== null && (worst === null || st.pct < worst.pct)) {
            worst = st; worstSub = sub;
          }
        });
        return { worst, worstSub };
      })();
      const needed = worstStats.worst
        ? classesNeeded(worstStats.worst.present, worstStats.worst.effective) : 0;
      return `<div class="at-risk-item">
        <div class="at-risk-avatar ${avatarClass(idx)}">${initials(stu.name)}</div>
        <div class="at-risk-info">
          <div class="at-risk-name">${stu.name}</div>
          <div class="at-risk-roll">${stu.roll}</div>
          <div class="at-risk-subjects" style="margin-top:0.4rem">${pillsHtml}</div>
        </div>
        <div class="at-risk-classes">
          ${needed > 0
            ? `<span style="color:var(--amber)">Need ${needed} more<br>consecutive</span>`
            : '<span style="color:var(--red)">Critical</span>'}
        </div>
      </div>`;
    }).join('');
  }

  // Prediction list
  const predEl = document.getElementById('predictionList');
  const predStudents = [];
  db.students.forEach((stu, idx) => {
    if (atRiskSet.has(stu.id)) return; // already at risk
    const warnings = [];
    db.subjects.forEach(sub => {
      const stats = getStats(stu.id, sub.id);
      if (stats.pct === null) return;
      const { predictedPct } = predictPct(stu.id, sub.id);
      if (predictedPct !== null && predictedPct < 75 && stats.pct >= 75) {
        warnings.push({ sub, currentPct: stats.pct, predictedPct });
      }
    });
    if (warnings.length > 0) predStudents.push({ stu, idx, warnings });
  });

  document.getElementById('predBadge').textContent = predStudents.length;
  if (predStudents.length === 0) {
    predEl.innerHTML = `<div class="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      <p>No students predicted to fall below 75%</p></div>`;
  } else {
    predEl.innerHTML = predStudents.map(({ stu, idx, warnings }) => {
      const pillsHtml = warnings.map(w =>
        `<span class="subject-pill warning">${w.sub.code}: ${w.currentPct.toFixed(1)}% → ${w.predictedPct.toFixed(1)}%</span>`
      ).join('');
      return `<div class="at-risk-item">
        <div class="at-risk-avatar ${avatarClass(idx)}">${initials(stu.name)}</div>
        <div class="at-risk-info">
          <div class="at-risk-name">${stu.name}</div>
          <div class="at-risk-roll">${stu.roll}</div>
          <div class="at-risk-subjects" style="margin-top:0.4rem">${pillsHtml}</div>
        </div>
        <div class="at-risk-classes"><span style="color:var(--amber)">⚠ Trending down</span></div>
      </div>`;
    }).join('');
  }

  // Subject chart
  renderSubjectChart();
}

function renderSubjectChart() {
  const ctx = document.getElementById('subjectChart').getContext('2d');
  const labels = db.subjects.map(s => s.code);
  const data = db.subjects.map(sub => {
    let total = 0, count = 0;
    db.students.forEach(stu => {
      const stats = getStats(stu.id, sub.id);
      if (stats.pct !== null) { total += stats.pct; count++; }
    });
    return count > 0 ? Math.round(total / count) : 0;
  });

  if (subjectChartInst) subjectChartInst.destroy();

  subjectChartInst = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Avg Attendance %',
        data,
        backgroundColor: data.map(v =>
          v >= 85 ? 'rgba(34,197,94,0.6)' :
          v >= 75 ? 'rgba(245,158,11,0.6)' :
                   'rgba(255,79,106,0.6)'
        ),
        borderColor: data.map(v =>
          v >= 85 ? '#22c55e' : v >= 75 ? '#f59e0b' : '#ff4f6a'
        ),
        borderWidth: 2,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.raw}% average attendance`
          }
        }
      },
      scales: {
        y: {
          min: 0, max: 100,
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: {
            color: '#94a3b8',
            callback: v => v + '%'
          }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#94a3b8' }
        }
      }
    }
  });
}

/* =============================================
   MARK ATTENDANCE
   ============================================= */
function initMarkSection() {
  const dateEl = document.getElementById('markDate');
  if (!dateEl.value) {
    dateEl.value = new Date().toISOString().slice(0, 10);
  }
  populateSubjectDropdown('markSubject');
}

function populateSubjectDropdown(id) {
  const el = document.getElementById(id);
  const current = el.value;
  el.innerHTML = '<option value="">Select subject…</option>';
  db.subjects.forEach(sub => {
    el.innerHTML += `<option value="${sub.id}">${sub.name} (${sub.code})</option>`;
  });
  if (current) el.value = current;
}

let currentMarkState = {}; // studentId -> 'P'|'A'|'M'

function loadMarkSheet() {
  const date = document.getElementById('markDate').value;
  const subjectId = document.getElementById('markSubject').value;
  if (!date || !subjectId) { showToast('Please select date and subject', 'error'); return; }
  if (db.students.length === 0) { showToast('No students added yet. Go to Settings.', 'error'); return; }

  const sub = db.subjects.find(s => s.id === subjectId);
  document.getElementById('markSheetTitle').textContent =
    `${sub.name} — ${formatDate(date)}`;
  document.getElementById('markSheetPanel').style.display = '';

  // Load existing marks
  currentMarkState = {};
  const existing = db.attendance[date]?.[subjectId] || {};
  db.students.forEach(stu => {
    currentMarkState[stu.id] = existing[stu.id] || 'P';
  });

  renderMarkSheet();
}

function renderMarkSheet() {
  const container = document.getElementById('markSheetBody');
  container.innerHTML = db.students.map((stu, idx) => {
    const mark = currentMarkState[stu.id] || 'P';
    return `<div class="student-mark-row" id="smr-${stu.id}">
      <span class="smr-num">${idx + 1}</span>
      <div class="smr-avatar ${avatarClass(idx)}">${initials(stu.name)}</div>
      <div class="smr-info">
        <div class="smr-name">${stu.name}</div>
        <div class="smr-roll">${stu.roll}</div>
      </div>
      <div class="smr-controls">
        <div class="smr-btn-group">
          <button class="mark-btn mark-btn-p ${mark==='P'?'selected':''}"
            onclick="setMark('${stu.id}','P')" title="Present">P</button>
          <span class="mark-btn-label">Present</span>
        </div>
        <div class="smr-btn-group">
          <button class="mark-btn mark-btn-a ${mark==='A'?'selected':''}"
            onclick="setMark('${stu.id}','A')" title="Absent">A</button>
          <span class="mark-btn-label">Absent</span>
        </div>
        <div class="smr-btn-group">
          <button class="mark-btn mark-btn-m ${mark==='M'?'selected':''}"
            onclick="setMark('${stu.id}','M')" title="Medical Leave">M</button>
          <span class="mark-btn-label">Medical</span>
        </div>
      </div>
    </div>`;
  }).join('');
}

function setMark(studentId, mark) {
  currentMarkState[studentId] = mark;
  // Update button states without full re-render
  const row = document.getElementById('smr-' + studentId);
  row.querySelectorAll('.mark-btn').forEach(btn => btn.classList.remove('selected'));
  const cls = mark === 'P' ? '.mark-btn-p' : mark === 'A' ? '.mark-btn-a' : '.mark-btn-m';
  row.querySelector(cls).classList.add('selected');
}

function markAll(mark) {
  db.students.forEach(stu => { currentMarkState[stu.id] = mark; });
  renderMarkSheet();
}

function saveAttendance() {
  const date = document.getElementById('markDate').value;
  const subjectId = document.getElementById('markSubject').value;
  if (!date || !subjectId) return;

  if (!db.attendance[date]) db.attendance[date] = {};
  db.attendance[date][subjectId] = { ...currentMarkState };
  saveDB();
  showToast('Attendance saved successfully!', 'success');
}

/* =============================================
   STUDENTS
   ============================================= */
function renderStudents() {
  const query = (document.getElementById('studentSearch')?.value || '').toLowerCase();
  const grid = document.getElementById('studentsGrid');

  const filtered = db.students.filter(s =>
    s.name.toLowerCase().includes(query) || s.roll.toLowerCase().includes(query)
  );

  if (filtered.length === 0) {
    grid.innerHTML = `<div class="no-data-msg">No students found</div>`;
    return;
  }

  grid.innerHTML = filtered.map((stu, fi) => {
    const idx = db.students.indexOf(stu);
    let isAtRisk = false;
    const subRows = db.subjects.map(sub => {
      const stats = getStats(stu.id, sub.id);
      const pct = stats.pct;
      if (pct !== null && pct < 75) isAtRisk = true;
      const pctStr = pct !== null ? pct.toFixed(1) + '%' : '—';
      const barW   = pct !== null ? pct : 0;
      const bCls   = barClass(pct);
      return `<div class="sc-subject-row">
        <span class="sc-subject-name" title="${sub.name}">${sub.code}</span>
        <div class="sc-bar-wrap"><div class="sc-bar ${bCls}" style="width:${barW}%"></div></div>
        <span class="sc-pct ${pctClass(pct)}">${pctStr}</span>
      </div>`;
    }).join('');

    // overall average
    let avgTotal = 0, avgCount = 0;
    db.subjects.forEach(sub => {
      const st = getStats(stu.id, sub.id);
      if (st.pct !== null) { avgTotal += st.pct; avgCount++; }
    });
    const avgPct = avgCount > 0 ? avgTotal / avgCount : null;
    const statusCls = avgPct === null ? '' : avgPct >= 85 ? 'ok' : avgPct >= 75 ? 'warn' : 'bad';
    const statusTxt = avgPct === null ? 'No data'
      : avgPct >= 85 ? '✓ Good Standing'
      : avgPct >= 75 ? '⚠ Borderline'
      : '✗ At Risk';

    return `<div class="student-card${isAtRisk ? ' at-risk' : ''}" onclick="openStudentModal('${stu.id}')">
      <div class="sc-header">
        <div class="sc-avatar ${avatarClass(idx)}">${initials(stu.name)}</div>
        <div>
          <div class="sc-name">${stu.name}</div>
          <div class="sc-roll">${stu.roll}</div>
        </div>
      </div>
      <div class="sc-subjects">${subRows}</div>
      ${avgPct !== null ? `<div class="sc-status ${statusCls}">${statusTxt} (${avgPct.toFixed(1)}%)</div>` : ''}
    </div>`;
  }).join('');
}

function openStudentModal(studentId) {
  const stu = db.students.find(s => s.id === studentId);
  if (!stu) return;
  const idx = db.students.indexOf(stu);

  document.getElementById('modalStudentName').textContent = stu.name;
  document.getElementById('modalStudentRoll').textContent = `Roll No: ${stu.roll}`;

  // Build subject table
  const rows = db.subjects.map(sub => {
    const stats = getStats(stu.id, sub.id);
    const pct = stats.pct;
    const needed = pct !== null && pct < 75
      ? classesNeeded(stats.present, stats.effective) : 0;
    const pctStr = pct !== null ? pct.toFixed(2) + '%' : '—';
    const { predictedPct } = predictPct(stu.id, sub.id);

    return `<tr>
      <td>${sub.name}</td>
      <td>${sub.code}</td>
      <td>${stats.present}</td>
      <td>${stats.effective}</td>
      <td>${stats.medical}</td>
      <td class="pct-cell ${pctClass(pct)}">${pctStr}</td>
      <td class="pct-cell ${pctClass(predictedPct)}">${predictedPct !== null ? predictedPct.toFixed(1) + '%' : '—'}</td>
      <td class="classes-needed-cell">${pct !== null && pct < 75 && needed > 0 ? `+${needed} classes` : pct !== null && pct >= 75 ? '✓ Safe' : '—'}</td>
    </tr>`;
  }).join('');

  document.getElementById('modalSubjectTable').innerHTML = `
    <table class="modal-subject-table">
      <thead>
        <tr>
          <th>Subject</th><th>Code</th><th>Present</th><th>Effective</th><th>Medical</th>
          <th>Current %</th><th>Predicted %</th><th>To Reach 75%</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;

  // Radar chart
  const radarCtx = document.getElementById('studentRadarChart').getContext('2d');
  if (studentRadarInst) studentRadarInst.destroy();

  const radarData = db.subjects.map(sub => {
    const st = getStats(stu.id, sub.id);
    return st.pct !== null ? Math.round(st.pct) : 0;
  });

  studentRadarInst = new Chart(radarCtx, {
    type: 'radar',
    data: {
      labels: db.subjects.map(s => s.code),
      datasets: [{
        label: 'Attendance %',
        data: radarData,
        backgroundColor: 'rgba(108,99,255,0.2)',
        borderColor: '#6c63ff',
        borderWidth: 2,
        pointBackgroundColor: '#6c63ff',
        pointRadius: 4,
      }, {
        label: '75% Threshold',
        data: db.subjects.map(() => 75),
        backgroundColor: 'rgba(255,79,106,0.05)',
        borderColor: 'rgba(255,79,106,0.6)',
        borderWidth: 1.5,
        borderDash: [5, 5],
        pointRadius: 0,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#94a3b8', boxWidth: 12 } } },
      scales: {
        r: {
          min: 0, max: 100,
          ticks: { display: false },
          grid: { color: 'rgba(255,255,255,0.1)' },
          angleLines: { color: 'rgba(255,255,255,0.1)' },
          pointLabels: { color: '#e2e8f0', font: { size: 12 } }
        }
      }
    }
  });

  document.getElementById('studentModal').style.display = 'flex';
}

function closeStudentModal(e) {
  if (!e || e.target.id === 'studentModal') {
    document.getElementById('studentModal').style.display = 'none';
  }
}

/* =============================================
   WEEKLY REPORT
   ============================================= */
function initReportSection() {
  const el = document.getElementById('reportWeekStart');
  if (!el.value) {
    const mon = getMonday(new Date());
    el.value = mon.toISOString().slice(0, 10);
  }

  // Populate subject filter
  const sf = document.getElementById('reportSubjectFilter');
  sf.innerHTML = '<option value="all">All Subjects</option>';
  db.subjects.forEach(sub => {
    sf.innerHTML += `<option value="${sub.id}">${sub.name}</option>`;
  });

  renderWeeklyReport();
}

function renderWeeklyReport() {
  const weekStart = document.getElementById('reportWeekStart').value;
  const subFilter = document.getElementById('reportSubjectFilter').value;

  if (!weekStart) return;

  const mon = new Date(weekStart + 'T00:00:00');
  // Week: Mon to Sun (7 days)
  const days = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(mon);
    d.setDate(mon.getDate() + i);
    days.push(d.toISOString().slice(0, 10));
  }

  const subjects = subFilter === 'all' ? db.subjects : db.subjects.filter(s => s.id === subFilter);

  document.getElementById('printWeekLabel').textContent =
    `Week: ${formatDate(days[0])} – ${formatDate(days[6])}`;

  const tableContainer = document.getElementById('weeklyReportTable');

  if (db.students.length === 0 || subjects.length === 0) {
    tableContainer.innerHTML = '<div class="no-data-msg">No data to display. Add students and subjects in Settings.</div>';
    return;
  }

  let html = '';
  subjects.forEach(sub => {
    const dayHeaders = days.map(d => {
      const dt = new Date(d + 'T00:00:00');
      return `<th class="day-col">${dt.toLocaleDateString('en-IN',{weekday:'short'})}<br>${dt.getDate()}</th>`;
    }).join('');

    const rows = db.students.map((stu, idx) => {
      const cells = days.map(d => {
        const mark = db.attendance[d]?.[sub.id]?.[stu.id];
        if (mark === 'P') return `<td class="cell-p">P</td>`;
        if (mark === 'A') return `<td class="cell-a">A</td>`;
        if (mark === 'M') return `<td class="cell-m">M</td>`;
        return `<td class="cell-na">—</td>`;
      }).join('');

      // Weekly stats for this subject
      let wp = 0, wa = 0, wm = 0;
      days.forEach(d => {
        const m = db.attendance[d]?.[sub.id]?.[stu.id];
        if (m === 'P') wp++;
        else if (m === 'A') wa++;
        else if (m === 'M') wm++;
      });
      const we = wp + wa;
      const wpct = we > 0 ? ((wp / we) * 100).toFixed(1) : '—';

      const stats = getStats(stu.id, sub.id);
      const overall = stats.pct !== null ? stats.pct.toFixed(1) + '%' : '—';

      return `<tr>
        <td><span class="at-risk-avatar ${avatarClass(idx)}" style="display:inline-flex;width:24px;height:24px;border-radius:50%;align-items:center;justify-content:center;font-size:0.65rem;font-weight:700;margin-right:0.5rem">${initials(stu.name)}</span>${stu.name}</td>
        <td>${stu.roll}</td>
        ${cells}
        <td style="font-weight:600;color:var(--text)">${we > 0 ? wpct + '%' : '—'}</td>
        <td class="pct-cell ${pctClass(stats.pct)}">${overall}</td>
      </tr>`;
    }).join('');

    html += `
      <div style="margin-bottom:2rem">
        <div class="panel-header" style="padding:0.75rem 0;border-bottom:1px solid var(--border)">
          <h3 style="font-size:0.95rem;font-weight:600">${sub.name} <span style="color:var(--text-muted);font-size:0.8rem">(${sub.code})</span></h3>
        </div>
        <div style="overflow-x:auto">
          <table class="report-table">
            <thead>
              <tr>
                <th>Student</th><th>Roll</th>
                ${dayHeaders}
                <th>Week %</th><th>Overall %</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>`;
  });

  tableContainer.innerHTML = html;
}

function printReport() {
  window.print();
}

/* =============================================
   SETTINGS
   ============================================= */
function renderSettings() {
  renderStudentsList();
  renderSubjectsList();
}

function renderStudentsList() {
  const el = document.getElementById('studentsList');
  if (db.students.length === 0) {
    el.innerHTML = '<div class="no-data-msg">No students yet. Click + Add.</div>';
    return;
  }
  el.innerHTML = db.students.map((stu, idx) => `
    <div class="settings-item">
      <div class="at-risk-avatar ${avatarClass(idx)}" style="width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.75rem;flex-shrink:0">${initials(stu.name)}</div>
      <div class="si-info">
        <div class="si-name">${stu.name}</div>
        <div class="si-sub">${stu.roll}</div>
      </div>
      <button class="si-delete" onclick="deleteStudent('${stu.id}')" title="Delete">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
      </button>
    </div>`).join('');
}

function renderSubjectsList() {
  const el = document.getElementById('subjectsList');
  if (db.subjects.length === 0) {
    el.innerHTML = '<div class="no-data-msg">No subjects yet. Click + Add.</div>';
    return;
  }
  el.innerHTML = db.subjects.map((sub, idx) => `
    <div class="settings-item">
      <div class="at-risk-avatar ${avatarClass(idx + 2)}" style="width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.65rem;flex-shrink:0">${sub.code.slice(0,3)}</div>
      <div class="si-info">
        <div class="si-name">${sub.name}</div>
        <div class="si-sub">${sub.code}</div>
      </div>
      <button class="si-delete" onclick="deleteSubject('${sub.id}')" title="Delete">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
      </button>
    </div>`).join('');
}

function showAddStudent() {
  document.getElementById('addStudentForm').style.display = '';
  document.getElementById('newStudentName').focus();
}
function hideAddStudent() {
  document.getElementById('addStudentForm').style.display = 'none';
  document.getElementById('newStudentName').value = '';
  document.getElementById('newStudentRoll').value = '';
}

function addStudent() {
  const name = document.getElementById('newStudentName').value.trim();
  const roll = document.getElementById('newStudentRoll').value.trim();
  if (!name || !roll) { showToast('Please enter name and roll number', 'error'); return; }
  if (db.students.find(s => s.roll === roll)) { showToast('Roll number already exists', 'error'); return; }
  db.students.push({ id: uid(), name, roll });
  saveDB();
  hideAddStudent();
  renderStudentsList();
  showToast(`${name} added!`, 'success');
}

function deleteStudent(id) {
  confirmDialog('Delete Student?', 'All their attendance records will also be removed.', () => {
    db.students = db.students.filter(s => s.id !== id);
    Object.values(db.attendance).forEach(dayData => {
      Object.values(dayData).forEach(subData => delete subData[id]);
    });
    saveDB();
    renderStudentsList();
    showToast('Student deleted', 'info');
  });
}

function showAddSubject() {
  document.getElementById('addSubjectForm').style.display = '';
  document.getElementById('newSubjectName').focus();
}
function hideAddSubject() {
  document.getElementById('addSubjectForm').style.display = 'none';
  document.getElementById('newSubjectName').value = '';
  document.getElementById('newSubjectCode').value = '';
}

function addSubject() {
  const name = document.getElementById('newSubjectName').value.trim();
  const code = document.getElementById('newSubjectCode').value.trim().toUpperCase();
  if (!name || !code) { showToast('Please enter subject name and code', 'error'); return; }
  if (db.subjects.find(s => s.code === code)) { showToast('Subject code already exists', 'error'); return; }
  db.subjects.push({ id: uid(), name, code });
  saveDB();
  hideAddSubject();
  renderSubjectsList();
  showToast(`${name} added!`, 'success');
}

function deleteSubject(id) {
  confirmDialog('Delete Subject?', 'All attendance data for this subject will be removed.', () => {
    db.subjects = db.subjects.filter(s => s.id !== id);
    Object.values(db.attendance).forEach(dayData => delete dayData[id]);
    saveDB();
    renderSubjectsList();
    showToast('Subject deleted', 'info');
  });
}

/* =============================================
   DATA EXPORT / IMPORT
   ============================================= */
function exportData() {
  const blob = new Blob([JSON.stringify(db, null, 2)], { type: 'application/json' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = 'attendiq_backup.json';
  a.click();
  URL.revokeObjectURL(url);
  showToast('Data exported!', 'success');
}

function importData(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    try {
      const parsed = JSON.parse(e.target.result);
      if (!parsed.students || !parsed.subjects || !parsed.attendance)
        throw new Error('Invalid format');
      db = parsed;
      saveDB();
      renderDashboard();
      showToast('Data imported successfully!', 'success');
    } catch {
      showToast('Invalid JSON file', 'error');
    }
  };
  reader.readAsText(file);
  event.target.value = '';
}

function confirmClearData() {
  confirmDialog('Clear All Data?', 'This will permanently delete all students, subjects, and attendance records. This cannot be undone.', () => {
    db = { students: [], subjects: [], attendance: {} };
    saveDB();
    renderDashboard();
    renderSettings();
    showToast('All data cleared', 'info');
  });
}

/* =============================================
   CONFIRM DIALOG
   ============================================= */
function confirmDialog(title, message, onConfirm) {
  document.getElementById('confirmTitle').textContent   = title;
  document.getElementById('confirmMessage').textContent = message;
  const modal = document.getElementById('confirmModal');
  modal.style.display = 'flex';
  const btn = document.getElementById('confirmBtn');
  const handler = () => {
    closeConfirm();
    onConfirm();
    btn.removeEventListener('click', handler);
  };
  btn.addEventListener('click', handler);
}

function closeConfirm() {
  document.getElementById('confirmModal').style.display = 'none';
}

/* =============================================
   TOAST
   ============================================= */
let toastTimer = null;

function showToast(msg, type = 'info') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type} show`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 3200);
}

/* =============================================
   KEYBOARD SHORTCUTS
   ============================================= */
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    closeStudentModal();
    closeConfirm();
  }
});

/* =============================================
   INIT
   ============================================= */
document.addEventListener('DOMContentLoaded', () => {
  loadDB();
  renderDashboard();
});
