"""BD影视（juhebd）磁力/网盘直链抓取。

链路：
  1) GET https://www.juhebd.com/q/index?k=<片名>  -> 解析影片列表（详情页 /mv/XXXX + 标题）
  2) 详情页路径末尾 id（如 0lj0）即 res 资源 id
  3) GET https://res.juhebd.com/api/rl?id=<id>   -> data 为 Base64(JSON)，含磁力/网盘链接

仅做链接索引与展示，不托管任何内容。
"""
import base64
import json
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("zhuiju.bd")

SEARCH_URL = "https://www.juhebd.com/q/index"
RES_API = "https://res.juhebd.com/api/rl"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

_CACHE = {}
CACHE_TTL = 600  # 10 分钟

TYPE_LABELS = {
    "magnet": "磁力",
    "ed2k": "电驴",
    "quark": "夸克网盘",
    "baidu": "百度网盘",
    "xunlei": "迅雷网盘",
    "115": "115网盘",
    "aliyun": "阿里云盘",
    "xunlei": "迅雷网盘",
}


def _cache_get(key):
    v = _CACHE.get(key)
    if v and time.time() - v[0] < CACHE_TTL:
        return v[1]
    return None


def _cache_set(key, val):
    _CACHE[key] = (time.time(), val)


def _type_label(t):
    return TYPE_LABELS.get(t or "", t or "其他")


def search_films(keyword):
    """第一步：按片名搜索，返回影片列表 [{id,title,detail_url,year,...}]。"""
    keyword = (keyword or "").strip()
    if not keyword:
        return [], {"keyword": keyword, "error": "关键词为空"}

    ck = f"films|{keyword}"
    cached = _cache_get(ck)
    if cached is not None:
        return cached, {"keyword": keyword, "cached": True, "count": len(cached)}

    try:
        resp = requests.get(
            SEARCH_URL,
            params={"k": keyword},
            headers={"User-Agent": UA, "Accept": "text/html"},
            timeout=25,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        films = []
        seen = set()
        for a in soup.find_all("a", href=re.compile(r"^/(mv|tv|acg)/[A-Za-z0-9]+$")):
            href = a.get("href", "")
            fid = href.rsplit("/", 1)[-1]
            # 标题里关键词被 <em>/<span> 高亮包裹，get_text 会插入空格，去掉即可
            title = re.sub(r"\s+", "", a.get_text("", strip=True))
            if not title or fid in seen:
                continue
            seen.add(fid)
            films.append({"id": fid, "title": title, "detail_url": href})
        _cache_set(ck, films)
        return films, {"keyword": keyword, "cached": False, "count": len(films)}
    except Exception as e:
        logger.error(f"BD影视搜索失败 [{keyword}]: {e}")
        return [], {"keyword": keyword, "cached": False, "error": str(e)}


def get_resources(film_id):
    """第二步：按影片 id 返回真实磁力/网盘链接列表。"""
    film_id = (film_id or "").strip()
    if not film_id:
        return [], {"id": film_id, "error": "影片id为空"}

    ck = f"res|{film_id}"
    cached = _cache_get(ck)
    if cached is not None:
        return cached, {"id": film_id, "cached": True, "count": len(cached)}

    try:
        resp = requests.get(
            RES_API,
            params={"id": film_id},
            headers={
                "User-Agent": UA,
                "Referer": "https://res.juhebd.com/",
                "Accept": "application/json",
            },
            timeout=25,
        )
        resp.raise_for_status()
        payload = resp.json()
        if str(payload.get("code")) != "200" or not payload.get("data"):
            return [], {"id": film_id, "error": payload.get("msg") or "无数据"}

        raw = base64.b64decode(payload["data"])
        items = json.loads(raw)
        resources = []
        for it in items:
            url = it.get("url")
            if not url:
                continue  # 无有效链接的条目跳过
            size_mb = it.get("size") or 0
            resources.append(
                {
                    "filename": it.get("filename") or "未命名",
                    "url": url,
                    "type": it.get("type") or "other",
                    "type_label": _type_label(it.get("type")),
                    "size": round(size_mb / 1024, 2) if size_mb else 0,  # GB
                    "version": it.get("version") or "",
                }
            )
        # 磁力优先，再按大小降序
        order = {"magnet": 0, "quark": 1, "baidu": 2, "ed2k": 3}
        resources.sort(key=lambda x: (order.get(x["type"], 9), -x["size"]))
        _cache_set(ck, resources)
        return resources, {"id": film_id, "cached": False, "count": len(resources)}
    except Exception as e:
        logger.error(f"BD影视资源抓取失败 [{film_id}]: {e}")
        return [], {"id": film_id, "cached": False, "error": str(e)}
