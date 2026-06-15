// 澳门六合彩专属图表：波色、生肖、连击动量、五行等

function renderColorHotCold(colorData) {
    const container = document.getElementById('color-hotcold-view');
    if (!container || !colorData || !colorData.length) return;

    const colorMap = {
        '红波': { bg: 'rgba(239, 68, 68, 0.15)', border: 'rgba(239, 68, 68, 0.4)', bar: '#ef4444', glow: 'rgba(239, 68, 68, 0.6)', emoji: '🔴' },
        '蓝波': { bg: 'rgba(59, 130, 246, 0.15)', border: 'rgba(59, 130, 246, 0.4)', bar: '#3b82f6', glow: 'rgba(59, 130, 246, 0.6)', emoji: '🔵' },
        '绿波': { bg: 'rgba(34, 197, 94, 0.15)', border: 'rgba(34, 197, 94, 0.4)', bar: '#22c55e', glow: 'rgba(34, 197, 94, 0.6)', emoji: '🟢' }
    };

    container.innerHTML = `
        <p style="font-size: 0.75rem; color: #9ca3af; margin-bottom: 12px; line-height: 1.5;">
            基于几何分布 <code style="color:#6ee7b7;">P(X=k)=(1-p)<sup>k-1</sup>·p</code> 计算各波色遗漏极端度。极端度越高，说明该波色遗漏已超出历史正常波动范围的可能性越大。
        </p>

        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
            ${colorData.map(item => {
        const cm = colorMap[item.color] || colorMap['红波'];
        const isExtreme = item.extremity >= 85;
        const isHigh = item.extremity >= 60;
        return `
                <div class="color-analysis-card ${isExtreme ? 'pulse-glow' : ''}" style="
                    background: ${cm.bg};
                    border: 1px solid ${cm.border};
                    border-radius: 12px;
                    padding: 12px 14px;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    ${isExtreme ? 'box-shadow: 0 0 20px ' + cm.glow + ';' : ''}
                    transition: all 0.3s ease;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 1.4rem;">${cm.emoji}</span>
                            <div>
                                <div style="font-size: 1rem; font-weight: 800; color: #f3f4f6;">${item.color}</div>
                                <div style="font-size: 0.65rem; color: #9ca3af; margin-top: 2px;">近${item.total}期出现${item.count}次</div>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <span style="
                                display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 700;
                                background: ${isExtreme ? 'rgba(239, 68, 68, 0.3)' : (isHigh ? 'rgba(245, 158, 11, 0.3)' : 'rgba(34, 197, 94, 0.2)')};
                                color: ${isExtreme ? '#fca5a5' : (isHigh ? '#fbbf24' : '#86efac')};
                            ">${item.rebound_hint}</span>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;">
                        <div style="text-align: center; padding: 6px; background: rgba(0,0,0,0.2); border-radius: 6px;">
                            <div style="font-size: 0.65rem; color: #9ca3af; margin-bottom: 2px;">当前遗漏</div>
                            <div style="font-size: 1.1rem; font-weight: 900; color: ${isExtreme ? '#fca5a5' : '#f3f4f6'};">${item.current_gap}<span style="font-size:0.6rem;">期</span></div>
                        </div>
                        <div style="text-align: center; padding: 6px; background: rgba(0,0,0,0.2); border-radius: 6px;">
                            <div style="font-size: 0.65rem; color: #9ca3af; margin-bottom: 2px;">平均遗漏</div>
                            <div style="font-size: 1.1rem; font-weight: 900; color: #f3f4f6;">${item.avg_gap}<span style="font-size:0.6rem;">期</span></div>
                        </div>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 0.7rem;">
                         <span style="color:#9ca3af;">CDF概率</span>
                         <strong style="color: #f3f4f6;">${item.cdf}%</strong>
                    </div>
                    <div style="position: relative; height: 8px; background: rgba(0,0,0,0.3); border-radius: 4px; overflow: hidden;">
                        <div style="
                            height: 100%; width: ${Math.min(100, item.extremity)}%;
                            background: linear-gradient(90deg, ${cm.bar}, ${isExtreme ? '#fbbf24' : cm.bar});
                            border-radius: 4px; transition: width 1.5s ease;
                        "></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 6px; font-size: 0.7rem; color: #6b7280;">
                        <span>✅ 正常</span>
                        <span>极端度: ${item.extremity}%</span>
                        <span>🔥 反弹</span>
                    </div>
                </div>
            `}).join('')}
        </div>
    `;
}

// ===== 特码单双时间轴 K 线图 =====

function renderZodiacChart(zodiacData) {
    const canvas = document.getElementById('chart-zodiac');
    if (!canvas) return;

    const draws = zodiacData.draws || [];
    const zodiacOrder = zodiacData.zodiac_order || [];
    const BALL_R = 11;
    const ROW_H = BALL_R * 2 + 1; // 直径+1px，红球与网格近乎相切

    const labels = [];
    const scatterData = draws.map((d, i) => {
        labels.push(d.draw_number);
        return { x: i, y: d.zodiac_idx, label: d.num, actualDraw: d.draw_number };
    });

    const wrapper = document.getElementById('zodiac-scroll-wrapper');
    const container = document.getElementById('zodiac-chart-container');
    const pxPerPoint = 45;
    const totalW = Math.max(wrapper.clientWidth, draws.length * pxPerPoint);
    container.style.width = totalW + 'px';

    const chartAreaH = 13 * ROW_H; // 稍微增加高度以容纳扩大的 Y 轴区间
    const padTop = 25, padBot = 25, xAxisH = 60;
    const totalH = chartAreaH + padTop + padBot + xAxisH;
    container.style.height = totalH + 'px';

    if (state.charts.zodiac) state.charts.zodiac.destroy();
    if (state.charts.zodiacY) { state.charts.zodiacY.destroy(); state.charts.zodiacY = null; }

    const ballPlugin = {
        id: 'ballDraw',
        afterDatasetsDraw(chart) {
            const { ctx, chartArea } = chart;
            ctx.save();
            ctx.font = 'bold 11px "Noto Sans SC"';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            const meta = chart.getDatasetMeta(0);
            if (!meta.data) { ctx.restore(); return; }
            meta.data.forEach((pt, i) => {
                if (pt.x < chartArea.left - BALL_R || pt.x > chartArea.right + BALL_R) return;
                const raw = chart.data.datasets[0].data[i];
                ctx.fillStyle = getBallColorHex(raw.label);
                ctx.beginPath();
                ctx.arc(pt.x, pt.y, BALL_R, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = '#fff';
                ctx.fillText(raw.label, pt.x, pt.y);
            });
            ctx.restore();
        }
    };

    state.charts.zodiac = new Chart(canvas, {
        type: 'scatter',
        data: {
            datasets: [{
                data: scatterData, pointRadius: 0,
                showLine: true, borderColor: 'rgba(239,68,68,0.45)', borderWidth: 1.5, tension: 0
            }]
        },
        plugins: [ballPlugin],
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false, // 禁用初始动画提高加载速度
            hover: { animationDuration: 0 }, // 禁用鼠标悬浮重绘动画，解决Tooltip卡顿
            layout: { padding: { top: padTop, bottom: padBot, left: 10, right: 30 } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (c) {
                            const d = c.raw;
                            return '\u671f\u53f7: ' + d.actualDraw + ' | \u7279\u7801: ' + d.label + ' | \u751f\u8096: ' + zodiacOrder[d.y];
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'category',
                    labels: labels,
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: {
                        color: '#6b7280', font: { size: 10 },
                        maxRotation: 45, minRotation: 45,
                        autoSkip: true,
                        maxTicksLimit: Math.min(draws.length, 30) // 如果数据过多自动跳过多余标签
                    }
                },
                y: {
                    min: -0.8, max: 11.8,
                    grid: { color: 'rgba(255,255,255,0.08)' },
                    ticks: { display: false, stepSize: 1 },
                    afterFit: function (s) { s.width = 0; }
                }
            }
        }
    });

    // === DOM标签注入：从chart.scales.y读取真实像素坐标 ===
    const labelsBox = document.getElementById('zodiac-y-labels');
    labelsBox.innerHTML = '';
    labelsBox.style.height = totalH + 'px';

    const yScale = state.charts.zodiac.scales.y;
    zodiacOrder.forEach((name, idx) => {
        const py = yScale.getPixelForValue(idx);
        const lbl = document.createElement('div');
        lbl.textContent = name;
        lbl.style.cssText = 'position:absolute;right:6px;font-size:12px;font-weight:bold;color:#9ca3af;line-height:1;transform:translateY(-50%);white-space:nowrap;';
        lbl.style.top = py + 'px';
        labelsBox.appendChild(lbl);
    });

    setTimeout(() => { if (wrapper) wrapper.scrollLeft = wrapper.scrollWidth; }, 120);
}

// 全局绑定一次 markov_mode 切换事件
document.addEventListener('change', (e) => {
    if (e.target.name === 'markov_mode' && window.__markovData) {
        renderMarkovChart(window.__markovData);
    }
});

// ===== 智能马尔可夫链状态转移极地图 =====

function renderConsecutiveChart(consecutive) {
    const ctx = document.getElementById('chart-consecutive').getContext('2d');

    const dist = consecutive.pairs_distribution;
    const labels = Object.keys(dist).map(n => n === '0' ? '无连号' : `${n}组连号`);
    const values = Object.values(dist);

    const palette = [
        'rgba(59, 130, 246, 0.7)',
        'rgba(245, 200, 66, 0.7)',
        'rgba(239, 68, 68, 0.7)',
        'rgba(34, 197, 94, 0.7)',
        'rgba(168, 85, 247, 0.7)',
        'rgba(6, 182, 212, 0.7)',
    ];

    if (state.charts.consecutive) state.charts.consecutive.destroy();

    state.charts.consecutive = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '期数',
                data: values,
                backgroundColor: palette.slice(0, values.length),
                borderRadius: 6,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    cornerRadius: 8,
                    callbacks: {
                        label: function (ctx) {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((ctx.parsed.y / total) * 100).toFixed(1);
                            return `${ctx.parsed.y}期 (${pct}%)`;
                        }
                    }
                }
            },
            scales: {
                x: { grid: { display: false } },
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' } }
            }
        }
    });
}
// ===== 贝叶斯推断模型 =====

function renderFiveElementsChart(fiveData) {
    const canvas = document.getElementById('chart-five-elements');
    if (!canvas || !fiveData || !fiveData.chi_square) return;
    const ctx = canvas.getContext('2d');

    const items = fiveData.chi_square.items || [];
    const labels = items.map(i => i.element);
    const observed = items.map(i => i.observed);
    const expected = items.map(i => i.expected);

    if (state.charts.fiveElements) state.charts.fiveElements.destroy();

    state.charts.fiveElements = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: '实际频数',
                    data: observed,
                    backgroundColor: ['rgba(245,158,11,.75)', 'rgba(16,185,129,.75)', 'rgba(6,182,212,.75)', 'rgba(249,115,22,.75)', 'rgba(161,98,7,.75)'],
                    borderRadius: 6
                },
                {
                    label: '理论期望',
                    data: expected,
                    type: 'line',
                    borderColor: 'rgba(226,232,240,.9)',
                    backgroundColor: 'rgba(226,232,240,.18)',
                    borderWidth: 2,
                    tension: 0.25,
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#e5e7eb' } },
                tooltip: {
                    callbacks: {
                        footer: () => `卡方值 ${fiveData.chi_square.stat} | p=${fiveData.chi_square.p_value}`
                    }
                }
            },
            scales: {
                x: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,.05)' } },
                y: { ticks: { color: '#cbd5e1' }, grid: { color: 'rgba(255,255,255,.05)' } }
            }
        }
    });

    const summaryEl = document.getElementById('five-elements-summary');
    if (summaryEl) {
        const chi = fiveData.chi_square || {};
        const apriori = fiveData.apriori || {};
        const poisson = fiveData.poisson || {};
        summaryEl.innerHTML = `
            <div class="glass" style="padding:12px; border-radius:12px;">
                <div style="font-size:.75rem; color:#94a3b8;">卡方检验</div>
                <div style="font-size:1rem; font-weight:800; color:#f8fafc; margin-top:4px;">${chi.headline || '样本不足'}</div>
                <div style="font-size:.78rem; color:${chi.significant ? '#fca5a5' : '#86efac'}; margin-top:6px;">χ²=${chi.stat || 0} ｜ p=${chi.p_value || 0}</div>
            </div>
            <div class="glass" style="padding:12px; border-radius:12px;">
                <div style="font-size:.75rem; color:#94a3b8;">Apriori 关联</div>
                <div style="font-size:1rem; font-weight:800; color:#f8fafc; margin-top:4px;">${apriori.headline || '样本不足'}</div>
                <div style="font-size:.78rem; color:#cbd5e1; margin-top:6px;">验证五行相生相克是否真实存在</div>
            </div>
            <div class="glass" style="padding:12px; border-radius:12px;">
                <div style="font-size:.75rem; color:#94a3b8;">泊松遗漏</div>
                <div style="font-size:1rem; font-weight:800; color:#f8fafc; margin-top:4px;">${poisson.headline || '样本不足'}</div>
                <div style="font-size:.78rem; color:#cbd5e1; margin-top:6px;">关注极端遗漏后的均值回归拐点</div>
            </div>
        `;
    }

    const rulesEl = document.getElementById('five-elements-rules');
    if (rulesEl) {
        const rules = (fiveData.apriori && fiveData.apriori.rules) || [];
        const poissonItems = (fiveData.poisson && fiveData.poisson.items) || [];
        const topRules = rules.slice(0, 3).map(r =>
            `<div style="padding:10px 12px; border-radius:10px; background:rgba(15,23,42,.45); border:1px solid rgba(148,163,184,.16); margin-bottom:8px; color:#cbd5e1;">
                <strong style="color:#f8fafc;">${r.from} → ${r.to}</strong> ｜ 支持度 ${r.support}% ｜ 置信度 ${r.confidence}% ｜ Lift ${r.lift}
            </div>`
        ).join('');
        const topPoisson = poissonItems.slice(0, 2).map(r =>
            `<div style="padding:10px 12px; border-radius:10px; background:rgba(15,23,42,.45); border:1px solid rgba(148,163,184,.16); margin-bottom:8px; color:#cbd5e1;">
                <strong style="color:#f8fafc;">${r.element}</strong> ｜ 当前遗漏 ${r.current_gap} 期 ｜ 10期内零出现概率 ${r.p0_next_10}% ｜ ${r.hint}
            </div>`
        ).join('');
        rulesEl.innerHTML = `
            <div style="font-size:.8rem; color:#94a3b8; margin-bottom:8px;">五行关联 / 泊松窗口</div>
            ${topRules}${topPoisson}
        `;
    }

    const heatmapEl = document.getElementById('five-elements-heatmap');
    if (heatmapEl) {
        const matrix = (fiveData.apriori && fiveData.apriori.matrix) || [];
        const colHead = matrix[0]?.items?.map(item => `<th style="padding:8px; color:#cbd5e1; font-weight:700;">${item.to}</th>`).join('') || '';
        const rows = matrix.map(row => {
            const cells = row.items.map(item => {
                const alpha = Math.min(0.9, Math.max(0.08, item.confidence / 100));
                return `<td style="padding:8px; text-align:center; background:rgba(168,85,247,${alpha}); color:#f8fafc; border:1px solid rgba(255,255,255,.06); border-radius:8px;">${item.confidence}%</td>`;
            }).join('');
            return `<tr><th style="padding:8px; color:#e2e8f0; font-weight:700; text-align:left;">${row.from}</th>${cells}</tr>`;
        }).join('');
        heatmapEl.innerHTML = `
            <div style="font-size:.8rem; color:#94a3b8; margin-bottom:8px;">五行转移热力图（上期 → 下期）</div>
            <div style="overflow:auto; border-radius:12px; border:1px solid rgba(148,163,184,.14); background:rgba(15,23,42,.34); padding:10px;">
                <table style="width:100%; min-width:min(100%, 420px); border-collapse:separate; border-spacing:6px;">
                    <thead><tr><th></th>${colHead}</tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        `;
    }

    const omissionEl = document.getElementById('five-elements-omission');
    if (omissionEl) {
        const items = (fiveData.poisson && fiveData.poisson.items) || [];
        omissionEl.innerHTML = `
            <div style="font-size:.8rem; color:#94a3b8; margin-bottom:8px;">五行遗漏排行</div>
            ${items.map((item, idx) => {
            const bar = Math.max(8, Math.min(100, 100 - item.gap_tail_prob));
            return `<div style="padding:10px 12px; border-radius:10px; background:rgba(15,23,42,.45); border:1px solid rgba(148,163,184,.16); margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; gap:10px; align-items:center; margin-bottom:6px;">
                        <strong style="color:#f8fafc;">#${idx + 1} ${item.element}</strong>
                        <span style="font-size:.78rem; color:#cbd5e1;">遗漏 ${item.current_gap} 期 ｜ λ10=${item.lambda_10}</span>
                    </div>
                    <div style="height:8px; border-radius:999px; background:rgba(255,255,255,.06); overflow:hidden; margin-bottom:6px;">
                        <div style="width:${bar}%; height:100%; background:linear-gradient(90deg,#f59e0b,#ef4444);"></div>
                    </div>
                    <div style="font-size:.78rem; color:#94a3b8;">零出现概率 ${item.p0_next_10}% ｜ 尾部概率 ${item.gap_tail_prob}% ｜ ${item.hint}</div>
                </div>`;
        }).join('')}
        `;
    }

    const ballsEl = document.getElementById('five-elements-balls');
    if (ballsEl) {
        const map = fiveData.number_balls || {};
        const ballRows = Object.entries(map).map(([element, nums]) => {
            const balls = nums.map((num) => {
                const colorHex = getBallColorHex(num);
                const darkColor = colorHex === '#ef4444' ? '#d30000' : (colorHex === '#3b82f6' ? '#0055d3' : '#00a83b');
                return `<span style="display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px; border-radius:50%; background:radial-gradient(circle at 30% 30%, ${colorHex}, ${darkColor}); color:#fff; font-weight:900; font-size:.84rem; box-shadow:0 3px 8px rgba(0,0,0,.32); border:2px solid rgba(255,255,255,.3); text-shadow:1px 1px 0 rgba(0,0,0,.45);">${String(num).padStart(2, '0')}</span>`;
            }).join('');
            return `<div style="padding:10px 12px; border-radius:10px; background:rgba(15,23,42,.45); border:1px solid rgba(148,163,184,.16); margin-bottom:8px;">
                <div style="font-size:.84rem; font-weight:700; color:#f8fafc; margin-bottom:8px;">${element}</div>
                <div style="display:flex; flex-wrap:wrap; gap:8px;">${balls}</div>
            </div>`;
        }).join('');
        ballsEl.innerHTML = `
            <div style="font-size:.8rem; color:#94a3b8; margin-bottom:8px;">五行数字彩球映射</div>
            ${ballRows}
        `;
    }
}

// ===== LSTM 深度学习模型 =====
