"""Streamlit GUI to browse roadmap-generation runs — select a run, inspect
iteration logs with writer/reviewer expanders, and view roadmap diffs with
auto-refresh.
"""

import difflib
import itertools
import time

RUN_ID_DISPLAY_LENGTH = 8

import streamlit as st

st.set_page_config(layout="wide", page_title="Roadmapper")

from src.db import list_runs, get_run_logs


def _status(logs: list[dict]) -> str:
    """Determine run status from reviewer logs. Scans most recent reviewer
    entry for STATUS: ACCEPT; returns ACCEPTED, REVISE, or IN PROGRESS
    if no reviewer logs exist.
    """
    for log in reversed(logs):
        if log["node_type"] == "reviewer":
            text = (log.get("feedback") or "") + (log.get("raw_output") or "")
            if "STATUS: ACCEPT" in text.upper():
                return "ACCEPTED"
            return "REVISE"
    return "IN PROGRESS"


def _roadmap_diff(prev: str, curr: str) -> str:
    """Generate a unified diff string between previous and current roadmap
    content.
    """
    return "\n".join(
        difflib.unified_diff(
            prev.splitlines(),
            curr.splitlines(),
            fromfile="previous",
            tofile="current",
            lineterm="",
        )
    )


def _render_writer(log: dict, prev_roadmap: str) -> str:
    """Render a writer log entry with diff, prompt, raw output, and full
    roadmap expanders. Returns the current roadmap content.
    """
    curr_roadmap = log.get("roadmap_content") or ""
    st.markdown("**Writer**")

    if prev_roadmap and curr_roadmap:
        diff = _roadmap_diff(prev_roadmap, curr_roadmap)
        with st.expander("Diff"):
            st.code(diff, language="diff")

    with st.expander("Prompt"):
        st.text(log["prompt"] or "")
    with st.expander("Raw output"):
        st.text(log["raw_output"] or "")
    with st.expander("Full roadmap"):
        st.markdown(curr_roadmap)

    return curr_roadmap


def _render_reviewer(log: dict) -> None:
    """Render a reviewer log entry with feedback, prompt, and raw output
    expanders.
    """
    st.markdown("**Reviewer**")

    with st.expander("Feedback"):
        st.text(log.get("feedback") or "")
    with st.expander("Prompt"):
        st.text(log["prompt"] or "")
    with st.expander("Raw output"):
        st.text(log["raw_output"] or "")


auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)  # widget returns its current value
refresh_interval = st.sidebar.number_input("Refresh (s)", value=10, min_value=3)

runs = list_runs()

if not runs:
    st.info("No runs yet. Launch one via `docker compose run orchestrator ...`")
else:
    labels = [
        f"{str(r['run_id'])[:RUN_ID_DISPLAY_LENGTH]}  —  {r['iterations']} iter(s)  —  "
        f"{r['started_at'].strftime('%Y-%m-%d %H:%M') if r['started_at'] else '?'}"  # "ABC12345  —  6 iter(s)  —  2026-05-30 12:00"
        for r in runs
    ]
    idx = st.sidebar.selectbox("Run", range(len(labels)), format_func=lambda i: labels[i])
    run_id = str(runs[idx]["run_id"])

    logs = get_run_logs(run_id)

    if logs:
        total = max(log["iteration"] for log in logs)
        status = _status(logs)

        st.subheader(f"{run_id[:RUN_ID_DISPLAY_LENGTH]}  ·  {total} iteration(s)  ·  {status}")

        prev_roadmap = ""
        for iteration, group in itertools.groupby(logs, key=lambda x: x["iteration"]):
            group = list(group)
            with st.expander(f"Iteration {iteration}", expanded=(iteration == total)):
                for log in group:
                    if log["node_type"] == "writer":
                        prev_roadmap = _render_writer(log, prev_roadmap)
                    elif log["node_type"] == "reviewer":
                        _render_reviewer(log)

# runs the script top-to-bottom every time the page loads or refreshes. There's no event loop or request handler
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
