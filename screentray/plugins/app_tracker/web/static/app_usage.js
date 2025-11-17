// App Usage Plugin JavaScript
console.info("App Usage Plugin JavaScript loaded");

function formatAppDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

async function loadAppUsageDaily() {
  console.debug("loadAppUsageDaily called");
  try {
    const dateStr = formatDate(currentDate);
    const start = new Date(currentDate);
    start.setHours(0, 0, 0, 0);
    const end = new Date(currentDate);
    end.setHours(23, 59, 59, 999);

    const resp = await fetch(`/api/app_usage/top_apps?start=${start.toISOString()}&end=${end.toISOString()}&limit=10`);
    const data = await resp.json();

    const container = document.getElementById('app-usage-daily-list');
    if (!container) {
      console.error("Container #app-usage-daily-list not found");
      return;
    }

    if (!data || data.length === 0) {
      container.innerHTML = '<p style="color: var(--pico-muted-color);"><i>No app usage for this day</i></p>';
      return;
    }

    let html = '<div style="display: grid; gap: 0.25rem;">';
    data.forEach(item => {
      html += `<div style="display: flex; justify-content: space-between;">
        <span>${item.app}</span>
        <span style="color: var(--pico-muted-color);">${formatAppDuration(item.seconds)}</span>
      </div>`;
    });
    html += '</div>';

    container.innerHTML = html;
  } catch (e) {
    console.error('Failed to load daily app usage:', e);
  }
}

async function loadAppUsageTab() {
  console.debug("loadAppUsageTab called");
  const period = document.getElementById('app-usage-period').value;
  const limit = parseInt(document.getElementById('app-usage-limit').value);

  const end = new Date();
  let start = new Date();

  if (period === 'today') {
    start.setHours(0, 0, 0, 0);
  } else if (period === 'week') {
    start.setDate(start.getDate() - 7);
  } else if (period === 'month') {
    start.setDate(start.getDate() - 30);
  }

  try {
    const resp = await fetch(`/api/app_usage/top_apps?start=${start.toISOString()}&end=${end.toISOString()}&limit=${limit}`);
    const data = await resp.json();

    const tbody = document.getElementById('app-usage-tbody');
    const chart = document.getElementById('app-usage-chart');

    if (!tbody || !chart) {
      console.error("Required elements not found");
      return;
    }

    if (!data || data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" style="color: var(--pico-muted-color);"><i>No app usage for this period</i></td></tr>';
      chart.innerHTML = '<p style="text-align: center; color: var(--pico-muted-color);">No data</p>';
      return;
    }

    // Calculate total for percentages
    const total = data.reduce((sum, item) => sum + item.seconds, 0);

    // Render table
    let tableHtml = '';
    data.forEach(item => {
      const percentage = ((item.seconds / total) * 100).toFixed(1);
      tableHtml += `<tr>
        <td>${item.app}</td>
        <td>${formatAppDuration(item.seconds)}</td>
        <td>${percentage}%</td>
      </tr>`;
    });
    tbody.innerHTML = tableHtml;

    // Render chart
    const maxSeconds = Math.max(...data.map(d => d.seconds), 1);
    chart.innerHTML = '';
    data.forEach(item => {
      const bar = document.createElement('div');
      bar.className = 'bar';
      bar.style.height = `${(item.seconds / maxSeconds) * 100}%`;
      bar.innerHTML = `
        <div class="bar-value">${formatAppDuration(item.seconds)}</div>
        <div class="bar-label" style="max-width: 80px; overflow: hidden; text-overflow: ellipsis;">${item.app}</div>
      `;
      chart.appendChild(bar);
    });
  } catch (e) {
    console.error('Failed to load app usage tab:', e);
  }
}

// Call loadAppUsageOverview when page loads
console.debug("Setting up window.onload handler");
window.addEventListener('load', function() {
  console.debug("Window loaded, calling loadAppUsageOverview");
  // loadAppUsageOverview();
});

// Hook into existing loadPeriods if it exists
if (typeof loadPeriods !== 'undefined') {
  console.debug("Wrapping loadPeriods");
  const originalLoadPeriods = loadPeriods;
  loadPeriods = async function() {
    await originalLoadPeriods();
    // loadAppUsageOverview();
  };
}

// Hook into existing loadDailyView if it exists
if (typeof loadDailyView !== 'undefined') {
  console.debug("Wrapping loadDailyView");
  const originalLoadDaily = loadDailyView;
  loadDailyView = async function() {
    await originalLoadDaily();
    loadAppUsageDaily();
  };
}

// Setup event listeners when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  console.debug("DOM loaded, setting up event listeners");

  const periodSelect = document.getElementById('app-usage-period');
  const limitInput = document.getElementById('app-usage-limit');

  if (periodSelect) {
    periodSelect.addEventListener('change', loadAppUsageTab);
    console.debug("Added change listener to period select");
  }
  if (limitInput) {
    limitInput.addEventListener('change', loadAppUsageTab);
    console.debug("Added change listener to limit input");
  }

  // Setup Apps tab click handler
  // Use polling to wait for dynamically injected tab
  const attachTabHandler = () => {
    const appsTab = document.querySelector('a[data-tab="apps"]');
    if (appsTab) {
      console.debug("Apps tab found, attaching handler");
      appsTab.addEventListener('click', () => {
        console.debug("Apps tab clicked, loading data");
        loadAppUsageTab();
      });
      return true;
    }
    return false;
  };

  // Try immediately
  if (!attachTabHandler()) {
    // If not found, poll for it (in case it's injected after DOM ready)
    console.debug("Apps tab not found, polling...");
    const pollInterval = setInterval(() => {
      if (attachTabHandler()) {
        console.debug("Apps tab handler attached");
        clearInterval(pollInterval);
      }
    }, 100);

    // Stop polling after 5 seconds
    setTimeout(() => {
      clearInterval(pollInterval);
      console.debug("Stopped polling for Apps tab");
    }, 5000);
  }
});
