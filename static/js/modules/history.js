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


