import matplotlib.pyplot as plt
import io
import pandas as pd
import numpy as np

# 尝试设置中文字体，防止乱码。Windows 下常用的如 SimHei, Microsoft YaHei
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

from modules.constants import get_color_hex as get_color_by_number

def generate_zodiac_trend_image_bytes(df: pd.DataFrame, z_map: dict, periods: int = 100) -> bytes:
    if df is None or df.empty: return None
    df_recent = df.head(periods).copy()
    df_recent = df_recent.sort_values('draw_number', ascending=True)
    zodiac_order = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']
    x_labels, y_values = [], []
    for _, row in df_recent.iterrows():
        try:
            num = int(row['special_num'])
            z = z_map.get(num, '未知')
            y_val = zodiac_order.index(z) if z in zodiac_order else -1
            if y_val != -1:
                x_labels.append(str(row['draw_number'])[-3:]) 
                y_values.append(y_val)
        except: continue
    if not y_values: return None
    plt.figure(figsize=(12, 5))
    plt.plot(range(len(y_values)), y_values, marker='o', linestyle='-', color='#a855f7', linewidth=2, markersize=5)
    plt.yticks(range(12), zodiac_order)
    step = max(1, len(x_labels) // 20)
    plt.xticks(range(0, len(x_labels), step), [x_labels[i] for i in range(0, len(x_labels), step)], rotation=45)
    plt.title(f"最近 {len(y_values)} 期特码生肖走势图 (AI 视觉分析专用)", fontsize=14)
    plt.xlabel("期号 (从左旧至右新)", fontsize=12)
    plt.ylabel("生肖排位", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    plt.close()
    buf.seek(0)
    return buf.getvalue()

def generate_comprehensive_dashboard_bytes(stats_summary: dict, df_recent: pd.DataFrame, z_map: dict, dimensions: list = None) -> bytes:
    """
    生成综合仪表盘图片（根据用户勾选的维度动态生成）
    dimensions: 用户勾选的维度列表，如 ['big_small', 'odd_even', 'consecutive', 'bayesian', 'markov']
    """
    if df_recent is None or df_recent.empty: return None
    
    # 映射前端维度名到图表类型
    dim_to_chart = {
        'big_small': ('大小走势', True),   # 始终显示数值波动作为辅助
        'odd_even': ('单双走势', True),   # 始终显示奇偶辅助
        'consecutive': ('生肖路单', True), # 始终包含
        'bayesian': ('贝叶斯遗漏', 'bayesian' in stats_summary),
        'markov': ('马尔可夫链', 'markov' in stats_summary and 'weights' in stats_summary['markov']),
    }
    
    # 确定要显示的图表（只包含用户勾选的维度）
    charts_to_show = []
    if dimensions:
        for dim in dimensions:
            if dim in dim_to_chart:
                name, condition = dim_to_chart[dim]
                if condition:  # 如果条件满足
                    charts_to_show.append((dim, name))
    
    # 如果没有勾选任何维度，至少显示生肖路单
    if not charts_to_show:
        charts_to_show = [('consecutive', '生肖路单')]
    
    num_plots = len(charts_to_show)
    
    # 动态计算行列布局
    if num_plots == 1:
        rows, cols = 1, 1
    elif num_plots == 2:
        rows, cols = 1, 2
    elif num_plots <= 4:
        rows, cols = 2, 2
    elif num_plots <= 6:
        rows, cols = 2, 3
    else:
        rows, cols = 3, 2
    
    fig = plt.figure(figsize=(6 * cols, 5 * rows))
    dim_names = [name for _, name in charts_to_show]
    fig.suptitle(f'特码 AI 分析维度图 (已选: {", ".join(dim_names)})', fontsize=16, fontweight='bold')
    
    # 准备数据
    df_target = df_recent.sort_values('draw_number', ascending=True)
    length = len(df_target)
    draw_labels = [str(r['draw_number'])[-3:] for _, r in df_target.iterrows()]
    num_vals = [int(r['special_num']) for _, r in df_target.iterrows()]
    step = max(1, length // 12)
    zodiac_order = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']
    
    # 按选择顺序绘制图表
    for idx, (dim_key, dim_name) in enumerate(charts_to_show):
        ax = plt.subplot(rows, cols, idx + 1)
        
        if dim_key == 'big_small':
            # 大小数值波动
            colors = [get_color_by_number(n) for n in num_vals]
            ax.plot(range(length), num_vals, linestyle='-', color='#94a3b8', alpha=0.4, linewidth=1, zorder=1)
            ax.scatter(range(length), num_vals, color=colors, s=30, zorder=2)
            ax.axhline(y=24.5, color='r', linestyle='--', alpha=0.6, label='大小界线(24.5)')
            ax.set_title(f"📊 {dim_name}", fontsize=12)
            ax.set_ylabel("特码值")
            ax.grid(True, linestyle=':', alpha=0.5)
            ax.legend()
            ax.set_xticks(range(0, length, step))
            ax.set_xticklabels([draw_labels[i] for i in range(0, length, step)], rotation=30)
            
        elif dim_key == 'odd_even':
            # 单双走势
            odd_even_vals = [1 if n % 2 != 0 else 0 for n in num_vals]
            ax.step(range(length), odd_even_vals, where='mid', color='#f43f5e', linewidth=2)
            ax.set_yticks([0, 1])
            ax.set_yticklabels(['双', '单'])
            ax.set_title(f"🔢 {dim_name}", fontsize=12)
            ax.grid(True, linestyle=':', alpha=0.5)
            ax.set_xticks(range(0, length, step))
            ax.set_xticklabels([draw_labels[i] for i in range(0, length, step)], rotation=30)
            
        elif dim_key == 'consecutive':
            # 生肖路单
            y_vals_z = []
            for n in num_vals:
                z = z_map.get(n, '未知')
                y_vals_z.append(zodiac_order.index(z) if z in zodiac_order else -1)
            ax.plot(range(length), y_vals_z, marker='o', linestyle='-', color='#a855f7', linewidth=2, markersize=4)
            ax.set_yticks(range(12))
            ax.set_yticklabels(zodiac_order)
            ax.set_title(f"🐾 {dim_name}", fontsize=12)
            ax.grid(True, linestyle=':', alpha=0.5)
            ax.set_xticks(range(0, length, step))
            ax.set_xticklabels([draw_labels[i] for i in range(0, length, step)], rotation=30)
            
        elif dim_key == 'bayesian':
            # 贝叶斯遗漏
            bayes_data = stats_summary.get('bayesian', [])
            if bayes_data:
                b_names = [d['zodiac'] for d in bayes_data]
                b_omis = [d['omission'] for d in bayes_data]
                b_max = [d.get('max_omission', 0) for d in bayes_data]
                x = np.arange(len(b_names))
                width = 0.35
                ax.bar(x - width/2, b_omis, width, label='当前遗漏', color='#eab308')
                if any(b_max):
                    ax.bar(x + width/2, b_max, width, label='历史极限', color='#cbd5e1', alpha=0.7)
                ax.set_title(f"⚖️ {dim_name}", fontsize=12)
                ax.set_xticks(x)
                ax.set_xticklabels(b_names, rotation=30)
                ax.legend(loc='upper right')
                ax.grid(True, axis='y', linestyle=':', alpha=0.5)
            else:
                ax.text(0.5, 0.5, '无贝叶斯数据', ha='center', va='center', transform=ax.transAxes)
                
        elif dim_key == 'markov':
            # 马尔可夫链
            m_weights = stats_summary.get('markov', {}).get('weights', {})
            if m_weights:
                zodiac_names = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
                z_w = {k: v for k, v in m_weights.items() if k in zodiac_names}
                if z_w:
                    sorted_m = sorted(z_w.items(), key=lambda x: x[1], reverse=True)
                    names = [item[0] for item in sorted_m]
                    vals = [item[1] for item in sorted_m]
                    ax.bar(names, vals, color='#10b981')
                    ax.set_title(f"🕸️ {dim_name}", fontsize=12)
                    ax.set_ylabel("转移权重")
                    ax.grid(True, axis='y', linestyle=':', alpha=0.5)
                    ax.tick_params(axis='x', rotation=30)
            else:
                ax.text(0.5, 0.5, '无马尔可夫数据', ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
