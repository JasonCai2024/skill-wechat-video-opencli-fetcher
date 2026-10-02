# 微信视频号 OpenCLI 命令全量参考手册

本文档详细记录 `skill-wechat-video-opencli-fetcher` 各子命令的完整参数、修饰符以及输出字段结构。

---

## 一、命令清单速查

| 功能分类 | Python 统一调度命令 | 依赖条件 | 输出字段与用途 |
|---|---|---|---|
| 🩺 **环境探活** | `python scripts/wechat_video_fetcher.py doctor` | 无 | 诊断 OpenCLI 守护进程、Chrome 插件连通性及视频号登录状态 |
| 👤 **身份查询** | `python scripts/wechat_video_fetcher.py whoami` | 需在 Chrome 登录视频号助手 | 创作者 ID (`user_id`)、视频号名称 (`name`) |
| 🎬 **单视频详情提取** | `python scripts/wechat_video_fetcher.py video "<URL>" [-f json\|yaml\|plain] [-o 文件]` | 视频播放链接或分享文本 | 标题、创作者、发布时间、视频链接、封面、互动数据、脱水文案 |
| 📝 **仅提取纯文本口播文案** | `python scripts/wechat_video_fetcher.py video "<URL>" --text-only` | 视频播放链接或分享文本 | 纯文本终端直接打印，彻底剥离 HTML 与排版噪音 |
| 📚 **创作者作品列表** | `python scripts/wechat_video_fetcher.py posts [--limit 20] [-q "关键词"]` | 需在 Chrome 登录视频号助手 | 批量获取动态标题、发布时间、视频ID、播放量、点赞、评论等 |
| 📦 **作品列表+全量详情** | `python scripts/wechat_video_fetcher.py posts [--limit 10] --with-content` | 需在 Chrome 登录视频号助手 | 包含动态列表 + 逐条提取完整正文文案与视频链接 |
| 🔍 **全网搜索视频号内容** | `python scripts/wechat_video_fetcher.py search "<关键词>" [--limit 10]` | 无 | 全网相关微信视频号内容与图文链接 |

---

## 二、实测数据结构输出示例

### 1. `video`（单视频详情与脱水文案）
```bash
python scripts/wechat_video_fetcher.py video "https://channels.weixin.qq.com/web/pages/feed?feedId=export%2F..." -f json
```
**实测输出结构 (JSON)**：
```json
{
  "title": "深入剖析 Agentic AI 落地架构与实践路径",
  "author": "AI技术观察",
  "author_id": "v2_060000231...",
  "publish_time": "2026-10-01 19:30:00",
  "video_url": "https://finder.video.qq.com/251/20302/stodownload?encfilekey=...",
  "cover_url": "https://finder.video.qq.com/251/20304/stodownload?encfilekey=...",
  "duration": 96,
  "stats": {
    "likes": 12800,
    "forwards": 3200,
    "comments": 650,
    "favs": 4100
  },
  "tags": [
    "AI",
    "智能体",
    "技术架构"
  ],
  "url": "https://channels.weixin.qq.com/web/pages/feed?feedId=export%2F...",
  "content": "深入剖析 Agentic AI 落地架构与实践路径。\n\n本期视频重点拆解自主智能体系统的四大核心模块：规划拆解、工具调用、长期记忆与自愈反思。普通开发者如何快速构建生产级智能体应用？\n\n#AI #智能体 #技术架构"
}
```

### 2. `posts`（批量拉取视频号助手后台作品动态）
```bash
python scripts/wechat_video_fetcher.py posts --limit 2 -f json
```
**实测输出结构 (JSON)**：
```json
[
  {
    "index": 1,
    "title": "深入剖析 Agentic AI 落地架构与实践路径",
    "create_time": "2026-10-01 19:30:00",
    "export_id": "export/UzFzN5PxR1vK9aQ2w...",
    "read_count": 89000,
    "like_count": 12800,
    "forward_count": 3200,
    "comment_count": 650,
    "status": "已发表",
    "cover_url": "https://finder.video.qq.com/...",
    "link": "https://channels.weixin.qq.com/web/pages/feed?feedId=export%2FUzFzN5PxR1vK9aQ2w...",
    "full_content": "深入剖析 Agentic AI 落地架构与实践路径..."
  },
  {
    "index": 2,
    "title": "DeepSeek V4 架构深度拆解",
    "create_time": "2026-09-28 12:15:00",
    "export_id": "export/K2m9Pq0wLxR7v...",
    "read_count": 124000,
    "like_count": 19500,
    "forward_count": 5100,
    "comment_count": 980,
    "status": "已发表",
    "cover_url": "https://finder.video.qq.com/...",
    "link": "https://channels.weixin.qq.com/web/pages/feed?feedId=export%2FK2m9Pq0wLxR7v...",
    "full_content": "DeepSeek V4 架构深度拆解..."
  }
]
```

### 3. `search`（全网关键词检索）
```bash
python scripts/wechat_video_fetcher.py search "智能体应用" --limit 2 -f json
```
**实测输出结构 (JSON)**：
```json
[
  {
    "index": 1,
    "title": "2026 智能体落地应用实战全景",
    "url": "https://weixin.sogou.com/link?url=...",
    "summary": "全面解析当下智能体技术在各行各业的落地最佳实践...",
    "publish_time": "昨天"
  },
  {
    "index": 2,
    "title": "从零搭建专属业务智能体工作流",
    "url": "https://weixin.sogou.com/link?url=...",
    "summary": "详解开源框架与桌面端桥接技术...",
    "publish_time": "3天前"
  }
]
```
