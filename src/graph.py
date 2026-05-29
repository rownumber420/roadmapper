from langgraph.graph import END, START, StateGraph

from psycopg import connect as pg_connect
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver  # why not memory?

from src.config import get_settings
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
    conn = pg_connect(
        get_settings().database_url,
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
    )
    checkpointer = PostgresSaver(conn)
    checkpointer.setup()
    return builder.compile(checkpointer=checkpointer)
