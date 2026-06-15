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

