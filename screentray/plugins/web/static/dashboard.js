const API = "/api";
let periods = [];
let selectedIndex = -1;
let currentDate = new Date();
let currentWeekStart = new Date();
let periodsDisplayed = 20;

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
      if (targetId === "overview") loadPeriods();
      if (targetId === "weekly") loadWeeklyView();
      if (targetId === "events") loadEventsList();
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

// OVERVIEW TAB - Periods with infinite scroll
async function loadPeriods() {
  const hours = document.getElementById("hours").value;
  const resp = await fetch(`${API}/periods?hours=${hours}`);
  const data = await resp.json();
  
  periods = data.reverse(); // Most recent first
  periodsDisplayed = 20;

  renderPeriods();
  updateCurrentStats();

  const lastActive = periods.findIndex(p => p.state === "active");
  if (lastActive >= 0) selectPeriod(lastActive);
}

function renderPeriods() {
  const container = document.getElementById("periods");
  container.innerHTML = "";

  if (periods.error) {
    container.innerText = periods.error;
    return;
  }

  const toShow = periods.slice(0, periodsDisplayed);

  toShow.forEach((p, idx) => {
    const div = document.createElement("div");
    div.className = `period`;
    div.dataset.state = p.state;
    div.onclick = () => selectPeriod(idx);

    div.innerHTML = `
      <div class="period-header">
        <span>${p.state.toUpperCase()}</span>
        <span>${formatDuration(p.duration_sec)}</span>
      </div>
      <div style="font-size:0.85em;opacity:0.7;">
        ${formatTime(p.start)} → ${formatTime(p.end)}
      </div>
    `;
    container.appendChild(div);
  });

  // Show/hide loader
  const loader = document.getElementById("periods-loader");
  if (periodsDisplayed < periods.length) {
    loader.style.display = "block";
  } else {
    loader.style.display = "none";
  }
}

function updateCurrentStats() {
  const activeTime = periods.filter(p => p.state === 'active').reduce((sum, p) => sum + p.duration_sec, 0);
  const inactiveTime = periods.filter(p => p.state === 'inactive').reduce((sum, p) => sum + p.duration_sec, 0);

  const hours = document.getElementById("hours").value;
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
}

// Infinite scroll for periods
document.getElementById("periods-container").addEventListener("scroll", (e) => {
  const el = e.target;
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 50) {
    if (periodsDisplayed < periods.length) {
      periodsDisplayed = Math.min(periodsDisplayed + 20, periods.length);
      renderPeriods();
    }
  }
});

function selectPeriod(idx) {
  selectedIndex = idx;
  const p = periods[idx];

  document.querySelectorAll(".period").forEach((el, i) => {
    el.classList.toggle("selected", i === idx);
  });

  document.getElementById("period-index").innerText = `${idx + 1} / ${periods.length}`;
  document.getElementById("prev-period").disabled = idx === 0;
  document.getElementById("next-period").disabled = idx === periods.length - 1;

  const details = document.getElementById("period-details");
  const content = document.getElementById("detail-content");

  let html = `
    <p style="margin: 0.25rem 0;"><strong>State:</strong> ${p.state}</p>
    <p style="margin: 0.25rem 0;"><strong>Duration:</strong> ${formatDuration(p.duration_sec)}</p>
    <p style="margin: 0.25rem 0;"><strong>Start:</strong> ${formatTime(p.start)}</p>
    <p style="margin: 0.25rem 0;"><strong>End:</strong> ${formatTime(p.end)}</p>
  `;

  if (p.trigger_event) {
    html += `
      <p style="margin: 0.25rem 0;"><strong>Trigger:</strong> ${p.trigger_event.type}</p>
    `;
  }

  if (p.events && p.events.length > 0) {
    html += `
      <button class="toggle-btn outline secondary" onclick="togglePeriodEvents(event)">
        Show Events (${p.events.length})
      </button>
      <div class="event-list hidden" id="period-events" style="margin-top: 0.5rem;">
    `;
    p.events.forEach(e => {
      html += `
        <div style="border-left: 2px solid var(--pico-primary); padding: 0.25rem; margin: 0.25rem 0; font-family: monospace; font-size: 0.8em;">
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

// EVENTS TAB
async function loadEventsList(q = "") {
  const limit = document.getElementById("event-limit").value;
  const resp = await fetch(`${API}/events?limit=${limit}&offset=0${q ? "&q=" + encodeURIComponent(q) : ""}`);
  const events = await resp.json();

  const container = document.getElementById("event-list");
  container.innerHTML = "";

  events.forEach(e => {
    const div = document.createElement("div");
    div.innerHTML = `
      <article style="padding: 0.5rem; margin-bottom: 0.25rem; font-family: monospace; font-size: 0.85em;">
        <strong>${e.type}</strong> @ ${e.timestamp}
        ${e.detail ? `<br><span style="opacity:0.7">${e.detail}</span>` : ''}
      </article>
    `;
    container.appendChild(div);
  });
}

// Event listeners
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

document.getElementById("event-search-btn").onclick = () => {
  loadEventsList(document.getElementById("event-search").value);
};
document.getElementById("event-limit").onchange = () => {
  loadEventsList(document.getElementById("event-search").value);
};

// Init
window.onload = () => {
  loadTheme();
  setupTabSwitching();
  currentDate = new Date();
  currentWeekStart = new Date();
  loadDailyView(); // Daily view as default
};
