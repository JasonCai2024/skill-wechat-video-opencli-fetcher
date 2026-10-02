# -*- coding: utf-8 -*-
"""
微信视频号 OpenCLI 数据获取统一调度核心 (Dispatcher Engine)
1. 自动环境诊断与 OpenCLI 适配器自动就绪检测 (ensure_adapters_installed)
2. 单视频详情提取与文案脱水清洗 (HTTP + 真实 Chrome 浏览器双引擎保障)
3. 视频号创作者助手作品动态列表批量拉取 (依托已登录的 channels.weixin.qq.com 后台)
4. 创作者身份鉴权探活 (whoami) 与环境诊断 (doctor)
5. 视频搜索与外部短链接解析
"""

import os
import sys
import json
import time
import shutil
import subprocess
import pathlib
from typing import Dict, Any, List, Optional, Tuple

from .video_parser import clean_video_data, parse_raw_url, format_timestamp


class WeChatVideoDispatcher:
    @staticmethod
    def ensure_adapters_installed():
        """确保 adapters/wechat-channels/*.js 自动同步至 ~/.opencli/clis/wechat-channels/"""
        user_home = pathlib.Path.home()
        target_dir = user_home / ".opencli" / "clis" / "wechat-channels"
        
        # 查找本仓库内置的 adapters
        current_dir = pathlib.Path(__file__).resolve().parent
        source_dir = current_dir.parent.parent / "adapters" / "wechat-channels"
        
        if source_dir.exists() and source_dir.is_dir():
            target_dir.mkdir(parents=True, exist_ok=True)
            for src_file in source_dir.glob("*.js"):
                dst_file = target_dir / src_file.name
                if not dst_file.exists() or dst_file.stat().st_mtime < src_file.stat().st_mtime:
                    shutil.copy2(src_file, dst_file)

    @staticmethod
    def run_cmd(cmd_list: List[str], timeout: int = 60) -> Tuple[int, str, str]:
        """运行系统命令并捕获输出，自动压制警告与跨平台兼容"""
        WeChatVideoDispatcher.ensure_adapters_installed()
        env = os.environ.copy()
        env["NODE_NO_WARNINGS"] = "1"
        
        full_cmd = list(cmd_list)
        if full_cmd:
            exe_path = shutil.which(full_cmd[0])
            if exe_path:
                full_cmd[0] = exe_path

        try:
            res = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=timeout,
                shell=False
            )
            return res.returncode, res.stdout, res.stderr
        except subprocess.TimeoutExpired:
            return 124, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)

    @staticmethod
    def check_doctor() -> Dict[str, Any]:
        """环境探活检查：检测 OpenCLI 守护进程、Chrome 扩展连接以及视频号登录态"""
        code, out, err = WeChatVideoDispatcher.run_cmd(["opencli", "doctor"])
        connected = "Connectivity: connected" in out or "[OK] Connectivity" in out

        # 检查视频号助手是否已登录
        whoami_code, whoami_out, whoami_err = WeChatVideoDispatcher.run_cmd(
            ["opencli", "wechat-channels", "whoami", "-f", "json"],
            timeout=15
        )
        channels_logged_in = False
        channels_user = {}
        if whoami_code == 0 and whoami_out.strip():
            try:
                channels_user = json.loads(whoami_out.strip())
                if isinstance(channels_user, dict) and channels_user.get("user_id"):
                    channels_logged_in = True
            except Exception:
                pass

        return {
            "code": code,
            "connected": connected,
            "channels_logged_in": channels_logged_in,
            "channels_user": channels_user,
            "stdout": out,
            "stderr": err
        }

    @staticmethod
    def whoami() -> Dict[str, Any]:
        """查询当前 Chrome 中已登录的视频号创作者身份"""
        code, out, err = WeChatVideoDispatcher.run_cmd(
            ["opencli", "wechat-channels", "whoami", "-f", "json"],
            timeout=20
        )
        if code != 0 or not out.strip():
            if "AUTH_REQUIRED" in (out + err) or "sessionid cookie missing" in (out + err):
                raise RuntimeError(
                    "\n======================================================\n"
                    "⚠️ [微信视频号助手] 未检测到已登录的视频号创作者会话！\n"
                    "------------------------------------------------------\n"
                    "👉 请在已启用 OpenCLI 扩展的 Chrome 浏览器中访问：\n"
                    "   https://channels.weixin.qq.com/\n"
                    "👉 扫码登录视频号助手后台后即可正常使用。\n"
                    "======================================================\n"
                )
            raise RuntimeError(f"查询视频号创作者身份失败: {err or out}")

        try:
            return json.loads(out.strip())
        except Exception as e:
            raise RuntimeError(f"解析 whoami 输出失败: {e}\n输出: {out}")

    @staticmethod
    def _fetch_video_via_browser_session(url: str) -> Dict[str, Any]:
        """通过 OpenCLI 真实浏览器会话直接访问并解析视频页面"""
        session_name = f"wc_vid_{int(time.time()) % 10000}"
        try:
            # 1. 打开视频页面
            code, out, err = WeChatVideoDispatcher.run_cmd([
                "opencli", "browser", session_name, "open", url, "--window", "background"
            ], timeout=30)
            if code != 0:
                return {"error": f"Browser open failed: {err}"}

            # 2. 等待 3 秒渲染
            WeChatVideoDispatcher.run_cmd(["opencli", "browser", session_name, "wait", "time", "3"], timeout=10)

            # 3. 执行提取脚本
            extract_script = """(() => {
                const res = {
                    title: '',
                    author: '',
                    author_id: '',
                    publish_time: '',
                    video_url: '',
                    cover_url: '',
                    duration: 0,
                    likes: '0',
                    forwards: '0',
                    comments: '0',
                    favs: '0',
                    content: '',
                    url: window.location.href
                };
                const v = document.querySelector('video');
                if (v) {
                    res.video_url = v.src || v.currentSrc || '';
                    res.cover_url = v.poster || '';
                    res.duration = Math.round(v.duration || 0);
                }
                const og = (p) => {
                    const el = document.querySelector(`meta[property="${p}"], meta[name="${p}"]`);
                    return el ? el.getAttribute('content') : '';
                };
                res.title = og('og:title') || '';
                res.content = og('og:description') || '';
                if (og('og:video')) res.video_url = og('og:video');
                if (og('og:image')) res.cover_url = og('og:image');

                const descEl = document.querySelector('.feed-desc, .desc-text, [class*="desc-"], [class*="desc_"]');
                if (descEl && descEl.innerText) {
                    const t = descEl.innerText.trim();
                    if (!res.content || t.length > res.content.length) res.content = t;
                    if (!res.title) res.title = t.split('\\n')[0].slice(0, 100);
                }
                const authorEl = document.querySelector('.feed-author, .nickname, [class*="nickname"], [class*="author-name"]');
                if (authorEl && authorEl.innerText) res.author = authorEl.innerText.trim();

                const timeEl = document.querySelector('.feed-time, [class*="create-time"], [class*="publish-time"]');
                if (timeEl && timeEl.innerText) res.publish_time = timeEl.innerText.trim();

                return res;
            })()"""

            code, out, err = WeChatVideoDispatcher.run_cmd([
                "opencli", "browser", session_name, "eval", extract_script
            ], timeout=20)

            # 4. 关闭会话
            WeChatVideoDispatcher.run_cmd(["opencli", "browser", session_name, "close"], timeout=10)

            if code == 0 and out.strip():
                try:
                    return json.loads(out.strip())
                except Exception:
                    pass
            return {"error": f"Browser eval failed: {err}"}
        except Exception as e:
            WeChatVideoDispatcher.run_cmd(["opencli", "browser", session_name, "close"], timeout=10)
            return {"error": str(e)}

    @staticmethod
    def get_video(raw_url: str, force_browser: bool = False) -> Dict[str, Any]:
        """
        获取单篇微信视频号原始数据与脱水文案：
        - title: 视频标题
        - author: 视频号创作者昵称
        - author_id: 创作者唯一标识
        - publish_time: 标准化发布时间 (YYYY-MM-DD HH:mm:ss)
        - video_url: 视频原始播放链接
        - cover_url: 高清视频封面链接
        - duration: 视频时长（秒）
        - stats: 互动指标字典 (likes, forwards, comments, favs)
        - tags: 话题标签列表
        - url: 规范化永久链接
        - content: 纯文本脱水文案正文
        """
        clean_url = parse_raw_url(raw_url)
        if not clean_url:
            raise ValueError(f"无法从输入中提取有效视频链接: {raw_url}")

        raw_data = None

        if not force_browser:
            # 优先调用 OpenCLI 适配器命令
            code, out, err = WeChatVideoDispatcher.run_cmd([
                "opencli", "wechat-channels", "video", "--url", clean_url, "-f", "json"
            ], timeout=40)

            if code == 0 and out.strip():
                try:
                    raw_data = json.loads(out.strip())
                except Exception:
                    pass

        # 若适配器未能提取或强制使用浏览器会话
        if not raw_data or raw_data.get("error"):
            raw_data = WeChatVideoDispatcher._fetch_video_via_browser_session(clean_url)

        if not raw_data or (not raw_data.get("title") and not raw_data.get("video_url") and not raw_data.get("content")):
            return {
                "title": "",
                "author": "",
                "author_id": "",
                "publish_time": "",
                "video_url": "",
                "cover_url": "",
                "duration": 0,
                "stats": {"likes": 0, "forwards": 0, "comments": 0, "favs": 0},
                "tags": [],
                "url": clean_url,
                "content": "",
                "error": raw_data.get("error") if raw_data else "未能从页面提取视频号数据"
            }

        return clean_video_data(raw_data, clean_url)

    @staticmethod
    def get_posts(limit: int = 20, query: str = "", with_content: bool = False) -> List[Dict[str, Any]]:
        """
        从已登录微信视频号助手后台批量拉取动态作品列表与各项互动数据
        - 可选 query: 动态作品关键词检索
        - 可选 with_content=True: 同时提取每条动态的完整详细文案
        """
        target_limit = max(1, int(limit or 20))
        cmd = [
            "opencli", "wechat-channels", "posts",
            "--limit", str(target_limit),
            "-f", "json"
        ]
        if query and str(query).strip():
            cmd.extend(["--query", str(query).strip()])

        code, out, err = WeChatVideoDispatcher.run_cmd(cmd, timeout=90)

        if code != 0 or not out.strip():
            if "AuthRequiredError" in err or "未检测到有效的后台登录会话" in err or "sessionid cookie missing" in err:
                raise RuntimeError(
                    "\n======================================================\n"
                    "❌ [微信视频号助手] 未检测到有效的后台登录会话！\n"
                    "------------------------------------------------------\n"
                    "👉 本功能依托桌面 Chrome 浏览器中的视频号助手官方后台。\n"
                    "👉 请在已启用 OpenCLI 扩展的 Chrome 浏览器中访问：\n"
                    "   https://channels.weixin.qq.com/\n"
                    "👉 使用微信扫码登录您的视频号助手后台后，重新执行即可。\n"
                    "======================================================\n"
                )
            raise RuntimeError(f"微信视频号后台拉取作品列表失败: {err or out}")

        try:
            posts = json.loads(out)
        except Exception as e:
            raise RuntimeError(f"解析视频列表 JSON 失败: {e}\n输出内容: {out}")

        if not isinstance(posts, list):
            return []

        # 若需要丰富详情文案
        if with_content:
            for item in posts:
                link = item.get("link")
                if link:
                    try:
                        v_data = WeChatVideoDispatcher.get_video(link)
                        item["content"] = v_data.get("content", item.get("title", ""))
                        if v_data.get("video_url"):
                            item["video_url"] = v_data.get("video_url")
                        if v_data.get("cover_url"):
                            item["cover_url"] = v_data.get("cover_url")
                    except Exception as e:
                        item["content"] = f"[详情提取失败: {e}]"
                else:
                    item["content"] = item.get("title", "")
                time.sleep(0.3)

        return posts

    @staticmethod
    def search(query: str, limit: int = 10, with_content: bool = False) -> List[Dict[str, Any]]:
        """
        全网关键词检索微信视频号相关内容
        """
        search_query = str(query).strip()
        target_limit = max(1, int(limit or 10))

        # 结合搜狗微信检索与视频号专属词
        keyword = f"{search_query} 视频号" if "视频号" not in search_query else search_query

        code, out, err = WeChatVideoDispatcher.run_cmd([
            "opencli", "weixin", "search", keyword, "--limit", str(target_limit), "-f", "json"
        ], timeout=45)

        if code != 0 or not out.strip():
            # 降级：直接通过 query 搜索
            code, out, err = WeChatVideoDispatcher.run_cmd([
                "opencli", "weixin", "search", search_query, "--limit", str(target_limit), "-f", "json"
            ], timeout=45)

        if code != 0 or not out.strip():
            raise RuntimeError(f"检索微信内容失败: {err or out}")

        try:
            results = json.loads(out)
        except Exception as e:
            raise RuntimeError(f"解析搜索结果 JSON 失败: {e}\n输出内容: {out}")

        if not isinstance(results, list):
            return []

        clean_results = []
        for i, item in enumerate(results[:target_limit], 1):
            clean_results.append({
                "index": i,
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "summary": item.get("summary", ""),
                "publish_time": item.get("publish_time", ""),
            })

        return clean_results
