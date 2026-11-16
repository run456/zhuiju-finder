"""FastAPI 入口：提供搜索 API、状态、手动刷新，并托管前端。"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, updater
from .search import search
from .fetcher import search_links
from .bd import search_films, get_resources

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("zhuiju")


@asynccontextmanager
async def lifespan(app):
    await updater.startup()
    yield


app = FastAPI(title="追剧资源一站搜", docs_url="/api/docs", lifespan=lifespan)


@app.get("/api/search")
async def api_search(
    q: str = "",
    category: str = Query(default=None, description="cloud_search/magnet_search/online_video"),
    site: str = Query(default=None, description="按站点名/id 过滤"),
):
    results = search(q, category, site)
    return {
        "query": q,
        "total": sum(len(v["items"]) for v in results.values()),
        "results": results,
        "meta": updater.status(),
    }


@app.get("/api/status")
async def api_status():
    return updater.status()


@app.post("/api/refresh")
async def api_refresh():
    ok = await updater.refresh()
    return JSONResponse({"success": ok, **updater.status()})


@app.get("/api/bd/search")
async def api_bd_search(q: str = Query(default="", description="片名")):
    """BD影视：按片名搜索影片列表（第一步）。"""
    films, meta = await asyncio.to_thread(search_films, q)
    return {"films": films, "meta": meta}


@app.get("/api/bd/resources")
async def api_bd_resources(id: str = Query(default="", description="影片id，如 0lj0")):
    """BD影视：按影片id返回真实磁力/网盘链接（第二步）。"""
    resources, meta = await asyncio.to_thread(get_resources, id)
    return {"resources": resources, "meta": meta}


@app.get("/api/categories")
async def api_categories():
    return {"categories": [{"key": k, "label": v} for k, v in config.CATEGORY_LABELS.items()]}


@app.get("/api/links")
async def api_links(
    q: str = Query(default="", description="片名/关键词"),
    platform: str = Query(default="quark", description="网盘平台，目前支持 quark"),
    limit: int = Query(default=100, ge=1, le=200),
):
    """真实链接搜索：直接返回可打开的网盘分享链接。"""
    links, meta = await search_links(q, platform, limit)
    return {"links": links, "meta": meta}


app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(config.STATIC_DIR, "index.html"))


@app.get("/demo.html")
async def demo():
    return FileResponse(os.path.join(config.STATIC_DIR, "demo.html"))


@app.get("/healthz")
async def healthz():
    return {"ok": True}
