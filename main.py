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
    要求生成每个项目的中文翻译
    """
    repos_json = json.dumps(repos, ensure_ascii=False, indent=2)

    prompt = f"""你是一名技术内容编辑，现在请根据输入的 GitHub Trending 仓库数据，生成一份中文技术日报，准备发布到飞书群。

日期：{date_str}

输入字段说明：
- rank: 排名
- name: 仓库名
- url: 仓库链接
- description: 原始项目描述（英文）
- language: 编程语言
- stars: 总 star 数
- forks: fork 数
- today_stars: 今日新增 star 文本

原始数据如下：
{repos_json}

请严格按以下要求输出：

1. 标题：
《GitHub 每日热门项目速览 - {date_str}》

2. 输出"今日趋势"：
- 用 3~5 条总结今天的技术热点方向
- 语言简洁专业

3. 输出"热门项目 TOP {len(repos)}"：
每个项目必须包含以下格式：
```
**排名. 项目名** · 编程语言 · 今日新增 Stars
• 原文：英文描述
• 中文：中文翻译（一句话概括核心功能）
• 地址：https://github.com/xxx/xxx
```

4. 输出"重点关注"：
从项目中选 3 个最值得关注的项目，并说明原因

5. 输出要求：
- 必须使用中文
- 必须使用 Markdown
- 每个项目的格式严格按照：原文 + 中文 + 地址
- 中文翻译要简洁准确，一句话说明项目核心功能
- 结构清晰，适合直接发到飞书群
- 不要输出代码块
- 不要输出 JSON
- 如果信息不足，不要编造过于具体的事实，可以用相对稳妥的表述

请直接输出最终日报正文。""".strip()

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
        # 标题行：项目名称 · 语言 · 今日新增
        title = f"**{r['rank']}. {r['name']}**"
        if r['language'] and r['language'] != 'Unknown':
            title += f" · {r['language']}"
        if r['today_stars']:
            title += f" · {r['today_stars']}"
        lines.append(title)

        # 原文
        if r['description']:
            lines.append(f"• **原文**：{r['description']}")
        else:
            lines.append(f"• **原文**：暂无描述")

        # 中文（兜底模式下显示提示）
        lines.append(f"• **中文**：⚠️ Coze AI 服务暂时不可用，无法生成中文翻译")

        # 地址
        lines.append(f"• **地址**：{r['url']}")
        lines.append("")

    lines.append("🎯 重点关注")
    for r in repos[:3]:
        lines.append(f"- **{r['name']}**：当前热度较高，值得进一步关注其应用场景与社区增长。")

    lines.append("")
    lines.append("---")
    lines.append("⚠️ 注：Coze AI 服务暂时不可用，以上为自动生成的兜底报告。")

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


def send_to_feishu_card(date_str, repos, report_content, is_fallback=False):
    """
    发送卡片消息到飞书（推荐，更美观）
    样式仿照：原文 + 中文 + 地址 格式
    """
    if not FEISHU_WEBHOOK:
        raise RuntimeError("FEISHU_WEBHOOK is missing.")

    headers = {"Content-Type": "application/json"}

    # 构建项目列表元素 - 仿照第二张图片样式
    repo_elements = []
    for i, r in enumerate(repos[:5], 1):  # 只展示前5个
        # 项目标题行：序号 + 项目名称 + 语言 + Stars
        title_line = f"**{i}. {r['name']}**"
        if r['language'] and r['language'] != 'Unknown':
            title_line += f" · {r['language']}"
        if r['today_stars']:
            title_line += f" · {r['today_stars']}"

        repo_elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": title_line
            }
        })

        # 原文（英文简介）
        if r['description']:
            repo_elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"• **原文**：{r['description']}"
                }
            })

        # 中文（这里先显示占位，实际内容由 Coze 在 report_content 中生成详细翻译）
        # 或者可以调用翻译 API
        repo_elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"• **中文**：待 Coze AI 生成中文简介"
            }
        })

        # 地址
        repo_elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"• **地址**：[{r['url']}]({r['url']})"
            }
        })

        # 项目间分隔
        repo_elements.append({"tag": "hr"})

    # 移除最后一个分割线
    if repo_elements:
        repo_elements.pop()

    # 构建卡片
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
                        "content": report_content[:1500] if len(report_content) > 1500 else report_content
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**📊 热门项目详情**"
                    }
                },
                *repo_elements,
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
