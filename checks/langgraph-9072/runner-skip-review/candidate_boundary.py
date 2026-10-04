"""Discussion-only implementation of impartshadow's reject-first proposal.

The runner policy is not maintainer-approved. This substitution is used only
inside the isolated comparison, not in the user's installed LangGraph.
"""
from langgraph.errors import GraphInterrupt, InvalidUpdateError, ParentCommand
from langgraph.pregel import _runner


def reject_parent_batch(
    futs,
    *,
    timeout_exc_cls=TimeoutError,
    panic=True,
    handled_exception_ids=None,
    handled_futures=None,
):
    done, inflight = set(), set()
    for future in futs:
        if future.cancelled():
            continue
        (done if future.done() else inflight).add(future)
    interrupts, parents = [], []
    while done:
        future = done.pop()
        exc = _runner._exception(future)
        if exc is None or future in (handled_futures or ()):
            continue
        if id(exc) in (handled_exception_ids or ()):
            continue
        if panic:
            if isinstance(exc, GraphInterrupt):
                interrupts.append(exc)
            elif isinstance(exc, ParentCommand):
                parents.append(exc)
            elif future not in _runner.SKIP_RERAISE_SET:
                for pending in inflight:
                    pending.cancel()
                raise exc
    if inflight:
        for pending in inflight:
            pending.cancel()
        raise timeout_exc_cls("Timed out")
    if interrupts:
        raise GraphInterrupt(tuple(i for exc in interrupts for i in exc.args[0]))
    if len(parents) == 1:
        raise parents[0]
    if len(parents) > 1:
        raise InvalidUpdateError(
            "Multiple ParentCommand values were produced in one superstep; "
            "they cannot be ordered or merged safely"
        )
