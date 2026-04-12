import unittest
from types import SimpleNamespace

from main import extract_assistant_reply, parse_coze_stream_response


class ExtractAssistantReplyTests(unittest.TestCase):
    def test_prefers_answer_message(self):
        messages = [
            {"role": "assistant", "type": "verbose", "content": "{\"status\":\"done\"}"},
            {"role": "assistant", "type": "answer", "content": "report content"},
        ]

        self.assertEqual(extract_assistant_reply(messages), "report content")

    def test_falls_back_to_any_assistant_content(self):
        messages = [
            {"role": "user", "type": "question", "content": "hello"},
            {"role": "assistant", "type": "card", "content": "card content"},
        ]

        self.assertEqual(extract_assistant_reply(messages), "card content")


class ParseCozeStreamResponseTests(unittest.TestCase):
    def test_returns_completed_answer(self):
        lines = [
            "event:conversation.chat.created",
            'data:{"id":"1","conversation_id":"2","status":"created"}',
            "",
            "event:conversation.message.delta",
            'data:{"role":"assistant","type":"answer","content":"hello "}',
            "",
            "event:conversation.message.completed",
            'data:{"role":"assistant","type":"answer","content":"hello world"}',
            "",
            "event:done",
            'data:"[DONE]"',
        ]
        resp = SimpleNamespace(
            iter_lines=lambda decode_unicode=True: iter(lines),
            text="\n".join(lines),
        )

        self.assertEqual(parse_coze_stream_response(resp), "hello world")

    def test_handles_multiline_sse_data(self):
        lines = [
            "event:conversation.message.completed",
            'data:{"role":"assistant","type":"answer",',
            'data:"content":"hello world"}',
            "",
            "event:done",
            'data:"[DONE]"',
        ]
        resp = SimpleNamespace(
            iter_lines=lambda decode_unicode=True: iter(lines),
            text="\n".join(lines),
        )

        self.assertEqual(parse_coze_stream_response(resp), "hello world")

    def test_handles_bare_continuation_line(self):
        lines = [
            "event:conversation.message.completed",
            'data:{"role":"assistant","type":"answer","content":"hello',
            ' world"}',
            "",
            "event:done",
            'data:"[DONE]"',
        ]
        resp = SimpleNamespace(
            iter_lines=lambda decode_unicode=True: iter(lines),
            text="\n".join(lines),
        )

        self.assertEqual(parse_coze_stream_response(resp), "hello world")

    def test_decodes_utf8_bytes(self):
        lines = [
            b"event:conversation.message.completed",
            '{"role":"assistant","type":"answer","content":"你好"}'.encode("utf-8").join([b"data:", b""]),
            b"",
            b"event:done",
            b'data:"[DONE]"',
        ]
        resp = SimpleNamespace(
            iter_lines=lambda decode_unicode=False: iter(lines),
            text="",
        )

        self.assertEqual(parse_coze_stream_response(resp), "你好")


if __name__ == "__main__":
    unittest.main()
