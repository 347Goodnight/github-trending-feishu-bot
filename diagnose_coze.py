#!/usr/bin/env python3
import os
import json
import time
import requests
from datetime import datetime

DIAGNOSE_VERSION = "2026-04-12-diagnose-fix-04"

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
    "Content-Type": "application/json"
}

print("\n[2] Test Coze Chat create -> retrieve -> message/list")
print("-" * 70)

create_payload = {
    "bot_id": COZE_BOT_ID,
    "user_id": "diagnostic-tool",
    "additional_messages": [
        {
            "role": "user",
            "content": "Please reply with: hello",
            "content_type": "text"
        }
    ],
    "stream": False
}

print("  Step 1: POST /v3/chat")
resp = requests.post(
    "https://api.coze.cn/v3/chat",
    headers=headers,
    json=create_payload,
    timeout=30
)
print(f"  CREATE HTTP status: {resp.status_code}")
print(f"  CREATE response: {resp.text[:1000]}")

if resp.status_code != 200:
    print("  create request failed")
    raise SystemExit(1)

data = resp.json()
if data.get("code") != 0:
    print(f"  create business error: code={data.get('code')}, msg={data.get('msg')}")
    raise SystemExit(1)

chat_data = data.get("data", {})
chat_obj_id = chat_data.get("id")
conversation_id = chat_data.get("conversation_id")

print(f"  chat_id: {chat_obj_id}")
print(f"  conversation_id: {conversation_id}")
print(f"  status: {chat_data.get('status')}")

print("\n  Step 2: wait 2 seconds")
time.sleep(2)

print("\n  Step 3: POST /v3/chat/retrieve")
retrieve_payload = {
    "chat_id": chat_obj_id,
    "conversation_id": conversation_id
}
resp2 = requests.post(
    "https://api.coze.cn/v3/chat/retrieve",
    headers=headers,
    json=retrieve_payload,
    timeout=30
)
print(f"  RETRIEVE HTTP status: {resp2.status_code}")
print(f"  RETRIEVE request: {json.dumps(retrieve_payload, ensure_ascii=False)}")
print(f"  RETRIEVE response: {resp2.text[:1000]}")

if resp2.status_code != 200:
    print("  retrieve request failed")
    raise SystemExit(1)

data2 = resp2.json()
if data2.get("code") != 0:
    print(f"  retrieve business error: code={data2.get('code')}, msg={data2.get('msg')}")
    raise SystemExit(1)

print("\n  Step 4: POST /v1/conversation/message/list")
message_list_url = f"https://api.coze.cn/v1/conversation/message/list?conversation_id={conversation_id}"
message_list_payload = {
    "chat_id": chat_obj_id,
    "order": "desc",
    "limit": 20
}
resp3 = requests.post(
    message_list_url,
    headers=headers,
    json=message_list_payload,
    timeout=30
)
print(f"  MESSAGE LIST HTTP status: {resp3.status_code}")
print(f"  MESSAGE LIST request: {json.dumps(message_list_payload, ensure_ascii=False)}")
print(f"  MESSAGE LIST response: {resp3.text[:1000]}")

if resp3.status_code != 200:
    print("  message list request failed")
    raise SystemExit(1)

data3 = resp3.json()
if data3.get("code") != 0:
    print(f"  message list business error: code={data3.get('code')}, msg={data3.get('msg')}")
    raise SystemExit(1)

assistant_messages = [
    item for item in data3.get("data", [])
    if item.get("role") == "assistant" and isinstance(item.get("content"), str) and item.get("content").strip()
]

if not assistant_messages:
    print("  no assistant reply found in message list")
    raise SystemExit(1)

answer = next((item for item in assistant_messages if item.get("type") == "answer"), assistant_messages[0])
print(f"  assistant preview: {answer.get('content', '')[:200]}")

print("\n" + "=" * 70)
print("Diagnostic complete")
print("=" * 70)
