import unittest
from types import SimpleNamespace

from main import (
    extract_assistant_reply,
    normalize_report_content,
    parse_coze_stream_response,
    remove_duplicate_title,
)


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


class ReportFormattingTests(unittest.TestCase):
    def test_remove_duplicate_title(self):
        report = "# 🔥 GitHub 每日热门项目 - 2026-04-12\n\n内容"
        self.assertEqual(remove_duplicate_title(report, "2026-04-12"), "内容")

    def test_normalize_report_content(self):
        report = (
            "# 🔥 GitHub 每日热门项目 - 2026-04-12\n\n"
            "TOP 5 热门项目\n\n"
            "#1. microsoft/markitdown · Python\n"
            "简短描述：文档转换工具\n"
            "项目链接：[GitHub](https://github.com/microsoft/markitdown)\n"
        )
        normalized = normalize_report_content(report, "2026-04-12")
        self.assertIn("TOP 10 热门项目", normalized)
        self.assertIn("🥇 1. microsoft/markitdown · Python", normalized)
        self.assertIn("简介：文档转换工具", normalized)
        self.assertIn("链接：https://github.com/microsoft/markitdown", normalized)


if __name__ == "__main__":
    unittest.main()
