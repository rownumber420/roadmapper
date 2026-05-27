import contextlib

import psycopg2
import psycopg2.extras

from src.config import get_settings

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS iteration_logs (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    iteration INT NOT NULL,
    node_type VARCHAR(20) NOT NULL,
    raw_output TEXT,
    roadmap_content TEXT,
    feedback TEXT,
    prompt TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""

_INSERT = """
INSERT INTO iteration_logs (run_id, iteration, node_type, raw_output, roadmap_content, feedback, prompt)
VALUES (%(run_id)s, %(iteration)s, %(node_type)s, %(raw_output)s, %(roadmap_content)s, %(feedback)s, %(prompt)s)
"""

_GET_RUN_LOGS = """
SELECT * FROM iteration_logs WHERE run_id = %(run_id)s ORDER BY iteration ASC, id ASC
"""

_LIST_RUNS = """
SELECT run_id, MIN(created_at) AS started_at, MAX(iteration) AS iterations
FROM iteration_logs GROUP BY run_id ORDER BY started_at DESC
"""


@contextlib.contextmanager
def _conn():
    conn = psycopg2.connect(get_settings().database_url)
    try:
        yield conn
    finally:
        conn.close()


def ensure_table():
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_CREATE_TABLE)
        conn.commit()


def insert_log(
    run_id: str,
    iteration: int,
    node_type: str,
    *,
    raw_output: str | None = None,
    roadmap_content: str | None = None,
    feedback: str | None = None,
    prompt: str | None = None,
):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _INSERT,
                {
                    "run_id": run_id,
                    "iteration": iteration,
                    "node_type": node_type,
                    "raw_output": raw_output,
                    "roadmap_content": roadmap_content,
                    "feedback": feedback,
                    "prompt": prompt,
                },
            )
        conn.commit()


def get_run_logs(run_id: str) -> list[dict]:
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(_GET_RUN_LOGS, {"run_id": run_id})
            return [dict(r) for r in cur.fetchall()]


def list_runs() -> list[dict]:
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(_LIST_RUNS)
            return [dict(r) for r in cur.fetchall()]
