import argparse
import time
import uuid
from datetime import datetime

from src.config import configure, get_settings
from src.db import ensure_table
from src.graph import build_graph
from src.state import RoadmapState


def _ts():
    return datetime.now().strftime("%H:%M:%S")


def main():
    parser = argparse.ArgumentParser(description="Roadmapper orchestrator")
    parser.add_argument("--idea", dest="idea_path", default=None)
    parser.add_argument("--project-dir", dest="project_path", default=None)
    parser.add_argument("--output-dir", dest="output_path", default=None)
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument("--writer-model", default=None)
    parser.add_argument("--reviewer-model", default=None)
    parser.add_argument("--writer-timeout", type=int, default=None)
    parser.add_argument("--reviewer-timeout", type=int, default=None)
    args = parser.parse_args()

    overrides = {k: v for k, v in vars(args).items() if v is not None}
    configure(**overrides)
    settings = get_settings()

    run_id = str(uuid.uuid4())
    ensure_table()

    graph = build_graph()

    initial_state: RoadmapState = {
        "run_id": run_id,
        "project_path": settings.project_path,
        "iteration": 0,
        "max_iterations": settings.max_iterations,
        "is_stable": False,
    }

    config = {"configurable": {"thread_id": run_id}}
    run_start = time.time()

    print(f"[{_ts()}] Run {run_id} started")

    phase_start = run_start

    try:
        for event in graph.stream(initial_state, config, stream_mode="updates"):
            for node_name, output in event.items():
                now = time.time()
                elapsed = now - phase_start
                iteration = output.get("iteration", "?")

                if node_name == "writer_node":
                    print(f"[{_ts()}] Iteration {iteration}: Writer done ({elapsed:.1f}s)")
                elif node_name == "reviewer_node":
                    status = "ACCEPTED" if output.get("is_stable") else "REVISIONS REQUESTED"
                    print(f"[{_ts()}] Iteration {iteration}: Reviewer → {status} ({elapsed:.1f}s)")

                phase_start = now
    except Exception as e:
        print(f"[{_ts()}] ERROR: {e}")
        return

    state = graph.get_state(config)
    final = state.values if state else {}

    total = time.time() - run_start
    if final.get("is_stable"):
        print(f"[{_ts()}] Run finished — roadmap accepted after {final['iteration']} iteration(s) ({total:.1f}s)")
    else:
        print(f"[{_ts()}] Run finished — max iterations ({settings.max_iterations}) reached ({total:.1f}s)")


if __name__ == "__main__":
    main()
