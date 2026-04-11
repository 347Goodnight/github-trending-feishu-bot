#!/usr/bin/env python3
"""
GitHub Trending 飞书机器人
自动抓取 GitHub Trending，通过 Coze AI 生成日报，推送到飞书群
"""
import os
import re
import json
import time
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# 版本号
CODE_VERSION = "2026-04-11-main-fix-03"

# 配置
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK", "").strip()
COZE_API_TOKEN = os.getenv("COZE_API_TOKEN", "").strip()
COZE_BOT_ID = os.getenv("COZE_BOT_ID", "").strip()
COZE_WORKFLOW_ID = os.getenv("COZE_WORKFLOW_ID", "").strip()
HTTP_PROXY = os.getenv("HTTP_PROXY", "").strip()
HTTPS_PROXY = os.getenv("HTTPS_PROXY", "").strip()

PROXIES = None
if HTTP_PROXY or HTTPS_PROXY:
    PROXIES = {
        "http": HTTP_PROXY if HTTP_PROXY else None,
        "https": HTTPS_PROXY if HTTPS_PROXY else None
    }


def log(msg):
    """打印日志"""
    print(f"[LOG] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")


def request_kwargs(timeout):
    """统一 requests 参数"""
    return {
        "proxies": PROXIES if PROXIES else None,
        "timeout": timeout
    }


def get_today_str():
    """获取今日日期字符串"""
    return datetime.now().strftime("%Y-%m-%d")


def build_prompt(date_str, repos):
    """构建 Coze 提示词"""
    prompt = f"""请根据以下 {date_str} 的 GitHub Trending 数据，生成一份技术日报。

要求：
1. 标题使用 🔥 GitHub 每日热门项目 - {date_str}
2. 分析今日趋势（2-3 句话总结）
3. 列出 TOP 5 项目，每个项目包含：
   - 项目名称和语言
   - ⭐ 今日新增 stars 数
   - 简短描述（中文）
   - 项目链接
4. 使用 Markdown 格式
5. 语气专业但轻松

数据：
"""
    for i, repo in enumerate(repos[:10], 1):
        prompt += f"\n{i}. {repo['name']} ({repo['language']})\n"
        prompt += f"   Stars: {repo['stars']}, Today: +{repo['stars_today']}\n"
        prompt += f"   Description: {repo['description']}\n"
        prompt += f"   URL: {repo['url']}\n"
    
    return prompt


def fetch_github_trending(top_n=10):
    """抓取 GitHub Trending"""
    log("Fetching GitHub Trending...")
    url = "https://github.com/trending"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    resp = requests.get(url, headers=headers, **request_kwargs(30))
    soup = BeautifulSoup(resp.text, "html.parser")
    
    repos = []
    articles = soup.find_all("article", class_="Box-row")
    
    for article in articles[:top_n]:
        try:
            # 项目名称
            h2 = article.find("h2")
            if not h2:
                continue
            name = h2.get_text(strip=True).replace(" ", "").replace("\n", "")
            
            # 描述
            p = article.find("p", class_="col-9")
            description = p.get_text(strip=True) if p else "No description"
            
            # 语言
            lang_span = article.find("span", itemprop="programmingLanguage")
            language = lang_span.get_text(strip=True) if lang_span else "Unknown"
            
            # Stars
            stars_link = article.find("a", href=re.compile(r"/stargazers$"))
            stars = stars_link.get_text(strip=True).replace(",", "") if stars_link else "0"
            
            # 今日新增
            today_span = article.find("span", class_="d-inline-block float-sm-right")
            stars_today = "0"
            if today_span:
                text = today_span.get_text(strip=True)
                match = re.search(r"([\d,]+)", text)
                if match:
                    stars_today = match.group(1).replace(",", "")
            
            repos.append({
                "name": name,
                "description": description,
                "language": language,
                "stars": stars,
                "stars_today": stars_today,
                "url": f"https://github.com/{name}"
            })
        except Exception as e:
            log(f"Error parsing repo: {e}")
            continue
    
    log(f"Fetched {len(repos)} repos from GitHub Trending.")
    return repos


def parse_coze_response(resp_data):
    """
    解析 Coze 响应，提取 assistant 的消息内容
    支持：
    1. 直接传完整 resp.json()
    2. 直接传 data["data"]
    """
    if not isinstance(resp_data, dict):
        raise RuntimeError(f"Invalid Coze response type: {type(resp_data)}")
    candidates = []
    # 如果是完整响应，优先尝试 data
    if isinstance(resp_data.get("data"), dict):
        candidates.append(resp_data["data"])
    # 再尝试顶层本身
    candidates.append(resp_data)
    for candidate in candidates:
        messages = candidate.get("messages", [])
        if isinstance(messages, list):
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if isinstance(content, str) and content.strip():
                        log(f"Got response from assistant message, length={len(content)}")
                        return content.strip()
        content = candidate.get("content", "")
        if isinstance(content, str) and content.strip():
            log(f"Got response from content, length={len(content)}")
            return content.strip()
        output = candidate.get("output", "")
        if isinstance(output, str) and output.strip():
            log(f"Got response from output, length={len(output)}")
            return output.strip()
    raise RuntimeError(
        f"Unable to parse chat response: {json.dumps(resp_data, ensure_ascii=False)[:1000]}"
    )


def call_coze_chat_api(date_str, repos):
    """
    调用 Coze Chat API (异步轮询)
    """
    if not COZE_API_TOKEN or not COZE_BOT_ID:
        raise RuntimeError("COZE_API_TOKEN or COZE_BOT_ID is missing.")
    prompt = build_prompt(date_str, repos)
    headers = {
        "Authorization": f"Bearer {COZE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    # Step 1: 创建 chat
    log("Step 1: Creating Coze chat...")
    create_url = "https://api.coze.cn/v3/chat"
    payload = {
        "bot_id": COZE_BOT_ID,
        "user_id": "github-trending-bot",
        "additional_messages": [
            {
                "role": "user",
                "content": prompt,
                "content_type": "text"
            }
        ],
        "stream": False
    }
    resp = requests.post(
        create_url,
        headers=headers,
        json=payload,
        **request_kwargs(60)
    )
    log(f"Create chat status: {resp.status_code}")
    log(f"Create chat raw response: {resp.text[:1000]}")
    if resp.status_code != 200:
        raise RuntimeError(f"Create chat error: {resp.status_code}, {resp.text}")
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(
            f"Create chat business error: {data.get('code')}, {data.get('msg')}, resp={resp.text[:500]}"
        )
    chat_data = data.get("data", {})
    chat_obj_id = chat_data.get("id")
    conversation_id = chat_data.get("conversation_id")
    status = chat_data.get("status")
    log(f"Create chat parsed data: {json.dumps(chat_data, ensure_ascii=False)}")
    if not chat_obj_id:
        raise RuntimeError(f"No id in response: {resp.text[:500]}")
    log(
        f"Chat created: object_id={chat_obj_id}, "
        f"conversation_id={conversation_id}, status={status}"
    )
    # 如果创建接口直接返回 completed，就直接解析
    if status == "completed":
        return parse_coze_response(data)
    if status == "failed":
        last_error = chat_data.get("last_error", {})
        raise RuntimeError(f"Chat failed on create: {last_error}")
    # Step 2: 轮询
    log("Step 2: Polling for chat result...")
    max_retries = 10
    initial_delay = 2
    max_delay = 5
    for i in range(max_retries):
        retry_delay = min(initial_delay + i * 0.5, max_delay)
        time.sleep(retry_delay)
        retrieve_url = "https://api.coze.cn/v3/chat/retrieve"
        retrieve_payload = {
            "chat_id": chat_obj_id,
            "conversation_id": conversation_id
        }
        log(f"Poll {i+1}/{max_retries}: POST {retrieve_url}")
        log(f"Poll {i+1}/{max_retries}: payload={retrieve_payload}")
        resp = requests.post(
            retrieve_url,
            headers=headers,
            json=retrieve_payload,
            **request_kwargs(30)
        )
        log(f"Poll {i+1}/{max_retries}: HTTP status={resp.status_code}")
        log(f"Poll {i+1}/{max_retries}: raw response={resp.text[:500]}")
        if resp.status_code != 200:
            raise RuntimeError(
                f"Poll HTTP error: status={resp.status_code}, resp={resp.text[:500]}"
            )
        data = resp.json()
        if data.get("code") != 0:
            code = data.get("code")
            msg = data.get("msg", "")
            log(f"Poll {i+1}/{max_retries}: Business error {code}, msg={msg}")
            # 永久错误直接失败，不要继续重试
            if code in (4001, 4100):
                raise RuntimeError(
                    f"Coze retrieve failed permanently: code={code}, msg={msg}, "
                    f"object_id={chat_obj_id}, conversation_id={conversation_id}, "
                    f"resp={resp.text[:500]}"
                )
            continue
        chat_data = data.get("data", {})
        status = chat_data.get("status")
        log(f"Poll {i+1}/{max_retries}: status={status}")
        if status == "completed":
            log("Chat completed!")
            return parse_coze_response(data)
        if status == "failed":
            last_error = chat_data.get("last_error", {})
            raise RuntimeError(f"Chat failed: {last_error}")
        if status in ("in_progress", "queued", "processing"):
            continue
        log(f"Poll {i+1}/{max_retries}: unexpected status={status}")
    raise RuntimeError(
        f"Chat polling timeout after {max_retries} retries, "
        f"object_id={chat_obj_id}, conversation_id={conversation_id}"
    )


def call_coze_workflow_api(date_str, repos):
    """
    调用 Coze Workflow API
    """
    if not COZE_API_TOKEN or not COZE_WORKFLOW_ID:
        raise RuntimeError("COZE_API_TOKEN or COZE_WORKFLOW_ID is missing.")
    
    prompt = build_prompt(date_str, repos)
    url = "https://api.coze.cn/v1/workflow/run"
    headers = {
        "Authorization": f"Bearer {COZE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "workflow_id": COZE_WORKFLOW_ID,
        "parameters": {
            "input": prompt
        }
    }
    
    log("Calling Coze Workflow API...")
    resp = requests.post(url, headers=headers, json=payload, **request_kwargs(120))
    
    if resp.status_code != 200:
        raise RuntimeError(f"Coze Workflow API error: {resp.status_code}, {resp.text}")
    
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Coze Workflow business error: {data.get('code')}, {data.get('msg')}")
    
    # 解析 Workflow 响应
    report = None
    if "data" in data:
        workflow_data = data["data"]
        if isinstance(workflow_data, str):
            report = workflow_data.strip()
        elif isinstance(workflow_data, dict):
            report = workflow_data.get("output", "").strip()
    
    if not report:
        raise RuntimeError(f"Unable to parse Coze Workflow response: {resp.text[:500]}")
    
    return report


def call_coze_generate_report(date_str, repos):
    if not COZE_API_TOKEN:
        raise RuntimeError("COZE_API_TOKEN is missing.")
    # 如果配置了 Workflow，优先使用 Workflow
    if COZE_WORKFLOW_ID:
        log("Using Coze Workflow API...")
        return call_coze_workflow_api(date_str, repos)
    # 否则走 Chat API
    if not COZE_BOT_ID:
        raise RuntimeError("COZE_BOT_ID is missing.")
    log("Using Coze Chat API...")
    return call_coze_chat_api(date_str, repos)


def build_fallback_report(date_str, repos):
    """构建兜底报告"""
    lines = [
        f"## 🔥 GitHub 每日热门项目 - {date_str}",
        "",
        "> ⚠️ **兜底模式**：Coze AI 服务暂时不可用，以下为本地模板生成的项目列表。",
        "",
        "### 📊 今日趋势",
        "- 今日热门项目覆盖 AI、开发工具、自动化与基础设施等方向。",
        "- 开发者效率提升类工具持续受到关注。",
        "- 开源 AI 应用与工程化能力仍然是热点。",
        "",
        "### 🏆 热门项目 TOP 10",
        ""
    ]
    
    for i, repo in enumerate(repos, 1):
        lines.append(f"**{i}. {repo['name']}** · {repo['language']}")
        lines.append(f"📈 {repo['stars_today']} stars today · ⭐ {repo['stars']}")
        lines.append(f"简介：{repo['description']}")
        lines.append(f"链接：{repo['url']}")
        lines.append("")
    
    lines.append("---")
    lines.append("🤖 由 GitHub Actions + Coze AI 自动生成")
    lines.append(f"⏰ 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return "\n".join(lines)


def remove_duplicate_title(report, date_str):
    """移除重复的标题"""
    title_pattern = f"🔥 GitHub 每日热门项目 - {date_str}"
    lines = report.split('\n')
    result = []
    title_found = False
    
    for line in lines:
        if title_pattern in line and not title_found:
            result.append(line)
            title_found = True
        elif title_pattern in line and title_found:
            continue
        else:
            result.append(line)
    
    return '\n'.join(result)


def send_to_feishu(report, date_str=None, is_fallback=False, use_card=True):
    """
    发送消息到飞书群机器人
    默认使用卡片模式，失败时自动降级为文本模式
    """
    if use_card and date_str:
        try:
            send_to_feishu_card(date_str, report, is_fallback)
        except Exception as e:
            log(f"Card mode failed: {e}, using text mode...")
            send_to_feishu_text(report)
    else:
        send_to_feishu_text(report)


def send_to_feishu_text(report_content):
    """发送文本消息到飞书"""
    log("Sending text message to Feishu...")
    
    payload = {
        "msg_type": "text",
        "content": {
            "text": report_content
        }
    }
    
    resp = requests.post(FEISHU_WEBHOOK, json=payload, **request_kwargs(30))
    
    if resp.status_code == 200:
        log("Text message sent to Feishu successfully!")
    else:
        log(f"Failed to send text message: {resp.status_code}, {resp.text}")


def send_to_feishu_card(date_str, report_content, is_fallback=False):
    """发送卡片消息到飞书"""
    log("Sending card message to Feishu...")
    
    # 移除 Markdown 标记，转换为文本
    clean_content = report_content.replace('**', '').replace('## ', '').replace('### ', '')
    
    # 添加兜底模式标记
    if is_fallback:
        title_suffix = "（兜底模式）"
    else:
        title_suffix = ""
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🔥 GitHub 每日热门项目 - {date_str}{title_suffix}"
                },
                "template": "red" if is_fallback else "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": clean_content[:3000]  # 限制长度
                    }
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "🤖 由 GitHub Actions + Coze AI 自动生成"
                        }
                    ]
                }
            ]
        }
    }
    
    resp = requests.post(FEISHU_WEBHOOK, json=payload, **request_kwargs(30))
    
    if resp.status_code == 200:
        result = resp.json()
        if result.get("code") == 0:
            log("Card message sent to Feishu successfully!")
        else:
            log(f"Feishu API error: {result}")
    else:
        log(f"Failed to send card message: {resp.status_code}, {resp.text}")


def main():
    """
    主流程
    """
    try:
        log("=" * 50)
        log("Starting GitHub Trending Bot...")
        log(f"CODE_VERSION: {CODE_VERSION}")
        log("=" * 50)
        
        # 打印环境变量是否读取成功
        log(f"FEISHU_WEBHOOK configured: {'yes' if FEISHU_WEBHOOK else 'no'}")
        log(f"COZE_API_TOKEN configured: {'yes' if COZE_API_TOKEN else 'no'}")
        log(f"COZE_BOT_ID configured: {'yes' if COZE_BOT_ID else 'no'}")
        log(f"COZE_WORKFLOW_ID configured: {'yes' if COZE_WORKFLOW_ID else 'no'}")
        
        # 1. 获取今日日期
        date_str = get_today_str()
        log(f"Today: {date_str}")
        
        # 2. 抓取 GitHub Trending
        repos = fetch_github_trending(top_n=10)
        
        # 3. 调用 Coze 生成日报（失败时使用兜底报告）
        is_fallback = False
        try:
            report = call_coze_generate_report(date_str, repos)
            log("Coze report generated successfully.")
        except Exception as e:
            import traceback
            log(f"Coze failed, using fallback report. Error: {e}")
            log(traceback.format_exc())
            report = build_fallback_report(date_str, repos)
            is_fallback = True
        
        # 4. 移除重复标题
        report = remove_duplicate_title(report, date_str)
        
        # 5. 推送到飞书（使用卡片模式，更美观）
        send_to_feishu(report, date_str=date_str, is_fallback=is_fallback, use_card=True)
        
        log("=" * 50)
        log("All done! 🎉")
        log("=" * 50)
        
    except Exception as e:
        log(f"❌ Fatal error: {str(e)}")
        # 尝试发送错误通知
        try:
            if FEISHU_WEBHOOK:
                error_msg = f"❌ GitHub Trending Bot 运行失败\n\n错误信息：{str(e)}\n\n请检查 GitHub Actions 日志。"
                send_to_feishu(error_msg)
        except:
            pass
        raise


if __name__ == "__main__":
    main()
