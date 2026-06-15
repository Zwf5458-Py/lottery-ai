// 威力彩专属图表：一区预测概率、马尔可夫链、贝叶斯推断、LSTM模型等

function renderZ1ExclusiveChart(z1Data) {
    const ctx = document.getElementById('chart-z1-exclusive');
    if (!ctx) return;
    
    if (!z1Data || !z1Data.details) return;

    const labels = z1Data.details.map(d => d.number + '号');
    const values = z1Data.details.map(d => d.score);

    if (state.charts.z1Exclusive) state.charts.z1Exclusive.destroy();

    state.charts.z1Exclusive = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '关联得分',
                data: values,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.2)',
                borderWidth: 2,
                pointBackgroundColor: '#10b981',
                pointRadius: 4,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    titleColor: '#10b981',
                    borderColor: 'rgba(16, 185, 129, 0.3)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12
                }
            },
            scales: {
                x: {
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.04)' }
                }
            }
        }
    });
}

// ===== 第一区预测概率分布图 =====
function renderPredictProbChart(predictProb) {
    const ctx = document.getElementById('chart-predict-prob').getContext('2d');

    if (!predictProb || predictProb.length === 0) return;

    // 只展示概率最高的前 15 个号码
    const sorted = [...predictProb].sort((a, b) => b.probability - a.probability).slice(0, 15);

    const labels = sorted.map(item => `${item.number}号`);
    const values = sorted.map(item => item.probability);

    // 为不同状态的号码分配不同颜色：预警号码用红色，斜连邻号用黄色，普通号码用蓝色
    const backgroundColors = sorted.map(item => {
        if (item.is_alert) return 'rgba(239, 68, 68, 0.8)';
        if (item.is_neighbor) return 'rgba(245, 158, 11, 0.8)';
        return 'rgba(59, 130, 246, 0.8)';
    });

    if (state.charts.predictProb) state.charts.predictProb.destroy();

    state.charts.predictProb = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '下期推算概率 (%)',
                data: values,
                backgroundColor: backgroundColors,
                borderRadius: 3,
                borderSkipped: false
            }]
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
                    padding: 12,
                    callbacks: {
                        label: function (ctx) {
                            const idx = ctx.dataIndex;
                            const item = sorted[idx];
                            let extra = '';
                            if (item.is_alert) extra += ' (⚠️遗漏警报号)';
                            if (item.is_neighbor) extra += ' (邻近斜连号)';
                            return ` 推算概率: ${ctx.raw}%${extra}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: {
                        callback: function (value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

// ===== 冷热号排行 =====

function renderMarkovChart(markovData) {
    const canvas = document.getElementById('chart-markov-radar');
    if (!canvas || !markovData) return;

    const isWeilitsai = state.lotteryType === 'weilitsai';
    const parentCard = canvas.closest('.chart-card') || canvas.closest('.card');
    const titleEl = parentCard ? parentCard.querySelector('.chart-title') : null;
    if (titleEl) {
        titleEl.textContent = isWeilitsai ? '🕸️ 马尔可夫链 1区号码转移概率分布' : '🕸️ 马尔可夫链特码状态转移';
    }

    let mode = 'zodiac';
    if (isWeilitsai) {
        mode = 'number';
    } else {
        const modeEl = document.querySelector('input[name="markov_mode"]:checked');
        mode = modeEl ? modeEl.value : 'zodiac';
    }

    // 基础数据
    let targetDesc = '';
    let targetStr = '??';
    let weights = markovData.weights || {};
    let labels = [];
    let backgroundColors = [];
    let occurrences = weights._occurrences || {};

    if (isWeilitsai) {
        targetDesc = '1区正码';
        targetStr = '';
        labels = Array.from({length: 38}, (_, i) => (i + 1).toString());
        backgroundColors = labels.map(() => 'rgba(59, 130, 246, 0.7)');
    } else if (mode === 'zodiac') {
        targetDesc = markovData.target_zodiac || '未知';
        targetStr = markovData.target_num || '??';
        labels = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"];
    } else {
        targetDesc = markovData.target_color || '未知';
        targetStr = markovData.target_color || '??';
        weights = markovData.color_weights || {};
        labels = ["红波", "蓝波", "绿波"];
        occurrences = weights._occurrences || {};
    }

    const maxPeriods = weights.max_periods || 0;
    const periodStr = maxPeriods > 0 ? `近${maxPeriods}期` : '全历史数据';

    const descEl = parentCard ? parentCard.querySelector('p') : null;
    if (descEl) {
        descEl.innerHTML = `<span class="text-blue-400 font-bold">【概率推演】</span> 基于历史数据推演出真实的转移概率分布。${isWeilitsai ? '号码条形柱越突出，下一期开出倾向越强。' : '雷达轴越突出的维度，历史跃迁倾向越强。'}（统计基准：${periodStr}）`;
    }

    const values = labels.map(key => weights[key] || 1.0);
    const maxVal = Math.max(...values);

    const counts = labels.map(key => occurrences[key] || 0);
    const maxCount = Math.max(...counts);
    const avgCount = counts.length > 0 ? (counts.reduce((a, b) => a + b, 0) / counts.length) : 1;

    if (!isWeilitsai) {
        if (mode === 'zodiac') {
            backgroundColors = counts.map(count => {
                if (count === maxCount && count > avgCount * 1.2) return 'rgba(239, 68, 68, 0.7)';
                if (count > avgCount * 1.1) return 'rgba(245, 158, 11, 0.6)';
                if (count < avgCount * 0.7) return 'rgba(59, 130, 246, 0.4)';
                return 'rgba(156, 163, 175, 0.4)';
            });
        } else {
            backgroundColors = labels.map(colorName => {
                if (colorName === '红波') return 'rgba(239, 68, 68, 0.75)';
                if (colorName === '蓝波') return 'rgba(59, 130, 246, 0.75)';
                if (colorName === '绿波') return 'rgba(34, 197, 94, 0.75)';
                return 'rgba(156, 163, 175, 0.4)';
            });
        }
    }

    const radioContainer = parentCard ? parentCard.querySelector('.algorithm-toggle') : null;
    if (radioContainer) {
        radioContainer.style.display = isWeilitsai ? 'none' : '';
    }

    const chartWrapper = canvas.parentElement;
    chartWrapper.style.position = 'relative';
    chartWrapper.style.height = isWeilitsai ? '250px' : '360px';

    let layoutBox = chartWrapper.parentElement;
    if (!layoutBox.classList.contains('markov-layout-box')) {
        layoutBox = document.createElement('div');
        layoutBox.className = 'markov-layout-box';
        layoutBox.style.display = 'flex';
        layoutBox.style.alignItems = 'center';
        layoutBox.style.justifyContent = 'space-between';
        layoutBox.style.width = '100%';
        chartWrapper.parentNode.insertBefore(layoutBox, chartWrapper);
        layoutBox.appendChild(chartWrapper);
        chartWrapper.style.flexGrow = '1';
        chartWrapper.style.flexShrink = '1';
        chartWrapper.style.minWidth = '0';
    }

    const oldLegends = layoutBox.querySelectorAll('.custom-markov-legend');
    oldLegends.forEach(el => el.remove());

    const createLegendCol = (list, startIndex = 0) => {
        const col = document.createElement('div');
        col.className = 'custom-markov-legend';
        col.style.display = 'flex';
        col.style.flexDirection = 'column';
        col.style.gap = '10px';
        col.style.minWidth = mode === 'zodiac' ? '90px' : '70px';
        col.style.padding = '0 20px';

        list.forEach((key, index) => {
            const actualIdx = startIndex + index;
            const color = backgroundColors[actualIdx];
            const count = occurrences[key] || 0;
            const isMaxWeight = (weights[key] || 1.0) === maxVal;

            const item = document.createElement('div');
            item.style.display = 'flex';
            item.style.alignItems = 'center';
            item.style.fontSize = '0.9rem';
            item.style.color = '#e5e7eb';
            item.style.whiteSpace = 'nowrap';

            if (isMaxWeight) {
                item.className = 'pulse-glow';
                item.style.padding = '4px 8px';
                item.style.margin = '-4px -8px';
                item.style.borderRadius = '6px';
                item.style.backgroundColor = 'rgba(239, 68, 68, 0.15)';
                item.style.border = '1px solid rgba(239, 68, 68, 0.4)';
            }

            const box = document.createElement('span');
            box.style.display = 'inline-block';
            box.style.width = '14px';
            box.style.height = '14px';
            box.style.backgroundColor = color;
            box.style.marginRight = '8px';
            box.style.borderRadius = '3px';

            item.appendChild(box);
            item.appendChild(document.createTextNode(`${key}：${count}次`));
            col.appendChild(item);
        });
        return col;
    };

    if (!isWeilitsai) {
        if (mode === 'zodiac') {
            layoutBox.insertBefore(createLegendCol(labels.slice(0, 6), 0), chartWrapper);
            layoutBox.appendChild(createLegendCol(labels.slice(6, 12), 6));
        } else {
            layoutBox.insertBefore(createLegendCol(labels.slice(0, 2), 0), chartWrapper);
            layoutBox.appendChild(createLegendCol(labels.slice(2, 3), 2));
        }
    }

    const oldCenter = chartWrapper.querySelector('.markov-center-label');
    if (oldCenter) oldCenter.remove();

    if (!isWeilitsai && markovData.target_num) {
        const centerLabel = document.createElement('div');
        centerLabel.className = 'markov-center-label';
        centerLabel.style.position = 'absolute';
        centerLabel.style.top = '50%';
        centerLabel.style.left = '50%';
        centerLabel.style.transform = 'translate(-50%, -50%)';
        centerLabel.style.width = '56px';
        centerLabel.style.height = '56px';
        centerLabel.style.borderRadius = '50%';

        let centerBg = 'rgba(15, 23, 42, 0.95)';
        if (mode === 'color') {
            if (targetStr === '红波') centerBg = 'rgba(239, 68, 68, 0.85)';
            else if (targetStr === '蓝波') centerBg = 'rgba(59, 130, 246, 0.85)';
            else if (targetStr === '录波' || targetStr === '绿波') centerBg = 'rgba(34, 197, 94, 0.85)';
        }
        centerLabel.style.backgroundColor = centerBg;

        centerLabel.style.display = 'flex';
        centerLabel.style.alignItems = 'center';
        centerLabel.style.justifyContent = 'center';
        centerLabel.style.flexDirection = 'column';
        centerLabel.style.color = '#fff';
        centerLabel.style.border = '2px solid rgba(255, 255, 255, 0.15)';
        centerLabel.style.boxShadow = '0 4px 12px rgba(0,0,0,0.5)';
        centerLabel.style.zIndex = '99';
        centerLabel.style.pointerEvents = 'none';

        const centerText = mode === 'zodiac' ? targetStr : targetStr.replace('波', '');
        centerLabel.innerHTML = `
            <span class="mc-number" style="position: relative; z-index: 100; font-size: ${mode === 'color' ? '1.1rem' : '1.4rem'}; font-weight: bold; line-height: 1;">${centerText}</span>
        `;
        chartWrapper.appendChild(centerLabel);
    }

    if (state.charts.markov) state.charts.markov.destroy();

    state.charts.markov = new Chart(canvas, {
        type: isWeilitsai ? 'bar' : 'polarArea',
        data: {
            labels: labels,
            datasets: [{
                label: isWeilitsai ? '转移跃迁权重' : `上期开出【${targetDesc}】的跃迁权重`,
                data: values,
                backgroundColor: backgroundColors,
                borderWidth: 1,
                borderColor: 'rgba(255,255,255,0.1)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: 10 },
            scales: isWeilitsai ? {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9ca3af' }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9ca3af' },
                    min: 0.4,
                    max: 2.6
                }
            } : {
                r: {
                    angleLines: { color: 'rgba(255,255,255,0.05)' },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        display: false,
                        min: 0.4,
                        max: Math.max(2.6, maxVal + 0.6)
                    },
                    pointLabels: {
                        display: true,
                        centerPointLabels: true,
                        color: '#9ca3af',
                        font: { size: 12, weight: 'bold' },
                        padding: 15
                    }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: isWeilitsai,
                    external: isWeilitsai ? null : function (context) {
                        let tooltipEl = chartWrapper.querySelector('.markov-tooltip');
                        if (!tooltipEl) {
                            tooltipEl = document.createElement('div');
                            tooltipEl.className = 'markov-tooltip';
                            tooltipEl.style.cssText = 'position:absolute; z-index:50; pointer-events:none; background:rgba(0,0,0,0.85); color:#fff; padding:6px 10px; border-radius:6px; font-size:0.8rem; white-space:nowrap; transition:opacity 0.15s; opacity:0;';
                            chartWrapper.appendChild(tooltipEl);
                        }
                        const tooltipModel = context.tooltip;
                        if (tooltipModel.opacity === 0) {
                            tooltipEl.style.opacity = '0';
                            return;
                        }
                        const idx = tooltipModel.dataPoints?.[0]?.dataIndex;
                        if (idx !== undefined) {
                            const key = labels[idx];
                            const weight = values[idx].toFixed(2);
                            const count = occurrences[key] || 0;
                            tooltipEl.innerHTML = `<strong>${key}</strong>：${count}次（权重 ${weight}x）`;
                        }
                        tooltipEl.style.opacity = '1';
                        tooltipEl.style.right = '10px';
                        tooltipEl.style.top = '10px';
                        tooltipEl.style.left = 'auto';
                        tooltipEl.style.transform = 'none';
                    }
                }
            }
        },
        plugins: [{
            id: 'markovSliceGlow',
            afterDraw: (chart) => {
                if (state.lotteryType === 'weilitsai') return;
                const maxVal = Math.max(...values);
                if (maxVal === 0) return;

                const meta = chart.getDatasetMeta(0);
                const parent = chart.canvas.parentNode;

                let overlayCanvas = parent.querySelector('.markov-glow-overlay');
                if (!overlayCanvas) {
                    overlayCanvas = document.createElement('canvas');
                    overlayCanvas.className = 'markov-glow-overlay shape-pulse';
                    overlayCanvas.style.position = 'absolute';
                    overlayCanvas.style.pointerEvents = 'none';
                    overlayCanvas.style.zIndex = '10';
                    parent.appendChild(overlayCanvas);
                }

                overlayCanvas.style.top = chart.canvas.offsetTop + 'px';
                overlayCanvas.style.left = chart.canvas.offsetLeft + 'px';
                overlayCanvas.style.width = chart.canvas.offsetWidth + 'px';
                overlayCanvas.style.height = chart.canvas.offsetHeight + 'px';
                overlayCanvas.width = chart.canvas.width;
                overlayCanvas.height = chart.canvas.height;

                const ctx = overlayCanvas.getContext('2d');
                ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

                meta.data.forEach((arc, idx) => {
                    if (values[idx] === maxVal) {
                        ctx.save();
                        overlayCanvas.style.color = arc.options.backgroundColor;

                        ctx.beginPath();
                        if (arc.innerRadius > 0) {
                            ctx.arc(arc.x, arc.y, arc.outerRadius, arc.startAngle, arc.endAngle);
                            ctx.arc(arc.x, arc.y, arc.innerRadius, arc.endAngle, arc.startAngle, true);
                        } else {
                            ctx.moveTo(arc.x, arc.y);
                            ctx.arc(arc.x, arc.y, arc.outerRadius, arc.startAngle, arc.endAngle);
                        }
                        ctx.closePath();
                        ctx.fillStyle = arc.options.backgroundColor;
                        ctx.fill();
                        ctx.restore();
                    }
                });
            }
        }]
    });
}

// ===== 尾数分布柱状图 (复合双轴) =====

function renderBayesianChart(bayesianData) {
    const canvas = document.getElementById('chart-bayesian');
    if (!canvas || !bayesianData || bayesianData.length === 0) return;
    const ctx = canvas.getContext('2d');

    const isWeilitsai = state.lotteryType === 'weilitsai';
    const titleEl = canvas.closest('.chart-card')?.querySelector('.chart-title');
    if (titleEl) {
        titleEl.textContent = isWeilitsai ? '⚖️ 1区号码贝叶斯后验反弹图' : '⚖️ 贝叶斯遗漏反弹推测';
    }
    const descEl = canvas.closest('.chart-card')?.querySelector('p');
    if (descEl) {
        descEl.innerHTML = isWeilitsai
            ? `<strong class="text-blue-400">【动态概率更新】</strong>结合历史号码先验概率，利用1区号码最新遗漏极值作为证据，修正后验分布。推算1区号码在下期“触底反弹”的条件概率权重。`
            : `<strong class="text-blue-400">【动态概率更新】</strong>结合历史基础概率（先验），利用最新遗漏极值（新证据）不断修正后验概率。推算生肖在下期“触底反弹”的条件概率权重。`;
    }

    const labels = bayesianData.map(d => d.number !== undefined ? d.number.toString() : d.zodiac);
    const posteriorData = bayesianData.map(d => d.posterior);
    const omissionData = bayesianData.map(d => d.omission);

    if (state.charts.bayesian) state.charts.bayesian.destroy();

    state.charts.bayesian = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '后验反弹权重',
                    data: posteriorData,
                    backgroundColor: 'rgba(59, 130, 246, 0.7)', // 蓝色
                    borderRadius: 4,
                    yAxisID: 'y'
                },
                {
                    label: '当前连续遗漏期数',
                    data: omissionData,
                    type: 'line',
                    borderColor: 'rgba(239, 68, 68, 0.8)', // 红色
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    borderWidth: 2,
                    pointStyle: 'circle',
                    pointRadius: 4,
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
                    callbacks: {
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            if (context.datasetIndex === 0) {
                                label += context.raw + ' (权重)';
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
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9ca3af' }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    title: { display: true, text: '反弹权重', color: '#60a5fa' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    title: { display: true, text: '遗漏期数', color: '#f87171' }
                }
            }
        }
    });
}


function renderLSTMChart(lstmData) {
    const canvas = document.getElementById('chart-lstm');
    if (!canvas || !lstmData || lstmData.length === 0) return;
    const ctx = canvas.getContext('2d');

    const isWeilitsai = state.lotteryType === 'weilitsai';
    const titleEl = canvas.closest('.chart-card')?.querySelector('.chart-title');
    if (titleEl) {
        titleEl.textContent = isWeilitsai ? '🧠 1区号码神经网络 (MLP) 拟合图' : '🧠 LSTM 时序模拟与网络拟合度';
    }
    const descEl = canvas.closest('.chart-card')?.querySelector('p');
    if (descEl) {
        descEl.innerHTML = isWeilitsai 
            ? `<strong class="text-green-400">【非线性模式挖掘】</strong>将1区38个号码的频次与遗漏特征放入多层感知机网络进行特征拟合，预测下期开出倾向。<strong>局限性说明：</strong>纯随机噪音下，模型极易发生“过拟合”从而导致推演失效。`
            : `<strong class="text-green-400">【非线性模式挖掘】</strong>将生肖走势放入时间序列网络，寻找肉眼难辨的复杂周期。<strong>局限性说明：</strong>遇到纯随机噪音时，模型极易发生“过拟合”从而导致推演失效。`;
    }

    const labels = lstmData.map(d => d.number !== undefined ? d.number.toString() : d.zodiac);
    const scoreData = lstmData.map(d => d.score);
    const signalData = lstmData.map(d => d.signal);

    const pointColors = scoreData.map(score => {
        if (score >= 80) return 'rgba(16, 185, 129, 0.9)'; // 绿
        if (score >= 40) return 'rgba(245, 158, 11, 0.9)'; // 黄
        return 'rgba(239, 68, 68, 0.9)'; // 红
    });

    if (state.charts.lstm) state.charts.lstm.destroy();

    state.charts.lstm = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '网络拟合得分',
                data: scoreData,
                borderColor: 'rgba(168, 85, 247, 0.8)', // 紫色
                backgroundColor: 'rgba(168, 85, 247, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: pointColors,
                pointBorderColor: '#fff',
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            const idx = ctx.dataIndex;
                            return [`拟合得分: ${ctx.raw}`, `AI操作信号: 【${signalData[idx]}】`];
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9ca3af', font: { size: 13, weight: 'bold' } }
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9ca3af' },
                    title: { display: true, text: 'LSTM 拟合分值(0-100)', color: '#c084fc' }
                }
            }
        }
    });
}

// ==================== 模拟开奖 ====================
function initSimulator() {
    const btnSimulate = document.getElementById('btn-simulate');
    const countInput = document.getElementById('sim-count');
    const minusBtn = document.getElementById('sim-count-minus');
    const plusBtn = document.getElementById('sim-count-plus');

    if (!btnSimulate || !countInput || !minusBtn || !plusBtn) return;

    btnSimulate.addEventListener('click', runSimulation);

    minusBtn.addEventListener('click', () => {
        const current = parseInt(countInput.value) || 1;
        countInput.value = Math.max(1, current - 1);
    });

    plusBtn.addEventListener('click', () => {
        const current = parseInt(countInput.value) || 1;
        countInput.value = Math.min(1000, current + 1);
    });
}

async function runSimulation() {
    const count = parseInt(document.getElementById('sim-count').value) || 1;
    const btn = document.getElementById('btn-simulate');
    const btnText = btn.querySelector('.btn-text');
    const btnLoading = btn.querySelector('.btn-loading');

    // 按钮禁用状态
    btn.disabled = true;
    btnText.style.display = 'none';
    btnLoading.style.display = 'inline';

    // 隐藏之前的结果
    document.getElementById('sim-single-result').style.display = 'none';
    document.getElementById('sim-batch-result').style.display = 'none';

    // 显示动画
    const animationEl = document.getElementById('sim-animation');
    animationEl.style.display = 'block';

    // 重置球状态
    const balls = animationEl.querySelectorAll('.lottery-ball');
    balls.forEach(ball => {
        ball.textContent = '?';
        ball.classList.add('rolling');
        ball.classList.remove('revealed');
    });

    try {
        const response = await apiFetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: count, type: state.lotteryType })
        });
        const result = await response.json();

        if (result.success) {
            // 等待动画效果
            await new Promise(resolve => setTimeout(resolve, 1500));

            if (count === 1) {
                // 单期结果：逐个揭晓动画
                const draw = result.data.draws[0];
                await revealBalls(draw, balls);
                showSingleResult(draw);
            } else {
                // 批量结果
                animationEl.style.display = 'none';
                showBatchResult(result.data);
            }
        }
    } catch (error) {
        console.error('模拟请求失败:', error);
    } finally {
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
    }
}

async function revealBalls(draw, balls) {
    // 仅揭晓特码动画
    await new Promise(resolve => setTimeout(resolve, 800));
    const specialBall = balls[0];
    specialBall.classList.remove('rolling');
    specialBall.classList.add('revealed');
    specialBall.textContent = draw.special_num;

    await new Promise(resolve => setTimeout(resolve, 300));
}

function showSingleResult(draw) {
    const container = document.getElementById('result-balls');

    let html = '';

    html += `
        <div class="ball-wrapper" style="margin: 0 4px;">
            <div class="result-ball special">${draw.special_num}</div>
            ${draw.special_zodiac ? `<div class="zodiac-label" style="font-size: 0.8rem">${draw.special_zodiac}</div>` : ''}
        </div>
    `;

    container.innerHTML = html;
    document.getElementById('sim-single-result').style.display = 'block';
}

function showBatchResult(data) {
    // 统计摘要
    const summaryContainer = document.getElementById('batch-summary');
    const summary = data.summary;

    summaryContainer.innerHTML = `
        <div class="batch-stat">
            <div class="label">总模拟期数</div>
            <div class="value">${summary.total_draws}</div>
        </div>
        <div class="batch-stat">
            <div class="label">特码单双比</div>
            <div class="value">${summary.odd_even_ratio}</div>
        </div>
        <div class="batch-stat">
            <div class="label">特码大小比</div>
            <div class="value">${summary.big_small_ratio}</div>
        </div>
    `;

    // 显示最近 20 期
    const listContainer = document.getElementById('batch-draws-list');
    const showDraws = data.draws.slice(0, 20);

    listContainer.innerHTML = showDraws.map((draw, i) => {
        // Removed numsHtml as regular numbers are no longer displayed
        let specialHtml = `
            <div class="ball-wrapper" style="margin: 0 2px;">
                <div class="batch-ball special">${draw.special_num}</div>
                ${draw.special_zodiac ? `<div class="zodiac-label" style="font-size: 0.75rem">${draw.special_zodiac}</div>` : ''}
            </div>
        `;

        return `
            <div class="batch-draw-item">
                <span class="batch-draw-index">第${i + 1}期</span>
                <div class="batch-numbers" style="align-items: flex-start;">
                    ${specialHtml}
                </div>
            </div>
        `;
    }).join('');

    document.getElementById('sim-batch-result').style.display = 'block';
}

// ==================== 历史记录 ====================

let historySubTab = 'draw'; // 'draw' or 'ai'

function switchHistoryTab(tab) {
    const isWeilitsai = state.lotteryType === 'weilitsai';
    const link = isWeilitsai 
        ? "https://www.taiwanlottery.com/lotto/result/super_lotto638" 
        : "https://macaujc.com/macaujc2/";

    if (tab === 'draw') {
        if (historySubTab === 'draw') {
            // 如果已经是开奖记录 Tab，再次点击则在新窗口打开官方开奖页面
            window.open(link, '_blank');
            return;
        }
        historySubTab = tab;
        document.getElementById('btn-history-draw').innerHTML = '📊 开奖记录 <span style="font-size:0.8rem;opacity:0.8;">↗️</span>';
        document.getElementById('btn-history-draw').classList.add('active');
        document.getElementById('btn-history-ai').classList.remove('active');
        document.getElementById('history-draw-section').style.display = 'block';
        document.getElementById('history-ai-section').style.display = 'none';
        loadHistory(state.historyPage || 1);
    } else {
        historySubTab = tab;
        document.getElementById('btn-history-draw').innerHTML = '📊 开奖记录';
        document.getElementById('btn-history-draw').classList.remove('active');
        document.getElementById('btn-history-ai').classList.add('active');
        document.getElementById('history-draw-section').style.display = 'none';
        document.getElementById('history-ai-section').style.display = 'block';
        loadAIHistory(state.aiHistoryPage || 1);
    }
}

async function loadHistory(page) {
    try {
        const response = await fetch(`/api/history?page=${page}&per_page=20&type=${state.lotteryType}`);
        const result = await response.json();

        if (result.success) {
            renderHistory(result.data);
            state.historyPage = page;
            state.historyTotalPages = result.data.total_pages;
        }
    } catch (error) {
        console.error('加载历史记录失败:', error);
    }
}

