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
});

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

function renderSimulationBillingTip() {
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

    el.style.borderColor = border;
    el.innerHTML = `<strong style="color:${color};">${title}：</strong>${text}`;
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
    const isWeilitsai = state.lotteryType === 'weilitsai';
    
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
    const hiddenDimsForWeili = ['color'];
    const allDimsForWeili = ['color', 'markov', 'consecutive', 'bayesian', 'lstm'];
    allDimsForWeili.forEach(val => {
        const checkbox = document.querySelector(`input[name="dim"][value="${val}"]`);
        if (checkbox) {
            const label = checkbox.closest('.dim-checkbox');
            if (label) {
                label.style.display = (isWeilitsai && hiddenDimsForWeili.includes(val)) ? 'none' : '';
            }
            if (isWeilitsai && hiddenDimsForWeili.includes(val)) {
                checkbox.checked = false; // 威力彩屏蔽波色
            } else {
                checkbox.checked = true; // 默认重新勾选
            }
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
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 4px; flex-wrap: wrap;">
                        ${regularBallsHtml}
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 1rem; color: #a1a1aa; font-weight: bold;">+</span>
                        ${specialBallHtml}
                        <span style="font-size: 0.8rem; color: #9ca3af; font-weight: bold; margin-left: 4px;">上期开奖号码</span>
                    </div>
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
        () => renderFrequencyChart(data.number_frequency_z1),
        () => renderHotColdRanking(data.hot_cold_z1),
        () => renderPredictProbChart(data.predict_probabilities_z1),
        () => renderOddEvenChart(data.odd_even_z2),
        () => renderBigSmallChart(data.big_small_z2),
        () => renderTailChart(data.tail_numbers_z1),
        () => renderMarkovChart(data.markov),
        () => renderBayesianChart(data.bayesian),
        () => renderLSTMChart(data.lstm),
    ] : [
        () => renderFrequencyChart(data.number_frequency),
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
        chartTasks[taskIdx]();
        taskIdx++;
        if (taskIdx < chartTasks.length) {
            requestAnimationFrame(() => setTimeout(runNextChart, 0));
        }
    }
    runNextChart();

    // ===== 为所有图表标题追加统计期数标注 =====
    const periods = data.chart_periods || {};
    const periodLabel = (n) => n > 0 ? `近${n}期` : '全历史数据';

    // canvas ID → chart_periods key 映射
    const chartPeriodMap = {
        'chart-frequency': 'hot_cold',
        'chart-odd-even': 'odd_even',
        'chart-big-small': 'big_small',
        'chart-zodiac': 'zodiac_trend',
        'chart-five-elements': 'hot_cold',
        'chart-tail': 'tail',
        'chart-bayesian': 'bayesian',
        'chart-lstm': 'lstm',
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
        const card = canvasEl.closest('.chart-card');
        if (!card) return;
        const titleEl = card.querySelector('.chart-title');
        if (!titleEl) return;
        titleEl.innerHTML = titleEl.textContent.replace(/（统计基准.*?）/g, '').trim() +
            ` <span style="font-size:0.75rem; color:#9ca3af; font-weight:400;">（统计基准：${periodLabel(periods[periodKey] || 100)}）</span>`;
    });
}

function renderFrequencyChart(frequency) {
    const ctx = document.getElementById('chart-frequency').getContext('2d');

    const labels = Object.keys(frequency).map(n => n + '号');
    const values = Object.values(frequency);
    const maxVal = Math.max(...values);
    const minVal = Math.min(...values);

    // 根据频率生成颜色渐变（频率越高越红，越低越蓝）
    const colors = values.map(v => {
        const ratio = (v - minVal) / (maxVal - minVal || 1);
        if (ratio > 0.7) return 'rgba(239, 68, 68, 0.8)';
        if (ratio > 0.4) return 'rgba(245, 200, 66, 0.8)';
        return 'rgba(59, 130, 246, 0.8)';
    });

    if (state.charts.frequency) state.charts.frequency.destroy();

    state.charts.frequency = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '出现次数',
                data: values,
                backgroundColor: colors,
                borderRadius: 3,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    titleColor: '#f5c842',
                    borderColor: 'rgba(245, 200, 66, 0.3)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12
                }
            },
            scales: {
                x: {
                    ticks: { maxRotation: 90, font: { size: 10 } },
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.04)' }
                }
            }
        }
    });
}

// ===== 第一区预测概率分布图 =====
function renderPredictProbChart(predictProb) {
    const ctx = document.getElementById('chart-predict-prob').getContext('2d');

    if (!predictProb || predictProb.length === 0) return;

    // 只展示概率最高的前 15 个号码
    const sorted = [...predictProb].sort((a, b) => b.probability - a.probability).slice(0, 15);

    const labels = sorted.map(item => `${item.number}号`);
    const values = sorted.map(item => item.probability);

    // 为不同状态的号码分配不同颜色：预警号码用红色，斜连邻号用黄色，普通号码用蓝色
    const backgroundColors = sorted.map(item => {
        if (item.is_alert) return 'rgba(239, 68, 68, 0.8)';
        if (item.is_neighbor) return 'rgba(245, 158, 11, 0.8)';
        return 'rgba(59, 130, 246, 0.8)';
    });

    if (state.charts.predictProb) state.charts.predictProb.destroy();

    state.charts.predictProb = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '下期推算概率 (%)',
                data: values,
                backgroundColor: backgroundColors,
                borderRadius: 3,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    titleColor: '#f5c842',
                    borderColor: 'rgba(245, 200, 66, 0.3)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    callbacks: {
                        label: function (ctx) {
                            const idx = ctx.dataIndex;
                            const item = sorted[idx];
                            let extra = '';
                            if (item.is_alert) extra += ' (⚠️遗漏警报号)';
                            if (item.is_neighbor) extra += ' (邻近斜连号)';
                            return ` 推算概率: ${ctx.raw}%${extra}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: {
                        callback: function (value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

// ===== 冷热号排行 =====
function renderHotColdRanking(hotCold) {
    const gridContainer = document.getElementById('hot-cold-grid');
    if (!gridContainer) return;

    const overallMaxOmission = Math.max(
        ...hotCold.hot.map(h => h.omission),
        ...hotCold.cold.map(c => c.omission)
    );

    let html = '';

    // 1. 排名行
    html += `
    <div style="display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: bold; color: #a1a1aa; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; height: 38px;">排名</div>
    `;
    for (let i = 1; i <= 10; i++) {
        html += `
        <div style="display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: bold; color: #a1a1aa; height: 38px;">#${i}</div>
        `;
    }

    // 2. 热号行
    html += `
    <div style="display: flex; align-items: center; justify-content: center; font-size: 0.95rem; font-weight: bold; color: #ef4444; background: rgba(239, 68, 68, 0.06); border: 1px solid rgba(239, 68, 68, 0.15); border-radius: 8px; padding: 8px 4px; text-align: center; min-height: 115px;">🔥 热号</div>
    `;
    hotCold.hot.forEach((item) => {
        const colorHex = getBallColorHex(item.number);
        const darkColorHex = colorHex === '#ef4444' ? '#d30000' : (colorHex === '#3b82f6' ? '#0055d3' : (colorHex === '#22c55e' ? '#00d34b' : '#d4a017'));
        const omissionStyle = item.omission >= 25 ? 'color:#f87171;font-weight:bold;' : 'color:#9ca3af;';
        const omissionText = item.omission > 0 ? `遗漏${item.omission}期` : '上期开出';
        const isMaxOmission = item.omission === overallMaxOmission && overallMaxOmission > 0;
        const maxOmissionStyle = isMaxOmission ? 'box-shadow: 0 0 10px rgba(245, 200, 66, 0.6); border-color: rgba(245, 200, 66, 0.8) !important;' : '';

        html += `
        <div class="rank-item hot ${isMaxOmission ? 'pulse-glow' : ''}" style="display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 10px 4px; border-radius: 8px; text-align: center; gap: 8px; min-height: 115px; ${maxOmissionStyle}">
            <span class="overview-ball" style="display: inline-flex; align-items: center; justify-content: center; background: radial-gradient(circle at 30% 30%, ${colorHex}, ${darkColorHex}); border-radius: 50%; color: #ffffff !important; -webkit-text-fill-color: #ffffff; font-weight: 900; font-family: Arial, Helvetica, sans-serif; box-shadow: 0 3px 8px rgba(0,0,0,0.4); border: 2px solid rgba(255,255,255,0.4); width: 32px; height: 32px; font-size: 0.95rem; line-height: 1; text-shadow: 1px 1px 0 rgba(0,0,0,0.5);">${item.number}</span>
            <span class="rank-count" style="font-size: 0.85rem; font-weight: bold; color: #f3f4f6; line-height: 1; min-width: auto; text-align: center;">${item.count}次</span>
            <span style="font-size: 0.72rem; line-height: 1; ${omissionStyle}">${omissionText}</span>
        </div>
        `;
    });

    // 3. 冷号行
    html += `
    <div style="display: flex; align-items: center; justify-content: center; font-size: 0.95rem; font-weight: bold; color: #3b82f6; background: rgba(59, 130, 246, 0.06); border: 1px solid rgba(59, 130, 246, 0.15); border-radius: 8px; padding: 8px 4px; text-align: center; min-height: 115px;">❄️ 冷号</div>
    `;
    hotCold.cold.forEach((item) => {
        const colorHex = getBallColorHex(item.number);
        const darkColorHex = colorHex === '#ef4444' ? '#d30000' : (colorHex === '#3b82f6' ? '#0055d3' : (colorHex === '#22c55e' ? '#00d34b' : '#d4a017'));
        const omissionStyle = item.omission >= 50 ? 'color:#ef4444;font-weight:900;' : (item.omission >= 25 ? 'color:#f87171;' : 'color:#9ca3af;');
        const omissionText = item.omission > 0 ? `遗漏${item.omission}期` : '上期开出';
        const isMaxOmission = item.omission === overallMaxOmission && overallMaxOmission > 0;
        const maxOmissionStyle = isMaxOmission ? 'box-shadow: 0 0 10px rgba(245, 200, 66, 0.6); border-color: rgba(245, 200, 66, 0.8) !important;' : '';

        html += `
        <div class="rank-item cold ${isMaxOmission ? 'pulse-glow' : ''}" style="display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 10px 4px; border-radius: 8px; text-align: center; gap: 8px; min-height: 115px; ${maxOmissionStyle}">
            <span class="overview-ball" style="display: inline-flex; align-items: center; justify-content: center; background: radial-gradient(circle at 30% 30%, ${colorHex}, ${darkColorHex}); border-radius: 50%; color: #ffffff !important; -webkit-text-fill-color: #ffffff; font-weight: 900; font-family: Arial, Helvetica, sans-serif; box-shadow: 0 3px 8px rgba(0,0,0,0.4); border: 2px solid rgba(255,255,255,0.4); width: 32px; height: 32px; font-size: 0.95rem; line-height: 1; text-shadow: 1px 1px 0 rgba(0,0,0,0.5);">${item.number}</span>
            <span class="rank-count" style="font-size: 0.85rem; font-weight: bold; color: #f3f4f6; line-height: 1; min-width: auto; text-align: center;">${item.count}次</span>
            <span style="font-size: 0.72rem; line-height: 1; ${omissionStyle}">遗漏${item.omission}期</span>
        </div>
        `;
    });

    gridContainer.innerHTML = html;
}

// ===== 波色冷热切换事件 =====
document.addEventListener('change', (e) => {
    if (e.target.name === 'hotcold_mode') {
        const numView = document.getElementById('number-hotcold-view');
        const colorView = document.getElementById('color-hotcold-view');
        if (e.target.value === 'color') {
            if (numView) numView.style.display = 'none';
            if (colorView) colorView.style.display = 'block';
        } else {
            if (numView) numView.style.display = '';
            if (colorView) colorView.style.display = 'none';
        }
    }
});

// ===== 波色冷热极限推测卡片 =====
function renderColorHotCold(colorData) {
    const container = document.getElementById('color-hotcold-view');
    if (!container || !colorData || !colorData.length) return;

    const colorMap = {
        '红波': { bg: 'rgba(239, 68, 68, 0.15)', border: 'rgba(239, 68, 68, 0.4)', bar: '#ef4444', glow: 'rgba(239, 68, 68, 0.6)', emoji: '🔴' },
        '蓝波': { bg: 'rgba(59, 130, 246, 0.15)', border: 'rgba(59, 130, 246, 0.4)', bar: '#3b82f6', glow: 'rgba(59, 130, 246, 0.6)', emoji: '🔵' },
        '绿波': { bg: 'rgba(34, 197, 94, 0.15)', border: 'rgba(34, 197, 94, 0.4)', bar: '#22c55e', glow: 'rgba(34, 197, 94, 0.6)', emoji: '🟢' }
    };

    container.innerHTML = `
        <p style="font-size: 0.75rem; color: #9ca3af; margin-bottom: 12px; line-height: 1.5;">
            基于几何分布 <code style="color:#6ee7b7;">P(X=k)=(1-p)<sup>k-1</sup>·p</code> 计算各波色遗漏极端度。极端度越高，说明该波色遗漏已超出历史正常波动范围的可能性越大。
        </p>

        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
            ${colorData.map(item => {
        const cm = colorMap[item.color] || colorMap['红波'];
        const isExtreme = item.extremity >= 85;
        const isHigh = item.extremity >= 60;
        return `
                <div class="color-analysis-card ${isExtreme ? 'pulse-glow' : ''}" style="
                    background: ${cm.bg};
                    border: 1px solid ${cm.border};
                    border-radius: 12px;
                    padding: 12px 14px;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    ${isExtreme ? 'box-shadow: 0 0 20px ' + cm.glow + ';' : ''}
                    transition: all 0.3s ease;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 1.4rem;">${cm.emoji}</span>
                            <div>
                                <div style="font-size: 1rem; font-weight: 800; color: #f3f4f6;">${item.color}</div>
                                <div style="font-size: 0.65rem; color: #9ca3af; margin-top: 2px;">近${item.total}期出现${item.count}次</div>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <span style="
                                display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 700;
                                background: ${isExtreme ? 'rgba(239, 68, 68, 0.3)' : (isHigh ? 'rgba(245, 158, 11, 0.3)' : 'rgba(34, 197, 94, 0.2)')};
                                color: ${isExtreme ? '#fca5a5' : (isHigh ? '#fbbf24' : '#86efac')};
                            ">${item.rebound_hint}</span>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;">
                        <div style="text-align: center; padding: 6px; background: rgba(0,0,0,0.2); border-radius: 6px;">
                            <div style="font-size: 0.65rem; color: #9ca3af; margin-bottom: 2px;">当前遗漏</div>
                            <div style="font-size: 1.1rem; font-weight: 900; color: ${isExtreme ? '#fca5a5' : '#f3f4f6'};">${item.current_gap}<span style="font-size:0.6rem;">期</span></div>
                        </div>
                        <div style="text-align: center; padding: 6px; background: rgba(0,0,0,0.2); border-radius: 6px;">
                            <div style="font-size: 0.65rem; color: #9ca3af; margin-bottom: 2px;">平均遗漏</div>
                            <div style="font-size: 1.1rem; font-weight: 900; color: #f3f4f6;">${item.avg_gap}<span style="font-size:0.6rem;">期</span></div>
                        </div>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 0.7rem;">
                         <span style="color:#9ca3af;">CDF概率</span>
                         <strong style="color: #f3f4f6;">${item.cdf}%</strong>
                    </div>
                    <div style="position: relative; height: 8px; background: rgba(0,0,0,0.3); border-radius: 4px; overflow: hidden;">
                        <div style="
                            height: 100%; width: ${Math.min(100, item.extremity)}%;
                            background: linear-gradient(90deg, ${cm.bar}, ${isExtreme ? '#fbbf24' : cm.bar});
                            border-radius: 4px; transition: width 1.5s ease;
                        "></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 6px; font-size: 0.7rem; color: #6b7280;">
                        <span>✅ 正常</span>
                        <span>极端度: ${item.extremity}%</span>
                        <span>🔥 反弹</span>
                    </div>
                </div>
            `}).join('')}
        </div>
    `;
}

// ===== 特码单双时间轴 K 线图 =====
function renderOddEvenChart(oddEven) {
    const ctx = document.getElementById('chart-odd-even').getContext('2d');

    const labels = oddEven.labels || [];
    const values = oddEven.values || [];

    // 根据正负值分配不同的颜色，正数（奇）为蓝色，负数（偶）为红色
    const backgroundColors = values.map(val => val > 0 ? 'rgba(59, 130, 246, 0.8)' : 'rgba(239, 68, 68, 0.8)');

    if (state.charts.oddEven) state.charts.oddEven.destroy();

    state.charts.oddEven = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '长龙偏移 (正=奇, 负=偶)',
                data: values,
                backgroundColor: backgroundColors,
                borderRadius: 2,
                barPercentage: 0.8,
                categoryPercentage: 1.0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            hover: { animationDuration: 0 },
            layout: { padding: { bottom: 25 } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            const val = ctx.raw;
                            return val > 0 ? `奇数连开 ${val} 期` : `偶数连开 ${Math.abs(val)} 期`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        callback: function (value) {
                            if (value > 0) return '+' + value + ' 期奇';
                            if (value < 0) return Math.abs(value) + ' 期偶';
                            return '0';
                        }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { maxTicksLimit: 15 }
                }
            }
        }
    });
}

// ===== 特码大小时间轴 K 线图 =====
function renderBigSmallChart(bigSmall) {
    const ctx = document.getElementById('chart-big-small').getContext('2d');

    const labels = bigSmall.labels || [];
    const values = bigSmall.values || [];

    // 正数（大）为橙色，负数（小）为绿色
    const backgroundColors = values.map(val => val > 0 ? 'rgba(245, 158, 11, 0.8)' : 'rgba(16, 185, 129, 0.8)');

    if (state.charts.bigSmall) state.charts.bigSmall.destroy();

    state.charts.bigSmall = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '长龙偏移 (正=大, 负=小)',
                data: values,
                backgroundColor: backgroundColors,
                borderRadius: 2,
                barPercentage: 0.8,
                categoryPercentage: 1.0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            hover: { animationDuration: 0 },
            layout: { padding: { bottom: 25 } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            const val = ctx.raw;
                            return val > 0 ? `大号连开 ${val} 期` : `小号连开 ${Math.abs(val)} 期`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        callback: function (value) {
                            if (value > 0) return '+' + value + ' 期大';
                            if (value < 0) return Math.abs(value) + ' 期小';
                            return '0';
                        }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { maxTicksLimit: 15 }
                }
            }
        }
    });
}

// ===== 特码生肖-期数走势矩阵 (路单) =====
function renderZodiacChart(zodiacData) {
    const canvas = document.getElementById('chart-zodiac');
    if (!canvas) return;

    const draws = zodiacData.draws || [];
    const zodiacOrder = zodiacData.zodiac_order || [];
    const BALL_R = 11;
    const ROW_H = BALL_R * 2 + 1; // 直径+1px，红球与网格近乎相切

    const labels = [];
    const scatterData = draws.map((d, i) => {
        labels.push(d.draw_number);
        return { x: i, y: d.zodiac_idx, label: d.num, actualDraw: d.draw_number };
    });

    const wrapper = document.getElementById('zodiac-scroll-wrapper');
    const container = document.getElementById('zodiac-chart-container');
    const pxPerPoint = 45;
    const totalW = Math.max(wrapper.clientWidth, draws.length * pxPerPoint);
    container.style.width = totalW + 'px';

    const chartAreaH = 13 * ROW_H; // 稍微增加高度以容纳扩大的 Y 轴区间
    const padTop = 25, padBot = 25, xAxisH = 60;
    const totalH = chartAreaH + padTop + padBot + xAxisH;
    container.style.height = totalH + 'px';

    if (state.charts.zodiac) state.charts.zodiac.destroy();
    if (state.charts.zodiacY) { state.charts.zodiacY.destroy(); state.charts.zodiacY = null; }

    const ballPlugin = {
        id: 'ballDraw',
        afterDatasetsDraw(chart) {
            const { ctx, chartArea } = chart;
            ctx.save();
            ctx.font = 'bold 11px "Noto Sans SC"';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            const meta = chart.getDatasetMeta(0);
            if (!meta.data) { ctx.restore(); return; }
            meta.data.forEach((pt, i) => {
                if (pt.x < chartArea.left - BALL_R || pt.x > chartArea.right + BALL_R) return;
                const raw = chart.data.datasets[0].data[i];
                ctx.fillStyle = getBallColorHex(raw.label);
                ctx.beginPath();
                ctx.arc(pt.x, pt.y, BALL_R, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = '#fff';
                ctx.fillText(raw.label, pt.x, pt.y);
            });
            ctx.restore();
        }
    };

    state.charts.zodiac = new Chart(canvas, {
        type: 'scatter',
        data: {
            datasets: [{
                data: scatterData, pointRadius: 0,
                showLine: true, borderColor: 'rgba(239,68,68,0.45)', borderWidth: 1.5, tension: 0
            }]
        },
        plugins: [ballPlugin],
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false, // 禁用初始动画提高加载速度
            hover: { animationDuration: 0 }, // 禁用鼠标悬浮重绘动画，解决Tooltip卡顿
            layout: { padding: { top: padTop, bottom: padBot, left: 10, right: 30 } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (c) {
                            const d = c.raw;
                            return '\u671f\u53f7: ' + d.actualDraw + ' | \u7279\u7801: ' + d.label + ' | \u751f\u8096: ' + zodiacOrder[d.y];
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'category',
                    labels: labels,
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: {
                        color: '#6b7280', font: { size: 10 },
                        maxRotation: 45, minRotation: 45,
                        autoSkip: true,
                        maxTicksLimit: Math.min(draws.length, 30) // 如果数据过多自动跳过多余标签
                    }
                },
                y: {
                    min: -0.8, max: 11.8,
                    grid: { color: 'rgba(255,255,255,0.08)' },
                    ticks: { display: false, stepSize: 1 },
                    afterFit: function (s) { s.width = 0; }
                }
            }
        }
    });

    // === DOM标签注入：从chart.scales.y读取真实像素坐标 ===
    const labelsBox = document.getElementById('zodiac-y-labels');
    labelsBox.innerHTML = '';
    labelsBox.style.height = totalH + 'px';

    const yScale = state.charts.zodiac.scales.y;
    zodiacOrder.forEach((name, idx) => {
        const py = yScale.getPixelForValue(idx);
        const lbl = document.createElement('div');
        lbl.textContent = name;
        lbl.style.cssText = 'position:absolute;right:6px;font-size:12px;font-weight:bold;color:#9ca3af;line-height:1;transform:translateY(-50%);white-space:nowrap;';
        lbl.style.top = py + 'px';
        labelsBox.appendChild(lbl);
    });

    setTimeout(() => { if (wrapper) wrapper.scrollLeft = wrapper.scrollWidth; }, 120);
}

// 全局绑定一次 markov_mode 切换事件
document.addEventListener('change', (e) => {
    if (e.target.name === 'markov_mode' && window.__markovData) {
        renderMarkovChart(window.__markovData);
    }
});

// ===== 智能马尔可夫链状态转移极地图 =====
function renderMarkovChart(markovData) {
    const canvas = document.getElementById('chart-markov-radar');
    if (!canvas || !markovData) return;

    const isWeilitsai = state.lotteryType === 'weilitsai';
    const parentCard = canvas.closest('.chart-card') || canvas.closest('.card');
    const titleEl = parentCard ? parentCard.querySelector('.chart-title') : null;
    if (titleEl) {
        titleEl.textContent = isWeilitsai ? '🕸️ 马尔可夫链 1区号码转移概率分布' : '🕸️ 马尔可夫链特码状态转移';
    }

    let mode = 'zodiac';
    if (isWeilitsai) {
        mode = 'number';
    } else {
        const modeEl = document.querySelector('input[name="markov_mode"]:checked');
        mode = modeEl ? modeEl.value : 'zodiac';
    }

    // 基础数据
    let targetDesc = '';
    let targetStr = '??';
    let weights = markovData.weights || {};
    let labels = [];
    let backgroundColors = [];
    let occurrences = weights._occurrences || {};

    if (isWeilitsai) {
        targetDesc = '1区正码';
        targetStr = '';
        labels = Array.from({length: 38}, (_, i) => (i + 1).toString());
        backgroundColors = labels.map(() => 'rgba(59, 130, 246, 0.7)');
    } else if (mode === 'zodiac') {
        targetDesc = markovData.target_zodiac || '未知';
        targetStr = markovData.target_num || '??';
        labels = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"];
    } else {
        targetDesc = markovData.target_color || '未知';
        targetStr = markovData.target_color || '??';
        weights = markovData.color_weights || {};
        labels = ["红波", "蓝波", "绿波"];
        occurrences = weights._occurrences || {};
    }

    const maxPeriods = weights.max_periods || 0;
    const periodStr = maxPeriods > 0 ? `近${maxPeriods}期` : '全历史数据';

    const descEl = parentCard ? parentCard.querySelector('p') : null;
    if (descEl) {
        descEl.innerHTML = `<span class="text-blue-400 font-bold">【概率推演】</span> 基于历史数据推演出真实的转移概率分布。${isWeilitsai ? '号码条形柱越突出，下一期开出倾向越强。' : '雷达轴越突出的维度，历史跃迁倾向越强。'}（统计基准：${periodStr}）`;
    }

    const values = labels.map(key => weights[key] || 1.0);
    const maxVal = Math.max(...values);

    const counts = labels.map(key => occurrences[key] || 0);
    const maxCount = Math.max(...counts);
    const avgCount = counts.length > 0 ? (counts.reduce((a, b) => a + b, 0) / counts.length) : 1;

    if (!isWeilitsai) {
        if (mode === 'zodiac') {
            backgroundColors = counts.map(count => {
                if (count === maxCount && count > avgCount * 1.2) return 'rgba(239, 68, 68, 0.7)';
                if (count > avgCount * 1.1) return 'rgba(245, 158, 11, 0.6)';
                if (count < avgCount * 0.7) return 'rgba(59, 130, 246, 0.4)';
                return 'rgba(156, 163, 175, 0.4)';
            });
        } else {
            backgroundColors = labels.map(colorName => {
                if (colorName === '红波') return 'rgba(239, 68, 68, 0.75)';
                if (colorName === '蓝波') return 'rgba(59, 130, 246, 0.75)';
                if (colorName === '绿波') return 'rgba(34, 197, 94, 0.75)';
                return 'rgba(156, 163, 175, 0.4)';
            });
        }
    }

    const radioContainer = parentCard ? parentCard.querySelector('.algorithm-toggle') : null;
    if (radioContainer) {
        radioContainer.style.display = isWeilitsai ? 'none' : '';
    }

    const chartWrapper = canvas.parentElement;
    chartWrapper.style.position = 'relative';
    chartWrapper.style.height = isWeilitsai ? '250px' : '360px';

    let layoutBox = chartWrapper.parentElement;
    if (!layoutBox.classList.contains('markov-layout-box')) {
        layoutBox = document.createElement('div');
        layoutBox.className = 'markov-layout-box';
        layoutBox.style.display = 'flex';
        layoutBox.style.alignItems = 'center';
        layoutBox.style.justifyContent = 'space-between';
        layoutBox.style.width = '100%';
        chartWrapper.parentNode.insertBefore(layoutBox, chartWrapper);
        layoutBox.appendChild(chartWrapper);
        chartWrapper.style.flexGrow = '1';
        chartWrapper.style.flexShrink = '1';
        chartWrapper.style.minWidth = '0';
    }

    const oldLegends = layoutBox.querySelectorAll('.custom-markov-legend');
    oldLegends.forEach(el => el.remove());

    const createLegendCol = (list, startIndex = 0) => {
        const col = document.createElement('div');
        col.className = 'custom-markov-legend';
        col.style.display = 'flex';
        col.style.flexDirection = 'column';
        col.style.gap = '10px';
        col.style.minWidth = mode === 'zodiac' ? '90px' : '70px';
        col.style.padding = '0 20px';

        list.forEach((key, index) => {
            const actualIdx = startIndex + index;
            const color = backgroundColors[actualIdx];
            const count = occurrences[key] || 0;
            const isMaxWeight = (weights[key] || 1.0) === maxVal;

            const item = document.createElement('div');
            item.style.display = 'flex';
            item.style.alignItems = 'center';
            item.style.fontSize = '0.9rem';
            item.style.color = '#e5e7eb';
            item.style.whiteSpace = 'nowrap';

            if (isMaxWeight) {
                item.className = 'pulse-glow';
                item.style.padding = '4px 8px';
                item.style.margin = '-4px -8px';
                item.style.borderRadius = '6px';
                item.style.backgroundColor = 'rgba(239, 68, 68, 0.15)';
                item.style.border = '1px solid rgba(239, 68, 68, 0.4)';
            }

            const box = document.createElement('span');
            box.style.display = 'inline-block';
            box.style.width = '14px';
            box.style.height = '14px';
            box.style.backgroundColor = color;
            box.style.marginRight = '8px';
            box.style.borderRadius = '3px';

            item.appendChild(box);
            item.appendChild(document.createTextNode(`${key}：${count}次`));
            col.appendChild(item);
        });
        return col;
    };

    if (!isWeilitsai) {
        if (mode === 'zodiac') {
            layoutBox.insertBefore(createLegendCol(labels.slice(0, 6), 0), chartWrapper);
            layoutBox.appendChild(createLegendCol(labels.slice(6, 12), 6));
        } else {
            layoutBox.insertBefore(createLegendCol(labels.slice(0, 2), 0), chartWrapper);
            layoutBox.appendChild(createLegendCol(labels.slice(2, 3), 2));
        }
    }

    const oldCenter = chartWrapper.querySelector('.markov-center-label');
    if (oldCenter) oldCenter.remove();

    if (!isWeilitsai && markovData.target_num) {
        const centerLabel = document.createElement('div');
        centerLabel.className = 'markov-center-label';
        centerLabel.style.position = 'absolute';
        centerLabel.style.top = '50%';
        centerLabel.style.left = '50%';
        centerLabel.style.transform = 'translate(-50%, -50%)';
        centerLabel.style.width = '56px';
        centerLabel.style.height = '56px';
        centerLabel.style.borderRadius = '50%';

        let centerBg = 'rgba(15, 23, 42, 0.95)';
        if (mode === 'color') {
            if (targetStr === '红波') centerBg = 'rgba(239, 68, 68, 0.85)';
            else if (targetStr === '蓝波') centerBg = 'rgba(59, 130, 246, 0.85)';
            else if (targetStr === '录波' || targetStr === '绿波') centerBg = 'rgba(34, 197, 94, 0.85)';
        }
        centerLabel.style.backgroundColor = centerBg;

        centerLabel.style.display = 'flex';
        centerLabel.style.alignItems = 'center';
        centerLabel.style.justifyContent = 'center';
        centerLabel.style.flexDirection = 'column';
        centerLabel.style.color = '#fff';
        centerLabel.style.border = '2px solid rgba(255, 255, 255, 0.15)';
        centerLabel.style.boxShadow = '0 4px 12px rgba(0,0,0,0.5)';
        centerLabel.style.zIndex = '99';
        centerLabel.style.pointerEvents = 'none';

        const centerText = mode === 'zodiac' ? targetStr : targetStr.replace('波', '');
        centerLabel.innerHTML = `
            <span class="mc-number" style="position: relative; z-index: 100; font-size: ${mode === 'color' ? '1.1rem' : '1.4rem'}; font-weight: bold; line-height: 1;">${centerText}</span>
        `;
        chartWrapper.appendChild(centerLabel);
    }

    if (state.charts.markov) state.charts.markov.destroy();

    state.charts.markov = new Chart(canvas, {
        type: isWeilitsai ? 'bar' : 'polarArea',
        data: {
            labels: labels,
            datasets: [{
                label: isWeilitsai ? '转移跃迁权重' : `上期开出【${targetDesc}】的跃迁权重`,
                data: values,
                backgroundColor: backgroundColors,
                borderWidth: 1,
                borderColor: 'rgba(255,255,255,0.1)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: 10 },
            scales: isWeilitsai ? {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9ca3af' }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9ca3af' },
                    min: 0.4,
                    max: 2.6
                }
            } : {
                r: {
                    angleLines: { color: 'rgba(255,255,255,0.05)' },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        display: false,
                        min: 0.4,
                        max: Math.max(2.6, maxVal + 0.2)
                    },
                    pointLabels: {
                        display: true,
                        centerPointLabels: true,
                        color: '#9ca3af',
                        font: { size: 12, weight: 'bold' }
                    }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: isWeilitsai,
                    external: isWeilitsai ? null : function (context) {
                        let tooltipEl = chartWrapper.querySelector('.markov-tooltip');
                        if (!tooltipEl) {
                            tooltipEl = document.createElement('div');
                            tooltipEl.className = 'markov-tooltip';
                            tooltipEl.style.cssText = 'position:absolute; z-index:50; pointer-events:none; background:rgba(0,0,0,0.85); color:#fff; padding:6px 10px; border-radius:6px; font-size:0.8rem; white-space:nowrap; transition:opacity 0.15s; opacity:0;';
                            chartWrapper.appendChild(tooltipEl);
                        }
                        const tooltipModel = context.tooltip;
                        if (tooltipModel.opacity === 0) {
                            tooltipEl.style.opacity = '0';
                            return;
                        }
                        const idx = tooltipModel.dataPoints?.[0]?.dataIndex;
                        if (idx !== undefined) {
                            const key = labels[idx];
                            const weight = values[idx].toFixed(2);
                            const count = occurrences[key] || 0;
                            tooltipEl.innerHTML = `<strong>${key}</strong>：${count}次（权重 ${weight}x）`;
                        }
                        tooltipEl.style.opacity = '1';
                        tooltipEl.style.right = '10px';
                        tooltipEl.style.top = '10px';
                        tooltipEl.style.left = 'auto';
                        tooltipEl.style.transform = 'none';
                    }
                }
            }
        },
        plugins: [{
            id: 'markovSliceGlow',
            afterDraw: (chart) => {
                if (state.lotteryType === 'weilitsai') return;
                const maxVal = Math.max(...values);
                if (maxVal === 0) return;

                const meta = chart.getDatasetMeta(0);
                const parent = chart.canvas.parentNode;

                let overlayCanvas = parent.querySelector('.markov-glow-overlay');
                if (!overlayCanvas) {
                    overlayCanvas = document.createElement('canvas');
                    overlayCanvas.className = 'markov-glow-overlay shape-pulse';
                    overlayCanvas.style.position = 'absolute';
                    overlayCanvas.style.pointerEvents = 'none';
                    overlayCanvas.style.zIndex = '10';
                    parent.appendChild(overlayCanvas);
                }

                overlayCanvas.style.top = chart.canvas.offsetTop + 'px';
                overlayCanvas.style.left = chart.canvas.offsetLeft + 'px';
                overlayCanvas.style.width = chart.canvas.offsetWidth + 'px';
                overlayCanvas.style.height = chart.canvas.offsetHeight + 'px';
                overlayCanvas.width = chart.canvas.width;
                overlayCanvas.height = chart.canvas.height;

                const ctx = overlayCanvas.getContext('2d');
                ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

                meta.data.forEach((arc, idx) => {
                    if (values[idx] === maxVal) {
                        ctx.save();
                        overlayCanvas.style.color = arc.options.backgroundColor;

                        ctx.beginPath();
                        if (arc.innerRadius > 0) {
                            ctx.arc(arc.x, arc.y, arc.outerRadius, arc.startAngle, arc.endAngle);
                            ctx.arc(arc.x, arc.y, arc.innerRadius, arc.endAngle, arc.startAngle, true);
                        } else {
                            ctx.moveTo(arc.x, arc.y);
                            ctx.arc(arc.x, arc.y, arc.outerRadius, arc.startAngle, arc.endAngle);
                        }
                        ctx.closePath();
                        ctx.fillStyle = arc.options.backgroundColor;
                        ctx.fill();
                        ctx.restore();
                    }
                });
            }
        }]
    });
}

// ===== 尾数分布柱状图 (复合双轴) =====
function renderTailChart(tailData) {
    const ctx = document.getElementById('chart-tail').getContext('2d');

    // tailData 可能直接是 distribution (兼容旧接口)，也可能是 {distribution, omission}
    let dist = tailData;
    let omission = {};
    if (tailData.distribution) {
        dist = tailData.distribution;
        omission = tailData.omission || {};
    }

    const labels = Object.keys(dist).map(n => `尾数${n}`);
    const freqValues = Object.values(dist);
    const omissionValues = Object.keys(dist).map(k => omission[k] || 0);

    if (state.charts.tail) state.charts.tail.destroy();

    const container = ctx.canvas.parentNode;
    if (container._pulses) {
        container._pulses.forEach(el => el.remove());
    }
    container._pulses = [];

    state.charts.tail = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '出现次数',
                    data: freqValues,
                    backgroundColor: 'rgba(168, 85, 247, 0.7)',
                    borderRadius: 4,
                    order: 2,
                    yAxisID: 'y'
                },
                {
                    label: '当前连续遗漏',
                    data: omissionValues,
                    type: 'line',
                    borderColor: '#ef4444',
                    borderWidth: 2,
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    pointBackgroundColor: '#ef4444',
                    pointBorderColor: '#fff',
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    tension: 0.3,
                    order: 1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    labels: { color: '#e5e7eb' }
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    titleColor: '#a855f7',
                    borderColor: 'rgba(168, 85, 247, 0.3)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            if (context.datasetIndex === 0) {
                                label += context.raw + ' 次';
                            } else {
                                label += context.raw + ' 期';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#9ca3af' }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    title: { display: true, text: '出现频次', color: '#c084fc' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true,
                    grid: { drawOnChartArea: false },
                    title: { display: true, text: '当前遗漏期数', color: '#f87171' }
                }
            }
        },
        plugins: [{
            id: 'tailPulseOverlay',
            afterDraw: (chart) => {
                const maxVal = Math.max(...omissionValues);
                if (maxVal === 0) return;

                const metaBars = chart.getDatasetMeta(0); // get bars
                if (!metaBars || !metaBars.data) return;

                const parent = chart.canvas.parentNode;
                if (!parent._pulses) parent._pulses = [];

                let pulseIdx = 0;
                omissionValues.forEach((val, idx) => {
                    if (val === maxVal && metaBars.data[idx]) {
                        const bar = metaBars.data[idx];
                        let overlay = parent._pulses[pulseIdx];
                        if (!overlay) {
                            overlay = document.createElement('div');
                            overlay.className = 'bar-pulse';
                            overlay.style.position = 'absolute';
                            overlay.style.pointerEvents = 'none';
                            overlay.style.zIndex = '10';
                            parent.appendChild(overlay);
                            parent._pulses.push(overlay);
                        }

                        const width = bar.width;
                        const height = Math.abs(bar.base - bar.y);
                        const left = chart.canvas.offsetLeft + bar.x - width / 2;
                        const top = chart.canvas.offsetTop + Math.min(bar.y, bar.base);

                        if (bar.x >= 0 && bar.x <= chart.width) {
                            overlay.style.left = left + 'px';
                            overlay.style.top = top + 'px';
                            overlay.style.width = width + 'px';
                            overlay.style.height = height + 'px';
                            overlay.style.borderRadius = '4px';
                            overlay.style.display = 'block';
                        } else {
                            overlay.style.display = 'none';
                        }
                        pulseIdx++;
                    }
                });

                for (let i = pulseIdx; i < parent._pulses.length; i++) {
                    parent._pulses[i].style.display = 'none';
                }
            }
        }]
    });
}

// ===== 连号对数分布 =====
function renderConsecutiveChart(consecutive) {
    const ctx = document.getElementById('chart-consecutive').getContext('2d');

    const dist = consecutive.pairs_distribution;
    const labels = Object.keys(dist).map(n => n === '0' ? '无连号' : `${n}组连号`);
    const values = Object.values(dist);

    const palette = [
        'rgba(59, 130, 246, 0.7)',
        'rgba(245, 200, 66, 0.7)',
        'rgba(239, 68, 68, 0.7)',
        'rgba(34, 197, 94, 0.7)',
        'rgba(168, 85, 247, 0.7)',
        'rgba(6, 182, 212, 0.7)',
    ];

    if (state.charts.consecutive) state.charts.consecutive.destroy();

    state.charts.consecutive = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '期数',
                data: values,
                backgroundColor: palette.slice(0, values.length),
                borderRadius: 6,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    cornerRadius: 8,
                    callbacks: {
                        label: function (ctx) {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((ctx.parsed.y / total) * 100).toFixed(1);
                            return `${ctx.parsed.y}期 (${pct}%)`;
                        }
                    }
                }
            },
            scales: {
                x: { grid: { display: false } },
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' } }
            }
        }
    });
}
// ===== 贝叶斯推断模型 =====
function renderBayesianChart(bayesianData) {
    const canvas = document.getElementById('chart-bayesian');
    if (!canvas || !bayesianData || bayesianData.length === 0) return;
    const ctx = canvas.getContext('2d');

    const isWeilitsai = state.lotteryType === 'weilitsai';
    const titleEl = canvas.closest('.chart-card')?.querySelector('.chart-title');
    if (titleEl) {
        titleEl.textContent = isWeilitsai ? '⚖️ 1区号码贝叶斯后验反弹图' : '⚖️ 贝叶斯遗漏反弹推测';
    }
    const descEl = canvas.closest('.chart-card')?.querySelector('p');
    if (descEl) {
        descEl.innerHTML = isWeilitsai
            ? `<strong class="text-blue-400">【动态概率更新】</strong>结合历史号码先验概率，利用1区号码最新遗漏极值作为证据，修正后验分布。推算1区号码在下期“触底反弹”的条件概率权重。`
            : `<strong class="text-blue-400">【动态概率更新】</strong>结合历史基础概率（先验），利用最新遗漏极值（新证据）不断修正后验概率。推算生肖在下期“触底反弹”的条件概率权重。`;
    }

    const labels = bayesianData.map(d => d.number !== undefined ? d.number.toString() : d.zodiac);
    const posteriorData = bayesianData.map(d => d.posterior);
    const omissionData = bayesianData.map(d => d.omission);

    if (state.charts.bayesian) state.charts.bayesian.destroy();

    state.charts.bayesian = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '后验反弹权重',
                    data: posteriorData,
                    backgroundColor: 'rgba(59, 130, 246, 0.7)', // 蓝色
                    borderRadius: 4,
                    yAxisID: 'y'
                },
                {
                    label: '当前连续遗漏期数',
                    data: omissionData,
                    type: 'line',
                    borderColor: 'rgba(239, 68, 68, 0.8)', // 红色
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    borderWidth: 2,
                    pointStyle: 'circle',
                    pointRadius: 4,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    labels: { color: '#e5e7eb' }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            if (context.datasetIndex === 0) {
                                label += context.raw + ' (权重)';
                            } else {
                                label += context.raw + ' 期';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9ca3af' }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    title: { display: true, text: '反弹权重', color: '#60a5fa' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    title: { display: true, text: '遗漏期数', color: '#f87171' }
                }
            }
        }
    });
}

function renderFiveElementsChart(fiveData) {
    const canvas = document.getElementById('chart-five-elements');
    if (!canvas || !fiveData || !fiveData.chi_square) return;
    const ctx = canvas.getContext('2d');

    const items = fiveData.chi_square.items || [];
    const labels = items.map(i => i.element);
    const observed = items.map(i => i.observed);
    const expected = items.map(i => i.expected);

    if (state.charts.fiveElements) state.charts.fiveElements.destroy();

    state.charts.fiveElements = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: '实际频数',
                    data: observed,
                    backgroundColor: ['rgba(245,158,11,.75)', 'rgba(16,185,129,.75)', 'rgba(6,182,212,.75)', 'rgba(249,115,22,.75)', 'rgba(161,98,7,.75)'],
                    borderRadius: 6
                },
                {
                    label: '理论期望',
                    data: expected,
                    type: 'line',
                    borderColor: 'rgba(226,232,240,.9)',
                    backgroundColor: 'rgba(226,232,240,.18)',
                    borderWidth: 2,
                    tension: 0.25,
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#e5e7eb' } },
                tooltip: {
                    callbacks: {
                        footer: () => `卡方值 ${fiveData.chi_square.stat} | p=${fiveData.chi_square.p_value}`
                    }
                }
            },
            scales: {
                x: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,.05)' } },
                y: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,.05)' } }
            }
        }
    });

    const summaryEl = document.getElementById('five-elements-summary');
    if (summaryEl) {
        const chi = fiveData.chi_square || {};
        const apriori = fiveData.apriori || {};
        const poisson = fiveData.poisson || {};
        summaryEl.innerHTML = `
            <div class="glass" style="padding:12px; border-radius:12px;">
                <div style="font-size:.75rem; color:#94a3b8;">卡方检验</div>
                <div style="font-size:1rem; font-weight:800; color:#f8fafc; margin-top:4px;">${chi.headline || '样本不足'}</div>
                <div style="font-size:.78rem; color:${chi.significant ? '#fca5a5' : '#86efac'}; margin-top:6px;">χ²=${chi.stat || 0} ｜ p=${chi.p_value || 0}</div>
            </div>
            <div class="glass" style="padding:12px; border-radius:12px;">
                <div style="font-size:.75rem; color:#94a3b8;">Apriori 关联</div>
                <div style="font-size:1rem; font-weight:800; color:#f8fafc; margin-top:4px;">${apriori.headline || '样本不足'}</div>
                <div style="font-size:.78rem; color:#cbd5e1; margin-top:6px;">验证五行相生相克是否真实存在</div>
            </div>
            <div class="glass" style="padding:12px; border-radius:12px;">
                <div style="font-size:.75rem; color:#94a3b8;">泊松遗漏</div>
                <div style="font-size:1rem; font-weight:800; color:#f8fafc; margin-top:4px;">${poisson.headline || '样本不足'}</div>
                <div style="font-size:.78rem; color:#cbd5e1; margin-top:6px;">关注极端遗漏后的均值回归拐点</div>
            </div>
        `;
    }

    const rulesEl = document.getElementById('five-elements-rules');
    if (rulesEl) {
        const rules = (fiveData.apriori && fiveData.apriori.rules) || [];
        const poissonItems = (fiveData.poisson && fiveData.poisson.items) || [];
        const topRules = rules.slice(0, 3).map(r =>
            `<div style="padding:10px 12px; border-radius:10px; background:rgba(15,23,42,.45); border:1px solid rgba(148,163,184,.16); margin-bottom:8px; color:#cbd5e1;">
                <strong style="color:#f8fafc;">${r.from} → ${r.to}</strong> ｜ 支持度 ${r.support}% ｜ 置信度 ${r.confidence}% ｜ Lift ${r.lift}
            </div>`
        ).join('');
        const topPoisson = poissonItems.slice(0, 2).map(r =>
            `<div style="padding:10px 12px; border-radius:10px; background:rgba(15,23,42,.45); border:1px solid rgba(148,163,184,.16); margin-bottom:8px; color:#cbd5e1;">
                <strong style="color:#f8fafc;">${r.element}</strong> ｜ 当前遗漏 ${r.current_gap} 期 ｜ 10期内零出现概率 ${r.p0_next_10}% ｜ ${r.hint}
            </div>`
        ).join('');
        rulesEl.innerHTML = `
            <div style="font-size:.8rem; color:#94a3b8; margin-bottom:8px;">五行关联 / 泊松窗口</div>
            ${topRules}${topPoisson}
        `;
    }

    const heatmapEl = document.getElementById('five-elements-heatmap');
    if (heatmapEl) {
        const matrix = (fiveData.apriori && fiveData.apriori.matrix) || [];
        const colHead = matrix[0]?.items?.map(item => `<th style="padding:8px; color:#cbd5e1; font-weight:700;">${item.to}</th>`).join('') || '';
        const rows = matrix.map(row => {
            const cells = row.items.map(item => {
                const alpha = Math.min(0.9, Math.max(0.08, item.confidence / 100));
                return `<td style="padding:8px; text-align:center; background:rgba(168,85,247,${alpha}); color:#f8fafc; border:1px solid rgba(255,255,255,.06); border-radius:8px;">${item.confidence}%</td>`;
            }).join('');
            return `<tr><th style="padding:8px; color:#e2e8f0; font-weight:700; text-align:left;">${row.from}</th>${cells}</tr>`;
        }).join('');
        heatmapEl.innerHTML = `
            <div style="font-size:.8rem; color:#94a3b8; margin-bottom:8px;">五行转移热力图（上期 → 下期）</div>
            <div style="overflow:auto; border-radius:12px; border:1px solid rgba(148,163,184,.14); background:rgba(15,23,42,.34); padding:10px;">
                <table style="width:100%; min-width:min(100%, 420px); border-collapse:separate; border-spacing:6px;">
                    <thead><tr><th></th>${colHead}</tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        `;
    }

    const omissionEl = document.getElementById('five-elements-omission');
    if (omissionEl) {
        const items = (fiveData.poisson && fiveData.poisson.items) || [];
        omissionEl.innerHTML = `
            <div style="font-size:.8rem; color:#94a3b8; margin-bottom:8px;">五行遗漏排行</div>
            ${items.map((item, idx) => {
            const bar = Math.max(8, Math.min(100, 100 - item.gap_tail_prob));
            return `<div style="padding:10px 12px; border-radius:10px; background:rgba(15,23,42,.45); border:1px solid rgba(148,163,184,.16); margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; gap:10px; align-items:center; margin-bottom:6px;">
                        <strong style="color:#f8fafc;">#${idx + 1} ${item.element}</strong>
                        <span style="font-size:.78rem; color:#cbd5e1;">遗漏 ${item.current_gap} 期 ｜ λ10=${item.lambda_10}</span>
                    </div>
                    <div style="height:8px; border-radius:999px; background:rgba(255,255,255,.06); overflow:hidden; margin-bottom:6px;">
                        <div style="width:${bar}%; height:100%; background:linear-gradient(90deg,#f59e0b,#ef4444);"></div>
                    </div>
                    <div style="font-size:.78rem; color:#94a3b8;">零出现概率 ${item.p0_next_10}% ｜ 尾部概率 ${item.gap_tail_prob}% ｜ ${item.hint}</div>
                </div>`;
        }).join('')}
        `;
    }

    const ballsEl = document.getElementById('five-elements-balls');
    if (ballsEl) {
        const map = fiveData.number_balls || {};
        const ballRows = Object.entries(map).map(([element, nums]) => {
            const balls = nums.map((num) => {
                const colorHex = getBallColorHex(num);
                const darkColor = colorHex === '#ef4444' ? '#d30000' : (colorHex === '#3b82f6' ? '#0055d3' : '#00a83b');
                return `<span style="display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px; border-radius:50%; background:radial-gradient(circle at 30% 30%, ${colorHex}, ${darkColor}); color:#fff; font-weight:900; font-size:.84rem; box-shadow:0 3px 8px rgba(0,0,0,.32); border:2px solid rgba(255,255,255,.3); text-shadow:1px 1px 0 rgba(0,0,0,.45);">${String(num).padStart(2, '0')}</span>`;
            }).join('');
            return `<div style="padding:10px 12px; border-radius:10px; background:rgba(15,23,42,.45); border:1px solid rgba(148,163,184,.16); margin-bottom:8px;">
                <div style="font-size:.84rem; font-weight:700; color:#f8fafc; margin-bottom:8px;">${element}</div>
                <div style="display:flex; flex-wrap:wrap; gap:8px;">${balls}</div>
            </div>`;
        }).join('');
        ballsEl.innerHTML = `
            <div style="font-size:.8rem; color:#94a3b8; margin-bottom:8px;">五行数字彩球映射</div>
            ${ballRows}
        `;
    }
}

// ===== LSTM 深度学习模型 =====
function renderLSTMChart(lstmData) {
    const canvas = document.getElementById('chart-lstm');
    if (!canvas || !lstmData || lstmData.length === 0) return;
    const ctx = canvas.getContext('2d');

    const isWeilitsai = state.lotteryType === 'weilitsai';
    const titleEl = canvas.closest('.chart-card')?.querySelector('.chart-title');
    if (titleEl) {
        titleEl.textContent = isWeilitsai ? '🧠 1区号码神经网络 (MLP) 拟合图' : '🧠 LSTM 时序模拟与网络拟合度';
    }
    const descEl = canvas.closest('.chart-card')?.querySelector('p');
    if (descEl) {
        descEl.innerHTML = isWeilitsai 
            ? `<strong class="text-green-400">【非线性模式挖掘】</strong>将1区38个号码的频次与遗漏特征放入多层感知机网络进行特征拟合，预测下期开出倾向。<strong>局限性说明：</strong>纯随机噪音下，模型极易发生“过拟合”从而导致推演失效。`
            : `<strong class="text-green-400">【非线性模式挖掘】</strong>将生肖走势放入时间序列网络，寻找肉眼难辨的复杂周期。<strong>局限性说明：</strong>遇到纯随机噪音时，模型极易发生“过拟合”从而导致推演失效。`;
    }

    const labels = lstmData.map(d => d.number !== undefined ? d.number.toString() : d.zodiac);
    const scoreData = lstmData.map(d => d.score);
    const signalData = lstmData.map(d => d.signal);

    const pointColors = scoreData.map(score => {
        if (score >= 80) return 'rgba(16, 185, 129, 0.9)'; // 绿
        if (score >= 40) return 'rgba(245, 158, 11, 0.9)'; // 黄
        return 'rgba(239, 68, 68, 0.9)'; // 红
    });

    if (state.charts.lstm) state.charts.lstm.destroy();

    state.charts.lstm = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '网络拟合得分',
                data: scoreData,
                borderColor: 'rgba(168, 85, 247, 0.8)', // 紫色
                backgroundColor: 'rgba(168, 85, 247, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: pointColors,
                pointBorderColor: '#fff',
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            const idx = ctx.dataIndex;
                            return [`拟合得分: ${ctx.raw}`, `AI操作信号: 【${signalData[idx]}】`];
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9ca3af', font: { size: 13, weight: 'bold' } }
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9ca3af' },
                    title: { display: true, text: 'LSTM 拟合分值(0-100)', color: '#c084fc' }
                }
            }
        }
    });
}

// ==================== 模拟开奖 ====================
function initSimulator() {
    const btnSimulate = document.getElementById('btn-simulate');
    const countInput = document.getElementById('sim-count');
    const minusBtn = document.getElementById('sim-count-minus');
    const plusBtn = document.getElementById('sim-count-plus');

    if (!btnSimulate || !countInput || !minusBtn || !plusBtn) return;

    btnSimulate.addEventListener('click', runSimulation);

    minusBtn.addEventListener('click', () => {
        const current = parseInt(countInput.value) || 1;
        countInput.value = Math.max(1, current - 1);
    });

    plusBtn.addEventListener('click', () => {
        const current = parseInt(countInput.value) || 1;
        countInput.value = Math.min(1000, current + 1);
    });
}

async function runSimulation() {
    const count = parseInt(document.getElementById('sim-count').value) || 1;
    const btn = document.getElementById('btn-simulate');
    const btnText = btn.querySelector('.btn-text');
    const btnLoading = btn.querySelector('.btn-loading');

    // 按钮禁用状态
    btn.disabled = true;
    btnText.style.display = 'none';
    btnLoading.style.display = 'inline';

    // 隐藏之前的结果
    document.getElementById('sim-single-result').style.display = 'none';
    document.getElementById('sim-batch-result').style.display = 'none';

    // 显示动画
    const animationEl = document.getElementById('sim-animation');
    animationEl.style.display = 'block';

    // 重置球状态
    const balls = animationEl.querySelectorAll('.lottery-ball');
    balls.forEach(ball => {
        ball.textContent = '?';
        ball.classList.add('rolling');
        ball.classList.remove('revealed');
    });

    try {
        const response = await apiFetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: count, type: state.lotteryType })
        });
        const result = await response.json();

        if (result.success) {
            // 等待动画效果
            await new Promise(resolve => setTimeout(resolve, 1500));

            if (count === 1) {
                // 单期结果：逐个揭晓动画
                const draw = result.data.draws[0];
                await revealBalls(draw, balls);
                showSingleResult(draw);
            } else {
                // 批量结果
                animationEl.style.display = 'none';
                showBatchResult(result.data);
            }
        }
    } catch (error) {
        console.error('模拟请求失败:', error);
    } finally {
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
    }
}

async function revealBalls(draw, balls) {
    // 仅揭晓特码动画
    await new Promise(resolve => setTimeout(resolve, 800));
    const specialBall = balls[0];
    specialBall.classList.remove('rolling');
    specialBall.classList.add('revealed');
    specialBall.textContent = draw.special_num;

    await new Promise(resolve => setTimeout(resolve, 300));
}

function showSingleResult(draw) {
    const container = document.getElementById('result-balls');

    let html = '';

    html += `
        <div class="ball-wrapper" style="margin: 0 4px;">
            <div class="result-ball special">${draw.special_num}</div>
            ${draw.special_zodiac ? `<div class="zodiac-label" style="font-size: 0.8rem">${draw.special_zodiac}</div>` : ''}
        </div>
    `;

    container.innerHTML = html;
    document.getElementById('sim-single-result').style.display = 'block';
}

function showBatchResult(data) {
    // 统计摘要
    const summaryContainer = document.getElementById('batch-summary');
    const summary = data.summary;

    summaryContainer.innerHTML = `
        <div class="batch-stat">
            <div class="label">总模拟期数</div>
            <div class="value">${summary.total_draws}</div>
        </div>
        <div class="batch-stat">
            <div class="label">特码单双比</div>
            <div class="value">${summary.odd_even_ratio}</div>
        </div>
        <div class="batch-stat">
            <div class="label">特码大小比</div>
            <div class="value">${summary.big_small_ratio}</div>
        </div>
    `;

    // 显示最近 20 期
    const listContainer = document.getElementById('batch-draws-list');
    const showDraws = data.draws.slice(0, 20);

    listContainer.innerHTML = showDraws.map((draw, i) => {
        // Removed numsHtml as regular numbers are no longer displayed
        let specialHtml = `
            <div class="ball-wrapper" style="margin: 0 2px;">
                <div class="batch-ball special">${draw.special_num}</div>
                ${draw.special_zodiac ? `<div class="zodiac-label" style="font-size: 0.75rem">${draw.special_zodiac}</div>` : ''}
            </div>
        `;

        return `
            <div class="batch-draw-item">
                <span class="batch-draw-index">第${i + 1}期</span>
                <div class="batch-numbers" style="align-items: flex-start;">
                    ${specialHtml}
                </div>
            </div>
        `;
    }).join('');

    document.getElementById('sim-batch-result').style.display = 'block';
}

// ==================== 历史记录 ====================

let historySubTab = 'draw'; // 'draw' or 'ai'

function switchHistoryTab(tab) {
    historySubTab = tab;
    document.getElementById('btn-history-draw').classList.toggle('active', tab === 'draw');
    document.getElementById('btn-history-ai').classList.toggle('active', tab === 'ai');
    document.getElementById('history-draw-section').style.display = tab === 'draw' ? 'block' : 'none';
    document.getElementById('history-ai-section').style.display = tab === 'ai' ? 'block' : 'none';

    if (tab === 'draw') {
        loadHistory(state.historyPage || 1);
    } else {
        loadAIHistory(state.aiHistoryPage || 1);
    }
}

async function loadHistory(page) {
    try {
        const response = await fetch(`/api/history?page=${page}&per_page=20&type=${state.lotteryType}`);
        const result = await response.json();

        if (result.success) {
            renderHistory(result.data);
            state.historyPage = page;
            state.historyTotalPages = result.data.total_pages;
        }
    } catch (error) {
        console.error('加载历史记录失败:', error);
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
function renderBallsHtml(numbers, zodiacs, specialNum, specialZodiac, extraClass = '') {
    let html = '';
    
    // Add Zone 1 Label if Weilitsai
    if (state.lotteryType === 'weilitsai') {
        html += `<div style="display:inline-flex;flex-direction:column;align-items:center;margin-right:10px;"><span style="font-size:0.8rem;color:#888;">第一區 (Zone 1)</span></div>`;
    }
    
    numbers.forEach((n, i) => {
        const colorClass = getBallColorClass(n, 1);
        const zLabel = zodiacs && zodiacs[i] ? zodiacs[i] : '';
        html += `<div style="display:inline-flex;flex-direction:column;align-items:center;">
            <span class="ball-zodiac" style="margin-bottom: 4px; font-size: 0.8rem;${zLabel ? '' : ' height: 1.2rem;'}">${zLabel}</span>
            <div class="lottery-ball ${colorClass} ${extraClass}" style="animation-delay:${i * 0.1}s">${n}</div>
        </div>`;
    });
    html += `<div class="ball-divider" style="padding-top: 1.2rem;">+</div>`;
    
    // Add Zone 2 Label if Weilitsai
    if (state.lotteryType === 'weilitsai') {
        html += `<div style="display:inline-flex;flex-direction:column;align-items:center;margin-right:10px;"><span style="font-size:0.8rem;color:#888;">第二區 (Zone 2)</span></div>`;
    }
    
    const spColorClass = getBallColorClass(specialNum, 2);
    const spZLabel = specialZodiac || '';
    html += `<div style="display:inline-flex;flex-direction:column;align-items:center;">
        <span class="ball-zodiac" style="margin-bottom: 4px; font-size: 0.8rem; color: #facc15; font-weight: bold;${spZLabel ? '' : ' height: 1.2rem;'}">${spZLabel}</span>
        <div class="lottery-ball ${spColorClass} ${extraClass}">${specialNum}</div>
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
        
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: state.lotteryType,
                mode: 'ai',
                dimensions: dims,
                count: count
            })
        });
        const json = await res.json();

        document.getElementById('sim-animation').style.display = 'none';

            if (isWheeling) {
                // Wheeling System 批量结果
                if (json.success && json.data && json.data.draws) {
                    const data = json.data;
                    document.getElementById('sim-batch-result').style.display = 'block';
                    
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
                                <span class="draw-idx">组合 ${i + 1}</span>
                                <div class="draw-balls">
                                    ${renderBallsHtml(d.numbers, d.zodiacs, d.special_num, d.special_zodiac, classSpecial)}
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
async function fetchProviderModels() {
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

async function loadSettings() {
    try {
        const titleEl = document.querySelector('.settings-header h2');
        if (titleEl) {
            titleEl.textContent = state.lotteryType === 'weilitsai' ? '⚙️ 系统设置 (威力彩)' : '⚙️ 系统设置 (新澳门六合彩)';
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

        const payload = {
            ai: {
                platform: activePlatform,
                model: activeModel,
                custom_platforms: settingsCustomPlatforms.slice(),
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
                    ${renderBallsHtml(ai.numbers, ai.zodiacs, ai.special_num, ai.special_zodiac, 'ai-ball')}
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
                            <div style="display: flex; gap: 6px;">
                                <button class="btn-sync" style="flex: 1; background: rgba(34, 197, 94, 0.1); color: #86efac; border-color: rgba(34, 197, 94, 0.2); font-size: 0.7rem; padding: 6px; border-radius: 6px;" onclick="shareAICard(this)">📤 分享图片</button>
                                <button class="btn-sync" style="flex: 1; background: rgba(239, 68, 68, 0.1); color: #fca5a5; border-color: rgba(239, 68, 68, 0.2); font-size: 0.7rem; padding: 6px; border-radius: 6px;" onclick="deleteAIHistory(${item.id})">🗑️ 删除档案</button>
                            </div>
                        </div>

                        <!-- 预测球/排名 -->
                        ${ballsHTML}

                        <!-- 分析维度标签块 -->
                        <div style="padding: 16px; background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px dashed rgba(255,255,255,0.08);">
                            <div style="font-size: 0.7rem; color: #6b7280; margin-bottom: 12px; letter-spacing: 0.5px; text-transform: uppercase; font-weight: 700; display: flex; align-items: center; gap: 5px;">
                                <span style="width: 3px; height: 10px; background: #a855f7; border-radius: 2px;"></span> 核心参考基准
                            </div>
                            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                                ${(item.dimensions || ['默认维度']).map(function (d) {
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
            var icon = dimIcons[d] || '📌';
            var label = dimNames[d] || d;
            return '<div style="display: inline-flex; align-items: center; gap: 4px; padding: 4px 8px; background: rgba(168,85,247,0.06); border: 1px solid rgba(168,85,247,0.15); border-radius: 5px; font-size: 0.7rem; color: #c4b5fd; white-space: nowrap;">' + icon + ' ' + label + '</div>';
        }).join('')}
                            </div>
                        </div>
                    </div>

                    <!-- 推理文字区 -->
                    <div class="ai-card-main">
                        <div class="ai-card-analysis">
                            ${ai.analysis || '无有效推断文字'}
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
