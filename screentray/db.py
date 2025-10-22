import sqlite3
from .config import DB_PATH

def query_totals(day):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        WITH ordered AS (
            SELECT id, timestamp, type,
                   LAG(timestamp) OVER (ORDER BY id) AS prev_ts,
                   LAG(type) OVER (ORDER BY id) AS prev_type
            FROM events
            WHERE date(timestamp)=?
        ),
        intervals AS (
            SELECT prev_type AS from_type, type AS to_type,
                   CAST((strftime('%s',timestamp)-strftime('%s',prev_ts)) AS REAL) AS seconds
            FROM ordered WHERE prev_ts IS NOT NULL
        ),
        classified AS (
            SELECT CASE
                WHEN (from_type IN ('screen_on','idle_end','app_switch')
                      AND to_type IN ('app_switch','idle_start','screen_off'))
                     OR (from_type='idle_start' AND seconds < 300)
                THEN 'active' ELSE 'inactive' END AS state, seconds
            FROM intervals
        )
        SELECT state, SUM(seconds) FROM classified GROUP BY state
        """, (day,))
        return dict(c.fetchall())

def query_top_apps(day, limit=10):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f"""
        WITH cleaned AS (
            SELECT id, timestamp, type,
                   TRIM(SUBSTR(detail, INSTR(detail,'→')+1)) AS app,
                   LAG(timestamp) OVER (ORDER BY id) AS prev_ts,
                   LAG(type) OVER (ORDER BY id) AS prev_type
            FROM events WHERE date(timestamp)=?
        ),
        durations AS (
            SELECT app, CAST((strftime('%s',timestamp)-strftime('%s',prev_ts)) AS REAL) AS seconds
            FROM cleaned WHERE prev_type='app_switch'
              AND type IN ('app_switch','idle_start','screen_off')
              AND app IS NOT NULL AND app != ''
        )
        SELECT app, SUM(seconds) FROM durations GROUP BY app ORDER BY SUM(seconds) DESC LIMIT ?
        """, (day, limit))
        return c.fetchall()
