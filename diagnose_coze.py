#!/usr/bin/env python3
"""
完整的 Coze API 诊断工具
"""
import os
import json
import requests
from datetime import datetime

COZE_API_TOKEN = os.getenv("COZE_API_TOKEN", "").strip()
COZE_BOT_ID = os.getenv("COZE_BOT_ID", "").strip()
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK", "").strip()

print("=" * 70)
print("🔍 Coze API 完整诊断报告")
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

print("\n【2】Token 格式检查")
print("-" * 70)
if COZE_API_TOKEN:
    if COZE_API_TOKEN.startswith("pat_"):
        print("  ✅ Token 格式: Personal Access Token (pat_xxx)")
    elif COZE_API_TOKEN.startswith("bearer_"):
        print("  ⚠️  Token 格式: Bearer Token (bearer_xxx)")
    else:
        print(f"  ⚠️  Token 格式: 未知格式 (前缀: {COZE_API_TOKEN[:10]}...)")
    print(f"  Token 长度: {len(COZE_API_TOKEN)} 字符")
else:
    print("  ❌ 未提供 Token")

print("\n【3】Bot ID 检查")
print("-" * 70)
if COZE_BOT_ID:
    print(f"  Bot ID: {COZE_BOT_ID}")
    print(f"  Bot ID 长度: {len(COZE_BOT_ID)} 字符")
    if COZE_BOT_ID.isdigit():
        print("  ✅ Bot ID 为纯数字")
    elif COZE_BOT_ID.replace("-", "").isalnum():
        print("  ✅ Bot ID 格式正常 (可能为 UUID)")
else:
    print("  ❌ 未提供 Bot ID")

print("\n【4】测试 Coze Chat API v3")
print("-" * 70)

if not COZE_API_TOKEN or not COZE_BOT_ID:
    print("  ❌ 缺少必要的配置信息")
else:
    url = "https://api.coze.cn/v3/chat"
    headers = {
        "Authorization": f"Bearer {COZE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "bot_id": COZE_BOT_ID,
        "user_id": "diagnostic-tool",
        "additional_messages": [
            {
                "role": "user",
                "content": "你好",
                "content_type": "text"
            }
        ],
        "stream": False
    }

    print(f"  📡 请求信息:")
    print(f"     URL: {url}")
    print(f"     Method: POST")
    print(f"     Headers: Authorization=Bearer {COZE_API_TOKEN[:15]}...")

    try:
        print(f"\n  ⏳ 正在发送请求...")
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"\n  📥 响应信息:")
        print(f"     HTTP 状态码: {resp.status_code}")
        print(f"     响应头: {dict(resp.headers)}")
        print(f"\n  📄 响应体 (原始):")
        print(f"     {resp.text[:500]}")
        
        try:
            data = resp.json()
            print(f"\n  📄 响应体 (格式化):")
            print(f"     {json.dumps(data, ensure_ascii=False, indent=2)[:800]}")
        except:
            pass
        
        if resp.status_code == 200:
            print("\n  ✅ HTTP 请求成功!")
            data = resp.json()
            if data.get("code") == 0:
                print("  ✅ 业务逻辑成功!")
            else:
                print(f"  ❌ 业务逻辑失败: code={data.get('code')}, msg={data.get('msg')}")
        else:
            print(f"\n  ❌ HTTP 请求失败!")
            if resp.status_code == 401:
                print("     → 认证失败，请检查 Token 是否正确")
            elif resp.status_code == 403:
                print("     → 权限不足，请检查 Token 权限")
            elif resp.status_code == 404:
                print("     → Bot 未找到，请检查 Bot ID")
            elif resp.status_code == 410:
                print("     → 资源不可用，请检查 Bot 是否已发布")
            else:
                print(f"     → 未知错误")
                
    except requests.exceptions.Timeout:
        print("\n  ❌ 请求超时")
    except requests.exceptions.ConnectionError as e:
        print(f"\n  ❌ 连接失败: {e}")
    except Exception as e:
        print(f"\n  ❌ 发生异常: {e}")

print("\n" + "=" * 70)
print("诊断完成")
print("=" * 70)
