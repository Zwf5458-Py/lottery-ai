// 高阶统计算法衍生图表：极距回归、泊松同尾、三分比、AC值等

function renderThreeRegionPrimeCharts(threeRegion, primeComp) {
    if (!threeRegion || !primeComp) return;
    
    document.getElementById('pred-three-region-badge').textContent = `下期预测形态: ${threeRegion.next_pred}`;
    document.getElementById('pred-prime-badge').textContent = `下期质合预测: ${primeComp.next_pred}`;

    const trCtx = document.getElementById('chart-three-region').getContext('2d');
    const pcCtx = document.getElementById('chart-prime-composite').getContext('2d');

    const trLabels = Object.keys(threeRegion.distribution);
    const trData = Object.values(threeRegion.distribution);
    
    const trColors = [
        '#a855f7', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#6366f1',
        '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#84cc16',
        '#d946ef', '#0ea5e9', '#22c55e', '#eab308', '#f43f5e', '#4f46e5', '#c026d3'
    ];
    const bgColors = trLabels.map((_, i) => trColors[i % trColors.length]);

    if (window.chartThreeRegion) window.chartThreeRegion.destroy();
    window.chartThreeRegion = new Chart(trCtx, {
        type: 'doughnut',
        data: {
            labels: trLabels.map(l => `[${l}] 形态`),
            datasets: [{
                data: trData,
                backgroundColor: bgColors,
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: { display: true, text: '历史三分形态分布', color: '#f3f4f6' }
            }
        }
    });

    // 渲染双边自定义 HTML 图例
    const half = Math.ceil(trLabels.length / 2);
    let leftHtml = '';
    let rightHtml = '';
    trLabels.forEach((l, idx) => {
        const color = bgColors[idx];
        const itemHtml = `<div style="display:flex; align-items:center; gap:6px;"><span style="width:12px;height:12px;background:${color};border-radius:3px;display:inline-block;flex-shrink:0;"></span><span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">[${l}] 形态</span></div>`;
        if (idx < half) leftHtml += itemHtml;
        else rightHtml += itemHtml;
    });
    
    const elLeft = document.getElementById('legend-tr-left');
    const elRight = document.getElementById('legend-tr-right');
    if (elLeft) elLeft.innerHTML = leftHtml;
    if (elRight) elRight.innerHTML = rightHtml;

    const pcLabels = Object.keys(primeComp.distribution);
    const pcData = Object.values(primeComp.distribution);

    const pcColors = ['#2dd4bf', '#f43f5e', '#eab308', '#3b82f6', '#8b5cf6', '#14b8a6', '#f97316', '#a855f7', '#ec4899'];
    const pcBgColors = pcLabels.map((_, i) => pcColors[i % pcColors.length]);

    if (window.chartPrimeComp) window.chartPrimeComp.destroy();
    window.chartPrimeComp = new Chart(pcCtx, {
        type: 'doughnut',
        data: {
            labels: pcLabels.map(l => `[${l}] (质:合)`),
            datasets: [{
                data: pcData,
                backgroundColor: pcBgColors,
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: { display: true, text: '历史质合形态分布', color: '#f3f4f6' }
            }
        }
    });

    // 渲染双边自定义 HTML 图例 (质合形态)
    const pcHalf = Math.ceil(pcLabels.length / 2);
    let pcLeftHtml = '';
    let pcRightHtml = '';
    pcLabels.forEach((l, idx) => {
        const color = pcBgColors[idx];
        const itemHtml = `<div style="display:flex; align-items:center; gap:6px;"><span style="width:12px;height:12px;background:${color};border-radius:3px;display:inline-block;flex-shrink:0;"></span><span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">[${l}] (质:合)</span></div>`;
        if (idx < pcHalf) pcLeftHtml += itemHtml;
        else pcRightHtml += itemHtml;
    });
    
    const elPcLeft = document.getElementById('legend-pc-left');
    const elPcRight = document.getElementById('legend-pc-right');
    if (elPcLeft) elPcLeft.innerHTML = pcLeftHtml;
    if (elPcRight) elPcRight.innerHTML = pcRightHtml;
}

function renderRepeatsTailsCharts(repeatsTails) {
    if (!repeatsTails) return;

    document.getElementById('pred-repeats-badge').textContent = `下期重号预测: ${repeatsTails.next_repeat_pred} 个`;
    document.getElementById('pred-tails-badge').textContent = `同尾组数预测: ${repeatsTails.next_tails_pred} 组`;

    const rpCtx = document.getElementById('chart-repeats-poisson').getContext('2d');
    const itCtx = document.getElementById('chart-identical-tails').getContext('2d');

    const maxK = Math.max(
        ...Object.keys(repeatsTails.repeats_dist).map(Number),
        ...Object.keys(repeatsTails.poisson_probs).map(Number)
    );
    const rpLabels = [];
    const rpHistData = [];
    const rpPoissonData = [];
    
    // Convert counts to percentages for history
    const totalRepeats = Object.values(repeatsTails.repeats_dist).reduce((a, b) => a + b, 0);

    for (let i = 0; i <= maxK; i++) {
        rpLabels.push(`${i}个重号`);
        let histVal = repeatsTails.repeats_dist[i] || 0;
        rpHistData.push(totalRepeats > 0 ? (histVal / totalRepeats * 100).toFixed(2) : 0);
        rpPoissonData.push(repeatsTails.poisson_probs[i] || 0);
    }

    if (window.chartRepeatsPoisson) window.chartRepeatsPoisson.destroy();
    window.chartRepeatsPoisson = new Chart(rpCtx, {
        type: 'bar',
        data: {
            labels: rpLabels,
            datasets: [
                {
                    type: 'bar',
                    label: '历史频率 (%)',
                    data: rpHistData,
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderRadius: 4
                },
                {
                    type: 'line',
                    label: '泊松期望 (%)',
                    data: rpPoissonData,
                    borderColor: '#a855f7',
                    borderWidth: 2,
                    pointBackgroundColor: '#a855f7',
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
                x: { grid: { display: false }, ticks: { color: '#9ca3af' } }
            },
            plugins: {
                legend: { labels: { color: '#e5e7eb' } }
            }
        }
    });

    const itLabels = Object.keys(repeatsTails.tails_dist).sort();
    const itData = itLabels.map(k => repeatsTails.tails_dist[k]);

    if (window.chartIdenticalTails) window.chartIdenticalTails.destroy();
    window.chartIdenticalTails = new Chart(itCtx, {
        type: 'pie',
        data: {
            labels: itLabels.map(l => `${l} 组同尾`),
            datasets: [{
                data: itData,
                backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6'],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: '#e5e7eb' } },
                title: { display: true, text: '历史同尾组数分布', color: '#f3f4f6' }
            }
        }
    });
}

function renderRangeDriftCharts(rangeSpan, meanRegression) {
    if (!rangeSpan || !meanRegression) return;

    document.getElementById('pred-span-badge').textContent = `极距预测: ${rangeSpan.next_pred_span} (推荐: ${rangeSpan.suggested_range[0]}-${rangeSpan.suggested_range[1]})`;
    document.getElementById('pred-sum-badge').textContent = `和值预测: ${meanRegression.next_pred_sum} (均值: ${meanRegression.next_pred_mean})`;

    const rsCtx = document.getElementById('chart-range-span').getContext('2d');
    const mdCtx = document.getElementById('chart-mean-deviation').getContext('2d');

    const rsLabels = Object.keys(rangeSpan.distribution).sort((a,b) => Number(a)-Number(b));
    const rsData = rsLabels.map(k => rangeSpan.distribution[k]);

    if (window.chartRangeSpan) window.chartRangeSpan.destroy();
    window.chartRangeSpan = new Chart(rsCtx, {
        type: 'bar',
        data: {
            labels: rsLabels,
            datasets: [{
                label: '极距频次',
                data: rsData,
                backgroundColor: rsLabels.map(l => {
                    const val = Number(l);
                    return (val >= rangeSpan.suggested_range[0] && val <= rangeSpan.suggested_range[1]) ? 'rgba(168, 85, 247, 0.8)' : 'rgba(59, 130, 246, 0.5)';
                }),
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
                x: { grid: { display: false }, ticks: { color: '#9ca3af' } }
            },
            plugins: {
                legend: { display: false },
                title: { display: true, text: '历史极距分布 (紫柱为下期高光区)', color: '#f3f4f6' }
            }
        }
    });

    const mdLabels = meanRegression.deviations.map((_, i) => `前${meanRegression.deviations.length - i}期`);

    if (window.chartMeanDeviation) window.chartMeanDeviation.destroy();
    window.chartMeanDeviation = new Chart(mdCtx, {
        type: 'line',
        data: {
            labels: mdLabels,
            datasets: [
                {
                    label: '单期均值偏差',
                    data: meanRegression.deviations,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    yAxisID: 'y'
                },
                {
                    label: '累积偏差动力学',
                    data: meanRegression.cumulative_deviations,
                    borderColor: '#eab308',
                    backgroundColor: 'rgba(234, 179, 8, 0.1)',
                    borderWidth: 2,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: {
                    type: 'linear', display: true, position: 'left',
                    grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' },
                    title: { display: true, text: '单期偏差', color: '#9ca3af' }
                },
                y1: {
                    type: 'linear', display: true, position: 'right',
                    grid: { drawOnChartArea: false }, ticks: { color: '#eab308' },
                    title: { display: true, text: '累积偏差', color: '#eab308' }
                },
                x: { grid: { display: false }, ticks: { color: '#9ca3af' } }
            },
            plugins: {
                legend: { labels: { color: '#e5e7eb' } },
                title: { display: true, text: `近期重心倾向: ${meanRegression.recent_dev_trend}`, color: '#f3f4f6' }
            }
        }
    });
}

function renderACValueChart(acValue) {
    if (!acValue) return;

    document.getElementById('pred-ac-badge').textContent = `下期 AC推荐: ${acValue.next_pred_ac}`;

    const acCtx = document.getElementById('chart-ac-value').getContext('2d');
    const labels = Object.keys(acValue.distribution).sort((a,b) => Number(a)-Number(b));
    const data = labels.map(k => acValue.distribution[k]);

    if (window.chartACValue) window.chartACValue.destroy();
    window.chartACValue = new Chart(acCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'AC值频次',
                data: data,
                backgroundColor: labels.map(l => {
                    return acValue.high_prob_ac_range.includes(Number(l)) ? 'rgba(45, 212, 191, 0.8)' : 'rgba(107, 114, 128, 0.5)';
                }),
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
                x: { grid: { display: false }, ticks: { color: '#9ca3af' } }
            },
            plugins: {
                legend: { display: false },
                title: { display: true, text: '历史 AC值 复杂度分布 (青柱为理论高频区)', color: '#f3f4f6' }
            }
        }
    });
}
