#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import logging
import re
import json

logger = logging.getLogger(__name__)

SOURCES = [
    # 1. GitHub.com HTML scraping (most reliable from GitHub Actions)
    {"name": "scrape-daily", "type": "html", "url": "https://github.com/trending?since=daily", "timeout": 30},
    # 2. Alternative HTML (weekly as a different dataset)
    {"name": "scrape-weekly", "type": "html", "url": "https://github.com/trending?since=weekly", "timeout": 30},
    # 3. Vercel API mirror
    {"name": "vercel-api", "type": "json", "url": "https://github-trending-api.vercel.app/repositories", "timeout": 15},
    # 4. Alternative API
    {"name": "gitterapp-alt", "type": "json", "url": "https://tools.monetabot.workers.dev/repositories", "timeout": 15},
]


def _fetch_with_retry(url, headers, timeout, max_retries=2):
    """Helper: retry on transient errors."""
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < max_retries:
                logger.warning(f"  重试 {attempt+1}/{max_retries}: {e}")
                continue
            raise


def _parse_json(data):
    items = []
    for i, repo in enumerate(data[:20], 1):
        try:
            author = repo.get("author", "") or ""
            name_part = repo.get("name", "") or ""
            full_name = repo.get("full_name") or f"{author}/{name_part}".strip("/")

            items.append({
                "rank": i,
                "name": full_name,
                "url": repo.get("url") or f"https://github.com/{full_name}",
                "description": repo.get("description") or "",
                "language": repo.get("language") or "",
                "stars": repo.get("stars") or repo.get("totalStars", 0),
                "stars_today": repo.get("stars_today") or repo.get("currentPeriodStars", 0),
                "forks": repo.get("forks") or repo.get("forksCount", 0),
            })
        except Exception:
            continue
    return items


def _parse_html(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    items = []

    for i, art in enumerate(soup.select("article.Box-row")[:20], 1):
        try:
            h2 = art.select_one("h2 a")
            if not h2:
                continue
            name = h2.get("href", "").strip("/")

            desc_tag = art.select_one("p")
            desc = desc_tag.get_text(strip=True) if desc_tag else ""

            lang_tag = art.select_one("[itemprop='programmingLanguage']")
            lang = lang_tag.get_text(strip=True) if lang_tag else ""

            # Stars
            stars_tag = art.select_one("a[href*='/stargazers']")
            stars_text = stars_tag.get_text(strip=True) if stars_tag else "0"
            stars = int(stars_text.replace(",", "")) if stars_text.replace(",", "").isdigit() else 0

            # Stars today
            today = 0
            today_tag = art.select_one(".d-inline-block.float-sm-right")
            if today_tag:
                txt = today_tag.get_text(strip=True)
                m = re.search(r'([\d,]+)\s*stars?\s*today', txt)
                if m:
                    today = int(m.group(1).replace(",", ""))
                else:
                    # Try alternate format: "X stars today" or "X,XXX stars today"
                    m2 = re.search(r'([\d,]+)', txt)
                    if m2:
                        today = int(m2.group(1).replace(",", ""))

            # Forks
            forks_tag = art.select_one("a[href*='/forks']")
            forks_text = forks_tag.get_text(strip=True) if forks_tag else "0"
            forks = int(forks_text.replace(",", "")) if forks_text.replace(",", "").isdigit() else 0

            items.append({
                "rank": i,
                "name": name,
                "url": f"https://github.com/{name}",
                "description": desc,
                "language": lang,
                "stars": stars,
                "stars_today": today,
                "forks": forks,
            })
        except Exception:
            continue
    return items


def get_trending():
    errors = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    for src in SOURCES:
        try:
            logger.info(f"  尝试 {src['name']}...")
            if src["type"] == "json":
                resp = _fetch_with_retry(src["url"], headers, src["timeout"])
                items = _parse_json(resp.json())
            else:
                resp = _fetch_with_retry(src["url"], headers, src["timeout"])
                items = _parse_html(resp.text)

            if items:
                logger.info(f"  ✅ {src['name']} 成功，{len(items)} 条")
                return items, src["name"]
            else:
                logger.warning(f"  ⚠️ {src['name']} 返回 0 条数据")
        except Exception as e:
            errors.append(f"{src['name']}: {e}")
            logger.warning(f"  ❌ {src['name']} 失败: {e}")
            continue

    logger.error(f"❌ 所有数据源均失败: {errors}")
    raise RuntimeError(f"所有数据源均失败: {errors}")
