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


