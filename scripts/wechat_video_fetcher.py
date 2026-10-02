# -*- coding: utf-8 -*-
"""
微信视频号 OpenCLI 数据获取助手 (WeChat Video OpenCLI Fetcher)
统一命令行调度门面 (面向终端用户与 AI Agent)
"""

import sys
import json
import argparse
import pathlib
from typing import Any, Dict, List

# 确保能加载内部核心模块
current_dir = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

try:
    from _wechat_video_core import WeChatVideoDispatcher
except ImportError as e:
    print(f"❌ [错误] 核心调度模块加载失败: {e}", file=sys.stderr)
    sys.exit(1)


def format_output(data: Any, fmt: str = "json") -> str:
    """按指定格式格式化数据 (JSON, YAML 或 Plain)"""
    fmt = fmt.lower().strip()
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif fmt == "yaml":
        try:
            import yaml
            return yaml.dump(data, allow_unicode=True, sort_keys=False)
        except ImportError:
            return json.dumps(data, ensure_ascii=False, indent=2)
    elif fmt == "plain":
        if isinstance(data, dict):
            lines = []
            for k, v in data.items():
                if k == "content":
                    lines.append(f"\n【文案正文】:\n{v}\n")
                elif k == "stats" and isinstance(v, dict):
                    lines.append(f"【互动指标】: 点赞 {v.get('likes', 0)} | 转发 {v.get('forwards', 0)} | 评论 {v.get('comments', 0)} | 收藏 {v.get('favs', 0)}")
                elif k == "tags" and isinstance(v, list):
                    lines.append(f"【话题标签】: {' '.join(['#' + t for t in v])}")
                else:
                    lines.append(f"【{k}】: {v}")
            return "\n".join(lines)
        elif isinstance(data, list):
            lines = []
            for i, item in enumerate(data, 1):
                lines.append(f"--- [#{i}] ---")
                for k, v in item.items():
                    if k == "content" or k == "full_content":
                        snippet = str(v)[:200] + ("..." if len(str(v)) > 200 else "")
                        lines.append(f"【文案】: {snippet}")
                    elif k == "stats" and isinstance(v, dict):
                        lines.append(f"【互动】: 赞 {v.get('likes', 0)} / 评 {v.get('comments', 0)}")
                    else:
                        lines.append(f"【{k}】: {v}")
            return "\n".join(lines)
    return str(data)


def save_output(content: str, out_path: str):
    """保存输出到指定路径"""
    p = pathlib.Path(out_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"[+] 数据已成功保存至: {p}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="微信视频号 OpenCLI 数据提取工具 (免维护 Cookie、零风控、提取原始视频数据与纯文本正文)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  1. 提取单篇视频号原始数据与脱水文案:
     python wechat_video_fetcher.py video "https://channels.weixin.qq.com/web/pages/feed?feedId=..."
     python wechat_video_fetcher.py video "https://channels.weixin.qq.com/web/pages/feed?..." --text-only
     python wechat_video_fetcher.py video "https://channels.weixin.qq.com/web/pages/feed?..." -f plain

  2. 批量拉取视频号助手后台历史动态列表 (需已在 Chrome 登录视频号助手):
     python wechat_video_fetcher.py posts --limit 20
     python wechat_video_fetcher.py posts --limit 10 --with-content -o posts.json

  3. 全网搜索视频号相关内容:
     python wechat_video_fetcher.py search "DeepSeek 智能体" --limit 5

  4. 查询当前视频号登录账号:
     python wechat_video_fetcher.py whoami

  5. 环境自检探活:
     python wechat_video_fetcher.py doctor
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. video
    p_video = subparsers.add_parser("video", help="提取单篇视频号原始数据 (标题、文案、发布时间、视频链接、封面、互动数据)")
    p_video.add_argument("url", help="视频号播放链接或分享文本")
    p_video.add_argument("--text-only", action="store_true", help="仅输出脱水纯文本正文内容")
    p_video.add_argument("--force-browser", action="store_true", help="强制使用独立浏览器会话抓取")
    p_video.add_argument("-f", "--format", choices=["json", "yaml", "plain"], default="json", help="输出格式 (默认 json)")
    p_video.add_argument("-o", "--output", help="保存到本地文件路径")

    # 2. posts
    p_posts = subparsers.add_parser("posts", help="批量拉取视频号助手后台作品动态列表与互动指标 (需在 Chrome 登录 channels.weixin.qq.com)")
    p_posts.add_argument("--limit", type=int, default=20, help="获取条数 (默认 20)")
    p_posts.add_argument("-q", "--query", default="", help="作品关键词检索过滤")
    p_posts.add_argument("--with-content", action="store_true", help="同时拉取每条视频的完整正文文案")
    p_posts.add_argument("-f", "--format", choices=["json", "yaml", "plain"], default="json", help="输出格式 (默认 json)")
    p_posts.add_argument("-o", "--output", help="保存到本地文件路径")

    # 3. search
    p_search = subparsers.add_parser("search", help="全网关键词搜索视频号内容")
    p_search.add_argument("query", help="搜索关键词")
    p_search.add_argument("--limit", type=int, default=10, help="搜索条数 (默认 10)")
    p_search.add_argument("-f", "--format", choices=["json", "yaml", "plain"], default="json", help="输出格式 (默认 json)")
    p_search.add_argument("-o", "--output", help="保存到本地文件路径")

    # 4. whoami
    p_whoami = subparsers.add_parser("whoami", help="查询当前 Chrome 中已登录的视频号创作者身份")
    p_whoami.add_argument("-f", "--format", choices=["json", "yaml", "plain"], default="json", help="输出格式 (默认 json)")

    # 5. doctor
    p_doctor = subparsers.add_parser("doctor", help="检查 OpenCLI 守护进程、Chrome 扩展及视频号登录状态")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == "doctor":
            doc = WeChatVideoDispatcher.check_doctor()
            print(doc["stdout"])
            if doc["connected"]:
                print("✅ [OK] OpenCLI 真实浏览器桥接环境完全就绪！")
            else:
                print("⚠️ [提示] 尚未连接到 Chrome 浏览器扩展，请确保 Chrome 浏览器已打开且已安装 OpenCLI 插件。")

            if doc["channels_logged_in"]:
                user = doc["channels_user"]
                print(f"✅ [OK] 视频号助手已登录: {user.get('name', '创作者')} (ID: {user.get('user_id', '')})")
            else:
                print("ℹ️ [提示] 视频号助手尚未登录 (若需使用 posts 批量拉取自己的作品，请在 Chrome 访问 channels.weixin.qq.com 扫码登录)。")

        elif args.command == "whoami":
            user_info = WeChatVideoDispatcher.whoami()
            out_str = format_output(user_info, args.format)
            print(out_str)

        elif args.command == "video":
            data = WeChatVideoDispatcher.get_video(args.url, force_browser=args.force_browser)
            if args.text_only:
                content = data.get("content", "")
                if args.output:
                    save_output(content, args.output)
                else:
                    print(content)
            else:
                out_str = format_output(data, args.format)
                if args.output:
                    save_output(out_str, args.output)
                else:
                    print(out_str)

        elif args.command == "posts":
            data = WeChatVideoDispatcher.get_posts(limit=args.limit, query=args.query, with_content=args.with_content)
            out_str = format_output(data, args.format)
            if args.output:
                save_output(out_str, args.output)
            else:
                print(out_str)

        elif args.command == "search":
            data = WeChatVideoDispatcher.search(args.query, limit=args.limit)
            out_str = format_output(data, args.format)
            if args.output:
                save_output(out_str, args.output)
            else:
                print(out_str)

    except Exception as e:
        print(f"❌ [执行异常]: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
