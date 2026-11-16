"""搜索逻辑：按片名生成各站点的"一键搜索"链接，并按状态/风险排序。"""
from urllib.parse import quote

from . import config
from .updater import STATE

RISK_LABELS = {"low": "低", "medium": "中", "high": "高", "unknown": "未知"}
RISK_RANK = {"low": 0, "medium": 1, "high": 2, "unknown": 3}

# verification.status -> (前端状态键, 中文说明)
STATUS_MAP = {
    "ok": ("online", "正常收录"),
    "normal": ("online", "正常收录"),
    "caution": ("caution", "需注意"),
    "removed": ("removed", "已下架"),
    "unknown": ("unknown", "未检测"),
}
STATUS_RANK = {"online": 0, "caution": 1, "unknown": 2, "removed": 3}


def _overall_risk(risks):
    if not risks or not isinstance(risks, dict):
        return "unknown"
    return max(risks.values(), key=lambda v: RISK_RANK.get(v, 3))


def _build_search_url(site, q):
    base = (site.get("url") or "").rstrip("/")
    sid = site.get("id")
    tpl = STATE["templates"].get(sid) or config.DEFAULT_TEMPLATES.get(
        site.get("category"), "{base}?q={q}"
    )
    try:
        return tpl.format(base=base, q=quote(q))
    except Exception:
        return base


def _star(scores):
    if not scores:
        return 0
    vals = [v for v in scores.values() if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals)) if vals else 0


def search(query, category=None, site_filter=None):
    data = STATE["data"] or {}
    resources = data.get("resources", [])
    q = (query or "").strip()
    results = {}
    keyword = (site_filter or "").strip().lower()

    for cat in config.SEARCH_CATEGORIES:
        if category and cat != category:
            continue
        items = []
        for site in resources:
            if site.get("category") != cat:
                continue
            haystack = " ".join(
                [site.get("name", ""), site.get("id", ""), site.get("summary", "")]
            ).lower()
            if keyword and keyword not in haystack:
                continue
            verification = site.get("verification") or {}
            status_key, status_text = STATUS_MAP.get(
                verification.get("status", "unknown"), ("unknown", "未知")
            )
            risk = _overall_risk(site.get("risks"))
            items.append(
                {
                    "id": site.get("id"),
                    "name": site.get("name"),
                    "url": site.get("url"),
                    "summary": site.get("summary_short") or site.get("summary") or "",
                    "search_url": _build_search_url(site, q),
                    "precise": site.get("id") in STATE["templates"],
                    "status": status_key,
                    "status_text": status_text,
                    "last_checked": verification.get("last_checked"),
                    "risk": risk,
                    "risk_text": RISK_LABELS.get(risk, risk),
                    "star": _star(site.get("scores")),
                }
            )
        items.sort(
            key=lambda x: (
                STATUS_RANK.get(x["status"], 9),
                RISK_RANK.get(x["risk"], 9),
                -x["star"],
            )
        )
        results[cat] = {"label": config.CATEGORY_LABELS.get(cat, cat), "items": items}
    return results
