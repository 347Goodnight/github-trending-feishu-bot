#!/usr/bin/env python3
import json
import os
import requests
from datetime import datetime

DIAGNOSE_VERSION = "2026-04-12-diagnose-fix-05"

COZE_API_TOKEN = os.getenv("COZE_API_TOKEN", "").strip()
COZE_BOT_ID = os.getenv("COZE_BOT_ID", "").strip()
COZE_WORKFLOW_ID = os.getenv("COZE_WORKFLOW_ID", "").strip()
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK", "").strip()

print("=" * 70)
print("Coze API diagnostic report")
print(f"version: {DIAGNOSE_VERSION}")
print(f"time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

print("\n[1] Environment variable check")
print("-" * 70)
configs = [
    ("FEISHU_WEBHOOK", FEISHU_WEBHOOK, False),
    ("COZE_API_TOKEN", COZE_API_TOKEN, True),
    ("COZE_BOT_ID", COZE_BOT_ID, False),
    ("COZE_WORKFLOW_ID", COZE_WORKFLOW_ID, False),
]

for name, value, is_sensitive in configs:
    if value:
        if is_sensitive and len(value) > 10:
            display = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else "***"
        else:
            display = value
        print(f"  OK  {name}: {display}")
    else:
        print(f"  MISS {name}: not set")
    print(f"       length: {len(value)}")

if not COZE_API_TOKEN or not COZE_BOT_ID:
    print("\nMissing COZE_API_TOKEN or COZE_BOT_ID, cannot continue.")
    raise SystemExit(1)

headers = {
    "Authorization": f"Bearer {COZE_API_TOKEN}",
    "Content-Type": "application/json",
}

print("\n[2] Test Coze Chat stream")
print("-" * 70)

create_payload = {
    "bot_id": COZE_BOT_ID,
    "user_id": "diagnostic-tool",
    "additional_messages": [
        {
            "role": "user",
            "content": "Please reply with: hello",
            "content_type": "text",
        }
    ],
    "stream": True,
}

print("  Step 1: POST /v3/chat (stream=true)")
resp = requests.post(
    "https://api.coze.cn/v3/chat",
    headers=headers,
    json=create_payload,
    stream=True,
    timeout=30,
)
print(f"  CREATE HTTP status: {resp.status_code}")

if resp.status_code != 200:
    print("  create request failed")
    raise SystemExit(1)

print("\n  Step 2: read stream events")
current_event = None
answer_chunks = []
completed_answer = ""
chat_failed = None

for raw_line in resp.iter_lines(decode_unicode=True):
    if raw_line is None:
        continue

    line = raw_line.strip()
    if not line:
        continue

    print(f"  STREAM {line[:300]}")

    if line.startswith("event:"):
        current_event = line[len("event:"):].strip()
        continue

    if not line.startswith("data:"):
        continue

    payload_text = line[len("data:"):].strip()
    if not payload_text or payload_text == '"[DONE]"':
        continue

    payload = json.loads(payload_text)
    if current_event == "conversation.message.delta":
        if payload.get("role") == "assistant" and payload.get("type") == "answer":
            answer_chunks.append(payload.get("content", ""))
    elif current_event == "conversation.message.completed":
        if payload.get("role") == "assistant" and payload.get("type") == "answer":
            completed_answer = payload.get("content", "")
    elif current_event == "conversation.chat.failed":
        chat_failed = payload.get("last_error", payload)

if chat_failed:
    print(f"  chat failed: {chat_failed}")
    raise SystemExit(1)

final_answer = completed_answer.strip() or "".join(answer_chunks).strip()
if not final_answer:
    print("  no assistant reply found in stream events")
    raise SystemExit(1)

print(f"  assistant preview: {final_answer[:200]}")

print("\n" + "=" * 70)
print("Diagnostic complete")
print("=" * 70)
