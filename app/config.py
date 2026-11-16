"""全局配置：数据源、更新周期、分类映射、默认搜索模板策略。"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
RESOURCES_FILE = os.path.join(DATA_DIR, "resources.json")
TEMPLATES_FILE = os.path.join(DATA_DIR, "search_templates.json")

# 官方数据源（raw.githubusercontent.com），可用环境变量覆盖
DATA_SOURCE_URL = os.getenv(
    "DATA_SOURCE_URL",
    "https://raw.githubusercontent.com/laoma528/awesome-zhuiju-free/main/resources/resources.json",
)
# 每日自动更新间隔（小时）
UPDATE_INTERVAL_HOURS = float(os.getenv("UPDATE_INTERVAL_HOURS", "24"))
# 启动时是否立即拉取一次
UPDATE_ON_START = os.getenv("UPDATE_ON_START", "1") == "1"
PORT = int(os.getenv("PORT", "8000"))

# 参与"片名搜索"的分类
SEARCH_CATEGORIES = ["cloud_search", "magnet_search", "online_video"]
CATEGORY_LABELS = {
    "cloud_search": "网盘搜索",
    "magnet_search": "磁力 / BT",
    "online_video": "在线影视",
}

# 未精确配置模板时，按分类使用的兜底搜索格式
# {base}=站点主页 {q}=URL编码后的片名
DEFAULT_TEMPLATES = {
    "cloud_search": "{base}?q={q}",
    "magnet_search": "{base}?q={q}",
    "online_video": "{base}/search?q={q}",
}
