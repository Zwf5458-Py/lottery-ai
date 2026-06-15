// 基础通用图表：冷热、单双、大小、尾号等

function renderFrequencyChart(frequency, bayesian, markov) {
    if (!frequency) return;
    const ctx = document.getElementById('chart-frequency').getContext('2d');

    const labels = Object.keys(frequency).map(n => n + '号');
    const values = Object.values(frequency);
    const maxVal = Math.max(...values);
    const minVal = Math.min(...values);

    const colors = values.map(v => {
        const ratio = (v - minVal) / (maxVal - minVal || 1);
        if (ratio > 0.7) return 'rgba(239, 68, 68, 0.8)';
        if (ratio > 0.4) return 'rgba(245, 200, 66, 0.8)';
        return 'rgba(59, 130, 246, 0.8)';
    });

    // 提取贝叶斯和马尔可夫的高频预测号码
    let predictedNums = new Set();
    if (bayesian && Array.isArray(bayesian)) {
        bayesian.slice(0, 3).forEach(b => predictedNums.add(b.number.toString()));
    }
    if (markov && markov.weights) {
        const sortedMarkov = Object.entries(markov.weights).sort((a, b) => b[1] - a[1]);
        sortedMarkov.slice(0, 3).forEach(m => predictedNums.add(m[0].toString()));
    }

    // 动态注入闪烁动画的 CSS
    if (!document.getElementById('star-blink-style')) {
        const style = document.createElement('style');
        style.id = 'star-blink-style';
        style.innerHTML = `@keyframes star-blink { 
            0% { opacity: 0.3; transform: translate(-50%, -50%) scale(0.8); filter: drop-shadow(0 0 2px rgba(255,215,0,0.5)); } 
            100% { opacity: 1; transform: translate(-50%, -50%) scale(1.3); filter: drop-shadow(0 0 8px rgba(255,215,0,1)); } 
        }`;
        document.head.appendChild(style);
    }

    const legendEl = document.getElementById('frequency-legend');
    if (legendEl) {
        legendEl.style.display = predictedNums.size > 0 ? 'inline-block' : 'none';
    }

    if (state.charts.frequency) state.charts.frequency.destroy();

    state.charts.frequency = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    type: 'bar',
                    label: '出现次数',
                    data: values,
                    backgroundColor: colors,
                    borderRadius: 3,
                    borderSkipped: false,
                }
            ]
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
        },
        plugins: [{
            id: 'htmlStars',
            afterRender(chart) {
                const container = chart.canvas.parentElement;
                container.style.position = 'relative';
                container.querySelectorAll('.blink-star').forEach(el => el.remove());
                
                const meta = chart.getDatasetMeta(0);
                if (!meta.data) return;
                
                const freqKeys = Object.keys(frequency);
                meta.data.forEach((bar, idx) => {
                    const n = freqKeys[idx];
                    if (predictedNums.has(n.toString())) {
                        const pt = bar.tooltipPosition();
                        const star = document.createElement('div');
                        star.className = 'blink-star';
                        star.innerHTML = '✨';
                        star.style.position = 'absolute';
                        star.style.left = pt.x + 'px';
                        star.style.top = (pt.y - 18) + 'px';
                        star.style.transform = 'translate(-50%, -50%)';
                        star.style.fontSize = '18px';
                        star.style.pointerEvents = 'none';
                        star.style.zIndex = '10';
                        star.style.animation = 'star-blink 0.6s infinite alternate ease-in-out';
                        container.appendChild(star);
                    }
                });
            }
        }]
    });
}


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
