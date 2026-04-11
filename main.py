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
    优化版本：中文简介 + 紧凑格式 + 重点关注
    """
    repos_json = json.dumps(repos, ensure_ascii=False, indent=2)

    prompt = f"""你是一名技术编辑，根据 GitHub Trending 数据生成一份中文技术日报。

日期：{date_str}

原始数据：
{repos_json}

请严格按照以下格式输出：

## 📊 今日趋势
用 3 条简洁有力的中文总结今日技术热点，像真正的技术编辑写的洞察，不要模板化。例如：
- AI Agent 与 AI Coding 工具仍是今日榜单主线，相关项目热度明显集中。
- 文档处理、自动化工程链路、开发效率工具继续保持高关注度。
- 趋势从"模型能力"逐步转向"工程落地与工作流可复用"。

## 🏆 热门项目 TOP {len(repos)}
每个项目压缩成 3 行，格式如下：

**排名. 项目名** · 编程语言
<font color='FF0000'>📈 今日 +xxx</font> · <font color='F5A623'>⭐ 总stars</font> · <font color='8C8C8C'>🍴 forks</font>
简介：一句中文提炼（不要英文原文，用你自己的话概括核心功能，15-25字）
`https://github.com/xxx/xxx`

示例：
**1. microsoft/markitdown** · Python
<font color='FF0000'>📈 今日 +2,353</font> · <font color='F5A623'>⭐ 97,991</font> · <font color='8C8C8C'>🍴 5,999</font>
简介：微软开源的文件与 Office 文档转 Markdown 工具。
`https://github.com/microsoft/markitdown`

注意：
- 简介必须是中文，不要放英文原文
- 今日新增放最前面，用红色高亮
- 链接用反引号包裹，单独一行
- Top 3 可以在排名后加 🥇🥈🥉  emoji

## 🎯 重点关注
从 Top 10 中选 3 个最值得关注的项目，用中文说明为什么值得关注（每项目 1 句话）。例如：
- **microsoft/markitdown**：实用性强，适合知识处理与文档转换场景，微软背书生态可靠。
- **coleam00/Archon**：代表 AI Coding 工程化趋势，强调可重复与可控。

---
📊 统计口径：GitHub Trending Daily
直接输出最终内容，不要代码块，不要多余解释。""".strip()

    return prompt


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
        proxies=PROXIES if PROXIES else None,
        timeout=60
    )
    log(f"Create chat status: {resp.status_code}")
    if resp.status_code != 200:
        raise RuntimeError(f"Create chat error: {resp.status_code}, {resp.text}")
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Create chat business error: {data.get('code')}, {data.get('msg')}")
    
    chat_data = data.get("data", {})
    chat_id = chat_data.get("id")
    conversation_id = chat_data.get("conversation_id")
    status = chat_data.get("status")
    
    if not chat_id:
        raise RuntimeError(f"No chat_id in response: {resp.text[:500]}")
    
    log(f"Chat created: id={chat_id}, status={status}")
    
    # 如果已经 completed，直接解析结果
    if status == "completed":
        return parse_coze_response(chat_data)
    
    # Step 2: 轮询获取结果
    log("Step 2: Polling for chat result...")
    max_retries = 30
    initial_delay = 2
    max_delay = 5
    
    for i in range(max_retries):
        retry_delay = min(initial_delay + i * 0.5, max_delay)
        time.sleep(retry_delay)
        
        # 查询对话状态
        retrieve_url = f"https://api.coze.cn/v3/chat/retrieve?chat_id={chat_id}&conversation_id={conversation_id}"
        resp = requests.get(retrieve_url, headers=headers, proxies=PROXIES if PROXIES else None, timeout=30)
        
        if resp.status_code != 200:
            log(f"Poll {i+1}/{max_retries}: HTTP error {resp.status_code}")
            continue
        
        data = resp.json()
        if data.get("code") != 0:
            log(f"Poll {i+1}/{max_retries}: Business error {data.get('code')}, {data.get('msg')}")
            continue
        
        chat_data = data.get("data", {})
        status = chat_data.get("status")
        log(f"Poll {i+1}/{max_retries}: status={status}")
        
        if status == "completed":
            log("Chat completed!")
            return parse_coze_response(chat_data)
        elif status == "failed":
            last_error = chat_data.get("last_error", {})
            raise RuntimeError(f"Chat failed: {last_error}")
    
    raise RuntimeError(f"Chat polling timeout after {max_retries} retries")

def parse_coze_response(chat_data):
    """
    解析 Coze 响应，提取 assistant 的消息内容
    """
    # 尝试从 messages 中提取
    messages = chat_data.get("messages", [])
    if isinstance(messages, list):
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if content and isinstance(content, str):
                    log(f"Got response from assistant, length={len(content)}")
                    return content.strip()
    
    # 尝试从 content 中提取
    content = chat_data.get("content", "")
    if isinstance(content, str) and content.strip():
        log(f"Got response from content, length={len(content)}")
        return content.strip()
    
    raise RuntimeError(f"Unable to parse chat response: {json.dumps(chat_data, ensure_ascii=False)[:500]}")
    



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
    if not COZE_API_TOKEN:
        raise RuntimeError("COZE_API_TOKEN is missing.")
    if not COZE_BOT_ID:
        raise RuntimeError("COZE_BOT_ID is missing.")
    return call_coze_chat_api(date_str, repos)


def build_fallback_report(date_str, repos):
    """
    当 Coze 调用失败时，生成兜底报告
    优化版本：紧凑格式 + 中文标识
    """
    lines = []

    # 状态说明
    lines.append("> ⚠️ **兜底模式**：Coze AI 服务暂时不可用，以下为本地模板生成的项目列表。")
    lines.append("")

    lines.append("## 📊 今日趋势")
    lines.append("- 今日热门项目覆盖 AI、开发工具、自动化与基础设施等方向。")
    lines.append("- 开发者效率提升类工具持续受到关注。")
    lines.append("- 开源 AI 应用与工程化能力仍然是热点。")
    lines.append("")

    lines.append(f"## 🏆 热门项目 TOP {len(repos)}")
    lines.append("")

    for r in repos:
        # 排名 emoji（Top 3）
        rank_emoji = ""
        if r['rank'] == 1:
            rank_emoji = "🥇 "
        elif r['rank'] == 2:
            rank_emoji = "🥈 "
        elif r['rank'] == 3:
            rank_emoji = "🥉 "

        # 第一行：排名 + 项目名 + 语言
        title = f"**{rank_emoji}{r['rank']}. {r['name']}**"
        if r['language'] and r['language'] != 'Unknown':
            title += f" · {r['language']}"
        lines.append(title)

        # 第二行：今日新增（红色）+ 总stars（黄色）+ forks（灰色）
        info_parts = []
        if r.get('today_stars'):
            info_parts.append(f"<font color='FF0000'>📈 {r['today_stars']}</font>")
        if r.get('stars'):
            info_parts.append(f"<font color='F5A623'>⭐ {r['stars']}</font>")
        if r.get('forks'):
            info_parts.append(f"<font color='8C8C8C'>🍴 {r['forks']}</font>")

        if info_parts:
            lines.append(" · ".join(info_parts))

        # 第三行：简介（兜底模式下显示英文原文）
        if r['description']:
            lines.append(f"简介：{r['description']}")
        else:
            lines.append("简介：暂无描述")

        # 第四行：链接
        lines.append(f"`{r['url']}`")
        lines.append("")

    lines.append("## 🎯 重点关注")
    for r in repos[:3]:
        lines.append(f"- **{r['name']}**：当前热度较高，值得进一步关注。")
    lines.append("")

    lines.append("---")
    lines.append("📊 统计口径：GitHub Trending Daily")
    lines.append("🤖 数据来源：GitHub Trending ｜ 本地模板生成")

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


def remove_duplicate_title(content):
    """
    删除 Coze 生成的重复标题（如果存在）
    直接删除包含 GitHub 和日期的第一行
    """
    lines = content.split('\n')

    # 找到第一个非空行
    first_content_line = 0
    for i, line in enumerate(lines):
        if line.strip():
            first_content_line = i
            break

    # 检查第一行是否是标题（包含 GitHub 和日期）
    first_line = lines[first_content_line] if first_content_line < len(lines) else ""
    if 'GitHub' in first_line and any(c.isdigit() for c in first_line):
        # 删除这一行
        lines.pop(first_content_line)

    return '\n'.join(lines).strip()


def send_to_feishu_card(date_str, repos, report_content, is_fallback=False):
    """
    发送卡片消息到飞书（推荐，更美观）
    只显示 Coze 生成的内容，避免重复
    """
    if not FEISHU_WEBHOOK:
        raise RuntimeError("FEISHU_WEBHOOK is missing.")

    headers = {"Content-Type": "application/json"}

    # 删除可能的重复标题
    cleaned_content = remove_duplicate_title(report_content)

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
                        "content": cleaned_content[:8000] if len(cleaned_content) > 8000 else cleaned_content
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
