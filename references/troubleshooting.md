# 微信视频号常见问题排查与自愈指南 (Troubleshooting)

本文档整理了运行 `skill-wechat-video-opencli-fetcher` 过程中的常见问题原因与快速自愈排查方案。

---

## 异常现象与自愈速查表

| 异常现象 / 错误信息 | 原因分析 | 快速自愈排查步骤 |
|---|---|---|
| **`未检测到有效的后台登录会话` / `AUTH_REQUIRED`** | 尚未在 Chrome 中登录视频号助手后台，或后台登录态已超时失效 | 1. 打开 Chrome 浏览器，访问 `https://channels.weixin.qq.com/`；<br>2. 用微信手机端扫码登录您的视频号助手后台；<br>3. 保持 Chrome 打开，重新执行 `python scripts/wechat_video_fetcher.py posts` 即可。 |
| **`Extension: disconnected`** | Chrome 浏览器未打开，或 OpenCLI 扩展被禁用 | 1. 启动桌面 Chrome 浏览器；<br>2. 访问 `chrome://extensions/` 确认 OpenCLI 扩展处于开启状态；<br>3. 运行 `python scripts/wechat_video_fetcher.py doctor` 重新探活。 |
| **`Daemon: not running`** | 本地 OpenCLI 守护进程未启动 | 终端执行 `opencli daemon restart` 重新唤起守护进程。 |
| **`未能从页面提取视频号数据`** | 传入的链接已失效、被作者删除或网络加载较慢 | 1. 在 Chrome 中手动打开该链接，核验视频是否仍然可播放；<br>2. 尝试添加 `--force-browser` 参数使用独立会话拉取；<br>3. 确保网络通畅。 |
| **`无法从输入中提取有效视频链接`** | 传入的文本不包含标准的 `http/https` 链接 | 请确认输入的分享文本包含 `https://channels.weixin.qq.com/...` 等有效 URL。 |

---

## 自愈检查三板斧

若命令执行出现任何未知异常，建议按以下顺序自检：

1. **第 1 步：执行统一探活**
   ```bash
   python scripts/wechat_video_fetcher.py doctor
   ```
2. **第 2 步：重启 OpenCLI 守护进程**
   ```bash
   opencli daemon restart
   ```
3. **第 3 步：确认 Chrome 浏览器状态**
   确保日常 Chrome 处于开启状态，右上角可见 OpenCLI 扩展图标正常亮起。
