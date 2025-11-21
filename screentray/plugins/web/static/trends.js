// Trends visualizations
async function load24hBar() {
  const resp = await fetch(`${API}/hourly/24h`);
  const data = await resp.json();

  const chart = document.getElementById("bar-24h");
  chart.innerHTML = "";

  const maxMinutes = Math.max(...data.map(d => d.minutes), 1);

  data.forEach(item => {
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.height = `${(item.minutes / maxMinutes) * 100}%`;
    bar.title = `${item.hour}:00 - ${Math.round(item.minutes)}m`;

    if (item.minutes > 0) {
      bar.innerHTML = `<div class="bar-value">${Math.round(item.minutes)}m</div>`;
    }

    chart.appendChild(bar);
  });
}

async function loadWeeklyTrend() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);

  const resp = await fetch(
    `${API}/daily/range?start=${formatDate(start)}&end=${formatDate(end)}`
  );
  const data = await resp.json();

  const chart = document.getElementById("trend-30d");
  chart.innerHTML = "";

  const maxSeconds = Math.max(...data.map(d => d.active_seconds), 1);

  data.forEach(item => {
    const date = new Date(item.date);
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.height = `${(item.active_seconds / maxSeconds) * 100}%`;
    bar.title = `${item.date} - ${formatDuration(item.active_seconds)}`;

    // Highlight weekends
    if (date.getDay() >= 5) {
      bar.style.opacity = "0.5";
    }

    chart.appendChild(bar);
  });
}

async function loadMonthlyHeatmap() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 90); // 3 months

  const resp = await fetch(
    `${API}/daily/range?start=${formatDate(start)}&end=${formatDate(end)}`
  );
  const data = await resp.json();

  const container = document.getElementById("heatmap-3m");
  container.innerHTML = "";

  // Find max for color scaling
  const maxHours = Math.max(...data.map(d => d.active_seconds / 3600), 1);

  data.forEach(item => {
    const hours = item.active_seconds / 3600;
    const intensity = Math.min(hours / maxHours, 1);

    const cell = document.createElement("div");
    cell.className = "heatmap-cell";
    cell.style.opacity = `${0.2 + intensity * 0.8}`;
    cell.title = `${item.date} - ${formatDuration(item.active_seconds)}`;

    const date = new Date(item.date);
    cell.innerHTML = `<span class="date">${date.getDate()}</span>`;

    container.appendChild(cell);
  });
}

async function loadTrendsTab() {
  await Promise.all([
    load24hBar(),
    loadWeeklyTrend(),
    loadMonthlyHeatmap()
  ]);
}
