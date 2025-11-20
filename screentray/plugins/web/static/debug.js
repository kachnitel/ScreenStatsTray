const API = "/api";
let periods = [];
let selectedIndex = -1;
let periodsDisplayed = 20;

function setupTabSwitching() {
  document.querySelectorAll('#tab-nav-list a[role="button"]').forEach(tab => {
    tab.onclick = (e) => {
      e.preventDefault();
      document.querySelectorAll('#tab-nav-list a[role="button"]').forEach(t => t.removeAttribute("aria-current"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      tab.setAttribute("aria-current", "page");
      const targetId = tab.dataset.tab;
      document.getElementById(targetId).classList.add("active");

      if (targetId === "periods") loadPeriods();
      if (targetId === "events") loadEventsList();
    };
  });
}

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

function extractScreenState(events) {
  // Find last poll event with screen state
  for (let i = events.length - 1; i >= 0; i--) {
    if (events[i].type === 'poll' && events[i].detail) {
      const match = events[i].detail.match(/screen=(on|off)/);
      if (match) return match[1];
    }
  }
  return 'unknown';
}

async function loadPeriods() {
  const hours = document.getElementById("hours").value;
  const resp = await fetch(`${API}/periods?hours=${hours}`);
  const data = await resp.json();

  periods = data.reverse();
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

    const screenState = extractScreenState(p.events || []);
    const stateIcon = p.state === 'active' ? '●' : '○';
    const screenIcon = screenState === 'on' ? '🖥' : screenState === 'off' ? '⬛' : '';

    div.innerHTML = `
      <div class="period-header">
        <span>${stateIcon} ${p.state.toUpperCase()} ${screenIcon}</span>
        <span>${formatDuration(p.duration_sec)}</span>
      </div>
      <div style="font-size:0.85em;opacity:0.7;">
        ${formatTime(p.start)} → ${formatTime(p.end)}
      </div>
    `;
    container.appendChild(div);
  });

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

  const screenState = extractScreenState(p.events || []);

  let html = `
    <p style="margin: 0.25rem 0;"><strong>State:</strong> ${p.state}</p>
    <p style="margin: 0.25rem 0;"><strong>Screen:</strong> ${screenState}</p>
    <p style="margin: 0.25rem 0;"><strong>Duration:</strong> ${formatDuration(p.duration_sec)}</p>
    <p style="margin: 0.25rem 0;"><strong>Start:</strong> ${formatTime(p.start)}</p>
    <p style="margin: 0.25rem 0;"><strong>End:</strong> ${formatTime(p.end)}</p>
  `;

  if (p.trigger_event) {
    html += `
      <p style="margin: 0.25rem 0;"><strong title="Event causing transition to next state">End Trigger:</strong> <span title="${formatTime(p.trigger_event.timestamp)}: ${p.trigger_event.detail}">${p.trigger_event.type}</span></p>
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

async function loadEventsList(q = "") {
  const limit = document.getElementById("event-limit").value;
  const resp = await fetch(`${API}/events?limit=${limit}&offset=0${q ? "&q=" + encodeURIComponent(q) : ""}`);
  const events = await resp.json();

  const container = document.getElementById("event-list");
  container.innerHTML = "";

  const stateEvents = ['idle_start', 'idle_end', 'screen_off', 'screen_on'];

  events.forEach(e => {
    const isStateChange = stateEvents.includes(e.type);
    const borderColor = isStateChange ? 'var(--pico-primary)' : 'var(--pico-muted-color)';
    const bgColor = isStateChange ? 'rgba(var(--pico-primary-rgb), 0.1)' : 'transparent';

    const div = document.createElement("div");
    div.innerHTML = `
      <article style="padding: 0.5rem; margin-bottom: 0.25rem; font-family: monospace; font-size: 0.85em; border-left: 3px solid ${borderColor}; background: ${bgColor};">
        <strong>${e.type}</strong> @ ${e.timestamp}
        ${e.detail ? `<br><span style="opacity:0.7">${e.detail}</span>` : ''}
      </article>
    `;
    container.appendChild(div);
  });
}

// Event listeners
document.getElementById("refresh").onclick = loadPeriods;
document.getElementById("hours").onchange = loadPeriods;

document.getElementById("prev-period").onclick = () => {
  if (selectedIndex > 0) selectPeriod(selectedIndex - 1);
};
document.getElementById("next-period").onclick = () => {
  if (selectedIndex < periods.length - 1) selectPeriod(selectedIndex + 1);
};

document.getElementById("event-search-btn").onclick = () => {
  loadEventsList(document.getElementById("event-search").value);
};
document.getElementById("event-limit").onchange = () => {
  loadEventsList(document.getElementById("event-search").value);
};

// Init
window.onload = () => {
  setupTabSwitching();
  loadPeriods();
};
