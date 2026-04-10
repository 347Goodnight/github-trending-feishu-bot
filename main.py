import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

GITHUB_TRENDING_URL = "https://github.com/trending?since=daily"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK", "").strip()
COZE_API_TOKEN = os.getenv("COZE_API_TOKEN", "").strip()
COZE_BOT_ID = os.getenv("COZE_BOT_ID", "").strip()
# 可选：如果使用 Coze Workflow API，配置工作流 ID
COZE_WORKFLOW_ID = os.getenv("COZE_WORKFLOW_ID", "").strip()

HTTP_PROXY = os.getenv("HTTP_PROXY", "").strip()
HTTPS_PROXY = os.getenv("HTTPS_PROXY", "").strip()

PROXIES = {}
if HTTP_PROXY:
    PROXIES["http"] = HTTP_PROXY
if HTTPS_PROXY:
    PROXIES["https"] = HTTPS_PROXY


def log(msg):
    print(f"[LOG] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")


def get_today_str():
    """获取中国时区的今天日期"""
    cn_tz = timezone(timedelta(hours=8))
    return datetime.now(cn_tz).strftime("%Y-%m-%d")


def clean_text(text):
    """清理文本中的多余空格和换行"""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_github_trending(top_n=10):
    """
    抓取 GitHub Trending 页面
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }

    log("Fetching GitHub Trending...")
    resp = requests.get(
        GITHUB_TRENDING_URL,
        headers=headers,
        proxies=PROXIES if PROXIES else None,
        timeout=30
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    articles = soup.select("article.Box-row")

    repos = []
    rank = 1

    for article in articles[:top_n]:
        title_tag = article.select_one("h2 a")
        if not title_tag:
            continue

        repo_name = clean_text(title_tag.get_text()).replace(" / ", "/").replace(" ", "")
        repo_url = "https://github.com" + title_tag.get("href", "")

        desc_tag = article.select_one("p")
        description = clean_text(desc_tag.get_text()) if desc_tag else ""

        lang_tag = article.select_one('[itemprop="programmingLanguage"]')
        language = clean_text(lang_tag.get_text()) if lang_tag else "Unknown"

        star_tags = article.select("a.Link--muted")
        stars = clean_text(star_tags[0].get_text()) if len(star_tags) > 0 else ""
        forks = clean_text(star_tags[1].get_text()) if len(star_tags) > 1 else ""

        today_stars = ""
        spans = article.select("span")
        for sp in spans:
            txt = clean_text(sp.get_text())
            if "star" in txt.lower() and ("today" in txt.lower() or "本日" in txt):
                today_stars = txt
                break

        repos.append({
            "rank": rank,
            "name": repo_name,
            "url": repo_url,
            "description": description,
            "language": language,
            "stars": stars,
            "forks": forks,
            "today_stars": today_stars
        })
        rank += 1

    if not repos:
        raise RuntimeError("No repositories parsed from GitHub Trending page.")

    log(f"Fetched {len(repos)} repos from GitHub Trending.")
    return repos


def build_prompt(date_str, repos):
    """
    构建发送给 Coze 的 Prompt
    简化版本：只展示项目信息，不翻译中文
    """
    repos_json = json.dumps(repos, ensure_ascii=False, indent=2)

    prompt = f"""根据 GitHub Trending 数据生成一份项目列表。

日期：{date_str}

数据：
{repos_json}

输出要求：

1. 直接开始项目列表，不要加标题（卡片头部已有标题）

2. 项目列表格式（每个项目）：
**排名. 项目名** · 编程语言 <font color='F5A623'>⭐ stars</font> | <font color='8C8C8C'>🍴 forks</font> | <font color='FF0000'>📈 today</font>
• Description: 英文描述
• Link: https://github.com/xxx/xxx

3. 最后加一段简短的今日趋势总结（3-5条）

4. 使用 <font color='颜色代码'>文本</font> 格式添加颜色

直接输出内容，不要代码块。""".strip()

    return prompt


def call_coze_chat_api(date_str, repos):
    """
    调用 Coze Chat API (v3/chat)
    适用于：Coze Bot 对话模式
    """
    if not COZE_API_TOKEN or not COZE_BOT_ID:
        raise RuntimeError("COZE_API_TOKEN or COZE_BOT_ID is missing.")

    prompt = build_prompt(date_str, repos)

    # Coze Chat API v3
    url = "https://api.coze.cn/v3/chat"
    headers = {
        "Authorization": f"Bearer {COZE_API_TOKEN}",
        "Content-Type": "application/json"
    }

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

    log("Calling Coze Chat API (v3)...")
    resp = requests.post(
        url,
        headers=headers,
        json=payload,
        proxies=PROXIES if PROXIES else None,
        timeout=120
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Coze API error: {resp.status_code}, {resp.text}")

    data = resp.json()
    log(f"Coze response: {json.dumps(data, ensure_ascii=False)[:500]}...")

    # 解析响应
    report = None

    if isinstance(data, dict):
        # v3 API 返回结构
        if "data" in data:
            chat_data = data["data"]
            if isinstance(chat_data, dict):
                # 尝试获取最后一条 assistant 消息
                if "messages" in chat_data and isinstance(chat_data["messages"], list):
                    for msg in reversed(chat_data["messages"]):
                        if msg.get("role") == "assistant":
                            report = msg.get("content", "")
                            break

        # 兼容旧版结构
        if not report and "messages" in data and isinstance(data["messages"], list):
            for msg in reversed(data["messages"]):
                content = msg.get("content")
                if content:
                    report = content
                    break

        if not report and "content" in data:
            report = data["content"]

    if not report:
        raise RuntimeError(f"Unable to parse Coze response: {resp.text[:500]}")

    return report.strip()


def call_coze_workflow_api(date_str, repos):
    """
    调用 Coze Workflow API (v1/workflow/run)
    适用于：Coze 工作流模式
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
            "input": prompt,
            "date": date_str,
            "repos_count": len(repos)
        }
    }

    log("Calling Coze Workflow API...")
    resp = requests.post(
        url,
        headers=headers,
        json=payload,
        proxies=PROXIES if PROXIES else None,
        timeout=120
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Coze Workflow API error: {resp.status_code}, {resp.text}")

    data = resp.json()
    log(f"Coze Workflow response: {json.dumps(data, ensure_ascii=False)[:500]}...")

    # 解析工作流响应
    report = None

    if isinstance(data, dict):
        if "data" in data:
            workflow_data = data["data"]
            if isinstance(workflow_data, dict):
                # 尝试获取 output 字段
                if "output" in workflow_data:
                    report = workflow_data["output"]
                elif "content" in workflow_data:
                    report = workflow_data["content"]

        if not report and "output" in data:
            report = data["output"]

    if not report:
        raise RuntimeError(f"Unable to parse Coze Workflow response: {resp.text[:500]}")

    return report.strip()


def call_coze_generate_report(date_str, repos):
    """
    调用 Coze 生成报告
    优先尝试 Chat API，如果配置了 Workflow ID 则尝试 Workflow API
    """
    errors = []

    # 如果配置了 Workflow ID，优先使用 Workflow API
    if COZE_WORKFLOW_ID:
        try:
            return call_coze_workflow_api(date_str, repos)
        except Exception as e:
            errors.append(f"Workflow API failed: {e}")
            log(f"Workflow API failed, trying Chat API...")

    # 尝试 Chat API
    if COZE_BOT_ID:
        try:
            return call_coze_chat_api(date_str, repos)
        except Exception as e:
            errors.append(f"Chat API failed: {e}")

    # 都失败了
    raise RuntimeError(f"All Coze API attempts failed: {'; '.join(errors)}")


def build_fallback_report(date_str, repos):
    """
    当 Coze 调用失败时，生成兜底报告
    """
    lines = []
    lines.append(f"🔥 《GitHub 每日热门项目速览 - {date_str}》")
    lines.append("")
    lines.append("📊 今日趋势")
    lines.append("- 今日热门项目覆盖 AI、开发工具、自动化与基础设施等方向。")
    lines.append("- 开发者效率提升类工具持续受到关注。")
    lines.append("- 开源 AI 应用与工程化能力仍然是热点。")
    lines.append("")
    lines.append(f"🏆 热门项目 TOP {len(repos)}")
    lines.append("")

    for r in repos:
        # 标题行：项目名称 · 语言 · 带颜色的统计信息
        title = f"**{r['rank']}. {r['name']}**"
        if r['language'] and r['language'] != 'Unknown':
            title += f" · {r['language']}"

        # 添加带颜色的 stars/forks/今日新增
        info_parts = []
        if r.get('stars'):
            info_parts.append(f"<font color='F5A623'>⭐ {r['stars']}</font>")
        if r.get('forks'):
            info_parts.append(f"<font color='8C8C8C'>🍴 {r['forks']}</font>")
        if r.get('today_stars'):
            info_parts.append(f"<font color='FF0000'>📈 {r['today_stars']}</font>")

        if info_parts:
            title += " " + " | ".join(info_parts)

        lines.append(title)

        # 描述
        if r['description']:
            lines.append(f"• Description: {r['description']}")
        else:
            lines.append(f"• Description: No description")

        # 链接
        lines.append(f"• Link: {r['url']}")
        lines.append("")

    lines.append("---")
    lines.append("📊 Auto-generated fallback report (Coze AI unavailable)")

    return "\n".join(lines).strip()


def send_to_feishu_text(text):
    """
    发送纯文本消息到飞书（兜底方案）
    """
    if not FEISHU_WEBHOOK:
        raise RuntimeError("FEISHU_WEBHOOK is missing.")

    headers = {"Content-Type": "application/json"}

    payload = {
        "msg_type": "text",
        "content": {
            "text": text
        }
    }

    log("Sending text message to Feishu...")
    resp = requests.post(
        FEISHU_WEBHOOK,
        headers=headers,
        json=payload,
        proxies=PROXIES if PROXIES else None,
        timeout=30
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Feishu webhook error: {resp.status_code}, {resp.text}")

    result = resp.json()
    log(f"Feishu response: {result}")

    if result.get("code") != 0:
        raise RuntimeError(f"Feishu send failed: {result}")

    log("Text message sent to Feishu successfully!")


def translate_description(desc):
    """
    简单的英文描述翻译（基础版）
    实际使用时建议调用 Coze 或翻译 API 进行更准确的翻译
    """
    # 这里可以扩展为调用翻译 API
    # 暂时返回空字符串，让 Coze 在生成报告时处理翻译
    return ""


def format_repo_info(r):
    """
    格式化项目信息，带颜色和符号
    """
    info_parts = []

    # 总 Stars - 黄色
    if r.get('stars'):
        info_parts.append(f"<font color='F5A623'>⭐ {r['stars']}</font>")

    # Forks - 灰色
    if r.get('forks'):
        info_parts.append(f"<font color='8C8C8C'>🍴 {r['forks']}</font>")

    # 今日新增 - 红色高亮
    if r.get('today_stars'):
        info_parts.append(f"<font color='FF0000'>📈 {r['today_stars']}</font>")

    return " | ".join(info_parts) if info_parts else ""


def send_to_feishu_card(date_str, repos, report_content, is_fallback=False):
    """
    发送卡片消息到飞书（推荐，更美观）
    只显示 Coze 生成的内容，避免重复
    """
    if not FEISHU_WEBHOOK:
        raise RuntimeError("FEISHU_WEBHOOK is missing.")

    headers = {"Content-Type": "application/json"}

    # 构建卡片 - 直接显示 Coze 生成的完整内容
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🔥 GitHub 每日热门项目 - {date_str}"
                },
                "template": "red"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": report_content[:8000] if len(report_content) > 8000 else report_content
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "🤖 由 GitHub Actions + Coze AI 自动生成" + (" | ⚠️ 兜底模式" if is_fallback else "")
                        }
                    ]
                }
            ]
        }
    }

    log("Sending card message to Feishu...")
    resp = requests.post(
        FEISHU_WEBHOOK,
        headers=headers,
        json=payload,
        proxies=PROXIES if PROXIES else None,
        timeout=30
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Feishu webhook error: {resp.status_code}, {resp.text}")

    result = resp.json()
    log(f"Feishu response: {result}")

    if result.get("code") != 0:
        # 卡片发送失败，尝试用文本模式兜底
        log("Card message failed, falling back to text mode...")
        send_to_feishu_text(report_content)
        return

    log("Card message sent to Feishu successfully!")


def send_to_feishu(text, date_str=None, repos=None, is_fallback=False, use_card=True):
    """
    发送消息到飞书群机器人
    默认使用卡片模式，失败时自动降级为文本模式
    """
    if use_card and date_str and repos:
        try:
            send_to_feishu_card(date_str, repos, text, is_fallback)
        except Exception as e:
            log(f"Card mode failed: {e}, using text mode...")
            send_to_feishu_text(text)
    else:
        send_to_feishu_text(text)


def main():
    """
    主流程
    """
    try:
        log("=" * 50)
        log("Starting GitHub Trending Bot...")
        log("=" * 50)

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
            log(f"Coze failed, using fallback report. Error: {e}")
            report = build_fallback_report(date_str, repos)
            is_fallback = True

        # 4. 推送到飞书（使用卡片模式，更美观）
        send_to_feishu(report, date_str=date_str, repos=repos, is_fallback=is_fallback, use_card=True)

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
