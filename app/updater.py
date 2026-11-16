"""数据源更新：启动时+定时从 GitHub 拉取 resources.json，原子写入本地缓存。"""
import asyncio
import json
import logging
import os
import tempfile

import requests

from . import config

logger = logging.getLogger("zhuiju.updater")

# 进程内共享状态
STATE = {
    "data": None,
    "templates": {},
    "last_updated": None,
    "last_status": "未初始化",
    "resource_count": 0,
    "source_url": config.DATA_SOURCE_URL,
}

_background_task = None


def _load_local():
    """从本地缓存加载数据（容器启动网络不通也能用）。"""
    try:
        with open(config.RESOURCES_FILE, encoding="utf-8") as f:
            data = json.load(f)
        STATE["data"] = data
        STATE["last_updated"] = data.get("updated_at")
        STATE["resource_count"] = len(data.get("resources", []))
        STATE["last_status"] = "本地缓存"
        logger.info(f"本地缓存已加载，{STATE['resource_count']} 条资源")
    except Exception as e:
        logger.error(f"加载本地数据失败: {e}")
    try:
        with open(config.TEMPLATES_FILE, encoding="utf-8") as f:
            tpl = json.load(f)
        STATE["templates"] = tpl.get("templates", {})
    except Exception as e:
        logger.error(f"加载搜索模板失败: {e}")


def _atomic_write(path, data):
    """原子写：先写临时文件再替换，避免半截文件。"""
    directory = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _fetch():
    resp = requests.get(
        config.DATA_SOURCE_URL,
        timeout=25,
        headers={"User-Agent": "zhuiju-finder/1.0", "Accept": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict) or not isinstance(data.get("resources"), list):
        raise ValueError("数据结构不符合预期（缺少 resources 数组）")
    if len(data["resources"]) < 10:
        raise ValueError("资源数量异常，疑似数据不完整")
    return data


async def refresh():
    """拉取远程数据并更新缓存与内存状态。"""
    try:
        data = await asyncio.to_thread(_fetch)
        _atomic_write(config.RESOURCES_FILE, data)
        STATE["data"] = data
        STATE["last_updated"] = data.get("updated_at")
        STATE["resource_count"] = len(data.get("resources", []))
        STATE["last_status"] = "正常"
        logger.info(f"资源更新成功，共 {STATE['resource_count']} 条")
        return True
    except Exception as e:
        logger.error(f"资源更新失败: {e}")
        STATE["last_status"] = f"更新失败：{e}"
        return False


async def _loop():
    """后台更新循环：可选先立即更新一次，之后按间隔循环。不阻塞服务启动。"""
    if config.UPDATE_ON_START:
        await refresh()
    while True:
        await asyncio.sleep(config.UPDATE_INTERVAL_HOURS * 3600)
        await refresh()


async def startup():
    global _background_task
    _load_local()
    # 后台任务执行网络更新，服务用本地缓存立即可用，避免网络慢时阻塞启动
    _background_task = asyncio.create_task(_loop())


def status():
    return {
        "last_updated": STATE["last_updated"],
        "last_status": STATE["last_status"],
        "resource_count": STATE["resource_count"],
        "source_url": STATE["source_url"],
        "update_interval_hours": config.UPDATE_INTERVAL_HOURS,
    }
