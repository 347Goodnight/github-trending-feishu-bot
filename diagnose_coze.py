#!/usr/bin/env python3
import os
import json
import time
import requests
from datetime import datetime

DIAGNOSE_VERSION = "2026-04-11-diagnose-fix-03"

COZE_API_TOKEN = os.getenv("COZE_API_TOKEN", "").strip()
COZE_BOT_ID = os.getenv("COZE_BOT_ID", "").strip()
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK", "").strip()

print("=" * 70)
print("🔍 Coze API 完整诊断报告")
print(f"版本: {DIAGNOSE_VERSION}")
print(f"⏰ 诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

print("\n【1】环境变量配置检查")
print("-" * 70)
configs = [
    ("FEISHU_WEBHOOK", FEISHU_WEBHOOK, False),
    ("COZE_API_TOKEN", COZE_API_TOKEN, True),
    ("COZE_BOT_ID", COZE_BOT_ID, False),
]

for name, value, is_sensitive in configs:
    if value:
        if is_sensitive and len(value) > 10:
            display = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else "***"
        else:
            display = value
        print(f"  ✅ {name}: {display}")
    else:
        print(f"  ❌ {name}: 未设置")
    print(f"     长度: {len(value)} 字符")

if not COZE_API_TOKEN or not COZE_BOT_ID:
    print("\n❌ 缺少 COZE_API_TOKEN 或 COZE_BOT_ID，无法继续诊断")
    raise SystemExit(1)

headers = {
    "Authorization": f"Bearer {COZE_API_TOKEN}",
    "Content-Type": "application/json"
}

print("\n【2】测试 Coze Chat API create -> retrieve 全链路")
print("-" * 70)

create_payload = {
    "bot_id": COZE_BOT_ID,
    "user_id": "diagnostic-tool",
    "additional_messages": [
        {
            "role": "user",
            "content": "请回复：你好",
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
print(f"  CREATE HTTP 状态码: {resp.status_code}")
print(f"  CREATE 响应体: {resp.text[:1000]}")

if resp.status_code != 200:
    print("  ❌ create 请求失败")
    raise SystemExit(1)

data = resp.json()
if data.get("code") != 0:
    print(f"  ❌ create 业务失败: code={data.get('code')}, msg={data.get('msg')}")
    raise SystemExit(1)

chat_data = data.get("data", {})
chat_obj_id = chat_data.get("id")
conversation_id = chat_data.get("conversation_id")

print(f"  object_id: {chat_obj_id}")
print(f"  conversation_id: {conversation_id}")
print(f"  status: {chat_data.get('status')}")

print("\n  Step 2: 等待 2 秒")
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
print(f"  RETRIEVE HTTP 状态码: {resp2.status_code}")
print(f"  RETRIEVE 请求体: {json.dumps(retrieve_payload, ensure_ascii=False)}")
print(f"  RETRIEVE 响应体: {resp2.text[:1000]}")

print("\n" + "=" * 70)
print("诊断完成")
print("=" * 70)
