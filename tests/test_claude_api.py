"""SPEC NFR-7 › MVP：Claude（API）轉接器的離線驗收：用假的 SDK client，不連網、不需要 API key。"""
from __future__ import annotations

import asyncio
import contextlib
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import uuid

import anthropic
import httpx2

from app.storage import turns
from app.web import __main__ as web_main
from app.web import bridges, claude_api
from app.web.config import ConfigError
from app.web.runner import Failed, Hooks, Interrupted, TurnInput

REQUEST = httpx2.Request('POST', 'https://api.anthropic.com/v1/messages')


def status_error(cls, status, error_type, message='原始錯誤訊息'):
    response = httpx2.Response(status, request=REQUEST, headers={'request-id': 'req_test'})
    return cls(message, response=response, body={'error': {'type': error_type, 'message': message}})


def reply(text='你好', stop_reason='end_turn'):
    blocks = [SimpleNamespace(type='thinking', thinking='想一下')]
    if text is not None:
        blocks.append(SimpleNamespace(type='text', text=text))
    return SimpleNamespace(content=blocks, stop_reason=stop_reason)


def block_events(message):
    """依訊息的內容區塊產生串流事件：每個區塊一個開始、一個結束。"""
    events = []
    for index, block in enumerate(message.content):
        events.append(SimpleNamespace(type='content_block_start', index=index,
                                      content_block=SimpleNamespace(type=block.type)))
        events.append(SimpleNamespace(type='content_block_stop', index=index))
    return events


class FakeStream:
    def __init__(self, messages):
        self.messages = messages
        self.read_all = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def __aiter__(self):
        self.messages.started.set()
        try:
            await asyncio.sleep(self.messages.delay)
        except asyncio.CancelledError:
            self.messages.cancelled = True
            raise
        if self.messages.error is not None:
            raise self.messages.error
        events = self.messages.events if self.messages.events is not None else block_events(self.messages.message)
        for event in events:
            yield event
        self.read_all = True

    async def get_final_message(self):
        assert self.read_all, '要先讀完串流'
        return self.messages.message


class FakeMessages:
    def __init__(self, *, message=None, input_tokens=0, error=None, count_error=None, delay=0.0, events=None):
        self.message = message if message is not None else reply()
        self.events = events
        self.input_tokens, self.error, self.count_error, self.delay = input_tokens, error, count_error, delay
        self.counted, self.streamed, self.cancelled = [], [], False
        self.started = asyncio.Event()

    async def count_tokens(self, **params):
        self.counted.append(params)
        if self.count_error is not None:
            raise self.count_error
        return SimpleNamespace(input_tokens=self.input_tokens)

    def stream(self, **params):
        self.streamed.append(params)
        return FakeStream(self)


def turn_input(**changes):
    base = dict(turn_id=str(uuid.uuid4()), conversation_id=str(uuid.uuid4()), member=str(uuid.uuid4()),
                message='這次的問題', timeout=60, adapter='claude_api', auth_mode='api_key')
    return TurnInput(**{**base, **changes})


class Recorder:
    def __init__(self):
        self.saved, self.began, self.progress = [], [], []
        self.hooks = Hooks(began=self.began.append, progress=self.progress.append,
                           save=lambda text, session=None, thinking_seconds=None:
                           self.saved.append((text, session, thinking_seconds)))


def ticking(*times):
    """假的時鐘：每呼叫一次回傳下一個時間。"""
    values = iter(times)
    return lambda: next(values)


class RunnerTest(unittest.IsolatedAsyncioTestCase):
    async def run_turn(self, messages, clock=None, **changes):
        runner = claude_api.ClaudeApiRunner(SimpleNamespace(messages=messages), **({'clock': clock} if clock else {}))
        recorder = Recorder()
        await runner.run(turn_input(**changes), recorder.hooks)
        return recorder

    async def failed_kind(self, messages, **changes):
        with self.assertRaises(Failed) as caught:
            await self.run_turn(messages, **changes)
        return caught.exception.kind

    async def test_reply_is_saved_with_history_default_model_and_no_tools(self):
        messages = FakeMessages(message=reply('答案'))
        recorder = await self.run_turn(messages, clock=ticking(10.0, 12.5), history=(('第一題', '第一答'),))
        # 只存文字，不存思考內容；沒有對話身分；思考區塊從 10.0 秒開始、12.5 秒結束。
        self.assertEqual(recorder.saved, [('答案', None, 2.5)])
        self.assertEqual(recorder.progress, [{'kind': 'phase', 'phase': 'thinking'},
                                             {'kind': 'phase', 'phase': 'answering'}])
        self.assertEqual(recorder.began, [])  # 不呼叫 began：重啟後回合標為未知
        [params] = messages.streamed
        self.assertEqual(params['model'], 'claude-opus-5-5')
        self.assertEqual(params['thinking'], {'type': 'adaptive'})  # 一律開啟；不要求回傳思考內容
        self.assertEqual(params['messages'], [{'role': 'user', 'content': '第一題'},
                                              {'role': 'assistant', 'content': '第一答'},
                                              {'role': 'user', 'content': '這次的問題'}])
        self.assertEqual(params['cache_control'], {'type': 'ephemeral'})
        self.assertEqual(params['max_tokens'], claude_api.MAX_OUTPUT)
        self.assertNotIn('tools', params)
        self.assertNotIn('output_config', params)  # 沒設推理強度就用模型預設
        self.assertEqual(messages.counted, [])  # 沒設花費上限就不必計數

    async def test_thinking_only_for_models_that_support_adaptive_thinking(self):
        for model, expected in (('claude-sonnet-5-5', {'type': 'adaptive'}), ('claude-haiku-5-5', {'type': 'adaptive'}),
                                ('claude-haiku-4-5', None), ('claude-unknown', None)):
            with self.subTest(model=model):
                messages = FakeMessages(message=reply('好', stop_reason='end_turn'))
                await self.run_turn(messages, clock=ticking(0.0, 1.0), model=model)
                self.assertEqual(messages.streamed[0].get('thinking'), expected)

    async def test_no_thinking_block_means_no_thinking_time(self):
        messages = FakeMessages(message=SimpleNamespace(content=[SimpleNamespace(type='text', text='直接答')],
                                                        stop_reason='end_turn'))
        recorder = await self.run_turn(messages)
        self.assertEqual(recorder.saved, [('直接答', None, None)])
        self.assertEqual(recorder.progress, [{'kind': 'phase', 'phase': 'answering'}])

    async def test_thinking_time_adds_up_blocks_and_phase_is_reported_on_change_only(self):
        def start(index, kind):
            return SimpleNamespace(type='content_block_start', index=index, content_block=SimpleNamespace(type=kind))

        def stop(index):
            return SimpleNamespace(type='content_block_stop', index=index)

        events = [start(0, 'thinking'), stop(0), start(1, 'redacted_thinking'), stop(1),
                  start(2, 'text'), stop(2), start(3, 'thinking'), stop(3), start(4, 'text'), stop(4)]
        messages = FakeMessages(message=reply('答'), events=events)
        recorder = await self.run_turn(messages, clock=ticking(0.0, 1.0, 1.0, 1.25, 5.0, 5.5))
        self.assertEqual(recorder.saved, [('答', None, 1.8)])  # 1.0 + 0.25 + 0.5，取到小數一位
        self.assertEqual([item['phase'] for item in recorder.progress],
                         ['thinking', 'answering', 'thinking', 'answering'])

    async def test_model_and_effort_come_from_member_settings(self):
        messages = FakeMessages()
        await self.run_turn(messages, model='claude-sonnet-5-5', effort='low')
        [params] = messages.streamed
        self.assertEqual((params['model'], params['output_config']), ('claude-sonnet-5-5', {'effort': 'low'}))

    async def test_budget_caps_output_and_counts_the_same_input(self):
        messages = FakeMessages(input_tokens=0)
        await self.run_turn(messages, budget=0.1)
        [counted], [streamed] = messages.counted, messages.streamed
        self.assertEqual(streamed['max_tokens'], 5000)  # 0.1 美元 ÷ 每百萬 20 美元
        self.assertEqual(counted, {key: value for key, value in streamed.items() if key != 'max_tokens'})

    async def test_large_budget_keeps_the_normal_output_limit(self):
        messages = FakeMessages(input_tokens=0)
        await self.run_turn(messages, budget=100)
        self.assertEqual(messages.streamed[0]['max_tokens'], claude_api.MAX_OUTPUT)

    async def test_budget_too_small_is_refused_before_sending(self):
        for budget, tokens in ((0.01, 0), (1.0, 200_000)):
            with self.subTest(budget=budget, tokens=tokens):
                messages = FakeMessages(input_tokens=tokens)
                self.assertEqual(await self.failed_kind(messages, budget=budget), turns.BUDGET_EXCEEDED)
                self.assertEqual(messages.streamed, [])

    async def test_unpriced_model_with_budget_is_refused_without_any_request(self):
        messages = FakeMessages()
        self.assertEqual(await self.failed_kind(messages, model='claude-unknown', budget=1.0), turns.MODEL_UNAVAILABLE)
        self.assertEqual((messages.counted, messages.streamed), ([], []))
        # 沒設上限時不需要價格表，照常送出（模型存不存在由 API 判斷）。
        await self.run_turn(FakeMessages(), model='claude-unknown')

    async def test_cut_off_reply_is_not_saved(self):
        cases = [(None, turns.REPLY_TOO_LONG), (0.1, turns.BUDGET_EXCEEDED), (100, turns.REPLY_TOO_LONG)]
        for budget, kind in cases:
            with self.subTest(budget=budget):
                messages = FakeMessages(message=reply('一半', stop_reason='max_tokens'))
                self.assertEqual(await self.failed_kind(messages, budget=budget), kind)

    async def test_input_too_big_for_budget_with_history_is_conversation_too_long(self):
        history = (('第一題', '第一答'),)
        cases = [
            # (上限, 輸入 token, 前文, 結果)：上限本身夠輸出 1,024 token、卻被輸入吃掉，而且有前文 → 對話太長
            (1.0, 200_000, history, turns.CONVERSATION_TOO_LONG),
            (1.0, 199_000, history, turns.CONVERSATION_TOO_LONG),  # 剩下的不到 1,024 token
            (1.0, 200_000, (), turns.BUDGET_EXCEEDED),  # 沒有前文：開新對話也沒用
            (0.01, 0, history, turns.BUDGET_EXCEEDED),  # 上限本身就不夠
        ]
        for budget, tokens, past, kind in cases:
            with self.subTest(budget=budget, tokens=tokens, history=bool(past)):
                messages = FakeMessages(input_tokens=tokens)
                self.assertEqual(await self.failed_kind(messages, budget=budget, history=past), kind)
                self.assertEqual(messages.streamed, [])

    async def test_reply_cut_by_context_window_is_conversation_too_long(self):
        messages = FakeMessages(message=reply('一半', stop_reason='model_context_window_exceeded'))
        self.assertEqual(await self.failed_kind(messages), turns.CONVERSATION_TOO_LONG)

    async def test_refusal_and_empty_reply_fail(self):
        self.assertEqual(await self.failed_kind(FakeMessages(message=reply('', stop_reason='refusal'))), turns.REFUSED)
        self.assertEqual(await self.failed_kind(FakeMessages(message=reply(None))), turns.INTERNAL_ERROR)
        self.assertEqual(await self.failed_kind(FakeMessages(message=reply('  \n'))), turns.INTERNAL_ERROR)

    async def test_api_errors_are_classified_and_raw_message_is_not_logged(self):
        error = status_error(anthropic.AuthenticationError, 401, 'authentication_error', '不能外流的原文')
        for messages in (FakeMessages(error=error), FakeMessages(count_error=error)):
            with self.assertLogs('app.web.claude_api', 'WARNING') as logs:
                self.assertEqual(await self.failed_kind(messages, budget=1.0), turns.AUTH_FAILED)
            self.assertIn('auth_failed', logs.output[0])
            self.assertIn('req_test', logs.output[0])
            self.assertNotIn('不能外流的原文', '\n'.join(logs.output))

    async def test_timeout_cancels_the_request(self):
        messages = FakeMessages(delay=30)
        self.assertEqual(await self.failed_kind(messages, timeout=0.05), turns.TIMEOUT)
        self.assertTrue(messages.cancelled)

    async def test_stop_cancels_the_request_and_reports_interrupted(self):
        messages = FakeMessages(delay=30)
        runner = claude_api.ClaudeApiRunner(SimpleNamespace(messages=messages))
        turn = turn_input()
        recorder = Recorder()
        task = asyncio.create_task(runner.run(turn, recorder.hooks))
        await messages.started.wait()
        await runner.stop(turn.turn_id)
        with self.assertRaises(Interrupted):
            await task
        self.assertTrue(messages.cancelled)
        self.assertEqual(recorder.saved, [])

    async def test_stop_before_run_sends_nothing(self):
        messages = FakeMessages()
        runner = claude_api.ClaudeApiRunner(SimpleNamespace(messages=messages))
        turn = turn_input()
        await runner.stop(turn.turn_id)
        with self.assertRaises(Interrupted):
            await runner.run(turn, Recorder().hooks)
        self.assertEqual((messages.counted, messages.streamed), ([], []))
        await runner.run(turn_input(), Recorder().hooks)  # 只影響被中斷的那個回合

    async def test_server_shutdown_cancels_the_request_and_propagates(self):
        messages = FakeMessages(delay=30)
        runner = claude_api.ClaudeApiRunner(SimpleNamespace(messages=messages))
        task = asyncio.create_task(runner.run(turn_input(), Recorder().hooks))
        await messages.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(messages.cancelled)


class ClassifyTest(unittest.TestCase):
    def test_fixed_categories(self):
        cases = [
            (status_error(anthropic.AuthenticationError, 401, 'authentication_error'), turns.AUTH_FAILED),
            (status_error(anthropic.PermissionDeniedError, 403, 'permission_error'), turns.AUTH_FAILED),
            (status_error(anthropic.APIStatusError, 402, 'billing_error'), turns.QUOTA_EXCEEDED),
            (status_error(anthropic.BadRequestError, 400, 'invalid_request_error',
                          'Your credit balance is too low to access the Anthropic API.'), turns.QUOTA_EXCEEDED),
            (status_error(anthropic.BadRequestError, 400, 'invalid_request_error', 'bad field'), turns.INTERNAL_ERROR),
            (status_error(anthropic.BadRequestError, 400, 'invalid_request_error',
                          'prompt is too long: 1000123 tokens > 1000000 maximum'), turns.CONVERSATION_TOO_LONG),
            (status_error(anthropic.APIStatusError, 413, 'request_too_large'), turns.CONVERSATION_TOO_LONG),
            (status_error(anthropic.NotFoundError, 404, 'not_found_error'), turns.MODEL_UNAVAILABLE),
            (status_error(anthropic.RateLimitError, 429, 'rate_limit_error'), turns.SERVICE_BUSY),
            (status_error(anthropic.InternalServerError, 529, 'overloaded_error'), turns.SERVICE_BUSY),
            (status_error(anthropic.InternalServerError, 500, 'api_error'), turns.SERVICE_BUSY),
            (anthropic.APIConnectionError(request=REQUEST), turns.SERVICE_BUSY),
            (anthropic.APITimeoutError(request=REQUEST), turns.SERVICE_BUSY),
        ]
        for error, kind in cases:
            with self.subTest(error=type(error).__name__, status=getattr(error, 'status_code', None)):
                self.assertEqual(claude_api.classify(error), kind)
                self.assertIn(kind, turns.ERROR_KINDS)


class PriceTest(unittest.TestCase):
    def test_output_limit(self):
        self.assertEqual(claude_api.output_limit(1.0, 'claude-opus-5-5', 0), 50_000)
        self.assertEqual(claude_api.output_limit(1.0, 'claude-opus-5-5', 200_000), 0)  # 輸入就花完了
        self.assertIsNone(claude_api.output_limit(1.0, 'claude-unknown', 0))

    def test_haiku_5_5_uses_higher_price_above_100k_input(self):
        self.assertEqual(claude_api.prices('claude-haiku-5-5', 100_000), (0.10, 0.50))
        self.assertEqual(claude_api.prices('claude-haiku-5-5', 100_001), (0.50, 2.50))

    def test_default_model_is_priced(self):
        self.assertIsNotNone(claude_api.prices(claude_api.DEFAULT_MODEL, 0))


class BuildTest(unittest.TestCase):
    def test_missing_key_refuses_to_start(self):
        with mock.patch.dict('os.environ', {claude_api.KEY_ENV: ''}):
            with self.assertRaisesRegex(ConfigError, claude_api.KEY_ENV):
                claude_api.build()
            with self.assertRaises(ConfigError):
                bridges.runners((claude_api.CODE,), '/nonexistent')

    def test_server_command_prints_one_line_and_exits_without_key(self):
        with tempfile.TemporaryDirectory(prefix='yiqunren-claude-api-test-') as temporary, \
                mock.patch.dict('os.environ', {claude_api.KEY_ENV: ''}), \
                mock.patch('app.web.__main__.uvicorn.run') as run, \
                contextlib.redirect_stderr(io.StringIO()) as stderr:
            env = {'YIQUNREN_STATE_DIR': str(Path(temporary) / 'state'), 'YIQUNREN_BRIDGES': claude_api.CODE}
            self.assertEqual(web_main.main([], env), 2)
        run.assert_not_called()
        self.assertEqual(stderr.getvalue(),
                         '設定錯誤：要接上 Claude（API）必須在啟動後端的環境裡設定 %s\n' % claude_api.KEY_ENV)

    def test_bridges_setting_builds_in_process_runner(self):
        with mock.patch.dict('os.environ', {claude_api.KEY_ENV: 'test-placeholder'}):
            found = bridges.runners((claude_api.CODE,), '/nonexistent')
        self.assertIsInstance(found[claude_api.CODE], claude_api.ClaudeApiRunner)


if __name__ == '__main__':
    unittest.main()
