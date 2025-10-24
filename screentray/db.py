import sqlite3
from typing import Dict, List, Tuple
from .config import DB_PATH, MAX_NO_EVENT_GAP


def query_totals(day: str) -> Dict[str, float]:
    """
    Return total active/inactive seconds for a given day.
    - Considers screen_off, lid_closed, and system_suspend as inactive states.
    - Ignores short inactive periods (< IDLE_THRESHOLD_SEC) as minor pauses (still active).
    - Gaps without events are considered inactive.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        WITH ordered AS (
            SELECT id, timestamp, type,
                   LAG(timestamp) OVER (ORDER BY id) AS prev_ts,
                   LAG(type) OVER (ORDER BY id) AS prev_type
            FROM events
            WHERE date(timestamp)=:day
        ),
        intervals AS (
            SELECT
                prev_type AS from_type,
                type AS to_type,
                CAST((strftime('%s',timestamp)-strftime('%s',prev_ts)) AS REAL) AS seconds
            FROM ordered
            WHERE prev_ts IS NOT NULL
        ),
        classified AS (
            SELECT
                CASE
                    WHEN (from_type IN ('screen_on','idle_end','app_switch','lid_open','system_resume')
                          AND to_type IN ('app_switch','idle_start','screen_off','lid_closed','system_suspend'))
                         OR (from_type='idle_start' AND seconds < :threshold)
                    THEN 'active'
                    ELSE 'inactive'
                END AS state,
                seconds
            FROM intervals
        ),
        merged AS (
            -- short inactive intervals (< threshold) are counted as active
            SELECT CASE WHEN state='inactive' AND seconds < :threshold THEN 'active' ELSE state END AS state,
                   seconds
            FROM classified
        )
        SELECT state, SUM(seconds) FROM merged GROUP BY state
        """, {"day": day, "threshold": MAX_NO_EVENT_GAP})
        return {state: float(seconds) for state, seconds in c.fetchall()}


def query_top_apps(day: str, limit: int = 10) -> List[Tuple[str, float]]:
    """
    Return top applications and active time in seconds for a given day.
    - Stops counting when idle, screen_off, lid_closed, or system_suspend occur.
    - Includes gaps smaller than the idle threshold as part of active time.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        WITH cleaned AS (
            SELECT id, timestamp, type,
                   TRIM(SUBSTR(detail, INSTR(detail,'→')+1)) AS app,
                   LAG(timestamp) OVER (ORDER BY id) AS prev_ts,
                   LAG(type) OVER (ORDER BY id) AS prev_type
            FROM events WHERE date(timestamp)=?
        ),
        durations AS (
            SELECT app,
                   CAST((strftime('%s',timestamp)-strftime('%s',prev_ts)) AS REAL) AS seconds,
                   type, prev_type
            FROM cleaned
            WHERE prev_ts IS NOT NULL
              AND app IS NOT NULL AND app != ''
        ),
        filtered AS (
            SELECT app, seconds
            FROM durations
            WHERE prev_type='app_switch'
              AND type IN ('app_switch','idle_start','screen_off','lid_closed','system_suspend')
              AND seconds >= 1
        )
        SELECT app, SUM(seconds) FROM filtered
        GROUP BY app
        ORDER BY SUM(seconds) DESC
        LIMIT ?
        """, (day, limit))
        return [(app, float(sec)) for app, sec in c.fetchall()]
