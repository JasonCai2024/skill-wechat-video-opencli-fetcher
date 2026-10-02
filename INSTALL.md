# 微信视频号 OpenCLI 数据获取助手安装指南 (INSTALL.md)

本文档提供从零开始配置 `skill-wechat-video-opencli-fetcher` 的完整操作步骤。

---

## 1. 系统要求与环境准备

在安装前请确认您的系统满足以下条件：
- **操作系统**: Windows / macOS / Linux
- **Node.js**: `>= 18.0.0`（通过 `node -v` 验证）
- **Python**: `>= 3.8`（通过 `python --version` 验证）
- **Google Chrome**: 桌面最新版本

---

## 2. 安装步骤

### 步骤 1：克隆或下载技能仓库
```bash
git clone https://github.com/JasonCai2024/skill-wechat-video-opencli-fetcher.git
cd skill-wechat-video-opencli-fetcher
```

### 步骤 2：安装 OpenCLI 全局命令行
```bash
npm install -g @jackwener/opencli
```
验证安装：
```bash
opencli --version
```

### 步骤 3：安装并启用 Chrome 浏览器扩展
1. 打开 Chrome 浏览器，在 Chrome Web Store 中搜索并安装 `OpenCLI` 扩展；
2. 或者在终端执行命令自动获取扩展包：
   ```bash
   opencli extension install
   ```
3. 在 Chrome 中打开 `chrome://extensions/`，开启右上角的 **开发者模式**，点击 **加载已解压的扩展程序** 并选择 `~/.opencli/extension` 目录；
4. 保持扩展处于启用状态。

### 步骤 4：安装 Python 依赖
```bash
pip install -r requirements.txt
```

### 步骤 5：登录微信视频号助手（可选）
若需拉取自己账号的作品动态与播放统计：
1. 在已启用 OpenCLI 扩展的 Chrome 中访问：[https://channels.weixin.qq.com/](https://channels.weixin.qq.com/)；
2. 用手机微信扫码登录视频号助手；
3. 保持 Chrome 浏览器打开。

---

## 3. 健康检查与联调验证

执行一键自检脚本：
```bash
python scripts/test_fetcher.py
```
若输出全部通过，再执行终端探活：
```bash
python scripts/wechat_video_fetcher.py doctor
```
看到 `✅ [OK] OpenCLI 真实浏览器桥接环境完全就绪！` 即表示全流程配置完毕。
