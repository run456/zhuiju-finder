# 磁力直链搜索（zhuiju-finder）

一个 Docker 部署的搜索工具：**输入片名 → 选影片 → 直接列出真实磁力/网盘链接**（文件名、类型、大小、真实 URL），点"复制"即可拿到，不需要跳转到各网站逐个搜索。

- **磁力直链（主功能）**：基于 BD影视聚合（juhebd），搜片名列出影片 → 选片后返回真实 `magnet:` 磁力链 + 夸克/迅雷网盘链接。实测搜"奥德赛"一部片即可拿到 129 条磁力链接
- **夸克直链（补充）**：调用 PanSou 公开接口，实时返回真实夸克网盘链接
- **站点导航**：附带基于 [laoma528/awesome-zhuiju-free](https://github.com/laoma528/awesome-zhuiju-free) 的 74 个站点入口

> ⚠️ **数据来源与边界**
> - ✅ **磁力 / 网盘直链**：基于 BD影视（juhebd）资源站，实测搜"奥德赛"一部片可拿到 129 条真实磁力链
> - ✅ **夸克网盘**：PanSou 公开接口返回真实 `pan.quark.cn/s/xxx` 链接
> - ⚠️ 资源站的搜索页/接口若改版或加反爬，抓取逻辑需相应调整；链接有效性由第三方决定
>
> 本项目仅做**链接索引与展示**，不托管任何影视文件、破解软件或作品内容，不对第三方链接的合法性、有效性、安全性作保证。请遵守所在地法律并自行判断风险。

## 功能

- 🧲 **磁力直链（核心）**：输入片名 → 影片列表 → 点选影片 → 列出该片全部真实磁力/网盘链接（文件名、类型、大小），支持"仅磁力/仅夸克"筛选和"复制全部"
- 🔗 **夸克直链**：PanSou 公开接口实时抓取真实夸克网盘链接
- 🧭 **站点导航补充**：74 个站点入口一键跳转
- 🔄 **站点数据每日更新** + 🐳 **Docker 开箱即用**

## 磁力抓取链路（BD影视）

```
片名 → GET juhebd.com/q/index?k=片名      → 影片列表 + 详情页id(如 0lj0)
     → GET res.juhebd.com/api/rl?id=0lj0  → Base64 编码数据
     → Base64 解码 → JSON                 → magnet:?xt=urn:btih:... 真实磁力链
```

实现见 `app/bd.py`。搜索页/资源接口若改版，需相应调整该模块的 URL 与解析逻辑。

## 快速开始

```bash
cd zhuiju-finder
docker compose up -d --build
# 打开 http://服务器IP:8000
```

也可本地运行：

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 页面说明

| 页面 | 作用 |
|---|---|
| `/` | 磁力直链主界面（搜片名 → 选影片 → 出磁力链接） |
| `/demo.html` | 离线可看的操作演示页（讲清流程和链路） |
| `/api/docs` | Swagger 接口文档 |

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/bd/search?q=片名` | **BD影视搜影片**，返回 `{films:[{id,title,detail_url}], meta}` |
| GET | `/api/bd/resources?id=0lj0` | **BD影视取真实磁力/网盘链接**，返回 `{resources:[{filename,url,type,type_label,size,version}], meta}` |
| GET | `/api/links?q=片名&platform=quark&limit=100` | 夸克网盘直链（PanSou 接口） |
| GET | `/api/search?q=片名&category=&site=` | 站点导航（一键跳转链接） |
| GET | `/api/status` | 站点数据源状态 |
| POST | `/api/refresh` | 手动更新站点数据 |

## 配置

环境变量（`docker-compose.yml` 中可改）：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DATA_SOURCE_URL` | 官方 raw 地址 | 站点索引数据源 |
| `UPDATE_INTERVAL_HOURS` | `24` | 站点数据自动更新间隔 |
| `UPDATE_ON_START` | `1` | 启动时是否更新站点数据 |
| `PORT` | `8000` | 监听端口 |

## 直链接口说明

直链抓取走公开接口 `POST https://pansou.de/api/v1/search/stream`（NDJSON 流式），解析 `candidate` 事件的 `results` 数组，去重后按时间排序。同一关键词有 5 分钟内存缓存，避免频繁请求。

- 抓取模块：`app/fetcher.py`（可自行调整接口地址、缓存时长、平台映射）
- 若公开接口变更导致抓取失败，前端会显示错误提示，可据此更新 `PANSOU_API` 及解析逻辑

## 数据文件

- `data/resources.json`：站点索引主数据（每日自动更新，volume 持久化）
- `data/search_templates.json`：站点搜索跳转模板
- `static/demo.html`：独立的操作演示页

## 开源协议与来源

站点索引来自 laoma528/awesome-zhuiju-free（CC BY 4.0）；直链搜索来自公开接口。本工具为个人技术实践，请合规使用。
