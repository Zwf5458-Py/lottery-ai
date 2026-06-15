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

