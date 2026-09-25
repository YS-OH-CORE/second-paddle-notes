# LangGraph 9072: portable regression tests and upstream compatibility

Youngseok Oh x Zero, AI collaboration partners. 2026-09-25.

Purpose: turn the earlier executable examples into a standalone pytest file that a developer can apply to a source checkout. Check the exact prior normalized candidate against the entire existing tests/test_tool_node.py file as well, not just our own selected success cases. No new runtime design is introduced in this run.

Pinned upstream: 7daa3ab49d678a5da75edb08baa87db4a2be52c3.
Original ToolNode Git blob: 95e161b9078e3123afa1854247a5dfd132410a53.
Original test_tool_node.py Git blob: 47ebdcae0d936167649c0d33103650388d290a9a.
Prior normalized candidate SHA-256: be4a47872cfd4764a3fcc3ae0e093295706a87f3b5d9960ab6dd6ebb8645ab8c.

The proposed test file contains twelve conditions through invoke and ainvoke, giving 24 pytest cases: prior single-send, sibling/reversed-sibling and string-route controls; dict/tuple, tuple/dict, tuple/tuple, dataclass/tuple, tuple/Pydantic, None/tuple and tuple/None update representations; and an unreduced conflicting key, which must raise InvalidUpdateError. Tests assert the compiled parent's values, tool call IDs, and workers. The test file does not patch runtime or rely on our previous probe scripts.

Run original upstream and new regression files in separate fresh pytest processes for each of two implementations: unchanged source and byte-identical prior normalized candidate. Preserve original conftest, existing fixtures, snapshots and test expectations. Use the repository's existing LANGGRAPH_TEST_FAST=true memory-backed mode; do not start PostgreSQL, Redis or hosted model services. Import required fixture dependencies without exercising their external stores. Record the exact test count, all failures/skips and JUnit names; never equate workflow completion with all assertions passing. Our regression cases should fail on buggy base except the string-route controls, and pass on the candidate; upstream compatibility is measured rather than assumed.

The new test file receives only import sorting and formatter changes before testing. Verify its non-import AST is unchanged, then run the library's configured Ruff checks and preserve the exact tested file plus a test-only git patch. Existing upstream tests and code outside the disposable ToolNode candidate are not modified. No PR or production repair is implied. The original report and other participants' contributions remain theirs.

Source/dependency download is the only intended network activity. During pytest, a plugin blocks Python socket connect and DNS, records attempted calls, and verifies that ToolNode, StateGraph, InMemorySaver and SDK functions resolve to the pinned source checkout. Use fresh subprocesses, bytecode disabled, tracing off and no API credentials. Existing upstream tests use their own mocks where originally designed; our new graph tests use real graph/tool components and deterministic values without a model.

Coverage remains limited to the complete upstream ToolNode test module and the new regression file. This is not the complete repository suite. Arbitrary root states, mixed parent destinations, merging non-None resume values, other Python versions and checkpoint replay are not established. The candidate remains experimental until those design questions and project review are resolved.
