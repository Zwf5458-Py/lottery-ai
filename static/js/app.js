/**
 * 前端交互逻辑
 * 功能：统计数据可视化、模拟开奖交互、历史记录分页
 */

// ==================== 全局状态 ====================
const state = {
    lotteryType: 'weilitsai',
    currentTab: 'statistics',
    statisticsLoaded: false,
    historyPage: 1,
    historyTotalPages: 1,
    aiHistoryPage: 1,
    charts: {}  // 存储 Chart.js 实例，防止重复创建
};

// ==================== Chart.js 全局性能优化 ====================
if (typeof Chart !== 'undefined') {
    Chart.defaults.animation = false;
    Chart.defaults.animations = {};
    Chart.defaults.transitions = { active: { animation: { duration: 0 } } };
    Chart.defaults.hover.animationDuration = 0;
    Chart.defaults.responsiveAnimationDuration = 0;
    Chart.defaults.elements.point.radius = 2;
    Chart.defaults.elements.point.hoverRadius = 4;
    Chart.defaults.elements.line.tension = 0.3;
}

let centerConfirmModal = null;

function ensureCenterConfirmModal() {
    if (centerConfirmModal) return centerConfirmModal;

    const overlay = document.createElement('div');
    overlay.id = 'center-confirm-overlay';
    overlay.style.cssText = [
        'position:fixed',
        'inset:0',
        'display:none',
        'align-items:center',
        'justify-content:center',
        'background:rgba(2,6,23,0.62)',
        'backdrop-filter:blur(4px)',
        'z-index:12000'
    ].join(';');

    overlay.innerHTML = `
        <div id="center-confirm-panel" style="width:min(92vw,460px);background:rgba(15,23,42,0.96);border:1px solid rgba(168,85,247,0.35);border-radius:14px;padding:18px 18px 14px;box-shadow:0 16px 40px rgba(0,0,0,.45);">
            <div id="center-confirm-title" style="font-size:1rem;font-weight:800;color:#e9d5ff;margin-bottom:10px;">操作确认</div>
            <div id="center-confirm-message" style="font-size:.92rem;line-height:1.65;color:#e5e7eb;margin-bottom:16px;word-break:break-word;"></div>
            <div style="display:flex;justify-content:flex-end;gap:10px;">
                <button id="center-confirm-cancel" type="button" style="border:1px solid rgba(148,163,184,.35);background:rgba(71,85,105,.55);color:#e2e8f0;border-radius:10px;padding:8px 16px;font-size:.88rem;font-weight:700;cursor:pointer;">取消</button>
                <button id="center-confirm-ok" type="button" style="border:1px solid rgba(168,85,247,.45);background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;border-radius:10px;padding:8px 16px;font-size:.88rem;font-weight:700;cursor:pointer;">确定</button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);
    centerConfirmModal = overlay;
    return overlay;
}

function showCenterConfirm(message, title = '操作确认') {
    return new Promise((resolve) => {
        const modal = ensureCenterConfirmModal();
        const titleEl = document.getElementById('center-confirm-title');
        const msgEl = document.getElementById('center-confirm-message');
        const okBtn = document.getElementById('center-confirm-ok');
        const cancelBtn = document.getElementById('center-confirm-cancel');

        titleEl.textContent = title;
        msgEl.textContent = message;
        modal.style.display = 'flex';

        const close = (result) => {
            modal.style.display = 'none';
            modal.removeEventListener('click', onOverlayClick);
            okBtn.removeEventListener('click', onOk);
            cancelBtn.removeEventListener('click', onCancel);
            document.removeEventListener('keydown', onKeyDown);
            resolve(result);
        };

        const onOverlayClick = (e) => {
            if (e.target === modal) close(false);
        };
        const onOk = () => close(true);
        const onCancel = () => close(false);
        const onKeyDown = (e) => {
            if (e.key === 'Escape') close(false);
            if (e.key === 'Enter') close(true);
        };

        modal.addEventListener('click', onOverlayClick);
        okBtn.addEventListener('click', onOk);
        cancelBtn.addEventListener('click', onCancel);
        document.addEventListener('keydown', onKeyDown);
        okBtn.focus();
    });
}

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

// ==================== Chart.js 全局配置 ====================
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.06)';
Chart.defaults.font.family = "'Inter', 'Noto Sans SC', sans-serif";

// ==================== 页面初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    initLotteryTypeSelector();
    updateUIForLotteryType();
    initTabs();
    initSimulator();
    loadStatistics();

    // VIP 权限控制：隐藏普通用户的 VIP 专属功能
    const user = window.__USER__ || {};
    const isVIP = !!(user.role === 'vip' || user.role === 'admin');
    if (!isVIP) {
        // 隐藏所有 vip-only 元素
        const vipOnlyEls = document.querySelectorAll('.vip-only');
        vipOnlyEls.forEach(el => el.style.display = 'none');

        // 显示提示信息
        const tip = document.getElementById('settings-permission-tip');
        if (tip) {
            tip.innerHTML = '💡 普通用户可选择平台和模型；AI 模拟每次扣 5 积分。<a href="/points" style="color:#a855f7;">升级VIP</a>后可设置自定义API并添加平台/模型。';
        }
    }

    renderRoleRules();
    renderSimulationBillingTip();
    initSpecialReferenceBoard();
    initDragAndDrop();
});

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

// ==================== 彩种切换 ====================
function initLotteryTypeSelector() {
    const typeBtns = document.querySelectorAll('.type-btn');
    typeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.classList.contains('active')) return;

            // 更新 UI
            typeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // 更新状态
            state.lotteryType = btn.dataset.type;

            updateUIForLotteryType();

            // 重置状态并重新加载当前页
            state.statisticsLoaded = false;

            if (state.currentTab === 'statistics') {
                loadStatistics();
            } else if (state.currentTab === 'history') {
                if (historySubTab === 'draw') {
                    state.historyPage = 1;
                    loadHistory(1);
                } else {
                    state.aiHistoryPage = 1;
                    loadAIHistory(1);
                }
            }
        });
    });
}

function updateUIForLotteryType() {
    applyChartOrder();
    const isWeilitsai = state.lotteryType === 'weilitsai';
    
    // 更新历史记录开奖 Tab 按钮文本
    const btnHistoryDraw = document.getElementById('btn-history-draw');
    if (btnHistoryDraw) {
        if (historySubTab === 'draw') {
            btnHistoryDraw.innerHTML = '📊 开奖记录 <span style="font-size:0.8rem;opacity:0.8;">↗️</span>';
        } else {
            btnHistoryDraw.innerHTML = '📊 开奖记录';
        }
    }
    
    const numbersCol = document.getElementById('history-numbers-col');
    if (numbersCol) {
        numbersCol.textContent = isWeilitsai ? '第一區' : '正码';
    }
    const specialCol = document.getElementById('history-special-col');
    if (specialCol) {
        specialCol.textContent = isWeilitsai ? '第二區' : '特码';
    }
    const zodiacCharts = [
        'chart-card-zodiac', 
        'chart-card-markov', 
        'chart-card-five-elements', 
        'chart-card-bayesian', 
        'chart-card-lstm'
    ];
    
    zodiacCharts.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            if (isWeilitsai && (id === 'chart-card-zodiac' || id === 'chart-card-five-elements')) {
                el.style.display = 'none';
            } else {
                el.style.display = '';
            }
        }
    });

    const weilitsaiExclusiveCharts = [
        'chart-card-three-region-prime',
        'chart-card-repeats-tails',
        'chart-card-range-drift',
        'chart-card-ac-value'
    ];
    
    weilitsaiExclusiveCharts.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.style.display = isWeilitsai ? 'block' : 'none';
        }
    });

    const colorMode = document.getElementById('hotcold-mode-color');
    const colorView = document.getElementById('color-hotcold-view');
    const numView = document.getElementById('number-hotcold-view');
    
    if (colorMode) {
        colorMode.style.display = isWeilitsai ? 'none' : '';
        if (isWeilitsai) {
            const numberRadio = document.querySelector('input[name="hotcold_mode"][value="number"]');
            if (numberRadio) {
                numberRadio.checked = true;
            }
        }
    }

    if (isWeilitsai) {
        if (colorView) colorView.style.display = 'none';
        if (numView) numView.style.display = 'flex';
    } else {
        const checkedVal = document.querySelector('input[name="hotcold_mode"]:checked')?.value || 'color';
        if (checkedVal === 'color') {
            if (numView) numView.style.display = 'none';
            if (colorView) colorView.style.display = 'block';
        } else {
            if (numView) numView.style.display = 'flex';
            if (colorView) colorView.style.display = 'none';
        }
    }

    // 动态更新单双连号和大小连号的卡片标题，以区分威力彩的第二区与普通特码
    const oddEvenTitle = document.querySelector('#chart-odd-even').closest('.chart-card').querySelector('.chart-title');
    if (oddEvenTitle) {
        oddEvenTitle.textContent = isWeilitsai ? '⚖️ 特码 (第二區) 单双连号（长龙）频次' : '⚖️ 特码单双连号（长龙）频次';
    }
    const bigSmallTitle = document.querySelector('#chart-big-small').closest('.chart-card').querySelector('.chart-title');
    if (bigSmallTitle) {
        bigSmallTitle.textContent = isWeilitsai ? '📐 特码 (第二區) 大小连号（长龙）频次' : '📐 特码大小连号（长龙）频次';
    }

    const predictProbCard = document.getElementById('chart-card-predict-prob');
    if (predictProbCard) {
        predictProbCard.style.display = isWeilitsai ? '' : 'none';
    }

    // 控制模拟开奖板块的维度和按钮在不同彩种时的显示/隐藏
    const weiliExclusiveDims = ['three_region', 'prime_composite', 'repeats_tails', 'ac_value', 'range_span', 'mean_regression'];
    const hiddenDimsForWeili = ['color'];
    const allControlDims = ['color', 'markov', 'consecutive', 'bayesian', 'lstm', ...weiliExclusiveDims];
    
    allControlDims.forEach(val => {
        const checkbox = document.querySelector(`input[name="dim"][value="${val}"]`);
        if (checkbox) {
            const label = checkbox.closest('.dim-checkbox');
            const isWeiliExclusive = weiliExclusiveDims.includes(val);
            const isHiddenForWeili = hiddenDimsForWeili.includes(val);
            
            let shouldShow = true;
            if (isWeilitsai) {
                // 威力彩下，隐藏波色，显示威力彩专属维度
                shouldShow = !isHiddenForWeili;
            } else {
                // 非威力彩下，显示波色，隐藏威力彩专属维度
                shouldShow = !isWeiliExclusive;
            }
            
            if (label) {
                label.style.display = shouldShow ? '' : 'none';
            }
            checkbox.checked = shouldShow;
        }
    });

    const btnZodiac = document.getElementById('btn-zodiac-simulate');
    if (btnZodiac) {
        btnZodiac.style.display = isWeilitsai ? 'none' : '';
    }

    const resZodiac = document.getElementById('sim-zodiac-result');
    if (resZodiac && isWeilitsai) {
        resZodiac.style.display = 'none';
    }

    // 切换彩种时自动刷新 AI 模型提示
    renderSimulationBillingTip();
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

// ==================== 统计数据加载与渲染 ====================
async function loadStatistics() {
    showLoading(true);

    try {
        const response = await apiFetch(`/api/statistics?type=${state.lotteryType}`);
        const result = await response.json();

        if (result.success) {
            renderStatistics(result.data);
            state.statisticsLoaded = true;
        } else {
            console.error('加载统计数据失败:', result.error);
        }
    } catch (error) {
        console.error('请求失败:', error);
    } finally {
        showLoading(false);
    }
}

function renderStatistics(data) {
    // 概览卡片
    document.getElementById('total-draws').textContent = data.total_draws.toLocaleString();

    const isWeilitsai = state.lotteryType === 'weilitsai';
    const hotColdData = isWeilitsai ? data.hot_cold_z1 : data.hot_cold;

    if (hotColdData && hotColdData.hot && hotColdData.hot.length > 0) {
        const num = hotColdData.hot[0].number;
        const count = hotColdData.hot[0].count;
        const color = getBallColorHex(num);
        const darkColor = color === '#ef4444' ? '#d30000' : (color === '#3b82f6' ? '#0055d3' : (color === '#22c55e' ? '#00d34b' : '#d4a017'));
        document.getElementById('hottest-number').innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
                <span class="overview-ball" style="display: inline-flex; align-items: center; justify-content: center; background: radial-gradient(circle at 30% 30%, ${color}, ${darkColor}); border-radius: 50%; color: #ffffff !important; -webkit-text-fill-color: #ffffff; font-weight: 900; font-family: Arial, Helvetica, sans-serif; box-shadow: 0 3px 8px rgba(0,0,0,0.4); border: 2px solid rgba(255,255,255,0.4); line-height: 1; text-shadow: 1px 1px 0 rgba(0,0,0,0.5);">${num}</span>
                <span style="font-size: 1rem; color: #f3f4f6; font-weight: 600;">(${count}次)</span>
            </div>
        `;
    }
    if (hotColdData && hotColdData.cold && hotColdData.cold.length > 0) {
        const num = hotColdData.cold[0].number;
        const count = hotColdData.cold[0].count;
        const color = getBallColorHex(num);
        const darkColor = color === '#ef4444' ? '#d30000' : (color === '#3b82f6' ? '#0055d3' : (color === '#22c55e' ? '#00d34b' : '#d4a017'));
        document.getElementById('coldest-number').innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
                <span class="overview-ball" style="display: inline-flex; align-items: center; justify-content: center; background: radial-gradient(circle at 30% 30%, ${color}, ${darkColor}); border-radius: 50%; color: #ffffff !important; -webkit-text-fill-color: #ffffff; font-weight: 900; font-family: Arial, Helvetica, sans-serif; box-shadow: 0 3px 8px rgba(0,0,0,0.4); border: 2px solid rgba(255,255,255,0.4); line-height: 1; text-shadow: 1px 1px 0 rgba(0,0,0,0.5);">${num}</span>
                <span style="font-size: 1rem; color: #f3f4f6; font-weight: 600;">(${count}次)</span>
            </div>
        `;
    }

    // 渲染上期开奖号码
    const titleEl = document.querySelector('#card-latest-zodiac .stat-label');
    if (titleEl) {
        if (isWeilitsai) {
            titleEl.style.display = 'none'; // 隐藏原本顶部的标签
        } else {
            titleEl.style.display = '';
            titleEl.textContent = '上期开奖特码';
        }
    }

    if (isWeilitsai) {
        const latestNum = data.latest_num || '??';
        const latestNumbers = data.latest_numbers || [];
        const iconEl = document.getElementById('latest-zodiac-icon');
        const infoEl = document.getElementById('latest-special-info');
        if (iconEl) iconEl.textContent = '🎫';
        if (infoEl) {
            const regularBallsHtml = latestNumbers.map(num => {
                return `<span class="overview-ball" style="display: inline-flex; align-items: center; justify-content: center; background: radial-gradient(circle at 30% 30%, #22c55e, #15803d); border-radius: 50%; color: #ffffff !important; -webkit-text-fill-color: #ffffff; font-weight: 900; font-family: Arial, Helvetica, sans-serif; box-shadow: 0 3px 8px rgba(0,0,0,0.4); border: 2px solid rgba(255,255,255,0.4); line-height: 1; text-shadow: 1px 1px 0 rgba(0,0,0,0.5); width: 28px; height: 28px; font-size: 0.85rem;">${num}</span>`;
            }).join('');
            
            const specialBallHtml = `<span class="overview-ball" style="display: inline-flex; align-items: center; justify-content: center; background: radial-gradient(circle at 30% 30%, #3b82f6, #0055d3); border-radius: 50%; color: #ffffff !important; -webkit-text-fill-color: #ffffff; font-weight: 900; font-family: Arial, Helvetica, sans-serif; box-shadow: 0 3px 8px rgba(0,0,0,0.4); border: 2px solid rgba(255,255,255,0.4); line-height: 1; text-shadow: 1px 1px 0 rgba(0,0,0,0.5); width: 28px; height: 28px; font-size: 0.85rem;">${latestNum}</span>`;
            
            infoEl.innerHTML = `
                <div style="display: flex; flex-direction: column; gap: 6px;">
                    <div style="display: flex; align-items: center; gap: 4px; flex-wrap: wrap;">
                        ${regularBallsHtml}
                        <span style="font-size: 0.9rem; color: #a1a1aa; font-weight: bold; margin: 0 2px;">+</span>
                        ${specialBallHtml}
                    </div>
                    <div style="font-size: 0.78rem; color: #9ca3af; font-weight: bold; margin-top: 2px;">上期开奖号码</div>
                </div>
            `;
        }
    } else {
        if (data.markov && data.markov.target_num) {
            const zEmoji = { '鼠': '🐭', '牛': '🐮', '虎': '🐯', '兔': '🐰', '龙': '🐲', '蛇': '🐍', '马': '🐴', '羊': '🐑', '猴': '🐵', '鸡': '🐔', '狗': '🐶', '猪': '猪' };
            const num = data.markov.target_num;
            const zodiac = data.markov.target_zodiac || '未知';
            const emoji = zEmoji[zodiac] || '🎰';

            const iconEl = document.getElementById('latest-zodiac-icon');
            const infoEl = document.getElementById('latest-special-info');

            if (iconEl) iconEl.textContent = emoji;
            if (infoEl) {
                const color = getBallColorHex(num);
                const darkColor = color === '#ef4444' ? '#d30000' : (color === '#3b82f6' ? '#0055d3' : (color === '#22c55e' ? '#00d34b' : '#d4a017'));
                infoEl.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 12px; margin-top: 4px;">
                        <span class="overview-ball" style="display: inline-flex; align-items: center; justify-content: center; background: radial-gradient(circle at 30% 30%, ${color}, ${darkColor}); border-radius: 50%; color: #ffffff !important; -webkit-text-fill-color: #ffffff; font-weight: 900; font-family: Arial, Helvetica, sans-serif; box-shadow: 0 3px 8px rgba(0,0,0,0.4); border: 2px solid rgba(255,255,255,0.4); line-height: 1; text-shadow: 1px 1px 0 rgba(0,0,0,0.5);">${num}</span>
                        <span style="font-size: 1.2rem; color: #f3f4f6; font-weight: 800; letter-spacing: 1px;">${zodiac}</span>
                    </div>
                `;
            }
        }
    }

    // 渲染图表 —— 分批渲染，避免长时间阻塞主线程
    window.__colorHotCold = isWeilitsai ? null : data.color_hot_cold;
    window.__markovData = data.markov;

    const chartTasks = isWeilitsai ? [
        () => renderFrequencyChart(data.number_frequency_z1, data.bayesian, data.markov),
        () => renderHotColdRanking(data.hot_cold_z1),
        () => renderPredictProbChart(data.predict_probabilities_z1),
        () => renderOddEvenChart(data.odd_even_z2),
        () => renderBigSmallChart(data.big_small_z2),
        () => renderTailChart(data.tail_numbers_z1),
        () => renderMarkovChart(data.markov),
        () => renderBayesianChart(data.bayesian),
        () => renderLSTMChart(data.lstm),
        () => {
            const z1Card = document.getElementById('chart-card-z1-exclusive');
            if (z1Card && data.zone1_exclusive) {
                z1Card.style.display = 'block';
                renderZ1ExclusiveChart(data.zone1_exclusive);
            }
        },
        () => { if (data.three_region && data.prime_composite) renderThreeRegionPrimeCharts(data.three_region, data.prime_composite); },
        () => { if (data.repeats_tails) renderRepeatsTailsCharts(data.repeats_tails); },
        () => { if (data.range_span && data.mean_regression) renderRangeDriftCharts(data.range_span, data.mean_regression); },
        () => { if (data.ac_value) renderACValueChart(data.ac_value); }
    ] : [
        () => renderFrequencyChart(data.number_frequency, data.bayesian, data.markov),
        () => renderHotColdRanking(data.hot_cold),
        () => renderColorHotCold(data.color_hot_cold),
        () => renderOddEvenChart(data.odd_even),
        () => renderBigSmallChart(data.big_small),
        () => renderZodiacChart(data.zodiac_stats),
        () => renderTailChart(data.tail_numbers),
        () => renderMarkovChart(data.markov),
        () => renderFiveElementsChart(data.five_elements),
        () => renderBayesianChart(data.bayesian),
        () => renderLSTMChart(data.lstm),
    ];

    // 使用 requestAnimationFrame + setTimeout 分批渲染
    let taskIdx = 0;
    function runNextChart() {
        if (taskIdx >= chartTasks.length) return;
        try {
            chartTasks[taskIdx]();
        } catch (e) {
            console.error("Error executing chart task " + taskIdx + ":", e);
        }
        taskIdx++;
        if (taskIdx < chartTasks.length) {
            requestAnimationFrame(() => setTimeout(runNextChart, 0));
        } else {
            // 所有图表异步渲染完毕后，追加统计期数标注，防止被渲染函数重写冲掉
            appendPeriodLabels();
        }
    }
    runNextChart();

    // ===== 为所有图表标题追加统计期数标注 =====
    function appendPeriodLabels() {
        const periods = data.chart_periods || {};
        const periodLabel = (n) => n > 0 ? `近${n}期` : '全历史数据';

        // canvas ID → chart_periods key 映射
        const chartPeriodMap = {
            'chart-frequency': 'hot_cold',
            'chart-odd-even': 'odd_even',
            'chart-big-small': 'big_small',
            'chart-zodiac': 'zodiac_trend',
            'chart-predict-prob': 'zodiac_trend', // 威力彩和值动量
            'chart-five-elements': 'hot_cold',
            'chart-tail': 'tail',
            'chart-bayesian': 'bayesian',
            'chart-lstm': 'lstm',
            'chart-markov-radar': 'markov', // 马尔可夫雷达图
            'chart-three-region': 'three_region',
            'chart-prime-composite': 'three_region',
            'chart-repeats-poisson': 'poisson_tail',
            'chart-identical-tails': 'poisson_tail',
            'chart-range-span': 'range_distribution',
            'chart-mean-deviation': 'range_distribution',
            'chart-ac-value': 'ac_value',
            'chart-z1-exclusive': 'z1_exclusive'
        };

        // 冷热号卡片没有 canvas，通过卡片 ID 处理
        const hotColdCard = document.getElementById('chart-card-hotcold');
        if (hotColdCard) {
            const titleEl = hotColdCard.querySelector('.chart-title');
            if (titleEl) {
                titleEl.innerHTML = titleEl.textContent.replace(/（统计基准.*?）/g, '').trim() +
                    ` <span style="font-size:0.75rem; color:#9ca3af; font-weight:400;">（统计基准：${periodLabel(periods.hot_cold || 100)}）</span>`;
            }
        }

        // 按 canvas 向上追溯卡片标题
        Object.entries(chartPeriodMap).forEach(([canvasId, periodKey]) => {
            const canvasEl = document.getElementById(canvasId);
            if (!canvasEl) return;
            const card = canvasEl.closest('.chart-card') || canvasEl.closest('.card');
            if (!card) return;
            const titleEl = card.querySelector('.chart-title');
            if (!titleEl) return;
            titleEl.innerHTML = titleEl.textContent.replace(/（统计基准.*?）/g, '').trim() +
                ` <span style="font-size:0.75rem; color:#9ca3af; font-weight:400;">（统计基准：${periodLabel(periods[periodKey] ?? 100)}）</span>`;
        });
    }
}


function renderHistory(data) {
    const tbody = document.getElementById('history-tbody');
    const isWeilitsai = state.lotteryType === 'weilitsai';

    tbody.innerHTML = data.data.map(row => {
        const sz = row.special_zodiac || '';
        const colorClass = getBallColorClass(row.special_num, isWeilitsai ? 2 : 1) || 'special';
        
        // 渲染 6 个正码球
        const regularBalls = (row.numbers || [])
            .map(num => {
                const ballColor = getBallColorClass(num, 1) || 'regular';
                return `<span class="table-ball ${ballColor}" style="margin: 0 2px; width: 28px; height: 28px; line-height: 28px; font-size: 0.85rem;">${num}</span>`;
            }).join('');

        return `
            <tr>
                <td>${row.draw_number}</td>
                <td>${row.draw_date}</td>
                <td style="text-align: center;">
                    <div class="ball-wrapper" style="flex-direction: row; align-items: center; justify-content: center; width: 100%; gap: 4px; flex-wrap: wrap;">
                        ${regularBalls}
                    </div>
                </td>
                <td style="text-align: center;">
                    <div class="ball-wrapper" style="flex-direction: row; align-items: center; justify-content: center; width: 100%; gap: 8px;">
                        ${sz ? `<span class="zodiac-label" style="font-size: 0.9rem; font-weight: 600; color: #fbbf24;">${sz}</span>` : ''}
                        <span class="table-ball ${colorClass}" style="margin: 0;">${row.special_num}</span>
                    </div>
                </td>
                <td style="text-align: center;">
                    <button class="table-copy-btn" onclick="copyTableLine(this)" title="复制该期号码" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 5px 8px; border-radius: var(--radius-xs); font-size: 0.8rem; cursor: pointer; color: var(--text-secondary); display: inline-flex; align-items: center; justify-content: center; transition: all 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.12)'; this.style.color='#fff';" onmouseout="this.style.background='rgba(255,255,255,0.05)'; this.style.color='var(--text-secondary)';">📋 复制</button>
                </td>
            </tr>
        `;
    }).join('');

    renderPagination(data);
}

function renderPagination(data) {
    const container = document.getElementById('pagination');
    const { page, total_pages, total } = data;

    let html = '';

    // 上一页
    html += `<button class="page-btn" onclick="loadHistory(${page - 1})" ${page <= 1 ? 'disabled' : ''}>◀ 上一页</button>`;

    // 页码按钮
    const range = getPageRange(page, total_pages);
    range.forEach(p => {
        if (p === '...') {
            html += `<span class="page-info">…</span>`;
        } else {
            html += `<button class="page-btn ${p === page ? 'active' : ''}" onclick="loadHistory(${p})">${p}</button>`;
        }
    });

    // 页码信息
    html += `<span class="page-info">共 ${total} 条</span>`;

    // 下一页
    html += `<button class="page-btn" onclick="loadHistory(${page + 1})" ${page >= total_pages ? 'disabled' : ''}>下一页 ▶</button>`;

    container.innerHTML = html;
}

function getPageRange(current, total) {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);

    const pages = [];
    if (current <= 4) {
        for (let i = 1; i <= 5; i++) pages.push(i);
        pages.push('...', total);
    } else if (current >= total - 3) {
        pages.push(1, '...');
        for (let i = total - 4; i <= total; i++) pages.push(i);
    } else {
        pages.push(1, '...');
        for (let i = current - 1; i <= current + 1; i++) pages.push(i);
        pages.push('...', total);
    }
    return pages;
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

// ==================== 智能模拟面板 ====================

// 根据数字获取波色CSS类名
function getBallColorClass(num, zone = 1) {
    const n = parseInt(num);
    
    if (state.lotteryType === 'weilitsai') {
        if (zone === 2) return 'ball-red'; // 第二區用紅色
        return 'ball-green'; // 第一區用綠色
    }

    const red = [1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46];
    const blue = [3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48];
    const green = [5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49];

    if (red.includes(n)) return 'ball-red';
    if (blue.includes(n)) return 'ball-blue';
    if (green.includes(n)) return 'ball-green';
    return ''; // default gold
}

// 根据波色获取颜色十六进制值 (用于图表)
function getBallColorHex(num, zone = 1) {
    const cls = getBallColorClass(num, zone);
    if (cls === 'ball-red') return '#ef4444';
    if (cls === 'ball-blue') return '#3b82f6';
    if (cls === 'ball-green') return '#22c55e';
    return '#facc15';
}

// 获取当前选中的加权维度
function getSelectedDimensions() {
    const checks = document.querySelectorAll('input[name="dim"]:checked');
    return Array.from(checks).map(c => c.value);
}

// 渲染球号 HTML
function renderBallsHtml(numbers, zodiacs, specialNum, specialZodiac, extraClass = '', simpleMode = false) {
    const isWeilitsai = state.lotteryType === 'weilitsai';

    // 威力彩排版居中对齐优化
    if (isWeilitsai && !simpleMode) {
        let zone1Html = '';
        numbers.forEach((n, i) => {
            const colorClass = getBallColorClass(n, 1);
            zone1Html += `<div style="display:inline-flex;flex-direction:column;align-items:center;margin: 0 4px;">
                <div class="lottery-ball ${colorClass} ${extraClass}" style="animation-delay:${i * 0.1}s">${n}</div>
            </div>`;
        });

        const spColorClass = getBallColorClass(specialNum, 2);
        let zone2Html = `<div style="display:inline-flex;flex-direction:column;align-items:center;">
            <div class="lottery-ball ${spColorClass} ${extraClass}">${specialNum}</div>
        </div>`;

        let html = '';
        // 第一区大盒子 (文字垂直居中在6个球正上方)
        html += `<div style="display:inline-flex;flex-direction:column;align-items:center;">
            <span style="font-size:0.85rem;color:#94a3b8;margin-bottom:8px;font-weight:600;letter-spacing:0.5px;">第一區 (Zone 1)</span>
            <div style="display:flex;justify-content:center;align-items:center;">${zone1Html}</div>
        </div>`;
        
        // 分隔加号 (对齐球心线)
        html += `<div class="ball-divider" style="align-self:flex-end;margin-bottom:12px;margin-left:14px;margin-right:14px;font-size:1.6rem;font-weight:bold;color:#64748b;height:42px;display:flex;align-items:center;">+</div>`;
        
        // 第二区大盒子 (文字垂直居中在1个球正上方)
        html += `<div style="display:inline-flex;flex-direction:column;align-items:center;">
            <span style="font-size:0.85rem;color:#94a3b8;margin-bottom:8px;font-weight:600;letter-spacing:0.5px;">第二區 (Zone 2)</span>
            <div style="display:flex;justify-content:center;align-items:center;">${zone2Html}</div>
        </div>`;
        
        return html;
    }

    // 非威力彩常规六合彩排版 (或 simpleMode 激活时的威力彩平铺排版)
    let html = '';
    numbers.forEach((n, i) => {
        const colorClass = getBallColorClass(n, 1);
        const zLabel = isWeilitsai ? '' : (zodiacs && zodiacs[i] ? zodiacs[i] : '');
        html += `<div style="display:inline-flex;flex-direction:column;align-items:center;justify-content:center;">`;
        if (!isWeilitsai) {
            html += `<span class="ball-zodiac" style="margin-bottom: 4px; font-size: 0.8rem;${zLabel ? '' : ' height: 1.2rem;'}">${zLabel}</span>`;
        }
        html += `<div class="lottery-ball ${colorClass} ${extraClass}" style="animation-delay:${i * 0.1}s">${n}</div>
        </div>`;
    });
    
    // 不管是否为 simpleMode，均输出加号分隔符，使用 inline-flex 确保不折行
    // 不再使用 margin-left: auto 推至右侧，保持紧凑同行排列，防止中间断裂和多余空白
    const plusPadding = isWeilitsai ? '' : 'padding-top: 1.2rem;';
    const marginStyle = 'margin: 0 10px;';
    html += `<div class="ball-divider" style="display: inline-flex !important; ${plusPadding} align-items: center; justify-content: center; font-size: 1.5rem; font-weight: bold; color: var(--text-secondary); ${marginStyle}">+</div>`;
    
    const spColorClass = getBallColorClass(specialNum, 2);
    const spZLabel = isWeilitsai ? '' : (specialZodiac || '');
    html += `<div style="display:inline-flex;flex-direction:column;align-items:center;justify-content:center;">`;
    if (!isWeilitsai) {
        html += `<span class="ball-zodiac" style="margin-bottom: 4px; font-size: 0.8rem; color: #facc15; font-weight: bold;${spZLabel ? '' : ' height: 1.2rem;'}">${spZLabel}</span>`;
    }
    html += `<div class="lottery-ball ${spColorClass} ${extraClass}">${specialNum}</div>
    </div>`;
    return html;
}

// 数据新鲜度检查
async function checkDataFreshness() {
    const dotEl = document.getElementById('status-dot');
    const textEl = document.getElementById('data-status-text');
    dotEl.className = 'status-dot checking';
    textEl.textContent = '正在检查...';

    try {
        const res = await fetch(`/api/data-check?type=${state.lotteryType}`);
        const json = await res.json();
        if (json.success) {
            const d = json.data;
            if (d.is_fresh) {
                dotEl.className = 'status-dot fresh';
                textEl.textContent = `✅ 数据已同步 | 最新期号: ${d.latest_draw} | 日期: ${d.latest_date}`;
            } else {
                dotEl.className = 'status-dot stale';
                textEl.textContent = `⚠️ 数据滞后 ${d.days_behind} 天 | 最新: ${d.latest_draw} (${d.latest_date})`;
            }
        }
    } catch (e) {
        dotEl.className = 'status-dot stale';
        textEl.textContent = '❌ 检查失败: ' + e.message;
    }
}

// 同步最新数据
async function syncLatestData() {
    const btn = document.getElementById('btn-sync-data');
    const textEl = document.getElementById('data-status-text');
    btn.disabled = true;
    btn.textContent = '⏳ 同步中...';
    textEl.textContent = '正在从官网抓取最新数据...';

    try {
        const res = await fetch('/api/sync-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: state.lotteryType })
        });
        const json = await res.json();
        if (json.success) {
            textEl.textContent = `✅ ${json.data.message}`;
            // 重新检查新鲜度
            setTimeout(checkDataFreshness, 500);
        } else {
            textEl.textContent = '❌ 同步失败: ' + (json.error || '未知错误');
        }
    } catch (e) {
        textEl.textContent = '❌ 同步失败: ' + e.message;
    }
    btn.disabled = false;
    btn.textContent = '🔄 同步最新';
}

// ==================== 保存 AI 分析结果为图片 ====================
async function shareAIResult(mode, btnEl) {
    let targetId = '';
    let fileNamePrefix = '';

    if (mode === 'zodiac') {
        targetId = 'sim-zodiac-result';
        fileNamePrefix = 'AI生肖推算';
    } else {
        targetId = 'sim-ai-result';
        fileNamePrefix = 'AI智能分析';
    }

    const card = document.getElementById(targetId);
    if (!card || card.style.display === 'none') {
        showCenterToast('暂无可保存的分析结果', 'warn');
        return;
    }

    // 更新按钮状态
    let origText = '📸 存图';
    if (btnEl) {
        origText = btnEl.textContent;
        btnEl.textContent = '⏳ 生成...';
        btnEl.disabled = true;
    }

    try {
        // 保存原始样式，临时调整用于截图
        const origBoxShadow = card.style.boxShadow;
        const origBorder = card.style.border;
        card.style.boxShadow = 'none';
        
        // 增加内边距防止拥挤
        const origPadding = card.style.padding;
        card.style.padding = '24px';

        // 添加水印
        const watermark = document.createElement('div');
        watermark.style.cssText = 'text-align:center; padding:16px 0 8px; font-size:0.8rem; color:#6b7280; border-top:1px solid rgba(255,255,255,0.06); margin-top:20px;';
        watermark.textContent = `🎰 六合彩智能分析系统 · ${fileNamePrefix}档案`;
        card.appendChild(watermark);

        // 如果未加载 html2canvas 则提示
        if (typeof html2canvas === 'undefined') {
            throw new Error("html2canvas 库未加载");
        }

        const canvas = await html2canvas(card, {
            backgroundColor: '#0f172a',
            scale: window.devicePixelRatio || 2,
            useCORS: true,
            logging: false,
            allowTaint: true,
            removeContainer: true,
        });

        // 恢复样式并移除水印
        card.removeChild(watermark);
        card.style.boxShadow = origBoxShadow;
        card.style.border = origBorder;
        card.style.padding = origPadding;

        // 尝试使用 Web Share API 纯分享图片（移动端优先）
        if (navigator.share && navigator.canShare) {
            canvas.toBlob(async (blob) => {
                const now = new Date();
                const ts = now.getFullYear() + String(now.getMonth() + 1).padStart(2, '0') + String(now.getDate()).padStart(2, '0') + '_' + String(now.getHours()).padStart(2, '0') + String(now.getMinutes()).padStart(2, '0');
                const file = new File([blob], `${fileNamePrefix}_${ts}.png`, { type: 'image/png' });
                try {
                    await navigator.share({
                        title: fileNamePrefix,
                        files: [file]
                    });
                } catch (shareErr) {
                    // 如果用户取消或分享失败，回退到下载功能
                    downloadCanvas(canvas, fileNamePrefix);
                }
            }, 'image/png');
        } else {
            // 桌面端或不支持分享的设备，直接下载图片
            downloadCanvas(canvas, fileNamePrefix);
        }
        
    } catch (err) {
        console.error('生成图片失败:', err);
        showCenterToast('生成图片失败: ' + err.message, 'error');
    } finally {
        if (btnEl) {
            btnEl.textContent = origText;
            btnEl.disabled = false;
        }
    }
}

function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showCenterToast('📋 分析结果已复制到剪贴板，可直接粘贴分享', 'success');
        }).catch(() => {
            fallbackCopy(text);
        });
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try {
        document.execCommand('copy');
        showCenterToast('📋 分析结果已复制到剪贴板', 'success');
    } catch {
        showCenterToast('❌ 复制失败，请手动选择文本', 'error');
    }
    document.body.removeChild(ta);
}

// ==================== AI 分析文本公共格式化函数 ====================
function formatAnalysisText(rawText) {
    if (!rawText) return '';
    let text = rawText;

    // 标题处理 (必须在 \n 转换前)
    text = text.replace(/^###\s+(.*)$/gm, '<h3 style="color:#e2e8f0; font-size:1.05rem; margin-top:16px; margin-bottom:8px; border-bottom:1px solid #334155; padding-bottom:4px; font-weight:bold;">$1</h3>');
    text = text.replace(/^##\s+(.*)$/gm, '<h2 style="color:#f8fafc; font-size:1.2rem; margin-top:20px; margin-bottom:10px; font-weight:bold;">$1</h2>');
    text = text.replace(/^#\s+(.*)$/gm, '<h1 style="color:#ffffff; font-size:1.4rem; margin-top:24px; margin-bottom:12px; font-weight:bold;">$1</h1>');

    // Markdown 加粗
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // 段落间距（连续两个换行）
    text = text.replace(/\n\s*\n/g, '<div style="height: 12px;"></div>');
    // 兼容 API 返回的字面量 \\n 转义
    text = text.replace(/\\n/g, '<br/>');
    // 真实换行符
    text = text.replace(/\n/g, '<br/>');

    // emoji 关键词增强
    const emojiMap = {
        '单双': '☯️ 单双', '大小': '⚖️ 大小', '连出': '🔥 连出',
        '冷门': '❄️ 冷门', '回补': '♻️ 回补', '反转': '🔄 反转',
        '极大值': '📈 极大值', '极小值': '📉 极小值', '预测': '🎯 预测',
        '结论': '💡 结论', '概率': '🎲 概率', '权重': '⚖️ 权重', '遗漏': '⌛ 遗漏'
    };
    for (const [key, emoji] of Object.entries(emojiMap)) {
        text = text.replace(new RegExp(key, 'g'), `<span style="color:#e2e8f0;">${emoji}</span>`);
    }

    // 行首数字列表样式
    text = text.replace(/(^|<br\/>)(\s*)(\d+[\.)])\s*/g,
        '$1$2<span style="color:#cbd5e1;font-weight:bold;margin-right:6px;">$3</span> ');

    return text;
}

// AI 智能分析
async function runAISimulation() {
    const role = (window.__USER__ && window.__USER__.role) || 'trial';
    if (role !== 'admin') {
        const feeText = role === 'vip'
            ? '本次 AI 模拟：平台模型扣 5 积分；自己模型免费。是否继续？'
            : '本次 AI 模拟将扣除 5 积分，是否继续？';
        const proceed = await showCenterConfirm(feeText, 'AI 扣分提醒');
        if (!proceed) return;
    }

    const btn = document.getElementById('btn-ai-simulate');
    const btnText = btn.querySelector('.btn-text');
    const btnLoad = btn.querySelector('.btn-loading');

    btn.disabled = true;
    btnText.style.display = 'none';
    btnLoad.style.display = 'inline';

    // 隐藏旧结果
    document.getElementById('sim-ai-result').style.display = 'none';
    document.getElementById('sim-weighted-result').style.display = 'none';
    document.getElementById('sim-single-result').style.display = 'none';
    document.getElementById('sim-zodiac-result').style.display = 'none';
    document.getElementById('sim-batch-result').style.display = 'none';

    // 显示动画
    document.getElementById('sim-animation').style.display = 'block';

    try {
        const dims = getSelectedDimensions();
        
        // 检查是否启用了旋转矩阵
        const wheelingRadio = document.querySelector('input[name="sim-mode"]:checked');
        const isWheeling = wheelingRadio && wheelingRadio.value === 'wheeling';
        const wheelingBudget = document.getElementById('wheeling-budget') ? parseInt(document.getElementById('wheeling-budget').value, 10) : 14;
        
        const endpoint = isWheeling ? '/api/simulate/wheeling' : '/api/simulate';
        const count = isWheeling ? wheelingBudget : 1;
        
        const reqBody = {
            type: state.lotteryType,
            mode: 'ai',
            dimensions: dims,
            count: count
        };
        
        reqBody.stream = true;
            
        // 构建流式打字机终端 UI
        let streamLog = document.getElementById('ai-stream-log');
        if (!streamLog) {
            streamLog = document.createElement('div');
            streamLog.id = 'ai-stream-log';
            streamLog.style.marginTop = '20px';
            streamLog.style.padding = '15px';
            streamLog.style.background = '#0f172a';
            streamLog.style.color = '#10b981';
            streamLog.style.borderRadius = '8px';
            streamLog.style.fontFamily = 'monospace';
            streamLog.style.fontSize = '0.9rem';
            streamLog.style.lineHeight = '1.6';
            streamLog.style.height = '250px';
            streamLog.style.overflowY = 'auto';
            streamLog.style.border = '1px solid #1e293b';
            streamLog.style.boxShadow = 'inset 0 0 15px rgba(0,0,0,0.8)';
            document.getElementById('sim-animation').after(streamLog);
        }
        streamLog.style.display = 'block';
        streamLog.innerHTML = '<div><span style="color:#f59e0b;">[SYSTEM]</span> 初始化分析引擎...</div>';
        if (isWheeling) {
            streamLog.innerHTML += '<div><span style="color:#f59e0b;">[SYSTEM]</span> 旋转矩阵算法启动，跨纬度抽样建立候选池...</div>';
            streamLog.innerHTML += '<div><span style="color:#f59e0b;">[SYSTEM]</span> 矩阵组合计算完毕，正在请求大模型综合推演...</div>';
        } else {
            streamLog.innerHTML += '<div><span style="color:#f59e0b;">[SYSTEM]</span> 建立神经网络链接，正在请求大模型...</div>';
        }

        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reqBody)
        });
        
        let json = null;
        if (reqBody.stream) {
            const reader = res.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";
            let streamLog = document.getElementById('ai-stream-log');
            
            // 为了打字机效果，我们需要一个 span 容器
            streamLog.innerHTML += '<div><span style="color:#3b82f6;">[MODEL]</span> <span id="ai-typing-cursor"></span></div>';
            let typingSpan = document.getElementById('ai-typing-cursor');

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                
                // 终极流缓冲解析：无视换行符和粘包，直接根据 data: 的物理边界来截断数据包
                while (true) {
                    let startIdx = buffer.indexOf('data: ');
                    if (startIdx === -1) {
                        // 如果连 data: 都没有，可能全是乱码或者残余空白，直接清空
                        buffer = "";
                        break;
                    }
                    
                    let nextIdx = buffer.indexOf('data: ', startIdx + 6);
                    if (nextIdx !== -1) {
                        // 发现下一个边界，说明当前的这块肯定是完整的
                        let msgBlock = buffer.substring(startIdx + 6, nextIdx).trim();
                        buffer = buffer.substring(nextIdx); // 留下剩余的给以后
                        
                        if (msgBlock === '[DONE]') continue;
                        if (!msgBlock) continue;
                        
                        try {
                            let parsed = JSON.parse(msgBlock);
                            if (parsed.type === 'chunk') {
                                let txt = parsed.text.replace(/\\n/g, '<br>');
                                typingSpan.innerHTML += txt;
                                streamLog.scrollTop = streamLog.scrollHeight;
                            } else if (parsed.type === 'result') {
                                json = parsed.payload;
                                if (json && json.analysis) {
                                    json.analysis = json.analysis.replace(/#/g, '');
                                }
                            }
                        } catch (e) {
                            console.error('SSE Parse Error:', msgBlock, e);
                        }
                    } else {
                        // 没有下一个 data: 边界，说明包没收完，退出内部循环等待更多网络数据
                        break;
                    }
                }
            }
            
            // 收尾阶段：处理流结束后的最后一块残余数据
            let finalStart = buffer.indexOf('data: ');
            if (finalStart !== -1) {
                let msgBlock = buffer.substring(finalStart + 6).trim();
                if (msgBlock && msgBlock !== '[DONE]') {
                    try {
                        let parsed = JSON.parse(msgBlock);
                        if (parsed.type === 'result') {
                            json = parsed.payload;
                            if (json && json.analysis) {
                                // 移除错误的去掉 # 的逻辑，保留 markdown 给前端渲染
                            }
                        }
                    } catch (e) {
                        console.error('Final SSE Parse Error:', msgBlock, e);
                    }
                }
            }

            streamLog.innerHTML += '<div><span style="color:#f59e0b;">[SYSTEM]</span> 模型分析完毕，准备渲染开奖...</div>';
            streamLog.style.display = 'none';
        } else {
            json = await res.json();
        }

        document.getElementById('sim-animation').style.display = 'none';

            if (isWheeling) {
                // Wheeling System 批量结果
                if (json.success && json.data && json.data.draws) {
                    const data = json.data;
                    document.getElementById('sim-batch-result').style.display = 'block';
                    
                    // 如果有 AI 大模型推理结果，也渲染出来以关联 AI 模型推算
                    const aiContainer = document.getElementById('sim-ai-result');
                    if (data.ai_result && data.ai_result.success) {
                        const ai = data.ai_result;
                        aiContainer.style.display = 'block';
                        document.getElementById('ai-confidence').textContent = `置信度: ${ai.confidence}`;
                        document.getElementById('ai-result-balls').innerHTML = renderBallsHtml(
                            ai.numbers, ai.zodiacs || [], ai.special_num, ai.special_zodiac || '', 'ai-ball'
                        );
                        let formattedText = formatAnalysisText(ai.analysis || '');
                        document.getElementById('ai-analysis-text').innerHTML = formattedText;
                        document.getElementById('ai-analysis-text').style.lineHeight = '1.8';
                    } else {
                        aiContainer.style.display = 'none';
                    }
                    
                    // Render summary
                    let summaryHtml = `<div class="summary-card">`;
                    if (data.summary.wheeling_info) {
                        summaryHtml += `<p style="color: #fcd34d; font-weight: 500; margin-bottom: 10px;">✨ ${data.summary.wheeling_info}</p>`;
                    }
                    summaryHtml += `<p>共生成 ${data.summary.total_draws} 注组合</p>
                        <p>奇偶比总计: ${data.summary.odd_even_ratio}</p>
                        <p>大小比总计: ${data.summary.big_small_ratio}</p>
                    </div>`;
                    document.getElementById('batch-summary').innerHTML = summaryHtml;
                    
                    // Render draws
                    let drawsHtml = '';
                    data.draws.forEach((d, i) => {
                        const classSpecial = state.lotteryType === 'weilitsai' ? 'weilitsai' : '';
                        drawsHtml += `
                            <div class="batch-draw-item">
                                <span class="batch-draw-index">组合 ${i + 1}</span>
                                <div class="batch-draw-balls">
                                    ${renderBallsHtml(d.numbers, d.zodiacs, d.special_num, d.special_zodiac, classSpecial, true)}
                                </div>
                            </div>
                        `;
                    });
                    document.getElementById('batch-draws-list').innerHTML = drawsHtml;
                } else {
                    showCenterToast('模拟失败: ' + (json.error || '未知错误'), 'error', true);
                }
            } else {
                // AI 结果 (Single)
                if (json.success && json.data) {
                    const data = json.data;
                    if (data.points_deducted && data.points_deducted > 0) {
                        const balanceText = data.points_balance !== null && data.points_balance !== undefined ? `，剩余 ${data.points_balance} 积分` : '';
                        showCenterToast(`本次平台AI模拟扣除 ${data.points_deducted} 积分${balanceText}`, 'warn');
                    }

                    // AI 结果
                    if (data.ai_result && data.ai_result.success) {
                        const ai = data.ai_result;
                        const aiContainer = document.getElementById('sim-ai-result');
                        aiContainer.style.display = 'block';

                        document.getElementById('ai-confidence').textContent = `置信度: ${ai.confidence}`;
                        document.getElementById('ai-result-balls').innerHTML = renderBallsHtml(
                            ai.numbers, ai.zodiacs || [], ai.special_num, ai.special_zodiac || '', 'ai-ball'
                        );
                        
                        let formattedText = formatAnalysisText(ai.analysis || '');
                        
                        document.getElementById('ai-analysis-text').innerHTML = formattedText;
                        document.getElementById('ai-analysis-text').style.lineHeight = '1.8';
                        
                    } else if (data.ai_result) {
                        // AI 调用失败，展示失败原因
                        const aiContainer = document.getElementById('sim-ai-result');
                        aiContainer.style.display = 'block';
                        document.getElementById('ai-confidence').textContent = '⚠️ AI 调用失败';
                        document.getElementById('ai-confidence').style.color = '#f87171';
                        document.getElementById('ai-result-balls').innerHTML = '';
                        document.getElementById('ai-analysis-text').innerHTML = (data.ai_result.analysis || 'AI 模型调用异常，请检查系统设置中的模型名称和 API Key 是否正确。').replace(/\n/g, '<br/>');
                    }

                    // 传统加权对比结果
                    if (data.weighted_result) {
                        const w = data.weighted_result;
                        const wContainer = document.getElementById('sim-weighted-result');
                        wContainer.style.display = 'block';
                        document.getElementById('weighted-result-balls').innerHTML = renderBallsHtml(
                            w.numbers, w.zodiacs, w.special_num, w.special_zodiac
                        );
                    }
                } else {
                    showCenterToast('模拟失败: ' + (json.error || '未知错误'), 'error', true);
                }
            }
    } catch (e) {
        document.getElementById('sim-animation').style.display = 'none';
        showCenterToast('请求失败: ' + e.message, 'error', true);
    }

    btn.disabled = false;
    btnText.style.display = 'inline';
    btnLoad.style.display = 'none';
}

// 传统加权模拟
async function runWeightedSimulation() {
    const btn = document.getElementById('btn-weighted-simulate');
    const btnText = btn.querySelector('.btn-text');
    const btnLoad = btn.querySelector('.btn-loading');

    btn.disabled = true;
    btnText.style.display = 'none';
    btnLoad.style.display = 'inline';

    // 隐藏旧结果
    document.getElementById('sim-ai-result').style.display = 'none';
    document.getElementById('sim-weighted-result').style.display = 'none';
    document.getElementById('sim-single-result').style.display = 'none';
    document.getElementById('sim-zodiac-result').style.display = 'none';
    document.getElementById('sim-batch-result').style.display = 'none';

    document.getElementById('sim-animation').style.display = 'block';

    try {
        const dims = getSelectedDimensions();
        const res = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: state.lotteryType,
                mode: 'weighted',
                dimensions: dims,
                count: 1
            })
        });
        const json = await res.json();

        document.getElementById('sim-animation').style.display = 'none';

        if (json.success && json.data && json.data.draws) {
            const draw = json.data.draws[0];
            const container = document.getElementById('sim-single-result');
            container.style.display = 'block';
            document.getElementById('result-balls').innerHTML = renderBallsHtml(
                draw.numbers, draw.zodiacs, draw.special_num, draw.special_zodiac
            );
        } else {
            showCenterToast('模拟失败: ' + (json.error || '未知错误'), 'error', true);
        }
    } catch (e) {
        document.getElementById('sim-animation').style.display = 'none';
        showCenterToast('请求失败: ' + e.message, 'error', true);
    }

    btn.disabled = false;
    btnText.style.display = 'inline';
    btnLoad.style.display = 'none';
}

// 初始化模拟面板的事件绑定
function initSimulatorPanel() {
    const syncBtn = document.getElementById('btn-sync-data');
    if (syncBtn) syncBtn.addEventListener('click', syncLatestData);

    const aiBtn = document.getElementById('btn-ai-simulate');
    if (aiBtn) aiBtn.addEventListener('click', runAISimulation);

    const weightedBtn = document.getElementById('btn-weighted-simulate');
    if (weightedBtn) weightedBtn.addEventListener('click', runWeightedSimulation);

    const zodiacBtn = document.getElementById('btn-zodiac-simulate');
    if (zodiacBtn) zodiacBtn.addEventListener('click', runZodiacSimulation);

    // 旋转矩阵配置区联动
    const wheelingRadios = document.querySelectorAll('input[name="sim-mode"]');
    const wheelingContainer = document.getElementById('wheeling-budget-container');
    if (wheelingRadios && wheelingContainer) {
        wheelingRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                if (e.target.value === 'wheeling') {
                    wheelingContainer.style.display = 'flex';
                } else {
                    wheelingContainer.style.display = 'none';
                }
            });
        });
    }

    // 切到模拟 Tab 时自动检查数据新鲜度
    const simTab = document.getElementById('tab-sim');
    if (simTab) {
        simTab.addEventListener('click', () => {
            setTimeout(checkDataFreshness, 300);
        });
    }
}

// 在页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    initSimulatorPanel();
    initSettingsPanel();
});

// AI 生肖推算
async function runZodiacSimulation() {
    const role = (window.__USER__ && window.__USER__.role) || 'trial';
    if (role !== 'admin') {
        const feeText = role === 'vip'
            ? '本次 AI 推算：平台模型扣 5 积分；自己模型免费。是否继续？'
            : '本次 AI 推算将扣除 5 积分，是否继续？';
        const proceed = await showCenterConfirm(feeText, 'AI 扣分提醒');
        if (!proceed) return;
    }

    const btn = document.getElementById('btn-zodiac-simulate');
    const btnText = btn.querySelector('.btn-text');
    const btnLoad = btn.querySelector('.btn-loading');

    btn.disabled = true;
    btnText.style.display = 'none';
    btnLoad.style.display = 'inline';

    // 隐藏其他结果
    document.getElementById('sim-ai-result').style.display = 'none';
    document.getElementById('sim-weighted-result').style.display = 'none';
    document.getElementById('sim-single-result').style.display = 'none';
    document.getElementById('sim-zodiac-result').style.display = 'none';
    document.getElementById('sim-batch-result').style.display = 'none';

    document.getElementById('sim-animation').style.display = 'block';

    try {
        const dims = getSelectedDimensions();
        const res = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: state.lotteryType,
                mode: 'ai_zodiac',
                dimensions: dims,
                count: 1
            })
        });
        const json = await res.json();

        document.getElementById('sim-animation').style.display = 'none';

        if (json.success && json.data && json.data.zodiac_result) {
            const zr = json.data.zodiac_result;
            const container = document.getElementById('sim-zodiac-result');
            container.style.display = 'block';

            if (json.data.points_deducted && json.data.points_deducted > 0) {
                const balanceText = json.data.points_balance !== null && json.data.points_balance !== undefined ? `，剩余 ${json.data.points_balance} 积分` : '';
                showCenterToast(`本次平台AI推算扣除 ${json.data.points_deducted} 积分${balanceText}`, 'warn');
            }

            if (zr.success) {
                document.getElementById('zodiac-confidence').textContent = `置信度: ${zr.confidence}`;
                renderZodiacPredictions(zr.zodiac_predictions);
                document.getElementById('zodiac-analysis-text').innerHTML = formatAnalysisText(zr.analysis || '');
                document.getElementById('zodiac-analysis-text').style.lineHeight = '1.8';
            } else {
                document.getElementById('zodiac-confidence').textContent = '⚠️ AI 调用失败';
                document.getElementById('zodiac-confidence').style.color = '#f87171';
                document.getElementById('zodiac-predictions').innerHTML = '';
                document.getElementById('zodiac-analysis-text').innerHTML = formatAnalysisText(zr.analysis || 'AI 模型调用异常');
            }
        } else {
            showCenterToast('推算失败: ' + (json.error || '未知错误'), 'error', true);
        }
    } catch (e) {
        document.getElementById('sim-animation').style.display = 'none';
        showCenterToast('请求失败: ' + e.message, 'error', true);
    }

    btn.disabled = false;
    btnText.style.display = 'inline';
    btnLoad.style.display = 'none';
}

function renderZodiacPredictions(predictions) {
    const container = document.getElementById('zodiac-predictions');
    if (!predictions || predictions.length === 0) {
        container.innerHTML = '<div style="text-align:center; color:var(--text-secondary);">无有效生肖推算</div>';
        return;
    }

    // 生肖对应 emoji
    const zodiacEmoji = {
        '鼠': '🐭', '牛': '🐮', '虎': '🐯', '兔': '🐰',
        '龙': '🐲', '蛇': '🐍', '马': '🐴', '羊': '🐑',
        '猴': '🐵', '鸡': '🐔', '狗': '🐶', '猪': '🐷'
    };

    // 排名奖牌颜色
    const medals = ['🥇', '🥈', '🥉'];
    const barColors = ['#a855f7', '#8b5cf6', '#7c3aed', '#6d28d9', '#5b21b6'];

    container.innerHTML = predictions.map((p, i) => {
        const emoji = zodiacEmoji[p.zodiac] || '🔮';
        const medal = medals[i] || `#${i + 1}`;
        const prob = p.probability || '?%';
        // 解析概率数字用于条形图宽度
        const probNum = parseFloat(prob) || 10;
        const barW = Math.min(100, Math.max(15, probNum * 3));

        return `
            <div style="display: flex; align-items: center; gap: 16px; padding: 16px; background: rgba(168,85,247,${0.08 + i * 0.02}); border-radius: 12px; border: 1px solid rgba(168,85,247,0.15);">
                <div style="font-size: 1.8rem; min-width: 36px; text-align: center;">${medal}</div>
                <div style="font-size: 2.5rem; min-width: 50px; text-align: center;">${emoji}</div>
                <div style="flex: 1;">
                    <div style="display: flex; align-items: baseline; gap: 12px; margin-bottom: 6px;">
                        <span style="font-size: 1.4rem; font-weight: 800; color: #e9d5ff;">${p.zodiac}</span>
                        <span style="font-size: 1.1rem; font-weight: 700; color: ${barColors[i] || '#a855f7'};">${prob}</span>
                    </div>
                    <div style="height: 8px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; margin-bottom: 8px;">
                        <div style="height: 100%; width: ${barW}%; background: linear-gradient(90deg, ${barColors[i] || '#a855f7'}, #c084fc); border-radius: 4px; transition: width 1s ease;"></div>
                    </div>
                    <div style="font-size: 0.85rem; color: #9ca3af; line-height: 1.4;">${p.reason || ''}</div>
                </div>
            </div>
        `;
    }).join('');
}


// ==================== 设置面板 ====================

const DEFAULT_PLATFORM_MODELS = {
    google: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
    openai: ['gpt-4o', 'gpt-4o-mini', 'o1-mini', 'o3-mini'],
    nvidia: ['nvidia/llama-3.3-nemotron-super-49b-v1.5', 'nvidia/llama-3.1-nemotron-70b-instruct'],
    local: ['gpt-5.4', 'gpt-5.4-mini']
};

const DEFAULT_PLATFORM_BASE_URLS = {
    google: 'https://generativelanguage.googleapis.com',
    openai: 'https://api.openai.com/v1',
    nvidia: 'https://integrate.api.nvidia.com/v1',
    local: 'http://127.0.0.1:8317/v1',
};
const DEFAULT_PLATFORM_LABELS = {
    google: 'Google Gemini',
    openai: 'OpenAI Compatible',
    nvidia: 'NVIDIA NIM',
    local: 'Local AI (127.0.0.1)'
};
const DEFAULT_PLATFORM_FORMATS = {
    google: 'google',
    openai: 'openai',
    nvidia: 'openai',
    local: 'openai'
};
const DEFAULT_PLATFORM_URLS = {
    google: 'https://aistudio.google.com/app/apikey',
    openai: 'https://platform.openai.com/api-keys',
    nvidia: 'https://build.nvidia.com',
    local: 'https://github.com/Zwf5458-Py/lottery-ai'
};

let settingsCustomPlatforms = [];
let settingsCustomPlatformModels = {}; // 仅作兼容保留
let settingsPlatformConfigs = {};
let settingsLastActivePlatform = '';
let settingsIsNewProvider = false; // 用来标记是新建还是编辑
let settingsEditingProviderName = ''; // 用来标记当前编辑的供应商原名称
let settingsFetchedModelsList = []; // 用来暂存当前拉取到或已有的模型列表，支持下拉选择

function initSettingsPanel() {
    const modal = document.getElementById('settings-modal');
    const btnOpen = document.getElementById('btn-open-settings');
    const btnClose = document.getElementById('btn-close-settings');
    const overlay = document.getElementById('settings-overlay');
    const btnSave = document.getElementById('btn-save-settings');
    const platformEl = document.getElementById('set-ai-platform');

    // 供应商编辑面板相关按钮
    const btnEditPlatform = document.getElementById('btn-edit-platform-ui');
    const btnCreatePlatform = document.getElementById('btn-create-platform-ui');
    const btnBackProvider = document.getElementById('btn-back-provider');
    const btnCloseProvider = document.getElementById('btn-close-provider');
    const btnSaveProvider = document.getElementById('btn-save-provider');
    const btnDeleteProvider = document.getElementById('btn-delete-provider');
    const btnFetchModels = document.getElementById('btn-fetch-models');
    const btnAddModelRow = document.getElementById('btn-add-model-row');
    const formatEl = document.getElementById('edit-provider-format');
    const btnToggleProviderKey = document.getElementById('btn-toggle-provider-key');

    if (!modal) return;

    // 打开设置
    if (btnOpen) btnOpen.addEventListener('click', () => {
        modal.style.display = 'flex';
        // 确保回到主设置页面视图
        showSettingsSubView('main');
        loadSettings();
    });

    // 关闭设置
    const closeModal = () => { modal.style.display = 'none'; };
    if (btnClose) btnClose.addEventListener('click', closeModal);
    if (overlay) overlay.addEventListener('click', closeModal);

    // 保存设置
    if (btnSave) btnSave.addEventListener('click', saveSettings);

    // 平台切换时联动模型下拉
    if (platformEl) {
        platformEl.addEventListener('change', () => {
            syncModelOptions();
        });
    }

    // 备用平台切换时联动模型下拉
    const backupPlatform1El = document.getElementById('set-backup-platform-1');
    if (backupPlatform1El) {
        backupPlatform1El.addEventListener('change', () => {
            syncBackupModelOptions(1);
        });
    }
    const backupPlatform2El = document.getElementById('set-backup-platform-2');
    if (backupPlatform2El) {
        backupPlatform2El.addEventListener('change', () => {
            syncBackupModelOptions(2);
        });
    }

    // --- 供应商编辑相关事件绑定 ---
    
    // 打开编辑当前平台
    if (btnEditPlatform) btnEditPlatform.addEventListener('click', () => {
        const platform = normalizePlatformName(platformEl?.value || 'google');
        openProviderEditView(platform, false);
    });

    // 打开新建平台
    if (btnCreatePlatform) btnCreatePlatform.addEventListener('click', () => {
        openProviderEditView('', true);
    });

    // 返回主页面
    if (btnBackProvider) btnBackProvider.addEventListener('click', () => {
        showSettingsSubView('main');
    });
    if (btnCloseProvider) btnCloseProvider.addEventListener('click', () => {
        closeModal();
    });

    // 保存当前供应商
    if (btnSaveProvider) btnSaveProvider.addEventListener('click', saveCurrentProvider);

    // 删除当前供应商
    if (btnDeleteProvider) btnDeleteProvider.addEventListener('click', deleteCurrentProvider);

    // 代理拉取模型列表
    if (btnFetchModels) btnFetchModels.addEventListener('click', fetchProviderModels);

    // 手动添加一行模型配置
    if (btnAddModelRow) btnAddModelRow.addEventListener('click', () => {
        addModelRow('', '');
    });

    // 格式切换时更新 API key 申请链接
    if (formatEl) {
        formatEl.addEventListener('change', () => {
            updateGetApiKeyLink(formatEl.value);
        });
    }

    // 密码明文切换
    if (btnToggleProviderKey) {
        btnToggleProviderKey.addEventListener('click', () => {
            const keyInput = document.getElementById('edit-provider-key');
            if (!keyInput) return;
            if (keyInput.type === 'password') {
                keyInput.type = 'text';
                btnToggleProviderKey.textContent = '🙈';
            } else {
                keyInput.type = 'password';
                btnToggleProviderKey.textContent = '👁';
            }
        });
    }

    // 重置图表期数默认值
    const btnResetPeriods = document.getElementById('btn-reset-periods');
    if (btnResetPeriods) {
        btnResetPeriods.addEventListener('click', resetPeriodsToDefault);
    }
}

// 视图显示切换
function showSettingsSubView(view) {
    const mainContainer = document.getElementById('settings-main-container');
    const providerContainer = document.getElementById('provider-edit-container');
    if (view === 'provider') {
        if (mainContainer) mainContainer.style.display = 'none';
        if (providerContainer) providerContainer.style.display = 'flex';
    } else {
        if (providerContainer) providerContainer.style.display = 'none';
        if (mainContainer) mainContainer.style.display = 'flex';
    }
}

// 打开编辑供应商视图
function openProviderEditView(platform, isNew) {
    settingsIsNewProvider = isNew;
    const titleEl = document.getElementById('provider-title');
    const nameEl = document.getElementById('edit-provider-name');
    const remarkEl = document.getElementById('edit-provider-remark');
    const urlEl = document.getElementById('edit-provider-url');
    const formatEl = document.getElementById('edit-provider-format');
    const keyEl = document.getElementById('edit-provider-key');
    const baseEl = document.getElementById('edit-provider-base');
    const deleteBtn = document.getElementById('btn-delete-provider');
    const modelsContainer = document.getElementById('provider-models-list-container');

    if (keyEl) keyEl.type = 'password';
    const toggleBtn = document.getElementById('btn-toggle-provider-key');
    if (toggleBtn) toggleBtn.textContent = '👁';

    if (isNew) {
        settingsEditingProviderName = '';
        settingsFetchedModelsList = [];
        if (titleEl) titleEl.textContent = '新建供应商';
        if (nameEl) {
            nameEl.value = '';
            nameEl.disabled = false;
            nameEl.readOnly = false;
        }
        if (remarkEl) remarkEl.value = '';
        if (urlEl) urlEl.value = '';
        if (formatEl) formatEl.value = 'openai';
        if (keyEl) keyEl.value = '';
        if (baseEl) baseEl.value = '';
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (modelsContainer) modelsContainer.innerHTML = '';
        updateGetApiKeyLink('openai');
    } else {
        settingsEditingProviderName = platform;
        if (titleEl) titleEl.textContent = '编辑供应商';
        
        const prov = settingsPlatformConfigs[platform] || {
            api_base: '', api_key: '', api_key_masked: '', remark: '', url: '', format: 'openai', models: []
        };
        // 预加载已存模型和内置默认模型到下拉菜单缓存中
        const existingModelIds = (prov.models || []).map(m => m.id).filter(Boolean);
        const defaultModelIds = DEFAULT_PLATFORM_MODELS[platform] || [];
        settingsFetchedModelsList = Array.from(new Set([...existingModelIds, ...defaultModelIds]));

        if (nameEl) {
            nameEl.value = platform;
            nameEl.disabled = false; // 允许修改供应商名称
            nameEl.readOnly = false;
        }
        if (remarkEl) remarkEl.value = prov.remark || '';
        if (urlEl) urlEl.value = prov.url || '';
        if (formatEl) formatEl.value = prov.format || 'openai';
        if (keyEl) keyEl.value = prov.api_key || prov.api_key_masked || '';
        if (baseEl) baseEl.value = prov.api_base || '';

        // 判断是否允许删除：非内置平台才能删
        const isBuiltin = Object.prototype.hasOwnProperty.call(DEFAULT_PLATFORM_MODELS, platform);
        if (deleteBtn) {
            deleteBtn.style.display = isBuiltin ? 'none' : 'inline-flex';
        }

        // 载入模型配置行
        if (modelsContainer) {
            modelsContainer.innerHTML = '';
            const models = prov.models || [];
            models.forEach(m => {
                addModelRow(m.id, m.displayName);
            });
            if (models.length === 0) {
                // 如果是空，为内置平台提供默认行
                const defModels = DEFAULT_PLATFORM_MODELS[platform] || [];
                defModels.forEach(mId => {
                    addModelRow(mId, '');
                });
            }
        }
        updateGetApiKeyLink(prov.format || 'openai', platform);
    }
    showSettingsSubView('provider');
}

// 智能更新 API key 申请链接
function updateGetApiKeyLink(format, platform = '') {
    const linkEl = document.getElementById('btn-get-provider-key');
    if (!linkEl) return;
    
    let url = 'https://platform.openai.com/api-keys';
    if (format === 'google') {
        url = 'https://aistudio.google.com/app/apikey';
    } else {
        const p = normalizePlatformName(platform);
        if (p === 'nvidia') {
            url = 'https://build.nvidia.com/';
        } else if (p === 'openai') {
            url = 'https://platform.openai.com/api-keys';
        } else if (DEFAULT_PLATFORM_URLS[p]) {
            url = DEFAULT_PLATFORM_URLS[p];
        }
    }
    linkEl.href = url;
}

// 追加一行模型配置
function addModelRow(modelId = '', displayName = '') {
    const container = document.getElementById('provider-models-list-container');
    if (!container) return;

    const row = document.createElement('div');
    row.className = 'provider-model-row';
    row.innerHTML = `
        <span style="color: #64748b; font-size: 0.8rem; user-select: none; width: 12px; text-align: center;">&gt;</span>
        <div class="model-id-wrapper" style="position: relative; flex: 1.5; display: flex; align-items: center; gap: 4px;">
            <input type="text" class="model-id-input" placeholder="模型 ID，如 gpt-4o" style="width: 100%; font-size: 0.8rem; padding: 6px 10px;" value="${modelId}">
            <button type="button" class="model-dropdown-toggle-btn" style="padding: 6px 8px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; color: #9ca3af; cursor: pointer; display: flex; align-items: center; justify-content: center; height: 30px; width: 30px; transition: all 0.2s;" title="选择模型">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
            </button>
        </div>
        <input type="text" class="model-display-input" placeholder="显示名称（可选）" style="flex: 1; font-size: 0.8rem; padding: 6px 10px;" value="${displayName}">
        <button type="button" class="btn-delete-model-row" title="删除模型">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                <line x1="10" y1="11" x2="10" y2="17"></line>
                <line x1="14" y1="11" x2="14" y2="17"></line>
            </svg>
        </button>
    `;

    // 绑定删除按钮
    const delBtn = row.querySelector('.btn-delete-model-row');
    if (delBtn) {
        delBtn.addEventListener('click', () => {
            row.remove();
        });
    }

    // 绑定下拉选择交互
    const toggleBtn = row.querySelector('.model-dropdown-toggle-btn');
    const idInput = row.querySelector('.model-id-input');
    const wrapper = row.querySelector('.model-id-wrapper');

    if (toggleBtn && idInput && wrapper) {
        toggleBtn.addEventListener('mouseenter', () => {
            toggleBtn.style.background = 'rgba(255,255,255,0.08)';
            toggleBtn.style.color = '#f3f4f6';
            toggleBtn.style.borderColor = 'rgba(255,255,255,0.15)';
        });
        toggleBtn.addEventListener('mouseleave', () => {
            toggleBtn.style.background = 'rgba(255,255,255,0.04)';
            toggleBtn.style.color = '#9ca3af';
            toggleBtn.style.borderColor = 'rgba(255,255,255,0.08)';
        });

        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();

            // 先关闭所有的下拉框以防重叠
            document.querySelectorAll('.model-dropdown-list').forEach(el => el.remove());

            if (!settingsFetchedModelsList || settingsFetchedModelsList.length === 0) {
                showSettingsToast('未拉取到模型列表，请先点击右上角“获取模型列表”', 'info');
                return;
            }

            // 创建绝对定位列表
            const list = document.createElement('div');
            list.className = 'model-dropdown-list';
            list.style.cssText = [
                'position:absolute',
                'top:100%',
                'left:0',
                'right:0',
                'background:#1e293b',
                'border:1px solid rgba(255,255,255,0.12)',
                'border-radius:8px',
                'z-index:9999',
                'max-height:160px',
                'overflow-y:auto',
                'margin-top:4px',
                'box-shadow:0 10px 25px rgba(0,0,0,0.5)',
                'padding:4px 0'
            ].join(';');

            settingsFetchedModelsList.forEach(m => {
                const item = document.createElement('div');
                item.className = 'model-dropdown-item';
                item.style.cssText = [
                    'padding:8px 12px',
                    'font-size:0.8rem',
                    'color:#f3f4f6',
                    'cursor:pointer',
                    'transition:background 0.15s'
                ].join(';');
                item.textContent = m;

                item.addEventListener('mouseenter', () => {
                    item.style.background = 'rgba(255,255,255,0.08)';
                });
                item.addEventListener('mouseleave', () => {
                    item.style.background = 'transparent';
                });

                item.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    idInput.value = m;
                    list.remove();
                });

                list.appendChild(item);
            });

            wrapper.appendChild(list);

            const closeList = () => {
                list.remove();
                document.removeEventListener('click', closeList);
            };
            document.addEventListener('click', closeList);
        });
    }

    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
}

// 代理向后端请求模型列表
async function fetchProviderModels(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    const btn = document.getElementById('btn-fetch-models');
    const origText = btn ? btn.innerHTML : '';
    const name = normalizePlatformName(document.getElementById('edit-provider-name')?.value || '');
    const apiBase = document.getElementById('edit-provider-base')?.value || '';
    const apiKey = document.getElementById('edit-provider-key')?.value || '';
    const format = document.getElementById('edit-provider-format')?.value || 'openai';

    if (!apiBase) {
        showSettingsToast('请输入 Base URL 才能拉取模型', 'warn');
        return;
    }

    try {
        if (btn) {
            btn.innerHTML = '⏳ 拉取中...';
            btn.disabled = true;
        }

        const res = await apiFetch('/api/settings/fetch_models', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                platform_name: name,
                api_base: apiBase,
                api_key: apiKey,
                format: format
            })
        });
        const result = await res.json();
        
        if (!result.success) {
            showSettingsToast('拉取失败: ' + (result.error || '未知错误'), 'error');
            return;
        }

        const models = result.models || [];
        if (models.length === 0) {
            showSettingsToast('拉取成功，但没有找到可用模型', 'info');
            return;
        }

        // 暂存拉取到的模型列表，提供下拉点选
        settingsFetchedModelsList = models;

        // 如果目前没有任何模型行，自动添加一个空行作为方便选择的入口
        const container = document.getElementById('provider-models-list-container');
        if (container && container.querySelectorAll('.provider-model-row').length === 0) {
            addModelRow('', '');
        }

        showSettingsToast(`成功拉取 ${models.length} 个模型，可点击模型 ID 右侧的下拉小箭头进行选择`, 'success');
    } catch (e) {
        console.error('拉取模型失败:', e);
        showSettingsToast('拉取模型失败: ' + e.message, 'error');
    } finally {
        if (btn) {
            btn.innerHTML = origText;
            btn.disabled = false;
        }
    }
}

// 保存当前供应商编辑状态
function saveCurrentProvider() {
    const nameInput = document.getElementById('edit-provider-name');
    const name = normalizePlatformName(nameInput ? nameInput.value : '');
    const remark = document.getElementById('edit-provider-remark')?.value || '';
    const url = document.getElementById('edit-provider-url')?.value || '';
    const format = document.getElementById('edit-provider-format')?.value || 'openai';
    const key = document.getElementById('edit-provider-key')?.value || '';
    const base = document.getElementById('edit-provider-base')?.value || '';

    if (!name) {
        showSettingsToast('供应商名称不能为空', 'warn');
        return;
    }
    if (!/^[a-z0-9_-]+$/.test(name)) {
        showSettingsToast('供应商名称只允许小写字母、数字和连字符', 'warn');
        return;
    }

    // 提取模型列表配置
    const modelsList = [];
    const container = document.getElementById('provider-models-list-container');
    if (container) {
        container.querySelectorAll('.provider-model-row').forEach(row => {
            const mId = normalizeModelName(row.querySelector('.model-id-input')?.value || '');
            const mDisp = row.querySelector('.model-display-input')?.value || '';
            if (mId) {
                modelsList.push({ id: mId, displayName: mDisp });
            }
        });
    }

    // 如果修改了供应商名称
    if (settingsEditingProviderName && settingsEditingProviderName !== name) {
        if (Object.prototype.hasOwnProperty.call(DEFAULT_PLATFORM_MODELS, name)) {
            showSettingsToast('供应商名称与内置平台名称冲突，请换一个名称', 'warn');
            return;
        }
        // 删除旧配置
        delete settingsPlatformConfigs[settingsEditingProviderName];
        // 更新自定义列表中的名称
        settingsCustomPlatforms = settingsCustomPlatforms.map(p => p === settingsEditingProviderName ? name : p);
    }

    // 更新或创建内存配置
    const oldCfg = settingsPlatformConfigs[name] || {};
    settingsPlatformConfigs[name] = {
        api_base: base,
        api_key: key.includes('****') ? '' : key,
        api_key_masked: key.includes('****') ? key : (key ? '' : oldCfg.api_key_masked),
        remark: remark,
        url: url,
        format: format,
        models: modelsList
    };

    if (settingsIsNewProvider && !settingsCustomPlatforms.includes(name)) {
        settingsCustomPlatforms.push(name);
    }

    // 回显到主视图
    renderPlatformOptions(name);
    syncModelOptions();
    showSettingsSubView('main');
    showSettingsToast('供应商配置已应用（需点击主界面保存设置物理保存）', 'success');
}

// 删除当前编辑的自定义供应商
function deleteCurrentProvider() {
    const name = normalizePlatformName(document.getElementById('edit-provider-name')?.value || '');
    const targetToDelete = settingsEditingProviderName || name;
    if (!targetToDelete) return;

    if (Object.prototype.hasOwnProperty.call(DEFAULT_PLATFORM_MODELS, targetToDelete)) {
        showSettingsToast('内置平台不能删除', 'warn');
        return;
    }

    if (confirm(`确定要删除供应商平台 ${targetToDelete} 及其下的所有模型配置吗？`)) {
        settingsCustomPlatforms = settingsCustomPlatforms.filter(p => p !== targetToDelete);
        delete settingsPlatformConfigs[targetToDelete];

        const next = getAllPlatforms()[0] || 'google';
        renderPlatformOptions(next);
        syncModelOptions();
        showSettingsSubView('main');
        showSettingsToast(`已删除供应商 ${targetToDelete}`, 'info');
    }
}

function normalizePlatformName(name) {
    return String(name || '').trim().toLowerCase();
}

function normalizeModelName(name) {
    return String(name || '').trim();
}

function getAllPlatforms() {
    const defaults = Object.keys(DEFAULT_PLATFORM_MODELS);
    return [...defaults, ...settingsCustomPlatforms.filter((p) => !defaults.includes(p))];
}

function renderPlatformOptions(selectedPlatform = '') {
    const platformEl = document.getElementById('set-ai-platform');
    if (!platformEl) return;

    const platforms = getAllPlatforms();
    platformEl.innerHTML = platforms
        .map((p) => `<option value="${p}">${DEFAULT_PLATFORM_LABELS[p] || p}</option>`)
        .join('');

    const target = normalizePlatformName(selectedPlatform) || platforms[0] || 'google';
    if (!platforms.includes(target)) {
        platformEl.insertAdjacentHTML('beforeend', `<option value="${target}">${target}</option>`);
        if (!Object.prototype.hasOwnProperty.call(DEFAULT_PLATFORM_MODELS, target) && !settingsCustomPlatforms.includes(target)) {
            settingsCustomPlatforms.push(target);
        }
    }
    platformEl.value = target;
}

function syncModelOptions(selectedModel = '') {
    const platformEl = document.getElementById('set-ai-platform');
    const modelEl = document.getElementById('set-ai-model');
    if (!modelEl || !platformEl) return;

    const platform = normalizePlatformName(platformEl.value) || 'google';

    // 优先从 settingsPlatformConfigs 读取绑定的 models 列表
    const prov = settingsPlatformConfigs[platform] || {};
    let allModels = [];
    if (Array.isArray(prov.models) && prov.models.length > 0) {
        allModels = prov.models;
    } else {
        const defaultModels = DEFAULT_PLATFORM_MODELS[platform] || [];
        const customModels = settingsCustomPlatformModels[platform] || [];
        allModels = [...defaultModels, ...customModels].map(m => ({ id: m, displayName: '' }));
    }

    const uniq = [];
    const seen = new Set();
    allModels.forEach((m) => {
        const n = normalizeModelName(m.id);
        if (!n || seen.has(n)) return;
        seen.add(n);
        uniq.push(m);
    });

    modelEl.innerHTML = uniq.map((m) => `<option value="${m.id}">${m.displayName || m.id}</option>`).join('');

    const target = normalizeModelName(selectedModel);
    if (target) {
        if (!seen.has(target)) {
            modelEl.insertAdjacentHTML('beforeend', `<option value="${target}">${target}</option>`);
        }
        modelEl.value = target;
    } else if (uniq.length > 0) {
        modelEl.value = uniq[0].id;
    }
}

function renderBackupPlatformOptions(index, selectedPlatform = '') {
    const platformEl = document.getElementById(`set-backup-platform-${index}`);
    if (!platformEl) return;

    const platforms = getAllPlatforms();
    platformEl.innerHTML = '<option value="">未启用</option>' + platforms
        .map((p) => `<option value="${p}">${DEFAULT_PLATFORM_LABELS[p] || p}</option>`)
        .join('');

    const target = normalizePlatformName(selectedPlatform);
    if (target && !platforms.includes(target)) {
        platformEl.insertAdjacentHTML('beforeend', `<option value="${target}">${target}</option>`);
    }
    platformEl.value = target || '';
}

function syncBackupModelOptions(index, selectedModel = '') {
    const platformEl = document.getElementById(`set-backup-platform-${index}`);
    const modelEl = document.getElementById(`set-backup-model-${index}`);
    if (!modelEl || !platformEl) return;

    const platform = normalizePlatformName(platformEl.value);
    if (!platform) {
        modelEl.innerHTML = '<option value="">未启用</option>';
        modelEl.value = '';
        return;
    }

    // 优先从 settingsPlatformConfigs 读取绑定的 models 列表
    const prov = settingsPlatformConfigs[platform] || {};
    let allModels = [];
    if (Array.isArray(prov.models) && prov.models.length > 0) {
        allModels = prov.models;
    } else {
        const defaultModels = DEFAULT_PLATFORM_MODELS[platform] || [];
        const customModels = settingsCustomPlatformModels[platform] || [];
        allModels = [...defaultModels, ...customModels].map(m => ({ id: m, displayName: '' }));
    }

    const uniq = [];
    const seen = new Set();
    allModels.forEach((m) => {
        const n = normalizeModelName(m.id);
        if (!n || seen.has(n)) return;
        seen.add(n);
        uniq.push(m);
    });

    modelEl.innerHTML = uniq.map((m) => `<option value="${m.id}">${m.displayName || m.id}</option>`).join('');

    const target = normalizeModelName(selectedModel);
    if (target) {
        if (!seen.has(target)) {
            modelEl.insertAdjacentHTML('beforeend', `<option value="${target}">${target}</option>`);
        }
        modelEl.value = target;
    } else if (uniq.length > 0) {
        modelEl.value = uniq[0].id;
    }
}

// 复制 AI 预测球号
function copyAIBalls() {
    const ballsContainer = document.getElementById('ai-result-balls');
    if (!ballsContainer) return;
    const ballDivs = ballsContainer.querySelectorAll('.lottery-ball');
    if (ballDivs.length === 0) return;
    
    const nums = [];
    ballDivs.forEach(div => {
        nums.push(div.textContent.trim());
    });
    
    let text = '';
    if (nums.length > 1) {
        const regular = nums.slice(0, -1).join(', ');
        const special = nums[nums.length - 1];
        text = `${regular} + ${special}`;
    } else {
        text = nums[0];
    }
    
    copyTextToClipboard(text, '已成功复制开奖号：' + text);
}

// 复制批量模拟结果中的全部组合
function copyBatchDraws() {
    const list = document.getElementById('batch-draws-list');
    if (!list) return;
    const items = list.querySelectorAll('.batch-draw-item');
    if (items.length === 0) return;
    
    let textLines = [];
    items.forEach(item => {
        const idxText = item.querySelector('.batch-draw-index') ? item.querySelector('.batch-draw-index').textContent.trim() : '';
        const ballDivs = item.querySelectorAll('.lottery-ball');
        if (ballDivs.length > 0) {
            const nums = [];
            ballDivs.forEach(div => {
                nums.push(div.textContent.trim());
            });
            let line = '';
            if (nums.length > 1) {
                const regular = nums.slice(0, -1).join(', ');
                const special = nums[nums.length - 1];
                line = `${regular} + ${special}`;
            } else {
                line = nums[0];
            }
            textLines.push(idxText ? `${idxText}: ${line}` : line);
        }
    });
    
    const text = textLines.join('\n');
    copyTextToClipboard(text, '已成功复制全部组合！');
}

// 通用复制板辅助函数 (现代浏览器 + Fallback 支持)
function copyTextToClipboard(text, successMsg) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showCenterToast(successMsg, 'success');
        }).catch(() => {
            fallbackCopyText(text, successMsg);
        });
    } else {
        fallbackCopyText(text, successMsg);
    }
}

function fallbackCopyText(text, successMsg) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        document.execCommand('copy');
        showCenterToast(successMsg, 'success');
    } catch (err) {
        showCenterToast('复制失败: ' + err, 'error');
    }
    document.body.removeChild(textArea);
}

// 复制历史记录卡片中的球号
function copyHistoryBalls(btn) {
    const container = btn.closest('.ai-card-sidebar') || btn.parentElement;
    if (!container) return;
    const ballDivs = container.querySelectorAll('.lottery-ball');
    if (ballDivs.length === 0) return;
    
    const nums = [];
    ballDivs.forEach(div => {
        nums.push(div.textContent.trim());
    });
    
    let text = '';
    if (nums.length > 1) {
        const regular = nums.slice(0, -1).join(', ');
        const special = nums[nums.length - 1];
        text = `${regular} + ${special}`;
    } else {
        text = nums[0];
    }
    
    copyTextToClipboard(text, '已成功复制历史预测号码：' + text);
}

// 复制开奖历史表格中的一行号码
function copyTableLine(btn) {
    const tr = btn.closest('tr');
    if (!tr) return;
    
    // 获取正码球 (在第三列 td 里)
    const regularBallEls = tr.querySelectorAll('td:nth-child(3) .table-ball');
    // 获取特码球 (在第四列 td 里)
    const specialBallEl = tr.querySelector('td:nth-child(4) .table-ball');
    
    if (regularBallEls.length === 0 && !specialBallEl) return;
    
    const regularNums = Array.from(regularBallEls).map(el => el.textContent.trim());
    const specialNum = specialBallEl ? specialBallEl.textContent.trim() : '';
    
    let text = '';
    if (regularNums.length > 0) {
        text = regularNums.join(', ');
        if (specialNum) {
            text += ' + ' + specialNum;
        }
    } else {
        text = specialNum;
    }
    
    const drawNum = tr.querySelector('td:nth-child(1)').textContent.trim();
    copyTextToClipboard(text, `已成功复制第 ${drawNum} 期开奖号码：${text}`);
}


// 轻量提示弹层（设置保存专用）
let centerToastWrapper = null;
let centerToastEl = null;
function showCenterToast(message, type = 'info', persistent = false) {
    if (!centerToastWrapper) {
        centerToastWrapper = document.createElement('div');
        centerToastWrapper.id = 'center-toast-wrapper';
        centerToastWrapper.style.position = 'fixed';
        centerToastWrapper.style.inset = '0';
        centerToastWrapper.style.display = 'flex';
        centerToastWrapper.style.alignItems = 'center';
        centerToastWrapper.style.justifyContent = 'center';
        centerToastWrapper.style.pointerEvents = 'none';
        centerToastWrapper.style.zIndex = '9999';
        document.body.appendChild(centerToastWrapper);
    }
    if (!centerToastEl) {
        centerToastEl = document.createElement('div');
        centerToastEl.id = 'center-toast';
        centerToastEl.style.minWidth = '260px';
        centerToastEl.style.maxWidth = '90%';
        centerToastEl.style.padding = '18px 20px';
        centerToastEl.style.borderRadius = '14px';
        centerToastEl.style.boxShadow = '0 15px 40px rgba(0,0,0,0.35)';
        centerToastEl.style.backdropFilter = 'blur(10px)';
        centerToastEl.style.textAlign = 'center';
        centerToastEl.style.fontWeight = '700';
        centerToastEl.style.lineHeight = '1.5';
        centerToastEl.style.color = '#e2e8f0';
        centerToastEl.style.cursor = 'pointer';
        centerToastEl.style.pointerEvents = 'auto';
        centerToastWrapper.appendChild(centerToastEl);
        centerToastEl.addEventListener('click', () => {
            centerToastEl.style.display = 'none';
            centerToastWrapper.style.display = 'none';
        });
    }

    const palette = {
        success: { bg: 'rgba(34,197,94,0.9)', text: '#ecfdf3' },
        error: { bg: 'rgba(239,68,68,0.92)', text: '#fff1f2' },
        info: { bg: 'rgba(55,65,81,0.9)', text: '#e5e7eb' },
        warn: { bg: 'rgba(234,179,8,0.95)', text: '#1f2937' }
    };
    const p = palette[type] || palette.info;

    centerToastEl.textContent = message;
    centerToastEl.style.background = p.bg;
    centerToastEl.style.color = p.text;
    centerToastEl.style.border = '1px solid rgba(255,255,255,0.15)';
    centerToastWrapper.style.display = 'flex';
    centerToastEl.style.display = 'block';

    if (!persistent) {
        clearTimeout(centerToastEl._timer);
        centerToastEl._timer = setTimeout(() => {
            centerToastEl.style.display = 'none';
            centerToastWrapper.style.display = 'none';
        }, 3600);
    }
}

function showSettingsToast(message, type = 'info', persistent = false) {
    showCenterToast(message, type, persistent);
}

const DEFAULT_PERIODS_MACAUJC = {
    zodiac_trend: 200,
    odd_even: 100,
    big_small: 100,
    markov: 0,
    hot_cold: 100,
    tail: 100,
    bayesian: 300,
    lstm: 150,
    ai_raw_data: 150,
    range_distribution: 150,
    three_region: 100,
    poisson_tail: 150,
    ac_value: 100
};

const DEFAULT_PERIODS_WEILITSAI = {
    zodiac_trend: 150,
    odd_even: 100,
    big_small: 100,
    markov: 0,
    hot_cold: 100,
    tail: 100,
    bayesian: 300,
    lstm: 150,
    ai_raw_data: 150,
    range_distribution: 150,
    three_region: 100,
    poisson_tail: 150,
    ac_value: 100
};

function resetPeriodsToDefault() {
    const isWeilitsai = state.lotteryType === 'weilitsai';
    const defaults = isWeilitsai ? DEFAULT_PERIODS_WEILITSAI : DEFAULT_PERIODS_MACAUJC;
    
    const fieldMap = {
        'set-zodiac-trend': defaults.zodiac_trend,
        'set-odd-even': defaults.odd_even,
        'set-big-small': defaults.big_small,
        'set-hot-cold': defaults.hot_cold,
        'set-tail': defaults.tail,
        'set-bayesian': defaults.bayesian,
        'set-lstm': defaults.lstm,
        'set-markov': defaults.markov,
        'set-ai-raw': defaults.ai_raw_data,
        'set-range-distribution': defaults.range_distribution || 50,
        'set-three-region': defaults.three_region || 50,
        'set-poisson-tail': defaults.poisson_tail || 50,
        'set-ac-value': defaults.ac_value || 50,
        'set-z1-exclusive': defaults.z1_exclusive || 100,
    };
    
    for (const [id, val] of Object.entries(fieldMap)) {
        const el = document.getElementById(id);
        if (el) el.value = val;
    }
    showCenterToast('已重置为默认期数推荐值，请记得点击“保存设置”以生效。', 'success');
}

async function loadSettings() {
    try {
        const titleEl = document.querySelector('.settings-header h2');
        if (titleEl) {
            titleEl.textContent = state.lotteryType === 'weilitsai' ? '⚙️ 系统设置 (威力彩)' : '⚙️ 系统设置 (新澳)';
        }

        const zodiacLabel = document.getElementById('set-zodiac-trend')?.previousElementSibling;
        if (zodiacLabel) {
            zodiacLabel.textContent = state.lotteryType === 'weilitsai' ? '和值动量' : '生肖路单';
        }

        const res = await apiFetch('/api/settings?type=' + state.lotteryType);
        const result = await res.json();
        if (!result.success) return;

        const cfg = result.data;
        const ai = cfg.ai || {};
        const periods = cfg.chart_periods || {};

        settingsCustomPlatforms = Array.isArray(ai.custom_platforms)
            ? ai.custom_platforms.map(normalizePlatformName).filter(Boolean)
            : [];
        settingsCustomPlatformModels = (ai.custom_platform_models && typeof ai.custom_platform_models === 'object')
            ? Object.fromEntries(
                Object.entries(ai.custom_platform_models).map(([k, v]) => [
                    normalizePlatformName(k),
                    Array.isArray(v) ? v.map(normalizeModelName).filter(Boolean) : []
                ])
            )
            : {};

        // 兼容旧字段 custom_models
        if (Array.isArray(ai.custom_models) && ai.custom_models.length > 0) {
            const legacyPlatform = normalizePlatformName(ai.platform || 'google');
            settingsCustomPlatformModels[legacyPlatform] = settingsCustomPlatformModels[legacyPlatform] || [];
            ai.custom_models.map(normalizeModelName).filter(Boolean).forEach((m) => {
                if (!settingsCustomPlatformModels[legacyPlatform].includes(m)) {
                    settingsCustomPlatformModels[legacyPlatform].push(m);
                }
            });
        }

        // 初始化每个平台的独立配置并支持旧配置平滑合并
        settingsPlatformConfigs = {};
        const providers = ai.providers || {};
        const allPlatforms = getAllPlatforms();
        
        allPlatforms.forEach(p => {
            const p_name = normalizePlatformName(p);
            const prov = providers[p_name] || {};
            
            let modelsList = [];
            if (Array.isArray(prov.models)) {
                modelsList = prov.models.map(m => typeof m === 'string' ? { id: m, displayName: '' } : { id: m.id || '', displayName: m.displayName || '' });
            } else {
                // 旧配置兼容合并
                const defModels = DEFAULT_PLATFORM_MODELS[p_name] || [];
                const custModels = settingsCustomPlatformModels[p_name] || [];
                const combined = [...defModels, ...custModels];
                const seen = new Set();
                combined.forEach(m => {
                    if (!m || seen.has(m)) return;
                    seen.add(m);
                    modelsList.push({ id: m, displayName: '' });
                });
            }

            settingsPlatformConfigs[p_name] = {
                api_base: prov.api_base || '',
                api_key: '',
                api_key_masked: prov.api_key_masked || '',
                remark: prov.remark || '',
                url: prov.url || DEFAULT_PLATFORM_URLS[p_name] || '',
                format: prov.format || DEFAULT_PLATFORM_FORMATS[p_name] || 'openai',
                models: modelsList
            };
        });

        // 兼容向下迁移旧有全局配置
        const currentPlatform = normalizePlatformName(ai.platform || 'google');
        if (settingsPlatformConfigs[currentPlatform]) {
            if (!settingsPlatformConfigs[currentPlatform].api_base && ai.api_base) {
                settingsPlatformConfigs[currentPlatform].api_base = ai.api_base;
            }
            if (!settingsPlatformConfigs[currentPlatform].api_key_masked && ai.api_key_masked) {
                settingsPlatformConfigs[currentPlatform].api_key_masked = ai.api_key_masked;
            }
        }

        renderPlatformOptions(ai.platform || 'google');
        syncModelOptions(ai.model || '');

        renderBackupPlatformOptions(1, ai.backup_platform_1 || '');
        syncBackupModelOptions(1, ai.backup_model_1 || '');

        renderBackupPlatformOptions(2, ai.backup_platform_2 || '');
        syncBackupModelOptions(2, ai.backup_model_2 || '');

        // 期数配置
        const fieldMap = {
            'set-zodiac-trend': periods.zodiac_trend ?? 200,
            'set-odd-even': periods.odd_even ?? 100,
            'set-big-small': periods.big_small ?? 100,
            'set-hot-cold': periods.hot_cold ?? 100,
            'set-tail': periods.tail ?? 100,
            'set-bayesian': periods.bayesian ?? 100,
            'set-lstm': periods.lstm ?? 100,
            'set-markov': periods.markov ?? 0,
            'set-ai-raw': periods.ai_raw_data ?? 300,
            'set-range-distribution': periods.range_distribution ?? 50,
            'set-three-region': periods.three_region ?? 50,
            'set-poisson-tail': periods.poisson_tail ?? 50,
            'set-ac-value': periods.ac_value ?? 50,
            'set-z1-exclusive': periods.z1_exclusive ?? 100,
        };
        for (const [id, val] of Object.entries(fieldMap)) {
            const el = document.getElementById(id);
            if (el) el.value = val;
        }

        // 加载邮箱
        try {
            const emailRes = await apiFetch('/api/account/email');
            const emailData = await emailRes.json();
            const emailEl = document.getElementById('set-email');
            if (emailEl && emailData.success) emailEl.value = emailData.email || '';
        } catch (e) { }

    } catch (e) {
        console.error('加载设置失败:', e);
    }
}

async function saveSettings() {
    const btn = document.getElementById('btn-save-settings');
    const origText = btn ? btn.textContent : '';

    try {
        if (btn) { btn.textContent = '⏳ 保存中...'; btn.disabled = true; }

        // 整理各个平台独立的 providers 数据发给后端，并同步兼容 custom_platform_models
        const payloadProviders = {};
        const customPlatformModelsSync = {};
        
        for (const [p, cfg] of Object.entries(settingsPlatformConfigs)) {
            payloadProviders[p] = {
                api_base: cfg.api_base,
                remark: cfg.remark,
                url: cfg.url,
                format: cfg.format,
                models: cfg.models
            };
            if (cfg.api_key) {
                payloadProviders[p].api_key = cfg.api_key;
            } else if (cfg.api_key_masked) {
                payloadProviders[p].api_key = cfg.api_key_masked;
            } else {
                payloadProviders[p].api_key = '';
            }

            // 同步 custom_platform_models：过滤出非内置的模型
            const defModels = DEFAULT_PLATFORM_MODELS[p] || [];
            const customList = (cfg.models || [])
                .map(m => m.id)
                .filter(id => !defModels.includes(id));
            customPlatformModelsSync[p] = customList;
        }

        const activePlatform = normalizePlatformName(document.getElementById('set-ai-platform')?.value || 'google');
        const activeModel = normalizeModelName(document.getElementById('set-ai-model')?.value || '');

        const backupPlatform1 = normalizePlatformName(document.getElementById('set-backup-platform-1')?.value || '');
        const backupModel1 = normalizeModelName(document.getElementById('set-backup-model-1')?.value || '');
        const backupPlatform2 = normalizePlatformName(document.getElementById('set-backup-platform-2')?.value || '');
        const backupModel2 = normalizeModelName(document.getElementById('set-backup-model-2')?.value || '');

        const payload = {
            ai: {
                platform: activePlatform,
                model: activeModel,
                backup_platform_1: backupPlatform1,
                backup_model_1: backupModel1,
                backup_platform_2: backupPlatform2,
                backup_model_2: backupModel2,
                custom_platforms: Array.isArray(settingsCustomPlatforms) ? settingsCustomPlatforms.slice() : [],
                custom_platform_models: customPlatformModelsSync,
                providers: payloadProviders,
            },
            chart_periods: {
                zodiac_trend: parseInt(document.getElementById('set-zodiac-trend')?.value) || 200,
                odd_even: parseInt(document.getElementById('set-odd-even')?.value) || 100,
                big_small: parseInt(document.getElementById('set-big-small')?.value) || 100,
                hot_cold: parseInt(document.getElementById('set-hot-cold')?.value) || 100,
                tail: parseInt(document.getElementById('set-tail')?.value) || 100,
                bayesian: parseInt(document.getElementById('set-bayesian')?.value) || 100,
                lstm: parseInt(document.getElementById('set-lstm')?.value) || 100,
                markov: parseInt(document.getElementById('set-markov')?.value) || 0,
                ai_raw_data: parseInt(document.getElementById('set-ai-raw')?.value) || 300,
                range_distribution: parseInt(document.getElementById('set-range-distribution')?.value) || 50,
                three_region: parseInt(document.getElementById('set-three-region')?.value) || 50,
                poisson_tail: parseInt(document.getElementById('set-poisson-tail')?.value) || 50,
                ac_value: parseInt(document.getElementById('set-ac-value')?.value) || 50,
                z1_exclusive: parseInt(document.getElementById('set-z1-exclusive')?.value) || 100,
            }
        };

        // 兼容保留全局的 api_base / api_key 字段，避免报错
        const currentActiveCfg = settingsPlatformConfigs[activePlatform];
        if (currentActiveCfg) {
            if (currentActiveCfg.api_base) {
                payload.ai.api_base = currentActiveCfg.api_base;
            }
            if (currentActiveCfg.api_key) {
                payload.ai.api_key = currentActiveCfg.api_key;
            } else if (currentActiveCfg.api_key_masked) {
                payload.ai.api_key = currentActiveCfg.api_key_masked;
            }
        }

        const res = await apiFetch('/api/settings?type=' + state.lotteryType, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        let result;
        try {
            result = await res.json();
        } catch (je) {
            throw new Error(`服务器返回了非预期的格式 (HTTP ${res.status})`);
        }

        if (result.success) {
            if (btn) btn.textContent = '✅ 已保存';
            if (result.note) {
                showSettingsToast(result.note, 'info');
            }
            if (result.points_deducted && result.points_deducted > 0) {
                const balanceText = result.points_balance !== null && result.points_balance !== undefined ? `，剩余 ${result.points_balance} 积分` : '';
                showSettingsToast(`本次设置保存扣除 ${result.points_deducted} 积分${balanceText}`, 'warn');
            }
            // 关闭弹窗并刷新统计数据
            setTimeout(() => {
                document.getElementById('settings-modal').style.display = 'none';
                if (btn) { btn.textContent = origText; btn.disabled = false; }
                state.statisticsLoaded = false;
                loadStatistics();
                renderSimulationBillingTip();
            }, 800);
        } else {
            showSettingsToast('保存失败: ' + (result.error || '未知错误'), 'error', true);
            if (btn) { btn.textContent = origText; btn.disabled = false; }
        }
    } catch (e) {
        console.error('保存设置失败:', e);
        showSettingsToast('保存设置出错: ' + e.message, 'error', true);
        if (btn) { btn.textContent = origText; btn.disabled = false; }
    }
}

// ==================== AI 分析档案加载与渲染 ====================

async function loadAIHistory(page = 1) {
    state.aiHistoryPage = page;
    const container = document.getElementById('ai-history-container');
    const pagination = document.getElementById('ai-pagination');
    if (!container) return;

    container.innerHTML = '<div style="text-align: center; color: var(--text-secondary); padding: 40px;">加载中...</div>';

    try {
        const response = await fetch(`/api/ai_history?page=${page}&per_page=10&type=${state.lotteryType}`);
        const result = await response.json();

        if (result.success) {
            renderAIHistory(result.data.items);
            renderAIPagination(result.data);
        } else {
            container.innerHTML = `<div style="text-align: center; color: var(--color-error); padding: 40px;">加载失败: ${result.error}</div>`;
        }
    } catch (error) {
        container.innerHTML = `<div style="text-align: center; color: var(--color-error); padding: 40px;">请求失败: ${error.message}</div>`;
    }
}

function renderAIHistory(items) {
    const container = document.getElementById('ai-history-container');
    if (!items || items.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-secondary); padding: 40px;">暂无 AI 智能推算的历史归档数据</div>';
        return;
    }

    container.innerHTML = items.map(item => {
        const ai = item.result;
        // 如果是有效结果则会有 analysis 等字段
        const hasResult = ai && ai.numbers && ai.special_num;
        const hasZodiacResult = ai && ai.zodiac_predictions && ai.zodiac_predictions.length > 0;

        // 渲染球，同模拟界面
        let ballsHTML = '';
        if (hasResult) {
            ballsHTML = `
                <div style="display: flex; gap: 8px; flex-wrap: wrap; margin: 16px 0;">
                    ${renderBallsHtml(ai.numbers, ai.zodiacs, ai.special_num, ai.special_zodiac, 'ai-ball', true)}
                </div>
            `;
        } else if (hasZodiacResult) {
            const zEmoji = { '鼠': '🐭', '牛': '🐮', '虎': '🐯', '兔': '🐰', '龙': '🐲', '蛇': '🐍', '马': '🐴', '羊': '🐑', '猴': '🐵', '鸡': '🐔', '狗': '🐶', '猪': '🐷' };
            const medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣'];
            const barColors = ['#a855f7', '#8b5cf6', '#7c3aed', '#6d28d9', '#5b21b6'];

            ballsHTML = '<div style="margin: 12px 0;">' + ai.zodiac_predictions.map((p, i) => {
                const emoji = zEmoji[p.zodiac] || '🔮';
                const medal = medals[i] || `#${i + 1}`;
                const prob = p.probability || '?%';
                const probNum = parseFloat(prob) || 10;
                const barW = Math.min(100, Math.max(15, probNum * 3));
                return `
                    <div style="padding: 14px; background: rgba(168,85,247,${0.08 + i * 0.02}); border-radius: 12px; border: 1px solid rgba(168,85,247,0.15); margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 1.1rem;">${medal}</span>
                                <span style="font-size: 1.6rem;">${emoji}</span>
                                <span style="font-size: 1.1rem; font-weight: 800; color: #e9d5ff;">${p.zodiac}</span>
                            </div>
                            <span style="font-size: 1rem; font-weight: 700; color: ${barColors[i] || '#a855f7'};">${prob}</span>
                        </div>
                        <div style="height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; margin-bottom: 10px;">
                            <div style="height: 100%; width: ${barW}%; background: linear-gradient(90deg, ${barColors[i] || '#a855f7'}, #c084fc); border-radius: 3px;"></div>
                        </div>
                        <div style="font-size: 0.82rem; color: #9ca3af; line-height: 1.4;">${p.reason || ''}</div>
                    </div>
                `;
            }).join('') + '</div>';
        }

        return `
            <div class="ai-card stat-card glass" style="text-align: left; padding: 28px; margin-bottom: 24px;">
                <div class="ai-card-layout">
                    <!-- 左侧工具面板 -->
                    <div class="ai-card-sidebar">
                        <!-- 模型与状态信息块 -->
                        <div style="background: rgba(255,255,255,0.03); border-radius: 14px; padding: 16px; border: 1px solid rgba(255,255,255,0.06); position: relative; overflow: hidden;">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                                <span style="display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; background: linear-gradient(135deg, #7c3aed, #a855f7); border-radius: 7px; font-size: 0.9rem;">🤖</span>
                                <span style="color: #e9d5ff; font-weight: 800; font-size: 0.95rem;">${item.model_name}</span>
                            </div>
                            <div style="font-size: 0.75rem; color: #9ca3af; margin-bottom: 14px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span>🗓️ ${
                                        (function(){
                                            try {
                                                const d = new Date(item.generated_at + 'Z');
                                                if(isNaN(d.getTime())) return item.generated_at.split(' ')[0];
                                                return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
                                            } catch(e) { return item.generated_at.split(' ')[0]; }
                                        })()
                                    }</span>
                                    <span>🕒 ${
                                        (function(){
                                            try {
                                                const d = new Date(item.generated_at + 'Z');
                                                if(isNaN(d.getTime())) return item.generated_at.split(' ')[1];
                                                return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;
                                            } catch(e) { return item.generated_at.split(' ')[1]; }
                                        })()
                                    }</span>
                                </div>
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px; width: 100%;">
                                <div style="display: flex; gap: 6px; width: 100%;">
                                    <button class="btn-sync" style="flex: 1; background: rgba(34, 197, 94, 0.1); color: #86efac; border-color: rgba(34, 197, 94, 0.2); font-size: 0.75rem; padding: 7px; border-radius: 6px; white-space: nowrap;" onclick="shareAICard(this)">📤 分享图片</button>
                                    <button class="btn-sync" style="flex: 1; background: rgba(168, 85, 247, 0.15); color: #d8b4fe; border-color: rgba(168, 85, 247, 0.25); font-size: 0.75rem; padding: 7px; border-radius: 6px; white-space: nowrap;" onclick="copyHistoryBalls(this)">📋 复制号码</button>
                                </div>
                                <button class="btn-sync" style="width: 100%; background: rgba(239, 68, 68, 0.1); color: #fca5a5; border-color: rgba(239, 68, 68, 0.2); font-size: 0.75rem; padding: 7px; border-radius: 6px; display: block;" onclick="deleteAIHistory(${item.id})">🗑️ 删除档案</button>
                            </div>
                        </div>

                        <!-- 预测球/排名 -->
                        ${ballsHTML}

                        <!-- 分析维度标签块 -->
                        <div style="padding: 16px; background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px dashed rgba(255,255,255,0.08);">
                            <div style="font-size: 0.7rem; color: #6b7280; margin-bottom: 12px; letter-spacing: 0.5px; text-transform: uppercase; font-weight: 700; display: flex; align-items: center; gap: 5px;">
                                <span style="width: 3px; height: 10px; background: #a855f7; border-radius: 2px;"></span> 核心参考基准
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 6px;">
                                ${(function() {
                                    var dimIcons = {
                                        'zodiac_mode': '🐲', 'markov': '🔗', 'consecutive': '📈',
                                        'bayesian': '🎯', 'lstm': '🧠', 'big_small': '⚖️',
                                        'odd_even': '🔄', 'hot_cold': '🔥', 'tail': '🔢', 'zodiac': '🐾', 'color': '🎨'
                                    };
                                    var dimNames = {
                                        'zodiac_mode': '生肖', 'markov': '马尔可夫', 'consecutive': '连续',
                                        'bayesian': '贝叶斯', 'lstm': 'LSTM', 'big_small': '大小',
                                        'odd_even': '单双', 'hot_cold': '冷热', 'tail': '尾数', 'zodiac': '生肖走势', 'color': '波色'
                                    };
                                    
                                    function renderTag(d) {
                                        var icon = dimIcons[d] || '📌';
                                        var label = dimNames[d] || d;
                                        return `<div style="display: inline-flex; align-items: center; gap: 4px; padding: 4px 8px; background: rgba(168,85,247,0.06); border: 1px solid rgba(168,85,247,0.15); border-radius: 5px; font-size: 0.7rem; color: #c4b5fd; white-space: nowrap;">${icon} ${label}</div>`;
                                    }

                                    var row1 = [];
                                    var row2 = [];
                                    var row3 = [];

                                    (item.dimensions || []).forEach(function(d) {
                                        if (d === 'markov' || d === 'bayesian') {
                                            row2.push(d);
                                        } else if (d === 'big_small' || d === 'odd_even' || d === 'hot_cold' || d === 'tail') {
                                            row1.push(d);
                                        } else {
                                            row3.push(d);
                                        }
                                    });

                                    var rowsHtml = '';
                                    if (row1.length > 0) {
                                        rowsHtml += `<div style="display: flex; flex-wrap: wrap; gap: 8px;">${row1.map(renderTag).join('')}</div>`;
                                    }
                                    if (row2.length > 0) {
                                        rowsHtml += `<div style="display: flex; flex-wrap: wrap; gap: 8px;">${row2.map(renderTag).join('')}</div>`;
                                    }
                                    if (row3.length > 0) {
                                        rowsHtml += `<div style="display: flex; flex-wrap: wrap; gap: 8px;">${row3.map(renderTag).join('')}</div>`;
                                    }
                                    return rowsHtml || `<div style="display: flex; flex-wrap: wrap; gap: 8px;">${renderTag('默认维度')}</div>`;
                                })()}
                            </div>
                        </div>
                    </div>

                    <!-- 推理文字区 -->
                    <div class="ai-card-main">
                        <div class="ai-card-analysis">
                            ${formatAnalysisText(ai.analysis || '无有效推断文字')}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}


// ==================== AI 档案分享为图片 ====================
async function shareAICard(btnEl) {
    // 找到最近的 .stat-card 父级
    const card = btnEl.closest('.stat-card');
    if (!card) return;

    const origText = btnEl.textContent;
    btnEl.textContent = '⏳ 生成中...';
    btnEl.disabled = true;

    try {
        // 临时调整样式以获得更好的截图效果
        card.style.boxShadow = 'none';

        // 添加水印
        const watermark = document.createElement('div');
        watermark.style.cssText = 'text-align:center; padding:12px 0 4px; font-size:0.72rem; color:#6b7280; border-top:1px solid rgba(255,255,255,0.06); margin-top:16px;';
        watermark.textContent = '🎰 六合彩智能分析系统 · AI 推算档案';
        card.appendChild(watermark);

        const canvas = await html2canvas(card, {
            backgroundColor: '#0f172a',
            scale: 2,
            useCORS: true,
            logging: false,
            allowTaint: true,
            removeContainer: true,
        });

        // 移除水印
        card.removeChild(watermark);
        card.style.boxShadow = '';

        // 尝试使用 Web Share API (移动端优先)
        if (navigator.share && navigator.canShare) {
            canvas.toBlob(async (blob) => {
                const file = new File([blob], 'AI分析档案.png', { type: 'image/png' });
                try {
                    await navigator.share({
                        title: 'AI 智能推算档案',
                        text: '六合彩智能分析系统 - AI 推算结果',
                        files: [file]
                    });
                } catch (shareErr) {
                    // 用户取消分享或不支持，fallback 到下载
                    downloadCanvas(canvas);
                }
            }, 'image/png');
        } else {
            // 桌面端直接下载
            downloadCanvas(canvas);
        }
    } catch (err) {
        console.error('生成图片失败:', err);
        alert('生成图片失败: ' + err.message);
        card.style.boxShadow = '';
    } finally {
        btnEl.textContent = origText;
        btnEl.disabled = false;
    }
}

function downloadCanvas(canvas, prefix = "AI分析档案") {
    const link = document.createElement('a');
    const now = new Date();
    const ts = now.getFullYear() + String(now.getMonth() + 1).padStart(2, '0') + String(now.getDate()).padStart(2, '0') + '_' + String(now.getHours()).padStart(2, '0') + String(now.getMinutes()).padStart(2, '0');
    link.download = `${prefix}_${ts}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
}

function renderAIPagination(data) {
    const pagination = document.getElementById('ai-pagination');
    if (!pagination) return;

    const { page, total_pages } = data;
    if (total_pages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';
    if (page > 1) {
        html += `<button class="page-btn" onclick="loadAIHistory(${page - 1})">上一页</button>`;
    } else {
        html += `<button class="page-btn disabled" disabled>上一页</button>`;
    }

    html += `<span style="padding: 0 16px; color: var(--text-secondary); line-height: 36px;">第 ${page} / ${total_pages} 页</span>`;

    if (page < total_pages) {
        html += `<button class="page-btn" onclick="loadAIHistory(${page + 1})">下一页</button>`;
    } else {
        html += `<button class="page-btn disabled" disabled>下一页</button>`;
    }

    pagination.innerHTML = html;
}

async function deleteAIHistory(id) {
    if (!confirm('确定要永久删除这条 AI 预测档案吗？')) return;

    try {
        const res = await apiFetch(`/api/ai_history/${id}`, { method: 'DELETE' });
        const json = await res.json();
        if (json.success) {
            loadAIHistory(1);
        } else {
            alert('删除失败: ' + json.error);
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
}

// ==================== 账号管理 ====================

async function saveEmail() {
    const email = document.getElementById('set-email').value.trim();
    try {
        const res = await apiFetch('/api/account/email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        alert(data.success ? '✅ 邮箱已保存' : ('❌ ' + (data.error || '保存失败')));
    } catch (e) {
        if (!e.message.includes('权限')) alert('❌ 网络错误');
    }
}

async function changePassword() {
    const oldPwd = document.getElementById('set-old-pwd').value;
    const newPwd = document.getElementById('set-new-pwd').value;
    if (!oldPwd || !newPwd) { alert('⚠️ 请填写旧密码和新密码'); return; }
    try {
        const res = await apiFetch('/api/account/password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password: oldPwd, new_password: newPwd })
        });
        const data = await res.json();
        if (data.success) {
            alert('✅ 密码修改成功！请重新登录。');
            window.location.href = '/logout';
        } else {
            alert('❌ ' + (data.error || '修改失败'));
        }
    } catch (e) {
        if (!e.message.includes('权限')) alert('❌ 网络错误');
    }
}

// ===== 高阶图表渲染函数 =====

// 全局快捷选择加权维度阵型函数
window.applyDimPreset = function(dimsToSelect) {
    // 遍历所有的维度复选框
    const checkboxes = document.querySelectorAll('input[name="dim"]');
    checkboxes.forEach(cb => {
        // 如果该复选框的值在推荐列表中，则勾选，否则取消勾选
        cb.checked = dimsToSelect.includes(cb.value);
    });
    // 添加视觉反馈
    const dimContainer = document.querySelector('.dim-checkboxes');
    if(dimContainer) {
        dimContainer.style.transition = 'opacity 0.2s';
        dimContainer.style.opacity = '0.3';
        setTimeout(() => {
            dimContainer.style.opacity = '1';
        }, 200);
    }
};

