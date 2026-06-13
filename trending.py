#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)

SOURCES = [
    {"name": "gh-trending-api", "type": "json", "url": "https://gh-trending-api.herokuapp.com/repositories?since=daily", "timeout": 15},
    {"name": "gitterapp-api", "type": "json", "url": "https://api.gitterapp.com/repositories", "timeout": 15},
    {"name": "scrape-daily", "type": "html", "url": "https://github.com/trending?since=daily", "timeout": 20},
    {"name": "scrape-weekly", "type": "html", "url": "https://github.com/trending?since=weekly", "timeout": 20},
]

def _parse_json(data):
    items = []
    for i, repo in enumerate(data[:20], 1):
        try:
            name = repo.get("full_name") or repo.get("author","") + "/" + repo.get("name","")
            items.append({"rank": i, "name": name, "url": repo.get("url") or f"https://github.com/{name}", "description": repo.get("description") or "", "language": repo.get("language") or "", "stars": repo.get("stars") or repo.get("totalStars", 0), "stars_today": repo.get("stars_today") or repo.get("currentPeriodStars", 0), "forks": repo.get("forks") or repo.get("forksCount", 0)})
        except:
            continue
    return items

def _parse_html(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    items = []
    for i, art in enumerate(soup.select("article.Box-row")[:20], 1):
        try:
            h2 = art.select_one("h2 a")
            if not h2: continue
            name = h2.get("href","").strip("/")
            desc = (art.select_one("p").get_text(strip=True) if art.select_one("p") else "")
            lang = (art.select_one("[itemprop='programmingLanguage']").get_text(strip=True) if art.select_one("[itemprop='programmingLanguage']") else "")
            stars_text = (art.select_one("a[href*='/stargazers']").get_text(strip=True) if art.select_one("a[href*='/stargazers']") else "0")
            stars = int(stars_text.replace(",","")) if stars_text.replace(",","").isdigit() else 0
            today = 0
            today_tag = art.select_one(".d-inline-block.float-sm-right")
            if today_tag:
                m = re.search(r'([\d,]+)\s*stars?\s*today', today_tag.get_text(strip=True))
                if m: today = int(m.group(1).replace(",",""))
            forks_text = (art.select_one("a[href*='/forks']").get_text(strip=True) if art.select_one("a[href*='/forks']") else "0")
            forks = int(forks_text.replace(",","")) if forks_text.replace(",","").isdigit() else 0
            items.append({"rank": i, "name": name, "url": f"https://github.com/{name}", "description": desc, "language": lang, "stars": stars, "stars_today": today, "forks": forks})
        except:
            continue
    return items

def get_trending():
    errors = []
    for src in SOURCES:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            if src["type"] == "json":
                resp = requests.get(src["url"], headers=headers, timeout=src["timeout"])
                resp.raise_for_status()
                items = _parse_json(resp.json())
            else:
                resp = requests.get(src["url"], headers=headers, timeout=src["timeout"])
                resp.raise_for_status()
                items = _parse_html(resp.text)
            if items:
                logger.info(f"✅ {src['name']} 获取成功，{len(items)} 条")
                return items, src["name"]
        except Exception as e:
            errors.append(f"{src['name']}: {e}")
            continue
    logger.error(f"❌ 全部失败: {errors}")
    return None, None
