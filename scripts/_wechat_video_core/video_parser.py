# -*- coding: utf-8 -*-
"""
微信视频号数据解析与文本脱水清洗器 (Video Parser & Text Decanter)
提取并标准化核心字段：标题、作者、发布时间、视频流、封面、互动数据与纯文本正文
"""

import re
import html
import datetime
from typing import Dict, Any, List, Optional


def parse_raw_url(text: str) -> str:
    """从包含分享文本或不规则字符的输入中精准提取微信视频号链接"""
    if not text:
        return ""
    text = str(text).strip()
    
    # 查找 http 或 https 链接
    match = re.search(r"https?://[^\s\"'<>]+", text)
    if match:
        url = match.group(0)
        # 移除末尾常见标点
        url = re.sub(r"[，。！？；、）\]}>]+$", "", url)
        return url

    # 若未带协议头但以 channels.weixin.qq.com 开头
    if "channels.weixin.qq.com" in text:
        sub = re.search(r"channels\.weixin\.qq\.com[^\s\"'<>]+", text)
        if sub:
            return "https://" + sub.group(0)

    return text


def clean_text(raw_text: str) -> str:
    """彻底剥离 HTML 标签与多余控制字符，保留自然段落与话题"""
    if not raw_text:
        return ""

    # 解码 HTML 实体 (&nbsp;, &lt;, 等)
    decoded = html.unescape(str(raw_text))

    # 移除 script, style 标签及内容
    decoded = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", decoded, flags=re.DOTALL | re.IGNORECASE)

    # 块级换行标签替换为换行
    decoded = re.sub(r"<(p|div|br|h[1-6]|li|section|article)[^>]*>", "\n", decoded, flags=re.IGNORECASE)

    # 剥离所有 HTML 标签
    decoded = re.sub(r"<[^>]+>", "", decoded)

    # 按行整理，去除每行两端空白，压缩连续空行
    lines = [line.strip() for line in decoded.split("\n")]
    clean_lines = []
    last_empty = True
    for line in lines:
        if not line:
            if not last_empty:
                clean_lines.append("")
                last_empty = True
        else:
            clean_lines.append(line)
            last_empty = False

    return "\n".join(clean_lines).strip()


def extract_tags(text: str) -> List[str]:
    """从文本中提取 #话题标签"""
    if not text:
        return []
    matches = re.findall(r"#([^#\s，。！？、\n]+)", text)
    # 去重并保序
    seen = set()
    tags = []
    for m in matches:
        t = m.strip()
        if t and t not in seen:
            seen.add(t)
            tags.append(t)
    return tags


def normalize_stats(raw_val: Any) -> int:
    """将包含 '万'、'w'、'k' 或千分符的文本统计指标归一化为整型数字"""
    if raw_val is None:
        return 0
    if isinstance(raw_val, (int, float)):
        return int(raw_val)

    val_str = str(raw_val).strip().replace(",", "")
    if not val_str:
        return 0

    try:
        # 10万+ 或 10w
        m_wan = re.search(r"([0-9.]+)\s*[万wW]", val_str)
        if m_wan:
            return int(float(m_wan.group(1)) * 10000)

        # 1.2k
        m_k = re.search(r"([0-9.]+)\s*[kK]", val_str)
        if m_k:
            return int(float(m_k.group(1)) * 1000)

        # 提取纯数字
        nums = re.findall(r"\d+", val_str)
        if nums:
            return int("".join(nums))
    except Exception:
        pass

    return 0


def format_timestamp(raw_ts: Any) -> str:
    """将秒级/毫秒级时间戳或日期字符串格式化为标准 YYYY-MM-DD HH:mm:ss (UTC+8)"""
    if not raw_ts:
        return ""

    raw_str = str(raw_ts).strip()
    
    # 尝试纯数字时间戳
    if re.match(r"^\d+$", raw_str):
        try:
            ts = int(raw_str)
            if ts > 1000000000000:
                ts = ts // 1000
            if ts <= 0:
                return ""
            tz_offset = datetime.timezone(datetime.timedelta(hours=8))
            dt = datetime.datetime.fromtimestamp(ts, tz=tz_offset)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    # 匹配标准日期格式
    m_std = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?", raw_str)
    if m_std:
        year, month, day = m_std.group(1), m_std.group(2).zfill(2), m_std.group(3).zfill(2)
        hour = (m_std.group(4) or "00").zfill(2)
        minute = (m_std.group(5) or "00").zfill(2)
        second = (m_std.group(6) or "00").zfill(2)
        return f"{year}-{month}-{day} {hour}:{minute}:{second}"

    # 匹配中文年月日格式 (如 2026年10月1日)
    m_cn = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日(?:\s*(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?", raw_str)
    if m_cn:
        year, month, day = m_cn.group(1), m_cn.group(2).zfill(2), m_cn.group(3).zfill(2)
        hour = (m_cn.group(4) or "00").zfill(2)
        minute = (m_cn.group(5) or "00").zfill(2)
        second = (m_cn.group(6) or "00").zfill(2)
        return f"{year}-{month}-{day} {hour}:{minute}:{second}"

    return raw_str


def clean_video_data(raw_data: Dict[str, Any], source_url: str = "") -> Dict[str, Any]:
    """清洗并标准化视频结构化字典"""
    raw_content = raw_data.get("content") or raw_data.get("description") or raw_data.get("title") or ""
    pure_content = clean_text(raw_content)

    title = raw_data.get("title") or ""
    if not title and pure_content:
        # 取第一行作为标题
        title = pure_content.split("\n")[0][:100]

    author = (raw_data.get("author") or raw_data.get("nickname") or raw_data.get("finder_username") or "").strip()
    author_id = (raw_data.get("author_id") or raw_data.get("finderUsername") or "").strip()
    publish_time = format_timestamp(raw_data.get("publish_time") or raw_data.get("create_time"))

    video_url = raw_data.get("video_url") or raw_data.get("media_url") or raw_data.get("src") or ""
    cover_url = raw_data.get("cover_url") or raw_data.get("poster") or ""
    duration = int(raw_data.get("duration") or 0)

    tags = raw_data.get("tags") or []
    if not tags and pure_content:
        tags = extract_tags(pure_content)

    stats = {
        "likes": normalize_stats(raw_data.get("likes") or raw_data.get("like_count")),
        "forwards": normalize_stats(raw_data.get("forwards") or raw_data.get("forward_count")),
        "comments": normalize_stats(raw_data.get("comments") or raw_data.get("comment_count")),
        "favs": normalize_stats(raw_data.get("favs") or raw_data.get("fav_count")),
    }

    url = raw_data.get("url") or source_url

    return {
        "title": title,
        "author": author,
        "author_id": author_id,
        "publish_time": publish_time,
        "video_url": video_url,
        "cover_url": cover_url,
        "duration": duration,
        "stats": stats,
        "tags": tags,
        "url": url,
        "content": pure_content
    }
