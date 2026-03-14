"""
公共常量模块
功能：统一定义生肖映射、波色集合等全局常量，避免各模块重复定义。
"""

# ==================== 生肖映射 ====================

# 2026年（马年）1-49 号码 -> 生肖名称
ZODIAC_NUMS = {
    "马": [1, 13, 25, 37, 49],
    "蛇": [2, 14, 26, 38],
    "龙": [3, 15, 27, 39],
    "兔": [4, 16, 28, 40],
    "虎": [5, 17, 29, 41],
    "牛": [6, 18, 30, 42],
    "鼠": [7, 19, 31, 43],
    "猪": [8, 20, 32, 44],
    "狗": [9, 21, 33, 45],
    "鸡": [10, 22, 34, 46],
    "猴": [11, 23, 35, 47],
    "羊": [12, 24, 36, 48],
}

ZODIAC_ORDER = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

# 号码 -> 生肖 映射字典（预计算，避免每次调用都重建）
NUM_TO_ZODIAC = {}
for _zodiac_name, _nums in ZODIAC_NUMS.items():
    for _n in _nums:
        NUM_TO_ZODIAC[_n] = _zodiac_name

# 号码 -> 生肖索引 映射（用于生肖路单图表 Y 轴）
NUM_TO_ZODIAC_IDX = {}
for _zodiac_name, _nums in ZODIAC_NUMS.items():
    _idx = ZODIAC_ORDER.index(_zodiac_name)
    for _n in _nums:
        NUM_TO_ZODIAC_IDX[_n] = _idx


# ==================== 波色集合 ====================

RED_NUMS = frozenset({1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46})
BLUE_NUMS = frozenset({3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48})
GREEN_NUMS = frozenset({5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49})


def get_zodiac_mapping(lottery_type: str = 'macaujc') -> dict:
    """
    获取 1-49 号码 -> 生肖名称 映射字典。
    返回: {number(int): zodiac(str)}
    """
    return dict(NUM_TO_ZODIAC)


def get_color(num: int) -> str:
    """根据号码返回波色名称（红波/蓝波/绿波）"""
    if num in RED_NUMS:
        return '红波'
    if num in BLUE_NUMS:
        return '蓝波'
    if num in GREEN_NUMS:
        return '绿波'
    return '未知'


def get_color_hex(num: int) -> str:
    """根据号码返回波色的 hex 颜色值（用于图表渲染）"""
    try:
        n = int(num)
        if n in RED_NUMS:
            return '#ef4444'
        if n in BLUE_NUMS:
            return '#3b82f6'
        if n in GREEN_NUMS:
            return '#22c55e'
    except Exception:
        pass
    return '#eab308'  # 默认土黄
