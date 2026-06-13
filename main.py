#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
from datetime import datetime

import requests
from trending import get_trending

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def build_card(trending_list, source_name):
    today_str = datetime.now().strftime("%Y-%m-%d")
    medals = ["\U0001f947", "\U0001f948", "\U0001f949", "\U0001f3c5", "\U0001f3c5", "\U0001f3c5", "\U0001f3c5", "\U0001f3c5", "\U0001f3c5", "\U0001f3c5"]

    top10 = trending_list[:10]

    total_today = 0
    languages = {}
    for item in top10:
        today = item.get("stars_today", 0)
        if isinstance(today, (int, float)):
            total_today += int(today)
        lang = item.get("language", "Unknown") or "Unknown"
        languages[lang] = languages.get(lang, 0) + 1

    top_lang = max(languages, key=languages.get) if languages else "N/A"
    top_lang_count = languages[top_lang] if languages else 0
    top_desc_keywords = set()
    for item in top10:
        desc = (item.get("description") or "").lower()
        if "ai" in desc or "agent" in desc or "claude" in desc or "copilot" in desc:
            top_desc_keywords.add("AI")
        if "learn" in desc or "tutorial" in desc or "guide" in desc:
            top_desc_keywords.add("入门教程")
        if "free" in desc or "open" in desc:
            top_desc_keywords.add("免费资源")
        if "tool" in desc or "plugin" in desc or "extension" in desc:
            top_desc_keywords.add("插件/工具")

    trend_extra = "、".join(sorted(top_desc_keywords)) if top_desc_keywords else "多元化"
    trend_text = (
        f"今日GitHub趋势中，{trend_extra}类项目成为关注焦点。"
        f"TOP 10 共获得 **{total_today:,}** 颗新增星标，"
        f"**{top_lang}** 语言最受欢迎（{top_lang_count}个项目）。"
    )

    elements = [
        {
            "tag": "markdown",
            "content": (
                f"来源：{source_name}\n\n"
                f"**今日趋势分析：**\n{trend_text}\n"
            ),
        },
        {"tag": "hr"},
        {"tag": "markdown", "content": "**TOP 10 热门项目**"},
    ]

    for i, item in enumerate(top10, 1):
        medal = medals[i - 1]
        name = item.get("name", "?")
        lang = item.get("language", "N/A") or "N/A"
        stars_today_raw = item.get("stars_today", 0)
        stars_raw = item.get("stars", 0)
        forks_raw = item.get("forks", 0)
        desc = (item.get("description", "") or "暂无描述")[:150]
        url = item.get("url", f"https://github.com/{name}")

        def fmt(n):
            if isinstance(n, int):
                return f"{n:,}"
            return str(n)

        elements.append({
            "tag": "markdown",
            "content": (
                f"{medal} **{i}. [{name}]({url})** · {lang}\n"
                f"\U0001f4c8 今日新增 {fmt(stars_today_raw)} · \u2b50 总 {fmt(stars_raw)} · \U0001f374 {fmt(forks_raw)}\n"
                f"简介：{desc}\n"
                f"链接：{url}"
            ),
        })

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "\U0001f525 GitHub 每日热门项目"},
                "template": "blue",
            },
            "elements": elements,
        },
    }


def send_webhook(webhook_url, card):
    headers = {"Content-Type": "application/json; charset=utf-8"}
    try:
        resp = requests.post(webhook_url, headers=headers, json=card, timeout=10)
        result = resp.json()
        if result.get("StatusCode") == 0:
            logger.info("\u2705 消息发送成功")
        else:
            logger.error(f"\u274c 消息发送失败: {result}")
        return result
    except Exception as e:
        logger.error(f"\u274c 消息发送异常: {e}")
        return None


def main():
    logger.info("\U0001f680 GitHub Trending Bot 启动")

    webhook_url = os.environ.get("WEBHOOK_URL") or ""
    if not webhook_url:
        try:
            from config import WEBHOOK_URL as cfg_url
            webhook_url = cfg_url
        except (ImportError, KeyError):
            pass

    if not webhook_url:
        logger.error("\u274c 未配置 WEBHOOK_URL")
        return

    logger.info("\U0001f4e1 获取 GitHub Trending 数据...")
    trending_list, source_name = get_trending()

    if not trending_list:
        logger.error("❌ 无法获取 GitHub Trending 数据")
        raise SystemExit(1)

    logger.info(f"\u2705 成功获取 {len(trending_list)} 条数据（来源: {source_name}）")

    card = build_card(trending_list, source_name)
    result = send_webhook(webhook_url, card)
    logger.info(f"\U0001f4ec 发送结果: {result}")
    logger.info("\u2705 任务完成")


if __name__ == "__main__":
    main()
