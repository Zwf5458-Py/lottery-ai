/**
 * 前端核心模块 - 状态管理和工具函数
 */

const AppState = {
    lotteryType: 'macaujc2',
    currentTab: 'statistics',
    statisticsLoaded: false,
    historyPage: 1,
    historyTotalPages: 1,
    aiHistoryPage: 1,
    charts: {}
};

const AppUtils = {
    apiFetch: async function(url, options = {}) {
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
                if (typeof showCenterToast === 'function') {
                    showCenterToast('✨ ' + (data.error || '该功能仅 VIP 会员可用'), 'warn', true);
                }
            }
            throw new Error(data.error || '权限不足');
        }
        return res;
    },

    showCenterConfirm: function(message, title = '操作确认') {
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

            const onOverlayClick = (e) => { if (e.target === modal) close(false); };
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
    },

    ensureCenterConfirmModal: function() {
        if (window.centerConfirmModal) return window.centerConfirmModal;

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
        window.centerConfirmModal = overlay;
        return overlay;
    }
};

window.AppState = AppState;
window.AppUtils = AppUtils;
