#!/usr/bin/env python3
"""
测试 Coze API 连接
"""
import os
import json
import requests

# 从环境变量读取配置
COZE_API_TOKEN = os.getenv("COZE_API_TOKEN", "").strip()
COZE_BOT_ID = os.getenv("COZE_BOT_ID", "").strip()

def test_coze_api():
    print("=" * 60)
    print("Coze API 测试")
    print("=" * 60)
    
    # 检查环境变量
    print(f"\n1. 环境变量检查:")
    print(f"   COZE_API_TOKEN: {'已设置' if COZE_API_TOKEN else '未设置'} (长度: {len(COZE_API_TOKEN)})")
    print(f"   COZE_BOT_ID: {'已设置' if COZE_BOT_ID else '未设置'} (值: {COZE_BOT_ID})")
    
    if not COZE_API_TOKEN or not COZE_BOT_ID:
        print("\n❌ 错误: COZE_API_TOKEN 或 COZE_BOT_ID 未设置")
        return
    
    # 显示 token 前缀（用于调试，不显示完整 token）
    print(f"\n2. Token 信息:")
    print(f"   Token 前缀: {COZE_API_TOKEN[:15]}...")
    print(f"   Token 长度: {len(COZE_API_TOKEN)}")
    
    # 测试 API 调用
    print(f"\n3. 测试 API 调用:")
    url = "https://api.coze.cn/v3/chat"
    headers = {
        "Authorization": f"Bearer {COZE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "bot_id": COZE_BOT_ID,
        "user_id": "test-user",
        "additional_messages": [
            {
                "role": "user",
                "content": "Hello, this is a test message.",
                "content_type": "text"
            }
        ],
        "stream": False
    }
    
    print(f"   URL: {url}")
    print(f"   Bot ID: {COZE_BOT_ID}")
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"\n4. 响应结果:")
        print(f"   HTTP 状态码: {resp.status_code}")
        print(f"   响应内容: {resp.text[:1000]}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n✅ API 调用成功!")
            print(f"   响应数据结构: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
        else:
            print(f"\n❌ API 调用失败!")
            print(f"   错误信息: {resp.text}")
            
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_coze_api()
