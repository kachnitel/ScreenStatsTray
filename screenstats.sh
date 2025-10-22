#!/usr/bin/env bash
DB="$HOME/.local/share/screentracker.db"
if [ ! -f "$DB" ]; then
  echo "No database found at $DB"
  exit 1
fi

# Optional date argument (YYYY-MM-DD), default = today
DAY="${1:-$(date +%F)}"
echo "=== ScreenTracker summary for $DAY ==="

# Raw counts
sqlite3 -readonly "$DB" <<SQL
.mode column
.headers on
SELECT type, COUNT(*) AS count
FROM events
WHERE date(timestamp)='$DAY'
GROUP BY type
ORDER BY type;
SQL

# Total active and inactive durations (idle <5 min = active)
echo
echo "Total active vs inactive time:"
sqlite3 -readonly "$DB" <<SQL
.mode column
.headers on
WITH ordered AS (
  SELECT id, timestamp, type,
         LAG(timestamp) OVER (ORDER BY id) AS prev_ts,
         LAG(type) OVER (ORDER BY id) AS prev_type
  FROM events
  WHERE date(timestamp)='$DAY'
),
intervals AS (
  SELECT
    prev_type AS from_type,
    type AS to_type,
    CAST((strftime('%s',timestamp) - strftime('%s',prev_ts)) AS REAL) AS seconds
  FROM ordered
  WHERE prev_ts IS NOT NULL
),
classified AS (
  SELECT
    CASE
      WHEN (from_type IN ('screen_on','idle_end','app_switch')
            AND to_type IN ('app_switch','idle_start','screen_off'))
           OR (from_type='idle_start' AND seconds < 300)
        THEN 'active'
      ELSE 'inactive'
    END AS state,
    seconds
  FROM intervals
)
SELECT
  state,
  printf('%02d:%02d:%02d', SUM(seconds)/3600, (SUM(seconds)/60)%60, SUM(seconds)%60) AS hms,
  ROUND(SUM(seconds)/60.0,1) AS minutes
FROM classified
GROUP BY state
ORDER BY state DESC;
SQL

# Per-app active time (excluding idle <5 min)
echo
echo "Time per application (active only):"
sqlite3 -readonly "$DB" <<SQL
.mode column
.headers on
WITH cleaned AS (
  SELECT
    id,
    timestamp,
    type,
    TRIM(SUBSTR(detail, INSTR(detail, '→') + 1)) AS app,
    LAG(timestamp) OVER (ORDER BY id) AS prev_ts,
    LAG(type) OVER (ORDER BY id) AS prev_type
  FROM events
  WHERE date(timestamp)='$DAY'
),
durations AS (
  SELECT
    app,
    CAST((strftime('%s',timestamp) - strftime('%s',prev_ts)) AS REAL) AS seconds
  FROM cleaned
  WHERE prev_type='app_switch' AND type IN ('app_switch','idle_start','screen_off')
    AND app IS NOT NULL AND app != ''
),
filtered AS (
  SELECT app, seconds
  FROM durations
  WHERE seconds > 0
)
SELECT
  app,
  printf('%02d:%02d:%02d', SUM(seconds)/3600, (SUM(seconds)/60)%60, SUM(seconds)%60) AS active_time_hms,
  ROUND(SUM(seconds)/60.0,1) AS minutes
FROM filtered
GROUP BY app
ORDER BY SUM(seconds) DESC
LIMIT 15;
SQL

echo
python3 - <<'EOF'
import sys
from screentray.session import current_session_seconds
secs = current_session_seconds()
h, rem = divmod(int(secs), 3600)
m, s = divmod(rem, 60)
print(f"Current session (since last screen_on or idle_end): {h:02d}:{m:02d}:{s:02d}")
EOF

