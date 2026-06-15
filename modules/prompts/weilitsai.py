# 台湾威力彩分析提示词生成模块

def _build_weilitsai_analysis_prompt(stats: dict, dimensions: list, pre_sel_nums: list = None, pre_sel_special: int = 1, system_weights: dict = None, is_wheeling: bool = False) -> str:
    sections = []
    if 'big_small' in dimensions:
        try:
            bs_z1 = stats.get('big_small_z1', {})
            bs_z2 = stats.get('big_small_z2', {})
            b1 = bs_z1.get('total_big', '?')
            s1 = bs_z1.get('total_small', '?')
            vals_1 = bs_z1.get('values', [])
            last5_1 = vals_1[-5:] if vals_1 else []
            b2 = bs_z2.get('total_big', '?')
            s2 = bs_z2.get('total_small', '?')
            vals_2 = bs_z2.get('values', [])
            last5_2 = vals_2[-5:] if vals_2 else []
            desc = (
                f"- **第一區 (1-38，20及以上为大，19及以下为小)**: 近100期大 {b1} 次 | 小 {s1} 次，最近5期K线值(正大负小): {last5_1}\n"
                f"- **第二區 (1-8，5及以上为大，4及以下为小)**: 近100期大 {b2} 次 | 小 {s2} 次，最近5期K线值(正大负小): {last5_2}"
            )
            sections.append(f"### 📊 威力彩两區大小走势图表分析\n{desc}")
        except:
            sections.append("### 📊 威力彩两區大小走势图表分析\n暂无数据")

    if 'odd_even' in dimensions:
        try:
            oe_z1 = stats.get('odd_even_z1', {})
            oe_z2 = stats.get('odd_even_z2', {})
            o1 = oe_z1.get('total_odd', '?')
            e1 = oe_z1.get('total_even', '?')
            vals_1 = oe_z1.get('values', [])
            last5_1 = vals_1[-5:] if vals_1 else []
            o2 = oe_z2.get('total_odd', '?')
            e2 = oe_z2.get('total_even', '?')
            vals_2 = oe_z2.get('values', [])
            last5_2 = vals_2[-5:] if vals_2 else []
            desc = (
                f"- **第一區**: 近100期单 {o1} 次 | 双 {e1} 次，最近5期K线值(正单负双): {last5_1}\n"
                f"- **第二區**: 近100期单 {o2} 次 | 双 {e2} 次，最近5期K线值(正单负双): {last5_2}"
            )
            sections.append(f"### 🎲 威力彩两區单双走势图表分析\n{desc}")
        except:
            sections.append("### 🎲 威力彩两區单双走势图表分析\n暂无数据")

    if 'hot_cold' in dimensions:
        try:
            hc_z1 = stats.get('hot_cold_z1', {})
            hc_z2 = stats.get('hot_cold_z2', {})
            hot_1 = hc_z1.get('hot', [])
            cold_1 = hc_z1.get('cold', [])
            hot_2 = hc_z2.get('hot', [])
            cold_2 = hc_z2.get('cold', [])
            def _fmt_hc(lst):
                return ', '.join([f"{item['number']}号(出现{item['count']}次/遗漏{item['omission']}期)" for item in lst])
            desc = (
                f"- **第一區 (1-38)**:\n"
                f"  - 热门号码: {_fmt_hc(hot_1)}\n"
                f"  - 冷门号码: {_fmt_hc(cold_1)}\n"
                f"- **第二區 (1-8)**:\n"
                f"  - 热门号码: {_fmt_hc(hot_2)}\n"
                f"  - 冷门号码: {_fmt_hc(cold_2)}"
            )
            sections.append(f"### ❄️🔥 号码冷热频率与遗漏统计\n{desc}")
        except:
            sections.append("### ❄️🔥 号码冷热频率与遗漏统计\n暂无数据")

    if 'tail' in dimensions:
        try:
            t_z1 = stats.get('tail_numbers_z1', {})
            t_z2 = stats.get('tail_numbers_z2', {})
            dist_1 = t_z1.get('distribution', {})
            omi_1 = t_z1.get('omission', {})
            dist_2 = t_z2.get('distribution', {})
            omi_2 = t_z2.get('omission', {})
            def _fmt_tail(dist, omi):
                lines = []
                for t in range(10):
                    lines.append(f"尾数 {t}(出现 {dist.get(t, 0)} 次/遗漏 {omi.get(t, 0)} 期)")
                return ', '.join(lines)
            desc = (
                f"- **第一區 (Zone 1) 尾数**: {_fmt_tail(dist_1, omi_1)}\n"
                f"- **第二區 (Zone 2) 尾数**: {_fmt_tail(dist_2, omi_2)}"
            )
            sections.append(f"### 🔢 号码尾数分布统计\n{desc}")
        except:
            sections.append("### 🔢 号码尾数分布统计\n暂无数据")

    if 'markov' in dimensions:
        try:
            weight_cfg = stats.get('markov', {}).get('weights', {})
            markov_str = "暂无"
            if weight_cfg:
                z_weights = {int(k): v for k, v in dict(weight_cfg).items() if str(k).isdigit() and 1 <= int(k) <= 38}
                is_sig = weight_cfg.get('_is_significant', True)
                chi_val = weight_cfg.get('_chi_square_val', 0)
                sorted_z = sorted(z_weights.items(), key=lambda x: x[1], reverse=True)
                top_5 = [f"{num}号(跃迁权重 {w:.2f})" for num, w in sorted_z[:5]]
                bottom_5 = [f"{num}号(跃迁权重 {w:.2f})" for num, w in sorted_z[-5:]]
                sig_text = f"【显著有效】卡方检验验证(x²={chi_val})。" if is_sig else f"【噪音警告】卡方检验不显著(x²={chi_val} < 14.0671)。"
                markov_str = (
                    f"基于第一區号码全量数据的马尔可夫链状态转移：\n - {sig_text}\n"
                    f" - 极高概率跃迁目标：{', '.join(top_5)}\n"
                    f" - 最小概率跃迁目标：{', '.join(bottom_5)}"
                )
            sections.append(f"### 🕸️ 马尔可夫链第一區号码跃迁推演\n{markov_str}")
        except:
            sections.append("### 🕸️ 马尔可夫链第一區号码跃迁推演\n暂无数据")

    if 'consecutive' in dimensions:
        try:
            cons = stats.get('consecutive', {})
            trend = cons.get('current_trend', 'none')
            count = cons.get('consecutive_count', 0)
            rev_prob = cons.get('reversal_probability', 0)
            target_dir = cons.get('reversal_target_direction', 'none')
            curr_y = cons.get('current_y', -1)
            if count > 0 and trend != 'none' and trend != 'flat':
                dir_chi = "向上攀升" if trend == 'up' else "向下探底"
                target_chi = "向下回调" if target_dir == 'down' else "向上反弹"
                desc = (
                    f"- 当期图表状态：第一區 6 码正码和值折线处于【{dir_chi}】趋势中，已连续走势【{count}】期。\n"
                    f"- 当前最新正码和值为: {curr_y}\n"
                    f"- 动量反转预警：基于 RLE 连涨防跌变跳动能，系统推算在当前极限连庄形态下，下一期和值**{target_chi}**的概率为 {rev_prob}%。"
                )
                sections.append(f"### 📈 第一區正码和值动量路单拐点预判\n{desc}")
            else:
                sections.append("### 📈 第一區正码和值动量路单拐点预判\n- 当前正码和值折线波动平稳，暂无连涨连跌拐点。")
        except:
            sections.append("### 📈 第一區正码和值动量路单拐点预判\n暂无数据")

    if 'bayesian' in dimensions:
        try:
            bayesian = stats.get('bayesian', [])
            if bayesian:
                desc_list = []
                for item in bayesian[:5]:
                    record_flag = ""
                    if item.get('breaking_record', False):
                        record_flag = " 🚨突破历史极限！"
                    elif item['omission'] >= item.get('max_omission', 999) * 0.8:
                        record_flag = " ⚠️接近极限遗漏值"
                    desc_list.append(f"  - {item['number']}号(后验概率:{item['posterior']} | 遗漏:{item['omission']}期 / 历史极限:{item.get('max_omission','?')}期){record_flag}")
                sections.append(f"### ⚖️ 贝叶斯推断一区反弹概率 Top 5\n" + '\n'.join(desc_list))
            else:
                sections.append("### ⚖️ 贝叶斯推断\n无法推算反弹指数")
        except:
            sections.append("### ⚖️ 贝叶斯推断\n暂无数据")

    if 'lstm' in dimensions:
        try:
            lstm = stats.get('lstm', [])
            if lstm:
                top_5 = lstm[:5]
                desc_list = [f"  - {item['number']}号(神经网络评分:{item['score']} | AI信号判决:【{item['signal']}】)" for item in top_5]
                sections.append(f"### 🧠 MLP 神经网络拟合得分 Top 5 (一区号码)\n" + '\n'.join(desc_list))
            else:
                sections.append("### 🧠 MLP 神经网络拟合得分\n网络未形成明显信号")
        except:
            sections.append("### 🧠 MLP 神经网络拟合得分\n暂无数据")

    if 'three_region' in dimensions:
        try:
            tr = stats.get('three_region', {})
            next_pred = tr.get('next_pred', '2:2:2')
            r_status = tr.get('region_status', {})
            desc = (
                f"- **下一期三分比预测(一区:二区:三区)**: {next_pred}\n"
                f"- **区间状态**: 一区平均 {r_status.get('r1', {}).get('avg', '?')} 个数({r_status.get('r1', {}).get('trend', '平稳')}) | "
                f"二区平均 {r_status.get('r2', {}).get('avg', '?')} 个数({r_status.get('r2', {}).get('trend', '平稳')}) | "
                f"三区平均 {r_status.get('r3', {}).get('avg', '?')} 个数({r_status.get('r3', {}).get('trend', '平稳')})"
            )
            sections.append(f"### 📊 1区区间三分比分析\n{desc}")
        except:
            sections.append("### 📊 1区区间三分比分析\n暂无数据")

    if 'prime_composite' in dimensions:
        try:
            pc = stats.get('prime_composite', {})
            next_pred = pc.get('next_pred', '2:4')
            mean_primes = pc.get('mean_primes', '?')
            desc = (
                f"- **下一期质合比预测(质数:合数)**: {next_pred}\n"
                f"- **历史均值**: 平均每期包含质数 {mean_primes} 个 (质数指一区内 2,3,5,7,11,13,17,19,23,29,31,37)"
            )
            sections.append(f"### 📊 1区质合分布分析\n{desc}")
        except:
            sections.append("### 📊 1区质合分布分析\n暂无数据")

    if 'repeats_tails' in dimensions:
        try:
            rt = stats.get('repeats_tails', {})
            next_repeat = rt.get('next_repeat_pred', 0)
            next_tails = rt.get('next_tails_pred', 1)
            mean_repeats = rt.get('mean_repeats', '?')
            mean_tails = rt.get('mean_tails', '?')
            desc = (
                f"- **泊松预测下一期重号数**: {next_repeat} 个 (均值 {mean_repeats})\n"
                f"- **下一期同尾号组数预测**: {next_tails} 组 (均值 {mean_tails})"
            )
            sections.append(f"### 📊 重号分布(泊松预测)与同尾号分析\n{desc}")
        except:
            sections.append("### 📊 重号分布(泊松预测)与同尾号分析\n暂无数据")

    if 'ac_value' in dimensions:
        try:
            ac = stats.get('ac_value', {})
            next_pred = ac.get('next_pred_ac', 9)
            ac_probs = ac.get('ac_probs', {})
            probs_str = ', '.join([f"AC{k}({v}%)" for k, v in ac_probs.items() if float(v) > 5.0])
            desc = (
                f"- **下一期推荐AC值**: {next_pred} (高频范围: {ac.get('high_prob_ac_range', [7,8,9,10])})\n"
                f"- **AC值历史频率**: {probs_str}"
            )
            sections.append(f"### 📊 1区号码 AC值 (算术复杂度) 预测\n{desc}")
        except:
            sections.append("### 📊 1区号码 AC值 (算术复杂度) 预测\n暂无数据")

    if 'range_span' in dimensions:
        try:
            rs = stats.get('range_span', {})
            next_span = rs.get('next_pred_span', 31)
            mean_span = rs.get('mean_span', '?')
            s_range = rs.get('suggested_range', [28, 34])
            desc = (
                f"- **下一期极大极距预测**: {next_span} (历史平均极距 {mean_span})\n"
                f"- **建议极距搜索范围**: {s_range[0]} 至 {s_range[1]}"
            )
            sections.append(f"### 📊 1区号码极大极距分析\n{desc}")
        except:
            sections.append("### 📊 1区号码极大极距分析\n暂无数据")

    if 'mean_regression' in dimensions:
        try:
            mr = stats.get('mean_regression', {})
            next_mean = mr.get('next_pred_mean', 19.5)
            next_sum = mr.get('next_pred_sum', 117)
            trend = mr.get('recent_dev_trend', '围绕期望平稳震荡')
            desc = (
                f"- **下一期均值预测**: {next_mean} (对应6码和值 {next_sum})\n"
                f"- **近期偏差走势偏离警告**: 【{trend}】"
            )
            sections.append(f"### 📊 1区和值均值回归分析\n{desc}")
        except:
            sections.append("### 📊 1区和值均值回归分析\n暂无数据")

    data_block = '\n\n'.join(sections)
    recent_detail = ''
    try:
        if 'big_small' in dimensions or 'odd_even' in dimensions:
            oe_z1 = stats.get('odd_even_z1', {})
            bs_z1 = stats.get('big_small_z1', {})
            oe_z2 = stats.get('odd_even_z2', {})
            bs_z2 = stats.get('big_small_z2', {})
            oe_labels = oe_z1.get('labels', [])
            oe_values_z1 = oe_z1.get('values', [])
            bs_values_z1 = bs_z1.get('values', [])
            oe_values_z2 = oe_z2.get('values', [])
            bs_values_z2 = bs_z2.get('values', [])
            n = min(15, len(oe_labels))
            if n > 0:
                lines = []
                for i in range(n):
                    idx = len(oe_labels) - n + i
                    period = oe_labels[idx] if idx < len(oe_labels) else '?'
                    oe_v1 = oe_values_z1[idx] if idx < len(oe_values_z1) else 0
                    bs_v1 = bs_values_z1[idx] if idx < len(bs_values_z1) else 0
                    oe_tag1 = f"奇(连{oe_v1})" if oe_v1 > 0 else f"双(连{abs(oe_v1)})"
                    bs_tag1 = f"大(连{bs_v1})" if bs_v1 > 0 else f"小(连{abs(bs_v1)})"
                    oe_v2 = oe_values_z2[idx] if idx < len(oe_values_z2) else 0
                    bs_v2 = bs_values_z2[idx] if idx < len(bs_values_z2) else 0
                    oe_tag2 = f"奇(连{oe_v2})" if oe_v2 > 0 else f"双(连{abs(oe_v2)})"
                    bs_tag2 = f"大(连{bs_v2})" if bs_v2 > 0 else f"小(连{abs(bs_v2)})"
                    lines.append(f"  {period}期: [第一區] {oe_tag1}, {bs_tag1} | [第二區] {oe_tag2}, {bs_tag2}")
                recent_detail = f"## 最近 {n} 期第一區与第二區走势 K 线跳变明细\n" + '\n'.join(lines)
    except:
        recent_detail = '暂无明细'

    raw_draw_nums_str = "暂无"
    try:
        from modules.config_manager import get_chart_periods
        ai_raw_p = min(50, get_chart_periods(lottery_type='weilitsai').get('ai_raw_data', 300))
        from modules.data_processor import get_db_connection
        conn = get_db_connection()
        rows = conn.execute(
            f"SELECT draw_number, num1, num2, num3, num4, num5, num6, special_num FROM lottery_history WHERE lottery_type='weilitsai' ORDER BY draw_date DESC, draw_number DESC LIMIT {ai_raw_p}",
        ).fetchall()
        conn.close()
        if rows:
            rows = list(reversed(rows))
            raw_draw_nums_str = '\n'.join([
                f"  {r[0]}期: 一区({r[1]},{r[2]},{r[3]},{r[4]},{r[5]},{r[6]}) | 二区({r[7]})" for r in rows
            ])
    except:
        raw_draw_nums_str = '暂无'

    weights_info = ""
    if system_weights:
        weight_lines = []
        if 'big_small' in dimensions:
            _big_w = system_weights.get('big_weight', 1.0)
            _small_w = system_weights.get('small_weight', 1.0)
            weight_lines.append(f"- 大号权重: {_big_w:.2f}，小号权重: {_small_w:.2f}")
        if 'odd_even' in dimensions:
            _odd_w = system_weights.get('odd_weight', 1.0)
            _even_w = system_weights.get('even_weight', 1.0)
            weight_lines.append(f"- 单号权重: {_odd_w:.2f}，双号权重: {_even_w:.2f}")
        if 'hot_cold' in dimensions:
            hc_w_z1 = system_weights.get('hot_cold_weights_z1', {})
            hc_w_z2 = system_weights.get('hot_cold_weights_z2', {})
            z1_w_list = [f"{num}号({w:.2f})" for num, w in hc_w_z1.items() if w != 1.0] if isinstance(hc_w_z1, dict) else []
            z2_w_list = [f"{num}号({w:.2f})" for num, w in hc_w_z2.items() if w != 1.0] if isinstance(hc_w_z2, dict) else []
            if z1_w_list:
                weight_lines.append(f"- 第一區底层冷热/遗漏加权: {', '.join(z1_w_list)}")
            if z2_w_list:
                weight_lines.append(f"- 第二區底层冷热/遗漏加权: {', '.join(z2_w_list)}")
        if weight_lines:
            weights_info = "\n## 底层图表算法赋予的核心权重系数参考（数值>1代表看好，<1代表看衰）：\n" + "\n".join(weight_lines) + "\n"

    dim_names = {
        'big_small': '大小走势',
        'odd_even': '单双走势',
        'hot_cold': '冷热频率',
        'tail': '尾数分布',
        'markov': '马尔可夫',
        'consecutive': '正码和值动量拐点',
        'bayesian': '贝叶斯',
        'lstm': 'MLP神经网络',
        'three_region': '三分比走势',
        'prime_composite': '质合比走势',
        'repeats_tails': '重号同尾分布',
        'ac_value': 'AC值复杂度',
        'range_span': '极大极距走势',
        'mean_regression': '均值离差回归'
    }
    active_dims_text = '、'.join([dim_names.get(d, d) for d in dimensions])

    # 动态生成强制小标题大纲
    bullet_lines = []
    for d in dimensions:
        name = dim_names.get(d, d)
        bullet_lines.append(f"   - ### 【{name}分析】")
    dimensions_bullet_list = "\n".join(bullet_lines)

    report_parts = [
        "1. **宏观盘面与走势图景**：结合最近走势 and 已选维度的开奖信号概述，阐述威力彩 Zone 1 与 Zone 2 的总体盘面特征。",
        f"2. **加权维度逐项剖析**：【⚠️重要纪律要求：必须依次输出下方这 {len(dimensions)} 个三级小标题，且在每个标题下写出独立的分段分析，严禁合并，每个小标题下字数均不得少于100字】：\n{dimensions_bullet_list}",
    ]
    if weights_info:
        report_parts.append("3. **算法底层加权解码**：结合上述各个维度的剖析，带入底层设定的各个权重系数，解释系统是如何利用权重抑制次要矛盾、放大主要趋势的。")
        
    if is_wheeling:
        report_parts.append(f"4. **旋转矩阵包牌共振与最后定胆**：【⚠️重要纪律要求：必须在此总结章节，对上述全部勾选维度进行融合归纳，严密扣合最终敲定的第一區精选码池 {pre_sel_nums} 和第二區特别号 {pre_sel_special}，论证其数学期望与图形均值回归的必然性】。阐述为什么本期底层数学模型筛选出的【{len(pre_sel_nums)}码精选码池】{pre_sel_nums} 在组合概率上具有巨大优势，并合理推演选择第二區特别号 {pre_sel_special} 的合理性；同时说明使用旋转矩阵（中5保4）进行包牌对冲，是如何将资金利用率和中奖概率期望最大化的。")
    else:
        report_parts.append(f"4. **双区多维共振与最后定胆**：【⚠️重要纪律要求：必须在此总结章节，对上述全部勾选维度进行融合归纳，严密扣合最终敲定的第一區号码组合 {pre_sel_nums} 和第二區特别号 {pre_sel_special}，论证其数学期望与图形均值回归的必然性】。论证在多重算法约束和指标下产生的合力，是如何完美指向第二區特别号码 {pre_sel_special} 与第一區号码组合 {pre_sel_nums} 这个推算解的。通过大量的概率均值回归、连庄断龙、极限遗漏反弹进行论证。")
        
    report_structure = "\n\n".join(report_parts)

    active_algos = []
    if 'big_small' in dimensions or 'odd_even' in dimensions: active_algos.append('大小单双防连跳')
    if 'markov' in dimensions: active_algos.append('马尔可夫转移')
    if 'bayesian' in dimensions: active_algos.append('贝叶斯反弹')
    if 'lstm' in dimensions: active_algos.append('MLP神经网络')
    if 'hot_cold' in dimensions: active_algos.append('冷热遗漏')
    if 'tail' in dimensions: active_algos.append('尾数分布')
    algo_desc = '、'.join(active_algos) if active_algos else '统计算法'

    if is_wheeling:
        prompt_nums_str = f"👉 **本期底层算法最终敲定的【第一區旋转矩阵 {len(pre_sel_nums)}码精选码池】：{pre_sel_nums}**"
        target_lock_str = f"1. 目标锁定：你最后的分析结论【必须、无可争议地】指向第一區这 {len(pre_sel_nums)} 个精选码池号码 {pre_sel_nums} 和第二區特别号 {pre_sel_special}。所有的概率推理、数学模型均须收敛并服务于此，论证其作为旋转矩阵输入的概率优势与保底中奖的合理性。任何与这组预测号码背道而驰的推理均为严重错误！"
    else:
        prompt_nums_str = f"👉 **本期底层算法最终敲定的【第一區号码组合】：{pre_sel_nums}**"
        target_lock_str = f"1. 目标锁定：你最后的分析结论【必须、无可争议地】指向第一區号码组合 {pre_sel_nums} 和 second 區特别号 {pre_sel_special}。所有的概率推理、数学模型推算均须收敛于此，最终一定要归纳并论证该组号码的合理性与概率优势。任何与这组预测号码背道而驰的推理均为严重错误！"

    prompt = f"""你是一位资深的彩票走势分析专家与系统推理报告撰写者。

【系统高度机密指令】：底层的工业级统计算法（含{algo_desc}等）已经高度结合了图表规则，**精准计算并选定了本期的号码**。
你的唯一任务是：作为系统的“首席分析师”，根据下方的【历史走势数据】与【底层权重系数】，写一篇严丝合缝、极具逻辑说服力的长篇图表规则报告，向用户解释**底层数学模型基于图表为什么推算出了这组号码**，从而彻底消除你的逻辑幻觉，完美匹配图表。

【注意】：台湾威力彩(威力彩)由两个区组成，开奖规则与六合彩截然不同：
第一區 (Zone 1): 从 1-38 中随机摇出 6 个号码 (正码)
第二區 (Zone 2): 从 1-8 中随机摇出 1 个号码 (特别号)
请绝对不要提及任何生相动物（如鼠、牛等）、球色波段（如红、蓝、绿等颜色波段）、五行属性等其他彩票玩法的特有术语！

{prompt_nums_str}
👉 **本期底层算法最终敲定的【第二區特别号】：{pre_sel_special}**

⚠️ 绝不妥协的纪律要求：
{target_lock_str}
2. 🚫 严格维度隔离：用户本次只勾选了【{active_dims_text}】这些维度。你的分析报告中**只允许引用和讨论这些维度的数据**。绝对禁止提及、引用或编造任何未勾选维度的数据或概念。
3. 🚫 绝对禁止合并标题段落：你撰写的分析报告在《加权维度逐项剖析》章节中，必须严格、完整、一字不差地依次使用这 {len(dimensions)} 个 Markdown 三级小标题，不得将多项合为一个标题发表评论，也不得遗漏任何一个标题。每个小标题下独立成段且字数不少于100字！这是系统判定合格的硬性标准，否则报告将被拒收！
4. ✨ 深度关注图像反转与图表多模态综合：你必须假装你正盯着几张实时更新的【数据走势图表】。请用“从大小单双折线图、和值连涨防跌曲线、冷热遗漏分布图来看”等典型的图表视觉描述手法，把【大小】、【单双】、【尾数】和【正码和值动量】这几个图表维度的特征联合研判！提取它们在“图表轨迹”上的共振图形缩影（如双向探顶、和值极限回踩等），向用户论证均值回归规律必然爆发的原因。
5. 杜绝对数据的数值幻觉：你在分析中引用的任何数据百分比，**必须**从下方的《已选维度统计数据》中提取！如果数据里没提，绝对不要自己编造具体数字。

## 最近 50 期原始 【中奖号码】 序列（从旧到新，供你挖掘第一區和值与第二區特别号的隐藏走势规律）：
{raw_draw_nums_str}

{recent_detail}

## 已选维度统计数据与底层推算中间变量
{data_block}
{weights_info}

## 分析撰写结构要求（参考字数 800 - 1500 字）
请按以下模块化结构撰写这篇极品分析报告（格式自行美化，可使用加粗等）：
{report_structure}

请严格以如下 JSON 格式回复（将你的长篇推算报告置于 analysis 字段，号码原样回传）：
{{
"numbers": {pre_sel_nums},
"special_num": {pre_sel_special},
"analysis": "你的严密推算报告...",
"confidence": "高"
}}"""
    return prompt


