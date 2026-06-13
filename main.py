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

    total_today = 0
    languages = {}
    for item in trending_list[:10]:
        today = item.get("stars_today", 0)
        if isinstance(today, (int, float)):
            total_today += today
        lang = item.get("language", "Unknown") or "Unknown"
        languages[lang] = languages.get(lang, 0) + 1

    top_lang = max(languages, key=languages.get) if languages else "N/A"
    top_lang_count = languages[top_lang] if languages else 0

    trend_text = (
        f"今日 TOP 10 共获得 **{total_today:,}** 颗新增星标，"
        f"**{top_lang}** 语言最受欢迎（{top_lang_count} 个项目）。"
    )

    elements = [
        {
            "tag": "markdown",
            "content": (
                f"**\U0001f525 GitHub 每日热门项目 - {today_str}**\n"
                f"来源：{source_name}\n\n"
                f"**今日趋势分析：**\n{trend_text}\n"
            ),
        },
        {"tag": "hr"},
        {"tag": "markdown", "content": "**TOP 10 热门项目**"},
    ]

    for i, item in enumerate(trending_list[:10], 1):
        medal = medals[i - 1]
        name = item.get("name", "?")
        lang = item.get("language", "N/A") or "N/A"
        stars_today = item.get("stars_today", "?")
        stars = item.get("stars", "?")
        forks = item.get("forks", "?")
        desc = (item.get("description", "") or "暂无描述")[:120]
        url = item.get("url", f"https://github.com/{name}")

        if isinstance(stars_today, int):
            stars_today = f"{stars_today:,}"
        if isinstance(stars, int):
            stars = f"{stars:,}"
        if isinstance(forks, int):
            forks = f"{forks:,}"

        elements.append({
            "tag": "markdown",
            "content": (
                f"{medal} **{i}. [{name}]({url})** \u00b7 {lang}\n"
                f"\U0001f4c8 今日新增 {stars_today} \u00b7 \u2b50 总 {stars} \u00b7 \U0001f374 {forks}\n"
                f"简介：{desc}"
            ),
        })

    elements.append({"tag": "hr"})
    elements.append({
        "tag": "markdown",
        "content": "\u0001f916 由 GitHub Trending Bot 自动生成",
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
        logger.error("\u274c 无法获取 GitHub Trending 数据")
        return

    logger.info(f"\u2705 成功获取 {len(trending_list)} 条数据（来源: {source_name}）")

    card = build_card(trending_list, source_name)
    result = send_webhook(webhook_url, card)
    logger.info(f"\U0001f4ec 发送结果: {result}")
    logger.info("\u2705 任务完成")


if __name__ == "__main__":
    main()
