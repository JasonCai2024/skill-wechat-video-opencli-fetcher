import { AuthRequiredError, EmptyResultError, CommandExecutionError } from '@jackwener/opencli/errors';
import { cli, Strategy } from '@jackwener/opencli/registry';

const WECHAT_CHANNELS_DOMAIN = 'channels.weixin.qq.com';

function formatTimestamp(tsSec) {
    if (!tsSec) return '';
    const d = new Date(Number(tsSec) * 1000 + 8 * 3600 * 1000);
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`;
}

async function hasChannelsSessionCookie(page) {
    const cookies = await page.getCookies({ url: 'https://channels.weixin.qq.com' });
    return cookies.some(c => c.name === 'sessionid' && c.value);
}

export const postsCommand = cli({
    site: 'wechat-channels',
    name: 'posts',
    access: 'read',
    description: '通过已登录的微信视频号助手后台批量拉取动态作品列表与各项互动数据指标',
    domain: WECHAT_CHANNELS_DOMAIN,
    strategy: Strategy.COOKIE,
    browser: true,
    navigateBefore: false,
    args: [
        { name: 'limit', type: 'int', default: 20, help: '抓取视频条数 (默认 20)' },
        { name: 'query', type: 'string', default: '', help: '作品关键词检索过滤 (可选)' },
    ],
    columns: ['index', 'title', 'create_time', 'export_id', 'read_count', 'like_count', 'forward_count', 'comment_count', 'status'],

    func: async (page, kwargs) => {
        const targetLimit = Math.max(1, parseInt(kwargs.limit || 20, 10));
        const searchKeyword = (kwargs.query || '').trim().toLowerCase();

        // 1. 验证登录 Cookie
        if (!await hasChannelsSessionCookie(page)) {
            throw new AuthRequiredError(WECHAT_CHANNELS_DOMAIN, '微信视频号助手需要已登录会话。请在 Chrome 浏览器中访问 channels.weixin.qq.com 并完成扫码登录。');
        }

        // 2. 访问视频号助手动态管理列表页
        await page.goto('https://channels.weixin.qq.com/platform/post/list');
        await page.wait(2.5);

        // 检查是否跳转到登录页
        const isLogin = await page.evaluate(() => /login\.html/.test(window.location.href));
        if (isLogin) {
            throw new AuthRequiredError(WECHAT_CHANNELS_DOMAIN, '微信视频号后台会话已失效。请在 Chrome 中重新登录 channels.weixin.qq.com。');
        }

        // 3. 优先通过后台原生 JSON 接口分页拉取作品
        const apiData = await page.evaluate(async (limit) => {
            try {
                let posts = [];
                let lastBuffer = '';
                let hasMore = true;

                while (posts.length < limit && hasMore) {
                    const reqBody = {
                        page_size: Math.min(20, limit - posts.length),
                        last_buffer: lastBuffer,
                    };

                    const resp = await fetch('/cgi-bin/mmfinderassistant-bin/helper/get_finder_post_list', {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(reqBody),
                    });

                    if (!resp.ok) break;
                    const resJson = await resp.json();
                    if (!resJson || resJson.base_resp?.ret !== 0) break;

                    const list = resJson.data?.list || resJson.list || [];
                    if (!list || list.length === 0) break;

                    posts = posts.concat(list);
                    lastBuffer = resJson.data?.last_buffer || resJson.last_buffer || '';
                    hasMore = Boolean(resJson.data?.has_more ?? resJson.has_more ?? false);
                    if (!lastBuffer) break;
                }

                return { ok: true, list: posts };
            } catch (err) {
                return { ok: false, error: String(err) };
            }
        }, targetLimit);

        const results = [];

        if (apiData.ok && apiData.list && apiData.list.length > 0) {
            for (const item of apiData.list) {
                const desc = (item.description || item.title || '').trim();
                if (searchKeyword && !desc.toLowerCase().includes(searchKeyword)) {
                    continue;
                }

                const createTime = item.create_time || item.post_time || 0;
                const exportId = item.export_id || item.object_id || '';
                const link = exportId ? `https://channels.weixin.qq.com/web/pages/feed?feedId=${encodeURIComponent(exportId)}` : '';

                results.push({
                    index: results.length + 1,
                    title: desc.slice(0, 100) || '无标题动态',
                    create_time: formatTimestamp(createTime),
                    export_id: exportId,
                    read_count: item.read_count || item.view_count || 0,
                    like_count: item.like_count || 0,
                    forward_count: item.forward_count || 0,
                    comment_count: item.comment_count || 0,
                    status: item.status_desc || item.status || '已发表',
                    cover_url: item.cover_url || item.head_url || '',
                    link: link,
                    full_content: desc,
                });

                if (results.length >= targetLimit) break;
            }
        }

        // 4. 备用 DOM 抓取：如果接口未返回数据，从页面渲染的表格/卡片中提取
        if (results.length === 0) {
            const domItems = await page.evaluate(() => {
                const items = [];
                // 遍历管理表格或列表项
                const rows = document.querySelectorAll('tr, .post-item, .weui-desktop-table__tr');
                for (const row of rows) {
                    const text = row.innerText.trim();
                    if (!text || text.includes('标题') && text.includes('发布时间')) continue;

                    const titleEl = row.querySelector('.post-title, [class*="title"], td:first-child');
                    const timeEl = row.querySelector('.post-time, [class*="time"], td:nth-child(2)');
                    const statEls = row.querySelectorAll('td, .stat-item');

                    if (titleEl) {
                        items.push({
                            title: titleEl.innerText.trim(),
                            create_time: timeEl ? timeEl.innerText.trim() : '',
                            raw_text: text,
                        });
                    }
                }
                return items;
            });

            for (const d of domItems) {
                if (searchKeyword && !d.title.toLowerCase().includes(searchKeyword)) {
                    continue;
                }
                results.push({
                    index: results.length + 1,
                    title: d.title,
                    create_time: d.create_time,
                    export_id: '',
                    read_count: 0,
                    like_count: 0,
                    forward_count: 0,
                    comment_count: 0,
                    status: '正常',
                    cover_url: '',
                    link: '',
                    full_content: d.title,
                });
                if (results.length >= targetLimit) break;
            }
        }

        if (results.length === 0) {
            const hint = searchKeyword ? `未找到包含关键词 "${searchKeyword}" 的作品` : `暂无可读取的动态作品`;
            throw new EmptyResultError(`wechat-channels posts`, hint);
        }

        return results;
    },
});
