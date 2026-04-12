import unittest

from main import extract_assistant_reply


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


if __name__ == "__main__":
    unittest.main()
