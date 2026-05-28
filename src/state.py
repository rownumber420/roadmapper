from typing import TypedDict

class RoadmapState(TypedDict):
    run_id: str
    iteration: int
    max_iterations: int
    is_stable: bool
