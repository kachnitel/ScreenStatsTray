const API = "/api";
let periods = [];
let selectedIndex = -1;
let currentDate = new Date();
let currentWeekStart = new Date();

// --- THEME MANAGEMENT ---
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

// --- TAB SWITCHING LOGIC ---
function setupTabSwitching() {
    document.querySelectorAll('#tab-nav-list a[role="button"]').forEach(tab => {
        tab.onclick = (e) => {
            e.preventDefault();

            // 1. Remove active state from all tabs
            document.querySelectorAll('#tab-nav-list a[role="button"]').forEach(t => t.removeAttribute("aria-current"));

            // 2. Hide all content sections
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

            // 3. Set active state on clicked tab
            tab.setAttribute("aria-current", "page");

            // 4. Show the corresponding content section
            const targetId = tab.dataset.tab;
            document.getElementById(targetId).classList.add("active");

            // 5. Load data for the view
            if (targetId === "daily") loadDailyView();
            if (targetId === "weekly") loadWeeklyView();
            if (targetId === "events") loadEventsList();
        };
    });
}

// --- FORMAT HELPERS ---
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


// --- OVERVIEW TAB ---
async function loadPeriods() {
  const hours = document.getElementById("hours").value;
  const resp = await fetch(`${API}/periods?hours=${hours}`);
  periods = await resp.json();

  const container = document.getElementById("periods");
  container.innerHTML = "";

  if (periods.error) {
    container.innerText = periods.error;
    return;
  }

  periods.forEach((p, idx) => {
    const div = document.createElement("div");
    div.className = `period`;
    div.dataset.state = p.state;
    div.onclick = () => selectPeriod(idx);

    div.innerHTML = `
      <div class="period-header">
        <span>${p.state.toUpperCase()}</span>
        <span>${formatDuration(p.duration_sec)}</span>
      </div>
      <div style="font-size:0.9em;opacity:0.8;">
        ${formatTime(p.start)} → ${formatTime(p.end)}
      </div>
    `;
    container.appendChild(div);
  });

  // Update current stats
  const activeTime = periods.filter(p => p.state === 'active').reduce((sum, p) => sum + p.duration_sec, 0);
  const inactiveTime = periods.filter(p => p.state === 'inactive').reduce((sum, p) => sum + p.duration_sec, 0);

  document.getElementById("current-stats").innerHTML = `
    <span>
      <h5>Active (${hours}h)</h5>
      <p>${formatDuration(activeTime)}</p>
    </span>
    <span>
      <h5>Inactive (${hours}h)</h5>
      <p>${formatDuration(inactiveTime)}</p>
    </span>
  `;

  const lastActive = periods.findIndex(p => p.state === "active");
  if (lastActive >= 0) selectPeriod(lastActive);
}

function selectPeriod(idx) {
  selectedIndex = idx;
  const p = periods[idx];

  document.querySelectorAll(".period").forEach((el, i) => {
    el.classList.toggle("selected", i === idx);
  });

  document.getElementById("period-index").innerText = `Period ${idx + 1} / ${periods.length}`;
  document.getElementById("prev-period").disabled = idx === 0;
  document.getElementById("next-period").disabled = idx === periods.length - 1;

  const details = document.getElementById("period-details");
  const content = document.getElementById("detail-content");

  let html = `
    <p><strong>State:</strong> ${p.state}</p>
    <p><strong>Duration:</strong> ${formatDuration(p.duration_sec)}</p>
    <p><strong>Start:</strong> ${p.start}</p>
    <p><strong>End:</strong> ${p.end}</p>
  `;

  if (p.trigger_event) {
    html += `
      <p><strong>Triggered by:</strong> ${p.trigger_event.type}</p>
      <p style="font-size:0.9em;opacity:0.8;">${p.trigger_event.timestamp}</p>
    `;
  }

  if (p.events && p.events.length > 0) {
    html += `
      <button class="toggle-btn outline" onclick="togglePeriodEvents(event)">
        Show Events (${p.events.length})
      </button>
      <div class="event-list hidden" id="period-events">
    `;
    p.events.forEach(e => {
      html += `
        <div style="border-left: 3px solid var(--primary); padding: 5px; margin: 3px 0; font-family: monospace; font-size: 0.9em; background-color: var(--background-color);">
          <strong>${e.type}</strong> @ ${formatTime(e.timestamp)}
          ${e.detail ? `<br><span style="opacity:0.7">${e.detail}</span>` : ''}
        </div>
      `;
    });
    html += '</div>';
  }

  content.innerHTML = html;
  details.style.display = "block";
}

function togglePeriodEvents(event) {
  const el = document.getElementById("period-events");
  el.classList.toggle("hidden");
  event.target.textContent = el.classList.contains("hidden")
    ? `Show Events (${periods[selectedIndex].events.length})`
    : `Hide Events (${periods[selectedIndex].events.length})`;
}

// --- DAILY TAB ---
async function loadDailyView() {
  const dateStr = formatDate(currentDate);
  document.getElementById("daily-date").value = dateStr;

  const resp = await fetch(`${API}/stats/${dateStr}`);
  const stats = await resp.json();

  document.getElementById("daily-stats").innerHTML = `
    <article>
      <h4>Active Time</h4>
      <p style="font-size:1.5em;margin:5px 0;">${formatDuration(stats.active_seconds)}</p>
    </article>
    <article>
      <h4>Inactive Time</h4>
      <p style="font-size:1.5em;margin:5px 0;">${formatDuration(stats.inactive_seconds)}</p>
    </article>
    <article>
      <h4>Events</h4>
      ${Object.entries(stats.event_counts).map(([type, count]) =>
        `<p>${type}: ${count}</p>`
      ).join('')}
    </article>
  `;

  // Load hourly breakdown - fetch periods for the entire selected day
  const startOfDay = new Date(currentDate);
  startOfDay.setHours(0, 0, 0, 0);
  const endOfDay = new Date(currentDate);
  endOfDay.setHours(23, 59, 59, 999);

  // Calculate hours span for API call
  const now = new Date();
  const hoursFromNow = Math.ceil((now - startOfDay) / (1000 * 60 * 60));

  const hourlyResp = await fetch(`${API}/periods?hours=${Math.max(hoursFromNow, 24)}`);
  const allPeriods = await hourlyResp.json();

  const hourlyData = new Array(24).fill(0);

  allPeriods.forEach(p => {
    if (p.state !== 'active') return;

    const start = new Date(p.start);
    const end = new Date(p.end);

    // Only process periods that overlap with the selected day
    if (start.toDateString() !== currentDate.toDateString() &&
        end.toDateString() !== currentDate.toDateString()) return;

    // Clamp to day boundaries
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
      // Period within single hour
      hourlyData[startHour] += (endMinute - startMinute);
    } else {
      // Time in the start hour
      hourlyData[startHour] += (60 - startMinute);
      // Full hours between start and end
      for (let h = startHour + 1; h < endHour; h++) {
        hourlyData[h] += 60;
      }
      // Time in the end hour
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

// --- WEEKLY TAB ---
let weeklyStatsData = [];

async function loadWeeklyView() {
  const weekStart = new Date(currentWeekStart);
  // Monday start: adjust to previous Monday
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
  weeklyStatsData = [];

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  let maxActiveSeconds = 0;

  for (let i = 0; i < 7; i++) {
    const dayDate = new Date(weekStart);
    dayDate.setDate(dayDate.getDate() + i);
    const dateStr = formatDate(dayDate);

    // Fetch data for all 7 days
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

  // Render Day Summaries
  weeklyStatsData.forEach((data, i) => {
    const cell = document.createElement("div");
    cell.className = "day-summary-cell";
    if (data.isToday) {
      cell.classList.add("active-day");
    }
    cell.onclick = () => {
      // Click summary cell -> navigate to daily view for that day
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

  // Render Bar Chart
  const maxMinutes = Math.max(maxActiveSeconds / 60, 1);

  weeklyStatsData.forEach((data, i) => {
    const minutes = data.activeSeconds / 60;
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.height = `${(minutes / maxMinutes) * 100}%`;
    bar.onclick = () => {
      // Click bar -> navigate to daily view for that day
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

// --- EVENTS TAB ---
async function loadEventsList(q = "") {
  const limit = document.getElementById("event-limit").value;
  const resp = await fetch(`${API}/events?limit=${limit}&offset=0${q ? "&q=" + encodeURIComponent(q) : ""}`);
  const events = await resp.json();

  const container = document.getElementById("event-list");
  container.innerHTML = "";

  events.forEach(e => {
    const div = document.createElement("div");
    div.innerHTML = `
      <article style="padding: 10px; margin-bottom: 5px; font-family: monospace; font-size: 0.9em;">
        <strong>${e.type}</strong> @ ${e.timestamp}
        ${e.detail ? `<br><span style="opacity:0.7">${e.detail}</span>` : ''}
      </article>
    `;
    container.appendChild(div);
  });
}

// --- EVENT LISTENERS (Centralized) ---

// Overview listeners
document.getElementById("theme").onchange = e => {
  localStorage.setItem("theme", e.target.value);
  applyTheme(e.target.value);
};
document.getElementById("refresh").onclick = loadPeriods;
document.getElementById("hours").onchange = loadPeriods;

document.getElementById("prev-period").onclick = () => {
  if (selectedIndex > 0) selectPeriod(selectedIndex - 1);
};
document.getElementById("next-period").onclick = () => {
  if (selectedIndex < periods.length - 1) selectPeriod(selectedIndex + 1);
};

// Daily listeners
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

// Weekly listeners
document.getElementById("week-prev").onclick = () => {
  currentWeekStart.setDate(currentWeekStart.getDate() - 7);
  loadWeeklyView();
};

document.getElementById("week-next").onclick = () => {
  currentWeekStart.setDate(currentWeekStart.getDate() + 7);
  loadWeeklyView();
};

// Events listeners
document.getElementById("event-search-btn").onclick = () => {
  loadEventsList(document.getElementById("event-search").value);
};

document.getElementById("event-limit").onchange = () => {
  loadEventsList(document.getElementById("event-search").value);
};


// --- INITIALIZATION ---
window.onload = () => {
  loadTheme();
  setupTabSwitching();

  // Set initial dates
  currentDate = new Date();
  currentWeekStart = new Date();

  // Load the default view (Overview)
  loadPeriods();
};
