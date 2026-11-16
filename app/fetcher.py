"""真实链接抓取：调用 PanSou 公开搜索接口，直接返回真实的网盘分享链接。

数据以 NDJSON 流式返回，事件类型：
  meta      -> 元信息
  candidate -> results 数组，每条含 url/title/password/datetime/source
  done      -> 结束

说明：本项目仅做链接索引与导航，不托管任何影视文件。链接有效性由第三方决定。
"""
import asyncio
import logging
import re
import time

import requests

logger = logging.getLogger("zhuiju.fetcher")

PANSOU_API = "https://pansou.de/api/v1/search/stream"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
    "User-Agent": "Mozilla/5.0 (compatible; zhuiju-finder/1.0)",
}

# 简单内存缓存：同一关键词短时间内复用，避免频繁请求官方接口
_CACHE = {}
CACHE_TTL = 300  # 5 分钟


def _platform_of(url):
    u = (url or "").lower()
    mapping = [
        ("pan.quark.cn", "夸克网盘"),
        ("quark.cn", "夸克网盘"),
        ("pan.baidu.com", "百度网盘"),
        ("aliyundrive.com", "阿里云盘"),
        ("alipan.com", "阿里云盘"),
        ("115.com", "115网盘"),
        ("lanzou", "蓝奏云"),
        ("123pan.com", "123云盘"),
        ("123684.com", "123云盘"),
        ("caiyun.139.com", "天翼云盘"),
        ("magnet:?", "磁力链接"),
    ]
    for key, name in mapping:
        if key in u:
            return name
    return "网盘"


def _clean_title(t):
    t = re.sub(r"^Q\s*", "", t or "").strip()
    return t or "未命名资源"


def _fetch_sync(keyword, platform, max_results):
    payload = {
        "keyword": keyword,
        "platform": platform,
        "maxResults": max_results,
    }
    resp = requests.post(
        PANSOU_API, json=payload, headers=HEADERS, stream=True, timeout=45
    )
    resp.raise_for_status()

    raw = []
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            obj = __import__("json").loads(line)
        except Exception:
            continue
        if obj.get("event") == "candidate":
            for item in obj.get("results", []):
                url = item.get("url")
                if url:
                    raw.append(item)

    # 去重（按 url）+ 排序（时间新的在前）
    seen = set()
    uniq = []
    for it in raw:
        url = it["url"].strip()
        if url in seen:
            continue
        seen.add(url)
        uniq.append(it)
    uniq.sort(key=lambda x: x.get("datetime") or "", reverse=True)
    return uniq[:max_results]


def _format(items, keyword, platform):
    return [
        {
            "title": _clean_title(it.get("title")),
            "url": it.get("url"),
            "password": it.get("password") or "",
            "datetime": (it.get("datetime") or "")[:10],
            "source": it.get("source") or "",
            "platform": _platform_of(it.get("url")),
        }
        for it in items
    ]


async def search_links(keyword, platform="quark", max_results=100):
    """异步搜索，带短时缓存。返回 (links, meta)。"""
    keyword = (keyword or "").strip()
    if not keyword:
        return [], {"keyword": keyword, "cached": False, "error": "关键词为空"}

    cache_key = f"{platform}|{keyword}"
    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1], {"keyword": keyword, "cached": True, "count": len(cached[1])}

    try:
        items = await asyncio.to_thread(_fetch_sync, keyword, platform, max_results)
        links = _format(items, keyword, platform)
        _CACHE[cache_key] = (time.time(), links)
        return links, {"keyword": keyword, "cached": False, "count": len(links)}
    except Exception as e:
        logger.error(f"抓取链接失败 [{keyword}]: {e}")
        return [], {"keyword": keyword, "cached": False, "error": str(e)}
