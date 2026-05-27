from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.nodes.reviewer import reviewer_node
from src.nodes.writer import writer_node
from src.state import RoadmapState


def _should_continue(state: RoadmapState):
    # Always run at least 2 iterations so the writer gets a chance
    # to address feedback from the first review cycle.
    if state["iteration"] < 2:
        return "writer_node"
    if state["is_stable"] or state["iteration"] >= state["max_iterations"]:
        return END
    return "writer_node"


def build_graph():
    builder = StateGraph(RoadmapState)
    builder.add_node("writer_node", writer_node)
    builder.add_node("reviewer_node", reviewer_node)
    builder.add_edge(START, "writer_node")
    builder.add_edge("writer_node", "reviewer_node")
    builder.add_conditional_edges("reviewer_node", _should_continue)
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
