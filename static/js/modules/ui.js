// ==================== 用户权限 ====================
const currentUser = window.__USER__ || {};

/**
 * 全局 API fetch 包装器 — 统一处理 401（跳转登录）和 403（VIP 限制提示）
 */
async function apiFetch(url, options = {}) {
    const res = await fetch(url, options);
    if (res.status === 401) {
        const data = await res.json().catch(() => ({}));
        if (data.redirect) {
            window.location.href = data.redirect;
        } else {
            window.location.href = '/login';
        }
        throw new Error('需要登录');
    }
    if (res.status === 403) {
        const data = await res.json().catch(() => ({}));
        if (data.vip_required) {
            showCenterToast('✨ ' + (data.error || '该功能仅 VIP 会员可用，请升级后体验'), 'warn', true);
        }
        throw new Error(data.error || '权限不足');
    }
    return res;
}

// ==================== 统计图表卡片拖拽排列与持久化 ====================

// 按照本地存储的顺序重排图表卡片 DOM 节点
function applyChartOrder() {
    const grid = document.querySelector('.charts-grid');
    if (!grid) return;

    const orderKey = `chart_order_v3_${state.lotteryType}`;
    const savedOrder = localStorage.getItem(orderKey);
    if (!savedOrder) return;

    try {
        const orderArray = JSON.parse(savedOrder);
        // 如果旧的保存顺序不包含新图表，则废弃旧排列以防止新图表错位或被隐藏
        if (state.lotteryType === 'weilitsai' && !orderArray.includes('chart-card-three-region-prime')) {
            localStorage.removeItem(orderKey);
            return;
        }
        
        // 遍历保存的卡片 ID，按顺序 appendChild 重排 DOM
        orderArray.forEach(id => {
            const el = document.getElementById(id);
            if (el && el.parentNode === grid) {
                grid.appendChild(el);
            }
        });
    } catch (e) {
        console.error("Failed to apply chart order:", e);
    }
}

// 初始化 SortableJS 拖拽库
function initDragAndDrop() {
    const grid = document.querySelector('.charts-grid');
    if (!grid || typeof Sortable === 'undefined') return;

    // 首先应用已保存的排列顺序
    applyChartOrder();

    // 绑定重置图表排列按钮事件
    const btnResetOrder = document.getElementById('btn-reset-chart-order');
    if (btnResetOrder) {
        btnResetOrder.addEventListener('click', () => {
            resetChartOrder();
        });
    }

    // 初始化 Sortable 拖拽
    new Sortable(grid, {
        animation: 200, // 拖拽过渡动效时长 (ms)
        ghostClass: 'chart-card-ghost', // 占位符样式类
        chosenClass: 'chart-card-chosen', // 被选中卡片缩放样式类
        dragClass: 'chart-card-drag', // 拖拽中悬浮样式类
        delay: 200, // 移动端和 PC 端均启用 200ms 长按延时，防误触
        delayOnTouchOnly: false, // 电脑端也采用延时以防普通点击时误触抖动
        touchStartThreshold: 5, // 手机端手指移动 5px 以内仍判定为长按，超过则判定为滚动，防止误触
        handle: '.chart-title', // 限制只能拖拽卡片的标题区域，提升细节交互度
        onEnd: function () {
            // 拖拽结束时，实时收集子元素 ID 并更新 localStorage
            const orderKey = `chart_order_v3_${state.lotteryType}`;
            const currentOrder = Array.from(grid.children)
                .map(el => el.id)
                .filter(id => id); // 过滤无 ID 的多余节点
            localStorage.setItem(orderKey, JSON.stringify(currentOrder));
            
            // 触发微弱手机震动（如果设备支持，提升微交互品质）
            if (navigator.vibrate) {
                navigator.vibrate(15);
            }
        }
    });
}

// 恢复默认的卡片排列顺序
function resetChartOrder() {
    const orderKey = `chart_order_v3_${state.lotteryType}`;
    localStorage.removeItem(orderKey);
    // 重置后直接刷新页面以恢复默认布局
    window.location.reload();
}

function renderRoleRules() {
    const box = document.getElementById('settings-role-rules');
    if (!box) return;

    const role = (window.__USER__ && window.__USER__.role) || 'trial';
    const roleLabel = role === 'admin' ? '管理员' : (role === 'vip' ? 'VIP 会员' : '普通用户');

    let aiRule = 'AI 模拟每次扣 5 积分（用平台模型扣）';
    let periodRule = '修改图表期数：每项 1 积分（冷热号、尾数免费）';
    let modelRule = '可选平台与模型，不可自定义 API/平台/模型';

    if (role === 'vip') {
        aiRule = 'AI 模拟每次扣 5 积分（用平台模型扣）；自己模型免费';
        periodRule = '修改图表期数免费，任意分析图表';
        modelRule = '可配置自定义 API、平台与模型（自己模型免费）';
    } else if (role === 'admin') {
        aiRule = 'AI 模拟免费';
        periodRule = '修改图表期数免费，任意分析图表';
        modelRule = '可配置自定义 API、平台与模型';
    }

    box.innerHTML = `
        <div style="border:1px solid rgba(148,163,184,.25);border-radius:10px;padding:10px 12px;background:rgba(15,23,42,.45);">
            <div style="font-size:.82rem;font-weight:700;color:#e2e8f0;margin-bottom:6px;">当前权限：${roleLabel}</div>
            <div style="font-size:.78rem;line-height:1.65;color:#94a3b8;">• ${aiRule}</div>
            <div style="font-size:.78rem;line-height:1.65;color:#94a3b8;">• ${periodRule}</div>
            <div style="font-size:.78rem;line-height:1.65;color:#94a3b8;">• ${modelRule}</div>
        </div>
    `;
}

async function renderSimulationBillingTip() {
    const el = document.getElementById('sim-billing-tip');
    if (!el) return;

    const role = (window.__USER__ && window.__USER__.role) || 'trial';
    let title = '当前计费';
    let text = '平台 AI 模拟每次扣 5 积分。';
    let color = '#cbd5e1';
    let border = 'rgba(148,163,184,.18)';

    if (role === 'vip') {
        text = '平台模型每次扣 5 积分；使用你自己的 API / 自定义模型免费。';
        color = '#fde68a';
        border = 'rgba(245,158,11,.26)';
    } else if (role === 'admin') {
        text = '管理员 AI 模拟免费，不扣积分。';
        color = '#86efac';
        border = 'rgba(34,197,94,.28)';
    }

    // 尝试拉取当前配置，追加显示 AI 模型信息
    let modelText = '';
    try {
        const res = await fetch('/api/settings?type=' + state.lotteryType);
        const result = await res.json();
        if (result.success && result.data && result.data.ai) {
            const ai = result.data.ai;
            const modelName = ai.model || '未设置';
            const platformName = ai.platform || '未设置';
            modelText = ` <span style="margin-left: 15px; color: #a855f7; background: rgba(168,85,247,0.12); padding: 2px 8px; border-radius: 6px; font-size: 0.8rem; border: 1px solid rgba(168,85,247,0.25); font-weight: normal;">🤖 当前 AI 模型: <strong style="color: #c084fc;">${modelName}</strong> (${platformName})</span>`;
        }
    } catch (e) {
        console.error("加载当前 AI 模型配置失败:", e);
    }

    el.style.borderColor = border;
    el.innerHTML = `<strong style="color:${color};">${title}：</strong>${text}${modelText}`;
}

function initSpecialReferenceBoard() {
    const board = document.getElementById('special-reference-board');
    const status = document.getElementById('ref-board-status');
    if (!board || !status) return;

    const allChips = Array.from(board.querySelectorAll('.ref-chip'));
    let activeNumber = '';

    const zodiacMap = {
        '01': '马（本命）', '13': '马（本命）', '25': '马（本命）', '37': '马（本命）', '49': '马（本命）',
        '02': '蛇', '14': '蛇', '26': '蛇', '38': '蛇',
        '03': '龙', '15': '龙', '27': '龙', '39': '龙',
        '04': '兔', '16': '兔', '28': '兔', '40': '兔',
        '05': '虎', '17': '虎', '29': '虎', '41': '虎',
        '06': '牛', '18': '牛', '30': '牛', '42': '牛',
        '07': '鼠', '19': '鼠', '31': '鼠', '43': '鼠',
        '08': '猪', '20': '猪', '32': '猪', '44': '猪',
        '09': '狗', '21': '狗', '33': '狗', '45': '狗',
        '10': '鸡', '22': '鸡', '34': '鸡', '46': '鸡',
        '11': '猴', '23': '猴', '35': '猴', '47': '猴',
        '12': '羊', '24': '羊', '36': '羊', '48': '羊'
    };
    const colorMap = {
        '01': '红波', '02': '红波', '07': '红波', '08': '红波', '12': '红波', '13': '红波', '18': '红波', '19': '红波', '23': '红波', '24': '红波', '29': '红波', '30': '红波', '34': '红波', '35': '红波', '40': '红波', '45': '红波', '46': '红波',
        '03': '蓝波', '04': '蓝波', '09': '蓝波', '10': '蓝波', '14': '蓝波', '15': '蓝波', '20': '蓝波', '25': '蓝波', '26': '蓝波', '31': '蓝波', '36': '蓝波', '37': '蓝波', '41': '蓝波', '42': '蓝波', '47': '蓝波', '48': '蓝波',
        '05': '绿波', '06': '绿波', '11': '绿波', '16': '绿波', '17': '绿波', '21': '绿波', '22': '绿波', '27': '绿波', '28': '绿波', '32': '绿波', '33': '绿波', '38': '绿波', '39': '绿波', '43': '绿波', '44': '绿波', '49': '绿波'
    };
    const wuxingMap = {
        '06': '金', '07': '金', '20': '金', '21': '金', '28': '金', '29': '金', '36': '金', '37': '金', '44': '金', '45': '金',
        '01': '木', '08': '木', '09': '木', '16': '木', '17': '木', '30': '木', '31': '木', '38': '木', '39': '木', '46': '木', '47': '木',
        '04': '水', '05': '水', '12': '水', '13': '水', '26': '水', '27': '水', '34': '水', '35': '水', '48': '水', '49': '水',
        '02': '火', '03': '火', '10': '火', '11': '火', '18': '火', '19': '火', '32': '火', '33': '火', '40': '火', '41': '火',
        '14': '土', '15': '土', '22': '土', '23': '土', '24': '土', '25': '土', '42': '土', '43': '土'
    };

    const setStatus = (num) => {
        if (!num) {
            status.textContent = '点击任意数字高亮它在生肖、波色、五行中的对应关系';
            return;
        }
        status.textContent = `号码 ${num} -> 生肖：${zodiacMap[num] || '未知'} ｜ 波色：${colorMap[num] || '未知'} ｜ 五行：${wuxingMap[num] || '未知'}`;
    };

    allChips.forEach((chip) => {
        chip.addEventListener('click', () => {
            const num = chip.dataset.number || '';
            if (activeNumber === num) {
                activeNumber = '';
                allChips.forEach((item) => item.classList.remove('active'));
                setStatus('');
                return;
            }
            activeNumber = num;
            allChips.forEach((item) => {
                item.classList.toggle('active', item.dataset.number === num);
            });
            setStatus(num);
        });
    });
}

// ==================== 选项卡切换 ====================
function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // 先保存当前 Tab 的滚动位置
    if (state.currentTab) {
        if (!state.tabScrollPositions) state.tabScrollPositions = {};
        state.tabScrollPositions[state.currentTab] = window.scrollY || window.pageYOffset || 0;
    }

    // 更新按钮状态
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // 更新内容区
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    document.getElementById(`section-${tabName}`).classList.add('active');

    // 恢复目标 Tab 之前记忆的滚动位置（首次访问默认 0）
    const savedPos = (state.tabScrollPositions && state.tabScrollPositions[tabName]) || 0;
    window.scrollTo({ top: savedPos, behavior: 'instant' });

    state.currentTab = tabName;

    // 按需加载数据
    if (tabName === 'statistics' && !state.statisticsLoaded) {
        loadStatistics();
    } else if (tabName === 'history') {
        // 根据子标签加载对应内容
        if (historySubTab === 'draw') {
            loadHistory(state.historyPage || 1);
        } else {
            loadAIHistory(state.aiHistoryPage || 1);
        }
    }
}

// ==================== 工具函数 ====================
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (show) {
        overlay.classList.add('show');
    } else {
        overlay.classList.remove('show');
    }
}

