const API = "/api";
let currentDate = new Date();
let currentWeekStart = new Date();

// Theme management
function applyTheme(mode) {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  let theme = mode;
  if (mode === 'system') {
    theme = prefersDark ? 'dark' : 'light';
  }
  document.documentElement.setAttribute('data-theme', theme);
}

function loadTheme() {
  const saved = localStorage.getItem("theme") || "system";
  document.getElementById("theme").value = saved;
  applyTheme(saved);
}

// Tab switching
function setupTabSwitching() {
  document.querySelectorAll('#tab-nav-list a[role="button"]').forEach(tab => {
    tab.onclick = (e) => {
      e.preventDefault();
      document.querySelectorAll('#tab-nav-list a[role="button"]').forEach(t => t.removeAttribute("aria-current"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      tab.setAttribute("aria-current", "page");
      const targetId = tab.dataset.tab;
      document.getElementById(targetId).classList.add("active");
      
      if (targetId === "daily") loadDailyView();
      if (targetId === "weekly") loadWeeklyView();
    };
  });
}

// Format helpers
function formatDuration(sec) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return `${s}s`;
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString();
}

function formatDate(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().split('T')[0];
}

// DAILY TAB (DEFAULT VIEW)
async function loadDailyView() {
  const dateStr = formatDate(currentDate);
  document.getElementById("daily-date").value = dateStr;

  const resp = await fetch(`${API}/stats/${dateStr}`);
  const stats = await resp.json();

  document.getElementById("daily-stats").innerHTML = `
    <article style="padding: 0.75rem;">
      <h4 style="margin-bottom: 0.25rem;">Active Time</h4>
      <p style="font-size:1.5em;margin:5px 0;">${formatDuration(stats.active_seconds)}</p>
    </article>
    <article style="padding: 0.75rem;">
      <h4 style="margin-bottom: 0.25rem;">Events</h4>
      ${Object.entries(stats.event_counts).map(([type, count]) =>
        `<p style="margin: 0.25rem 0; font-size: 0.9em;">${type}: ${count}</p>`
      ).join('')}
    </article>
  `;

  // Hourly breakdown
  const startOfDay = new Date(currentDate);
  startOfDay.setHours(0, 0, 0, 0);
  const now = new Date();
  const hoursFromNow = Math.ceil((now - startOfDay) / (1000 * 60 * 60));

  const hourlyResp = await fetch(`${API}/periods?hours=${Math.max(hoursFromNow, 24)}`);
  const allPeriods = await hourlyResp.json();

  const hourlyData = new Array(24).fill(0);

  allPeriods.forEach(p => {
    if (p.state !== 'active') return;
    const start = new Date(p.start);
    const end = new Date(p.end);

    if (start.toDateString() !== currentDate.toDateString() &&
        end.toDateString() !== currentDate.toDateString()) return;

    const dayStart = new Date(currentDate);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(currentDate);
    dayEnd.setHours(23, 59, 59, 999);

    const periodStart = start < dayStart ? dayStart : start;
    const periodEnd = end > dayEnd ? dayEnd : end;

    if (periodStart >= periodEnd) return;

    const startHour = periodStart.getHours();
    const endHour = periodEnd.getHours();
    const startMinute = periodStart.getMinutes();
    const endMinute = periodEnd.getMinutes();

    if (startHour === endHour) {
      hourlyData[startHour] += (endMinute - startMinute);
    } else {
      hourlyData[startHour] += (60 - startMinute);
      for (let h = startHour + 1; h < endHour; h++) {
        hourlyData[h] += 60;
      }
      hourlyData[endHour] += endMinute;
    }
  });

  const maxMinutes = Math.max(...hourlyData, 1);
  const chart = document.getElementById("hourly-chart");
  chart.innerHTML = '';

  hourlyData.forEach((minutes, hour) => {
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.height = `${(minutes / maxMinutes) * 100}%`;
    bar.innerHTML = `
      <div class="bar-value">${Math.round(minutes)}m</div>
      <div class="bar-label">${hour}h</div>
    `;
    chart.appendChild(bar);
  });
}

// WEEKLY TAB
async function loadWeeklyView() {
  const weekStart = new Date(currentWeekStart);
  const day = weekStart.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  weekStart.setDate(weekStart.getDate() + diff);

  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekEnd.getDate() + 6);

  document.getElementById("week-label").textContent =
    `${formatDate(weekStart)} — ${formatDate(weekEnd)}`;

  const summaryContainer = document.getElementById("weekly-day-summaries");
  const chart = document.getElementById("weekly-bar-chart");
  summaryContainer.innerHTML = '';
  chart.innerHTML = '';
  
  const weeklyStatsData = [];
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  let maxActiveSeconds = 0;

  for (let i = 0; i < 7; i++) {
    const dayDate = new Date(weekStart);
    dayDate.setDate(dayDate.getDate() + i);
    const dateStr = formatDate(dayDate);

    const resp = await fetch(`${API}/stats/${dateStr}`);
    const stats = await resp.json();

    weeklyStatsData.push({
      date: dayDate,
      dayName: days[i],
      activeSeconds: stats.active_seconds,
      isToday: formatDate(dayDate) === formatDate(new Date())
    });

    if (stats.active_seconds > maxActiveSeconds) {
      maxActiveSeconds = stats.active_seconds;
    }
  }

  weeklyStatsData.forEach((data) => {
    const cell = document.createElement("div");
    cell.className = "day-summary-cell";
    if (data.isToday) cell.classList.add("active-day");
    cell.onclick = () => {
      currentDate = data.date;
      document.querySelector('a[data-tab="daily"]').click();
    };

    cell.innerHTML = `
      <span class="day-name">${data.dayName}</span>
      <span class="date">${data.date.getDate()}</span>
      <div class="duration">${formatDuration(data.activeSeconds)}</div>
    `;
    summaryContainer.appendChild(cell);
  });

  const maxMinutes = Math.max(maxActiveSeconds / 60, 1);

  weeklyStatsData.forEach((data) => {
    const minutes = data.activeSeconds / 60;
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.height = `${(minutes / maxMinutes) * 100}%`;
    bar.onclick = () => {
      currentDate = data.date;
      document.querySelector('a[data-tab="daily"]').click();
    };

    bar.innerHTML = `
      <div class="bar-value">${formatDuration(data.activeSeconds)}</div>
      <div class="bar-label">${data.dayName}</div>
    `;
    chart.appendChild(bar);
  });
}

// Event listeners
document.getElementById("theme").onchange = e => {
  localStorage.setItem("theme", e.target.value);
  applyTheme(e.target.value);
};

document.getElementById("daily-date").onchange = (e) => {
  currentDate = new Date(e.target.value);
  loadDailyView();
};
document.getElementById("daily-prev").onclick = () => {
  currentDate.setDate(currentDate.getDate() - 1);
  loadDailyView();
};
document.getElementById("daily-next").onclick = () => {
  currentDate.setDate(currentDate.getDate() + 1);
  loadDailyView();
};

document.getElementById("week-prev").onclick = () => {
  currentWeekStart.setDate(currentWeekStart.getDate() - 7);
  loadWeeklyView();
};
document.getElementById("week-next").onclick = () => {
  currentWeekStart.setDate(currentWeekStart.getDate() + 7);
  loadWeeklyView();
};

// Init
window.onload = () => {
  loadTheme();
  setupTabSwitching();
  currentDate = new Date();
  currentWeekStart = new Date();
  loadDailyView();
};
