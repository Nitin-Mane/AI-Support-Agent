import main
import ast
import contextlib
import io
import json
import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

os.environ['AWS_EC2_METADATA_DISABLED'] = 'true'


class LocalInterpreter:
    """Local test double executing the generated Python discount calculation in-process."""

    def invoke(self, operation, arguments):
        assert operation == 'executeCode'
        assert arguments['clearContext'] is True
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile(arguments['code'], '<discount>', 'exec'), {})
        return {'stream': iter([{'result': {'isError': False,
                'structuredContent': {'stdout': output.getvalue(), 'exitCode': 0}}}])}


@pytest.fixture
def interpreter(monkeypatch):
    @contextlib.contextmanager
    def session(region):
        yield LocalInterpreter()
    monkeypatch.setattr(main, 'code_session', session)


def test_gold_discount(interpreter):
    result = json.loads(main.calculate_loyalty_discount(4250, 'Gold', 150))
    assert result['points_redeemed'] == 4000
    assert result['tier_discount_pct'] == 10
    assert result['final_total'] == 99
    assert result['remaining_points'] == 349


def test_redemption_never_exceeds_half_order(interpreter):
    result = json.loads(main.calculate_loyalty_discount(20000, 'Silver', 19.99))
    assert result['points_redeemed'] == 500
    assert result['final_total'] == 14.99


def test_fallback_is_explicit_and_does_not_redeem(monkeypatch):
    monkeypatch.setattr(main, 'code_session', Mock(side_effect=RuntimeError('offline')))
    result = json.loads(main.calculate_loyalty_discount(4250, 'Gold', 150))
    assert result['calculation_mode'] == 'tier_only_fallback'
    assert result['points_redeemed'] == 0
    assert result['final_total'] == 135
    assert result['remaining_points'] == 4250


@pytest.mark.parametrize('points,tier,total,category', [
    (-1, 'Gold', 10, 'standard'), (1, 'Unknown', 10, 'standard'),
    (1, 'Gold', float('nan'), 'standard'), (1, 'Gold', -1, 'standard'),
    (1, 'Gold', 10, 'unknown'), (1.5, 'Gold', 10, 'standard'),
])
def test_invalid_discount_input(points, tier, total, category):
    assert 'error' in json.loads(main.calculate_loyalty_discount(points, tier, total, category))


def test_namespaces_support_both_sdk_formats():
    client = Mock()
    client.get_memory_strategies.return_value = [
        {'type': 'SEMANTIC', 'namespaceTemplates': ['cs_agent/{actorId}/facts']},
        {'type': 'USER_PREFERENCE', 'namespaces': ['cs_agent/{actorId}/preferences']},
    ]
    assert len(main.get_namespaces(client, 'memory')) == 2


def test_memory_saves_original_query_without_retrieved_context():
    client = Mock()
    client.get_memory_strategies.return_value = [
        {'type': 'SEMANTIC', 'namespaceTemplates': ['cs_agent/{actorId}/facts']},
        {'type': 'USER_PREFERENCE', 'namespaces': ['cs_agent/{actorId}/preferences']},
    ]
    client.retrieve_memories.return_value = [{'content': {'text': 'Prefers short answers'}}]
    hook = main.MemoryHook('CUST-123', 'new-session', client, 'memory')
    user = {'role': 'user', 'content': [{'text': 'What do you remember?'}]}
    agent = SimpleNamespace(messages=[user])
    hook.retrieve_customer_context(SimpleNamespace(agent=agent, message=user))
    assert 'Customer Context:' in user['content'][0]['text']
    assert client.retrieve_memories.call_count == 2
    assert {c.kwargs['namespace'] for c in client.retrieve_memories.call_args_list} == {
        'cs_agent/CUST-123/facts', 'cs_agent/CUST-123/preferences'}
    agent.messages.append({'role': 'assistant', 'content': [{'text': 'You prefer short answers.'}]})
    hook.save_support_interaction(SimpleNamespace(agent=agent, result=object()))
    assert client.create_event.call_args.kwargs['messages'] == [
        ('What do you remember?', 'USER'), ('You prefer short answers.', 'ASSISTANT')]


def test_tool_results_do_not_trigger_memory_retrieval():
    client = Mock()
    client.get_memory_strategies.return_value = []
    hook = main.MemoryHook('customer', 'session', client, 'memory')
    message = {'role': 'user', 'content': [{'toolResult': {'content': [{'text': 'result'}]}}]}
    hook.retrieve_customer_context(SimpleNamespace(message=message))
    client.retrieve_memories.assert_not_called()


def test_kb_joins_chunks_and_handles_missing_configuration(monkeypatch):
    monkeypatch.setattr(main, 'KB_ID', '')
    assert main.search_knowledge_base('policy') == 'Knowledge base not configured.'
    monkeypatch.setattr(main, 'KB_ID', 'ABC1234567')
    client = Mock()
    client.retrieve.return_value = {'retrievalResults': [
        {'content': {'text': 'A'}}, {'content': {'text': 'B'}}]}
    monkeypatch.setattr(main, '_bedrock_runtime', client)
    assert main.search_knowledge_base('policy') == 'A\n---\nB'


def test_entrypoint_rejects_empty_prompt():
    import asyncio
    assert asyncio.run(main.invoke({'prompt': ''}))['error'] == 'A non-empty prompt is required.'


def test_calculation_summary_uses_tool_values_instead_of_model_arithmetic():
    messages = [{'role': 'assistant', 'content': [{'toolUse': {'toolUseId': 'c1', 'name': 'calculate_loyalty_discount'}}]},
                {'role': 'user', 'content': [{'toolResult': {'toolUseId': 'c1', 'content': [{'text': json.dumps({
                    'points_redeemed': 4000, 'tier_discount_pct': 10, 'final_total': 99, 'remaining_points': 349,
                    'calculation_mode': 'code_interpreter'})}]}}]},
                {'role': 'assistant', 'content': [{'text': 'Your final total is $95.'}]}]
    response = main.verified_response(messages)
    assert '99' in response and '349' in response
    assert '$95' not in response


def test_missing_knowledge_base_does_not_allow_invented_policy():
    messages = [{'role': 'assistant', 'content': [{'toolUse': {'toolUseId': 'k1', 'name': 'search_knowledge_base'}}]},
                {'role': 'user', 'content': [
                    {'toolResult': {'toolUseId': 'k1', 'content': [{'text': 'Knowledge base not configured.'}]}}]},
                {'role': 'assistant', 'content': [{'text': 'Platinum gets 20% off.'}]}]
    assert main.verified_response(
        messages) == 'Knowledge base not configured. I cannot verify the requested catalog or policy information.'


def test_entrypoint_rejects_non_dict_payload():
    import asyncio
    assert 'error' in asyncio.run(main.invoke('not a dict'))


def test_entrypoint_validates_customer_id_format():
    import asyncio
    payload = {'prompt': 'hello', 'customer_id': 'invalid/id/with/slashes!'}
    result = asyncio.run(main.invoke(payload))
    assert 'error' in result
    assert 'invalid characters' in result['error']


def test_kb_empty_results(monkeypatch):
    monkeypatch.setattr(main, 'KB_ID', 'ABC1234567')
    client = Mock()
    client.retrieve.return_value = {'retrievalResults': []}
    monkeypatch.setattr(main, '_bedrock_runtime', client)
    assert main.search_knowledge_base('nonexistent') == 'No relevant information was found in the knowledge base.'


