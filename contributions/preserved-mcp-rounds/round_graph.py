"""Application-level MCP form rounds with a checkpoint before each review.

Not a monkey-patch to MCPAdapter. The caller owns connection lifetime, checkpoint
access, authentication and serializing concurrent resumes of one thread.
"""
from __future__ import annotations
from copy import deepcopy
import json
from typing import Any, TypedDict

class RoundState(TypedDict, total=False):
    tool_name: str
    arguments: dict[str, Any]
    frame: dict[str, Any]
    answers: dict[str, Any]
    round_index: int
    result: dict[str, Any]
    status: str


def validate_answers(request_keys: list[str], resume: object) -> dict[str, Any]:
    """Check correspondence without rewriting keys or mutating supplied answers.

    The server remains responsible for validating form content and authorization.
    This deliberately supports the existing responses/action/content shape only.
    """
    if not isinstance(resume, dict) or set(resume) != {'responses'}:
        raise ValueError('RESUME_SHAPE')
    answers = resume['responses']
    if not isinstance(answers, dict) or set(answers) != set(request_keys):
        raise ValueError('ANSWER_KEYS_DIFFER')
    for answer in answers.values():
        if not isinstance(answer, dict) or set(answer) - {'action', 'content'}:
            raise ValueError('ANSWER_SHAPE')
        if answer.get('action') not in ('accept', 'decline', 'cancel'):
            raise ValueError('ANSWER_ACTION')
        content = answer.get('content')
        if answer['action'] != 'accept' and content is not None:
            raise ValueError('CONTENT_WITHOUT_ACCEPT')
        if content is not None and not isinstance(content, dict):
            raise ValueError('CONTENT_SHAPE')
    # Check serializability before committing the decision to the checkpoint.
    encoded = json.dumps(answers, allow_nan=False, ensure_ascii=False)
    if len(encoded.encode('utf-8')) > 1_048_576:
        raise ValueError('ANSWERS_TOO_LARGE')
    return deepcopy(answers)


def pack_result(result: Any) -> dict[str, Any]:
    from mcp.types import CallToolResult, InputRequiredResult
    if isinstance(result, InputRequiredResult):
        kind = 'input'
    elif isinstance(result, CallToolResult):
        kind = 'terminal'
    else:
        raise TypeError('UNSUPPORTED_TOOL_RESULT')
    return {'kind': kind, 'value': result.model_dump(mode='json', by_alias=True, exclude_none=True)}


def build_round_graph(session: Any, checkpointer: Any, *, max_rounds: int = 8):
    """Build an opt-in graph around a connected session's call_tool method.

    The graph checkpoints each tool response *before* the interrupting node.
    Use the same code, tool identity, checkpoint store and thread on resume.
    Treat stored frames as private application state, not model-visible output.
    Completed checkpointed rounds are reused. This cannot promise exactly-once
    remote effects across a crash between a server commit and its checkpoint.
    """
    from langgraph.graph import StateGraph, START, END
    from langgraph.types import interrupt
    from mcp.types import ElicitRequest, ElicitRequestFormParams, ElicitResult, InputRequiredResult
    if checkpointer is None or type(max_rounds) is not int or max_rounds < 1:
        raise ValueError('CHECKPOINTER_AND_POSITIVE_LIMIT_REQUIRED')

    async def begin(state: RoundState):
        name, arguments = state['tool_name'], state['arguments']
        if not isinstance(name, str) or not name or not isinstance(arguments, dict):
            raise ValueError('TOOL_INPUT_SHAPE')
        json.dumps(arguments, allow_nan=False)
        received = await session.call_tool(name, arguments, allow_input_required=True)
        return {'frame': pack_result(received), 'round_index': 1, 'status': 'received'}

    def review(state: RoundState):
        if state['round_index'] > max_rounds:
            raise ValueError('ROUND_LIMIT')
        result = InputRequiredResult.model_validate(state['frame']['value'])
        if not result.input_requests:
            raise ValueError('CONTINUATION_UNSUPPORTED')
        questions = []
        for key, request in result.input_requests.items():
            if not isinstance(request, ElicitRequest) or not isinstance(request.params, ElicitRequestFormParams):
                raise ValueError('FORM_REQUESTS_ONLY')
            questions.append({'key': key, 'mode': 'form', 'message': request.params.message,
                              'requested_schema': request.params.requested_schema})
        # No new tools/call here. The opaque request_state is not in this payload.
        resume = interrupt({'type': 'mcp_form_review', 'tool_name': state['tool_name'],
                            'round_index': state['round_index'], 'requests': questions})
        answers = validate_answers(list(result.input_requests), resume)
        for answer in answers.values():
            ElicitResult.model_validate(answer)
        return {'answers': answers, 'status': 'answered'}

    async def continue_original_round(state: RoundState):
        original = InputRequiredResult.model_validate(state['frame']['value'])
        answers = {key: ElicitResult.model_validate(value) for key, value in state['answers'].items()}
        received = await session.call_tool(
            state['tool_name'], state['arguments'],
            request_state=original.request_state, input_responses=answers,
            allow_input_required=True,
        )
        return {'frame': pack_result(received), 'answers': {},
                'round_index': state['round_index'] + 1, 'status': 'received'}

    def finish(state: RoundState):
        value = deepcopy(state['frame']['value'])
        return {'result': value, 'status': 'tool_error' if value.get('isError', False) else 'completed'}

    def next_node(state: RoundState):
        return 'review' if state['frame']['kind'] == 'input' else 'finish'

    builder = StateGraph(RoundState)
    builder.add_node('begin', begin)
    builder.add_node('review', review)
    builder.add_node('continue_original_round', continue_original_round)
    builder.add_node('finish', finish)
    builder.add_edge(START, 'begin')
    builder.add_conditional_edges('begin', next_node, ['review', 'finish'])
    builder.add_edge('review', 'continue_original_round')
    builder.add_conditional_edges('continue_original_round', next_node, ['review', 'finish'])
    builder.add_edge('finish', END)
    return builder.compile(checkpointer=checkpointer)
