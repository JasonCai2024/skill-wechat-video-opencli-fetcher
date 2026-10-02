import { ArgumentError, CommandExecutionError } from '@jackwener/opencli/errors';
import { cli, Strategy } from '@jackwener/opencli/registry';

const WECHAT_CHANNELS_DOMAIN = 'channels.weixin.qq.com';

function cleanUrl(rawUrl) {
    if (!rawUrl) return '';
    let url = String(rawUrl).trim();
    // 匹配链接可能包含在分享文本中的情况
    const urlMatch = url.match(/https?:\/\/[^\s"'<>]+/);
    if (urlMatch) {
        url = urlMatch[0];
    }
    return url;
}

export const videoCommand = cli({
    site: 'wechat-channels',
    name: 'video',
    access: 'read',
    description: '通过真实浏览器环境提取微信视频号单视频详情数据 (标题、文案、创作者、发布时间、视频链接、封面图、互动指标)',
    domain: WECHAT_CHANNELS_DOMAIN,
    strategy: Strategy.PUBLIC,
    browser: true,
    navigateBefore: false,
    args: [
        { name: 'url', required: true, help: '视频号播放链接或包含链接的分享文本 (channels.weixin.qq.com/web/pages/feed...)' },
    ],
    columns: ['title', 'author', 'publish_time', 'video_url', 'cover_url', 'likes', 'forwards', 'comments', 'favs'],

    func: async (page, kwargs) => {
        const rawUrl = kwargs.url;
        const targetUrl = cleanUrl(rawUrl);

        if (!targetUrl) {
            throw new ArgumentError('未提供有效的微信视频号链接');
        }

        // 1. 浏览器导航至视频页面
        await page.goto(targetUrl);
        await page.wait(3.5);

        // 2. 深度从 DOM 和页面内嵌上下文中提取视频详情
        const extracted = await page.evaluate(() => {
            const result = {
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
                tags: [],
                content: '',
                url: window.location.href,
            };

            // 1. 尝试从 video DOM 标签提取
            const videoEl = document.querySelector('video');
            if (videoEl) {
                result.video_url = videoEl.src || videoEl.currentSrc || '';
                result.cover_url = videoEl.poster || '';
                result.duration = Math.round(videoEl.duration || 0);
            }

            // 2. 尝试从 meta 标签提取
            const getMeta = (prop) => {
                const el = document.querySelector(`meta[property="${prop}"]`) || document.querySelector(`meta[name="${prop}"]`);
                return el ? el.getAttribute('content') : '';
            };

            const ogTitle = getMeta('og:title');
            const ogDesc = getMeta('og:description');
            const ogVideo = getMeta('og:video');
            const ogImage = getMeta('og:image');

            if (ogTitle && !result.title) result.title = ogTitle;
            if (ogDesc && !result.content) result.content = ogDesc;
            if (ogVideo && !result.video_url) result.video_url = ogVideo;
            if (ogImage && !result.cover_url) result.cover_url = ogImage;

            // 3. 提取描述文案和标题 (常见的类名选择器)
            const descSelectors = [
                '.feed-desc',
                '.desc-text',
                '.feed-description',
                '[class*="desc-"]',
                '[class*="desc_"]',
                '[class*="feed_desc"]',
                '[class*="caption"]',
                '.weui-desktop-form__desc',
            ];
            for (const sel of descSelectors) {
                const el = document.querySelector(sel);
                if (el && el.innerText && el.innerText.trim()) {
                    const text = el.innerText.trim();
                    if (!result.content || text.length > result.content.length) {
                        result.content = text;
                    }
                    if (!result.title) {
                        result.title = text.split('\n')[0].slice(0, 100);
                    }
                    break;
                }
            }

            // 4. 提取作者/视频号昵称
            const authorSelectors = [
                '.feed-author',
                '.nickname',
                '[class*="nickname"]',
                '[class*="author-name"]',
                '[class*="finder-name"]',
                '.author-info .name',
                '[class*="auth_name"]',
                '[class*="account-name"]',
            ];
            for (const sel of authorSelectors) {
                const el = document.querySelector(sel);
                if (el && el.innerText && el.innerText.trim()) {
                    result.author = el.innerText.trim();
                    break;
                }
            }

            // 5. 提取发布时间
            const timeSelectors = [
                '.feed-time',
                '[class*="create-time"]',
                '[class*="publish-time"]',
                '[class*="date-text"]',
                '[class*="time-text"]',
                'time',
            ];
            for (const sel of timeSelectors) {
                const el = document.querySelector(sel);
                if (el && el.innerText && el.innerText.trim()) {
                    result.publish_time = el.innerText.trim();
                    break;
                }
            }

            // 6. 封面补充提取：若未找到封面，从页面中较大的图片或背景图提取
            if (!result.cover_url) {
                const allImgs = Array.from(document.querySelectorAll('img'));
                for (const img of allImgs) {
                    if ((img.naturalWidth > 120 || img.width > 120) && !img.className.includes('avatar') && !img.className.includes('head')) {
                        result.cover_url = img.src;
                        break;
                    }
                }
            }
            if (!result.cover_url) {
                const bgElements = Array.from(document.querySelectorAll('[style*="background"]'));
                for (const el of bgElements) {
                    const bg = el.style.backgroundImage || '';
                    const m = bg.match(/url\(["']?(https?:\/\/[^"')]+)["']?\)/);
                    if (m) {
                        result.cover_url = m[1];
                        break;
                    }
                }
            }

            // 7. 脚本内嵌数据嗅探
            try {
                const scripts = Array.from(document.querySelectorAll('script'));
                for (const s of scripts) {
                    const txt = s.innerText || s.textContent || '';
                    if (!result.video_url && txt.includes('.mp4')) {
                        const vMatch = txt.match(/https?:\/\/[^"'\s\\]+\.mp4[^"'\s\\]*/);
                        if (vMatch) result.video_url = vMatch[0].replace(/\\u002F/g, '/');
                    }
                    if (!result.cover_url && (txt.includes('stodownload') || txt.includes('coverUrl'))) {
                        const cMatch = txt.match(/https?:\/\/[^"'\s\\]+(?:stodownload|finder)[^"'\s\\]*/);
                        if (cMatch) result.cover_url = cMatch[0].replace(/\\u002F/g, '/');
                    }
                }
            } catch (_) {}

            // 8. 提取互动数据 (点赞、转发、评论、收藏)
            const textContent = document.body ? document.body.innerText : '';
            const parseNumber = (prefix) => {
                const reg = new RegExp(`${prefix}\\s*[:：]?\\s*([0-9.]+[万wWkK]?)`, 'i');
                const m = textContent.match(reg);
                return m ? m[1] : '0';
            };

            const findStatByIcon = (iconName) => {
                const el = document.querySelector(`[class*="${iconName}"]`);
                if (el) {
                    const parent = el.closest('button, div, span');
                    if (parent && parent.innerText) {
                        const num = parent.innerText.replace(/[^\d.wW万]/g, '').trim();
                        if (num) return num;
                    }
                }
                return '0';
            };

            result.likes = findStatByIcon('like') !== '0' ? findStatByIcon('like') : parseNumber('赞|点赞');
            result.forwards = findStatByIcon('forward') !== '0' ? findStatByIcon('forward') : parseNumber('转发|分享');
            result.comments = findStatByIcon('comment') !== '0' ? findStatByIcon('comment') : parseNumber('评论');
            result.favs = findStatByIcon('fav') !== '0' ? findStatByIcon('fav') : parseNumber('收藏');

            // 9. 提取话题标签
            if (result.content) {
                const tagMatches = result.content.match(/#([^#\s，。！？、\n]+)/g);
                if (tagMatches) {
                    result.tags = tagMatches.map(t => t.replace('#', '').trim()).filter(Boolean);
                }
            }

            return result;
        });

        if (!extracted || (!extracted.title && !extracted.video_url && !extracted.content)) {
            throw new CommandExecutionError(`未能从页面中解析出有效的视频号数据: ${targetUrl}`);
        }

        return extracted;
    },
});
