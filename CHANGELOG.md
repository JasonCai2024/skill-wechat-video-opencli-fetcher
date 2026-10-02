# Changelog

本文件记录本 skill 的所有用户可见变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增
- 待补充

## [1.0.0] - 2026-10-02

### 新增
- 初始版本发布
- 基于本地 OpenCLI 守护进程与 Chrome 真实扩展的微信视频号原始数据提取方案
- 核心命令 `video`：单视频详情解析（标题、作者、发布时间、视频流、封面、点赞/转发/评论/收藏互动指标、纯文本脱水文案）
- 核心命令 `posts`：批量拉取视频号助手后台作品动态列表及播放量/点赞数/评论数统计
- 核心命令 `search`：全网检索微信视频号相关内容
- 核心命令 `whoami`：查询当前 Chrome 中已登录的视频号身份
- 核心命令 `doctor`：环境健康探活与一键故障自检
- 自研 `video_parser.py` 文本脱水与指标归一化清洗引擎
- OpenCLI 原生适配器 `adapters/wechat-channels/video.js` 与 `adapters/wechat-channels/posts.js`
- 完善的文档规范与命令参考手册（`SKILL.md`, `README.md`, `INSTALL.md`, `commands-reference.md`, `setup-guide.md`, `troubleshooting.md`）

[Unreleased]: https://github.com/JasonCai2024/skill-wechat-video-opencli-fetcher
[1.0.0]: https://github.com/JasonCai2024/skill-wechat-video-opencli-fetcher/releases/tag/v1.0.0
