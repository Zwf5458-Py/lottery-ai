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

// ==================== Chart.js 全局配置 ====================
if (typeof Chart !== 'undefined') {
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.06)';
    Chart.defaults.font.family = "'Inter', 'Noto Sans SC', sans-serif";
}

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


