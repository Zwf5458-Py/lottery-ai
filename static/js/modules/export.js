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

