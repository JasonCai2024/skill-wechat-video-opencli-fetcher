# 微信视频号 OpenCLI 运行环境搭建与登录配置指南

本文档指导用户与 AI 助理首次配置运行环境，实现视频号数据免维护 Cookie 采集。

---

## 核心工作原理

本技能采用 **“Python 统一外壳 + 本地 OpenCLI 守护进程 + Chrome 桌面真实浏览器扩展”** 架构：
1. **Node.js Daemon**：在后台监听本地 `127.0.0.1:19825` 端口，提供高效安全的命令管道；
2. **Chrome 扩展**：直接桥接您日常使用的桌面 Chrome 浏览器，复用真实浏览器指纹与安全上下文；
3. **视频号会话继承**：通过真实已登录的 `channels.weixin.qq.com` 发起请求，完全继承真人指纹与 Session Token，彻底告别 Cookie 过期与封禁风险。

---

## 4 步快速配置流程

### 第 1 步：安装 OpenCLI
在终端运行：
```bash
npm install -g @jackwener/opencli
```

### 第 2 步：安装并启用 Chrome 浏览器扩展
- **途径 A（Chrome 网上应用店）**：
  直接在 Chrome Web Store 中搜索 `OpenCLI` 安装并开启扩展；
- **途径 B（本地解压安装）**：
  1. 终端执行：`opencli extension install`；
  2. 在 Chrome 地址栏打开 `chrome://extensions/` 开启右上角 **「开发者模式」**；
  3. 点击 **「加载已解压的扩展程序」**，选中 `~/.opencli/extension` 目录。

### 第 3 步：登录微信视频号助手（可选，拉取作品动态需具备）
1. 打开已启用 OpenCLI 扩展的 Chrome 浏览器，访问：[https://channels.weixin.qq.com/](https://channels.weixin.qq.com/)；
2. 使用手机微信扫码登录视频号助手后台；
3. 保持 Chrome 浏览器打开。

> 💡 **注**：若仅需提取公开单视频详情与口播文案（`video` 命令），无需登录视频号后台，桌面 Chrome 保持开启即可。

### 第 4 步：一键环境验证
在终端执行：
```bash
python scripts/wechat_video_fetcher.py doctor
```
看到 `[OK] Connectivity: connected` 即表示全链路准备就绪！
