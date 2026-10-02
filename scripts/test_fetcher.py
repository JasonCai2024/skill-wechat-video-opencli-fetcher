# -*- coding: utf-8 -*-
"""
微信视频号 OpenCLI 数据获取助手单元测试与联调自检
"""

import sys
import pathlib

# 添加路径
current_dir = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from _wechat_video_core import (
    WeChatVideoDispatcher,
    clean_video_data,
    parse_raw_url,
    format_timestamp,
)
from _wechat_video_core.video_parser import clean_text, extract_tags, normalize_stats


def test_url_parser():
    print("▶ 1. 测试 URL 解析与清洗...")
    case1 = "微信视频号分享：【普通人AI怎么选？】https://channels.weixin.qq.com/web/pages/feed?feedId=export%2Fxxx&nonceId=yyy"
    url1 = parse_raw_url(case1)
    assert url1.startswith("https://channels.weixin.qq.com/"), f"提取失败: {url1}"

    case2 = "https://channels.weixin.qq.com/web/pages/feed?feedId=123"
    assert parse_raw_url(case2) == case2

    print("  ✅ URL 解析测试通过！")


def test_text_cleaning():
    print("▶ 2. 测试文案脱水与标签提取...")
    raw_html = "<div class='feed-desc'>这是第一段内容。<br/><p>这是第二段正文 <b>加粗重点</b> &amp; 符号测试。</p>#AI #智能体 #大模型</div>"
    clean = clean_text(raw_html)
    assert "<" not in clean and ">" not in clean, f"仍有HTML标签: {clean}"
    assert "&" in clean, "HTML实体转义未生效"
    assert "这是第一段内容。" in clean

    tags = extract_tags(clean)
    assert "AI" in tags and "智能体" in tags and "大模型" in tags, f"标签提取不完整: {tags}"

    print("  ✅ 文本脱水与标签提取通过！")


def test_stats_normalization():
    print("▶ 3. 测试互动指标归一化...")
    assert normalize_stats("1.2万") == 12000
    assert normalize_stats("10w") == 100000
    assert normalize_stats("500") == 500
    assert normalize_stats("3.5k") == 3500
    assert normalize_stats(None) == 0
    print("  ✅ 互动指标归一化测试通过！")


def test_adapter_sync():
    print("▶ 4. 测试 OpenCLI 适配器自动同步...")
    WeChatVideoDispatcher.ensure_adapters_installed()
    target_dir = pathlib.Path.home() / ".opencli" / "clis" / "wechat-channels"
    assert (target_dir / "video.js").exists(), "video.js 未同步"
    assert (target_dir / "posts.js").exists(), "posts.js 未同步"
    print("  ✅ OpenCLI 适配器同步成功！")


def test_doctor():
    print("▶ 5. 测试环境探活...")
    doc = WeChatVideoDispatcher.check_doctor()
    print(f"  Doctor 执行状态码: {doc['code']}, 连通性就绪: {doc['connected']}")
    print("  ✅ 环境探活测试通过！")


def main():
    print("=" * 60)
    print("🚀 开始执行微信视频号 OpenCLI 获取助手全量自检...")
    print("=" * 60)
    test_url_parser()
    test_text_cleaning()
    test_stats_normalization()
    test_adapter_sync()
    test_doctor()
    print("=" * 60)
    print("🎉 全部测试项目通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
