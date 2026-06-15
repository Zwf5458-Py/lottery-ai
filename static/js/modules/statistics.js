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

