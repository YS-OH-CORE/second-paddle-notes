"""Pytest process guard and import provenance for the isolated validation run."""
import hashlib
import inspect
import json
import os
from pathlib import Path
import socket

EVENTS = []
IDENTITY = {}


def deny_network(*args, **kwargs):
    EVENTS.append(repr(args[1:] if args and isinstance(args[0], socket.socket) else args))
    raise RuntimeError("External networking is disabled in this test process")


socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.getaddrinfo = deny_network


def pytest_sessionstart(session):
    from langgraph.prebuilt import ToolNode
    from langgraph.graph import StateGraph
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph_sdk import get_client
    source = Path(inspect.getfile(ToolNode)).resolve()
    assert source == Path(os.environ["ZERO_EXPECTED_SOURCE"]).resolve()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == os.environ["ZERO_EXPECTED_SHA"]
    IDENTITY.update(tool_node=str(source), source_sha256=digest)
    paths = {"state_graph": inspect.getfile(StateGraph),
             "checkpoint": inspect.getfile(InMemorySaver),
             "sdk": inspect.getfile(get_client)}
    root = Path(os.environ["ZERO_REPO_ROOT"]).resolve()
    for name, path in paths.items():
        assert Path(path).resolve().is_relative_to(root), (name, path, root)
    IDENTITY.update(paths)


def pytest_sessionfinish(session, exitstatus):
    Path(os.environ["ZERO_GUARD_LOG"]).write_text(json.dumps({
        "exitstatus": int(exitstatus), "collected": session.testscollected,
        "blocked_network_attempts": EVENTS, "identity": IDENTITY,
    }, indent=2) + "\n", encoding="utf-8")
