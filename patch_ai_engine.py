import re

with open('modules/ai_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Chunk 1
c1_target = """    if dimensions is None:
        dimensions = ['big_small', 'odd_even', 'hot_cold', 'tail', 'zodiac']
    
    try:
        ai_cfg = _get_ai_config()"""

c1_replace = """    if dimensions is None:
        dimensions = ['big_small', 'odd_even', 'hot_cold', 'tail', 'zodiac']
    
    try:
        # ====== 新增：预先通过数学引擎算出结果与内部权重，让 AI 强制对齐 ======
        from modules.simulator import simulate_single, _calculate_trend_weights
        system_weights = _calculate_trend_weights(lottery_type, dimensions)
        system_choice = simulate_single(lottery_type, dimensions)
        pre_sel_nums = system_choice['numbers']
        pre_sel_special = system_choice['special_num']
        
        ai_cfg = _get_ai_config()"""

content = content.replace(c1_target, c1_replace)

# Chunk 2
c2_target = """        # 构建结构化 Prompt（仅包含勾选的维度）
        prompt = _build_analysis_prompt(stats_summary, lottery_type, dimensions)

        if platform == 'google':"""

c2_replace = """        # 构建结构化 Prompt（带入系统权重和预选号码强制向AI注入纪律）
        prompt = _build_analysis_prompt(stats_summary, lottery_type, dimensions, pre_sel_nums, pre_sel_special, system_weights)

        if platform == 'google':"""

content = content.replace(c2_target, c2_replace)

# Chunk 3
c3_target = """        # 校验号码范围
        numbers = [int(n) for n in result.get('numbers', [])]
        special = int(result.get('special_num', 1))
        numbers = [max(1, min(49, n)) for n in numbers][:6]
        special = max(1, min(49, special))
        
        # 确保正码不重复
        seen = set()
        unique_numbers = []
        for n in numbers:
            if n not in seen:
                seen.add(n)
                unique_numbers.append(n)
        while len(unique_numbers) < 6:
            for i in range(1, 50):
                if i not in seen:
                    unique_numbers.append(i)
                    seen.add(i)
                    break
        
        return {
            'success': True,
            'numbers': sorted(unique_numbers[:6]),
            'special_num': special,
            'analysis': result.get('analysis', 'AI 分析完成'),"""

c3_replace = """        # ====== 新增：无视AI瞎猜，强制返回系统底层的推算号码 ======
        # AI 只负责撰写 analysis，保障号码与权重推理100%匹配
        numbers = sorted(pre_sel_nums)
        special = pre_sel_special
        
        return {
            'success': True,
            'numbers': numbers,
            'special_num': special,
            'analysis': result.get('analysis', 'AI 分析完成'),"""

content = content.replace(c3_target, c3_replace)

# Chunk 4
c4_target = """def _build_analysis_prompt(stats: dict, lottery_type: str, dimensions: list) -> str:
    \"\"\"
    构建发送给 Gemini 的分析 Prompt。
    只包含用户勾选的维度数据，避免 AI 分析未选维度。
    新增最近 10 期特码明细，让 AI 能精确判断连续走势。
    \"\"\""""

c4_replace = """def _build_analysis_prompt(stats: dict, lottery_type: str, dimensions: list, pre_sel_nums: list = None, pre_sel_special: int = None, system_weights: dict = None) -> str:
    \"\"\"
    构建发送给 Gemini 的分析 Prompt。
    新增强制逻辑：系统已通过数学引擎计算出精确权重和选中号码，
    AI的任务是基于图表出具事后合规的推理报告。
    \"\"\""""

content = content.replace(c4_target, c4_replace)

with open('modules/ai_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied.")
