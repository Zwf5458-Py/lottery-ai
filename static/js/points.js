const state = {
    ledgerPage: 1,
    rechargePage: 1,
    pageSize: 10,
    ledgerTotalPages: 0,
    rechargeTotalPages: 0,
    loading: false
};

const reasonTextMap = {
    signup_bonus: '注册奖励',
    recharge: '充值到账',
    ai_simulation: 'AI 模拟扣费',
    settings_change: '设置变更扣费',
    share_reward_recharge: '推荐充值奖励',
    share_reward_vip: '推荐 VIP 奖励'
};

document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    loadReferralCode();
    loadPointsCenter();
});

function bindEvents() {
    document.getElementById('ledger-prev').addEventListener('click', () => {
        if (state.ledgerPage > 1) {
            state.ledgerPage -= 1;
            loadPointsCenter();
        }
    });
    document.getElementById('ledger-next').addEventListener('click', () => {
        if (state.ledgerPage < state.ledgerTotalPages) {
            state.ledgerPage += 1;
            loadPointsCenter();
        }
    });
    document.getElementById('recharge-prev').addEventListener('click', () => {
        if (state.rechargePage > 1) {
            state.rechargePage -= 1;
            loadPointsCenter();
        }
    });
    document.getElementById('recharge-next').addEventListener('click', () => {
        if (state.rechargePage < state.rechargeTotalPages) {
            state.rechargePage += 1;
            loadPointsCenter();
        }
    });
}

async function apiFetch(url, options = {}) {
    const res = await fetch(url, options);
    if (res.status === 401) {
        window.location.href = '/login';
        throw new Error('需要登录');
    }
    return res;
}

async function loadReferralCode() {
    try {
        const res = await apiFetch('/api/account/referral');
        const result = await res.json();
        if (result.success) {
            document.getElementById('ref-code').textContent = result.referral_code || '暂无';
        }
    } catch (_e) {
        document.getElementById('ref-code').textContent = '加载失败';
    }
}

async function loadPointsCenter() {
    if (state.loading) return;
    state.loading = true;
    showError('');

    renderLedgerLoading();
    renderRechargeLoading();

    try {
        const query = new URLSearchParams({
            ledger_page: String(state.ledgerPage),
            ledger_page_size: String(state.pageSize),
            recharge_page: String(state.rechargePage),
            recharge_page_size: String(state.pageSize)
        });

        const response = await apiFetch(`/api/account/points-center?${query.toString()}`);
        const result = await response.json();
        if (!result.success) {
            throw new Error(result.error || '加载失败');
        }

        const data = result.data || {};
        document.getElementById('points-balance').textContent = formatNum(data.points_balance || 0);

        renderLedger(data.points_ledger || [], data.points_ledger_pagination || {});
        renderRecharges(data.recharges || [], data.recharges_pagination || {});
    } catch (e) {
        showError(e.message || '加载失败，请稍后重试');
        renderLedgerEmpty('加载失败');
        renderRechargeEmpty('加载失败');
    } finally {
        state.loading = false;
    }
}

function renderLedgerLoading() {
    const body = document.getElementById('ledger-body');
    body.innerHTML = '<tr><td colspan="5" class="muted">正在加载积分流水...</td></tr>';
}

function renderRechargeLoading() {
    const body = document.getElementById('recharge-body');
    body.innerHTML = '<tr><td colspan="3" class="muted">正在加载充值记录...</td></tr>';
}

function renderLedgerEmpty(text) {
    const body = document.getElementById('ledger-body');
    body.innerHTML = `<tr><td colspan="5" class="muted">${escapeHtml(text)}</td></tr>`;
}

function renderRechargeEmpty(text) {
    const body = document.getElementById('recharge-body');
    body.innerHTML = `<tr><td colspan="3" class="muted">${escapeHtml(text)}</td></tr>`;
}

function renderLedger(items, pagination) {
    const body = document.getElementById('ledger-body');
    if (!items.length) {
        renderLedgerEmpty('暂无积分流水');
    } else {
        body.innerHTML = items.map((item) => {
            const amount = Number(item.change_amount || 0);
            const amountClass = amount >= 0 ? 'points-pos' : 'points-neg';
            const amountText = amount >= 0 ? `+${amount}` : `${amount}`;
            const reason = reasonTextMap[item.reason] || item.reason || '-';
            return `
                <tr>
                    <td>${escapeHtml(formatTime(item.created_at))}</td>
                    <td class="${amountClass}">${escapeHtml(amountText)}</td>
                    <td>${escapeHtml(formatNum(item.balance || 0))}</td>
                    <td>${escapeHtml(reason)}</td>
                    <td>${escapeHtml(item.meta || '-')}</td>
                </tr>
            `;
        }).join('');
    }

    state.ledgerPage = Math.max(1, Number(pagination.page || state.ledgerPage));
    state.ledgerTotalPages = Math.max(0, Number(pagination.total_pages || 0));
    document.getElementById('ledger-page-info').textContent = makePageInfo('流水', pagination);
    document.getElementById('ledger-prev').disabled = state.ledgerPage <= 1;
    document.getElementById('ledger-next').disabled = state.ledgerTotalPages === 0 || state.ledgerPage >= state.ledgerTotalPages;
}

function renderRecharges(items, pagination) {
    const body = document.getElementById('recharge-body');
    if (!items.length) {
        renderRechargeEmpty('暂无充值记录');
    } else {
        body.innerHTML = items.map((item) => `
            <tr>
                <td>${escapeHtml(formatTime(item.created_at))}</td>
                <td>${escapeHtml(Number(item.amount || 0).toFixed(2))}</td>
                <td class="points-pos">+${escapeHtml(formatNum(item.points || 0))}</td>
            </tr>
        `).join('');
    }

    state.rechargePage = Math.max(1, Number(pagination.page || state.rechargePage));
    state.rechargeTotalPages = Math.max(0, Number(pagination.total_pages || 0));
    document.getElementById('recharge-page-info').textContent = makePageInfo('充值', pagination);
    document.getElementById('recharge-prev').disabled = state.rechargePage <= 1;
    document.getElementById('recharge-next').disabled = state.rechargeTotalPages === 0 || state.rechargePage >= state.rechargeTotalPages;
}

function makePageInfo(label, pagination) {
    const page = Number(pagination.page || 1);
    const totalPages = Number(pagination.total_pages || 0);
    const total = Number(pagination.total || 0);
    if (!totalPages) {
        return `${label}：0 条`;
    }
    return `${label}：第 ${page}/${totalPages} 页，共 ${formatNum(total)} 条`;
}

function showError(text) {
    const el = document.getElementById('page-error');
    if (!text) {
        el.style.display = 'none';
        el.textContent = '';
        return;
    }
    el.style.display = 'block';
    el.textContent = text;
}

function formatNum(n) {
    return Number(n || 0).toLocaleString();
}

function formatTime(raw) {
    if (!raw) return '-';
    return String(raw).replace('T', ' ').slice(0, 19);
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
