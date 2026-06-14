"""
统计引擎模块单元测试
"""

import pytest
import pandas as pd
from modules.statistics_engine import (
    _get_five_element,
    _chi_square_p_value,
    five_elements_analysis,
    number_frequency,
    hot_cold_numbers,
    odd_even_ratio,
    big_small_ratio,
    tail_number_stats,
    calculate_omission_thresholds,
)


class TestFiveElements:
    """五行分析测试"""

    def test_number_frequency_weilitsai(self):
        import pandas as pd
        # Mock dataframe with weilitsai data
        df = pd.DataFrame({
            'lottery_type': ['weilitsai', 'weilitsai'],
            'num1': [1, 2], 'num2': [2, 3], 'num3': [3, 4], 
            'num4': [4, 5], 'num5': [5, 6], 'num6': [6, 7],
            'special_num': [1, 8]
        })
        
        # Test Zone 1
        freq_z1 = number_frequency(df=df, lottery_type='weilitsai', zone=1)
        assert freq_z1[1] == 1 and freq_z1[7] == 1
        assert freq_z1[8] == 0 # Special number shouldn't be here
        
        # Test Zone 2
        freq_z2 = number_frequency(df=df, lottery_type='weilitsai', zone=2)
        assert freq_z2[1] == 1 and freq_z2[8] == 1
        assert freq_z2[2] == 0

    def test_get_five_element_metal(self):
        """测试金属行"""
        assert _get_five_element(6) == "金"
        assert _get_five_element(7) == "金"
        assert _get_five_element(44) == "金"

    def test_get_five_element_wood(self):
        """测试木行"""
        assert _get_five_element(1) == "木"
        assert _get_five_element(8) == "木"

    def test_get_five_element_water(self):
        """测试水行"""
        assert _get_five_element(4) == "水"
        assert _get_five_element(5) == "水"

    def test_get_five_element_fire(self):
        """测试火行"""
        assert _get_five_element(2) == "火"
        assert _get_five_element(3) == "火"

    def test_get_five_element_earth(self):
        """测试土行"""
        assert _get_five_element(14) == "土"
        assert _get_five_element(15) == "土"

    def test_get_five_element_unknown(self):
        """测试无效数字"""
        assert _get_five_element(0) == "未知"
        assert _get_five_element(50) == "未知"


class TestChiSquare:
    """卡方检验测试"""

    def test_chi_square_p_value_zero_chi2(self):
        """测试零卡方值"""
        p = _chi_square_p_value(0, 4)
        assert p == 1.0

    def test_chi_square_p_value_negative_df(self):
        """测试负自由度"""
        p = _chi_square_p_value(10, -1)
        assert p == 1.0

    def test_chi_square_p_value_large_chi2(self):
        """测试大卡方值"""
        p = _chi_square_p_value(100, 4)
        assert 0 <= p <= 1


class TestNumberFrequency:
    """号码频率测试"""

    def test_frequency_returns_all_numbers(self):
        """测试返回所有号码"""
        freq = number_frequency()
        assert len(freq) == 49
        for i in range(1, 50):
            assert i in freq

    def test_frequency_values_are_integers(self):
        """测试返回值为整数"""
        freq = number_frequency()
        for count in freq.values():
            assert isinstance(count, int)

    def test_number_frequency_weilitsai(self):
        import pandas as pd
        
        # Mock dataframe with weilitsai data
        df = pd.DataFrame({
            'lottery_type': ['weilitsai', 'weilitsai'],
            'num1': [1, 2], 'num2': [2, 3], 'num3': [3, 4], 
            'num4': [4, 5], 'num5': [5, 6], 'num6': [6, 7],
            'special_num': [1, 8]
        })
        
        # Test Zone 1
        freq_z1 = number_frequency(df=df, lottery_type='weilitsai', zone=1)
        assert freq_z1[1] > 0 and freq_z1[7] > 0
        assert freq_z1.get(8, 0) == 0 # Special number shouldn't be here
        
        # Test Zone 2
        freq_z2 = number_frequency(df=df, lottery_type='weilitsai', zone=2)
        assert freq_z2[1] > 0 and freq_z2[8] > 0
        assert freq_z2.get(2, 0) == 0


class TestHotColdNumbers:
    """冷热号统计测试"""

    def test_hot_cold_returns_dict(self):
        """测试返回字典结构"""
        result = hot_cold_numbers()
        assert "hot" in result
        assert "cold" in result

    def test_hot_cold_returns_top_n(self):
        """测试返回指定数量"""
        result = hot_cold_numbers(top_n=5)
        assert len(result["hot"]) == 5
        assert len(result["cold"]) == 5

    def test_hot_cold_entries_have_required_fields(self):
        """测试返回条目包含必要字段"""
        result = hot_cold_numbers(top_n=3)
        for entry in result["hot"]:
            assert "number" in entry
            assert "count" in entry
            assert "omission" in entry


class TestOddEvenRatio:
    """单双比例测试"""

    def test_odd_even_returns_labels(self):
        """测试返回标签"""
        result = odd_even_ratio()
        assert "labels" in result
        assert "values" in result
        assert "total_odd" in result
        assert "total_even" in result

    def test_odd_even_total_matches(self):
        """测试奇偶总数匹配"""
        result = odd_even_ratio()
        assert result["total_odd"] >= 0
        assert result["total_even"] >= 0


class TestBigSmallRatio:
    """大小比例测试"""

    def test_big_small_returns_labels(self):
        """测试返回标签"""
        result = big_small_ratio()
        assert "labels" in result
        assert "values" in result
        assert "total_big" in result
        assert "total_small" in result


class TestTailNumberStats:
    """尾数统计测试"""

    def test_tail_stats_returns_distribution(self):
        """测试返回分布"""
        result = tail_number_stats()
        assert "distribution" in result
        assert "omission" in result

    def test_tail_stats_has_all_tails(self):
        """测试包含所有尾数"""
        result = tail_number_stats()
        for t in range(10):
            assert t in result["distribution"]
            assert t in result["omission"]


class TestOmissionThresholds:
    def test_calculate_omission_thresholds(self):
        df = pd.DataFrame({
            'draw_date': pd.date_range(start='1/1/2023', periods=18),
            'draw_number': range(1, 19),
            'num1': [1] + [2]*8 + [1] + [2]*8,
            'num2': [3]*18, 'num3': [4]*18, 'num4': [5]*18, 'num5': [6]*18, 'num6': [7]*18,
            'special_num': [8]*18
        })
        
        thresholds = calculate_omission_thresholds(df, lottery_type='weilitsai', zone=1)
        
        assert 1 in thresholds
        assert thresholds[1]['max_omission'] == 8
        assert thresholds[1]['current_omission'] == 8
        assert thresholds[1]['is_alert'] is True
        assert thresholds[2]['is_alert'] is False


class TestWeilitsaiRatioStatistics:
    """测试威力彩一区二区的大小奇偶比率统计功能"""
    def test_weilitsai_zone1_odd_even_ratio(self):
        # 真实数据为降序，造测试数据也为降序 (最新的 3 在最前，最老的 1 在最后)
        df = pd.DataFrame({
            'draw_date': ['2026-01-03', '2026-01-02', '2026-01-01'],
            'draw_number': [3, 2, 1],
            'draw_issue': ['003', '002', '001'],
            'num1': [3, 2, 1], 
            'num2': [13, 12, 11], 
            'num3': [23, 22, 21], 
            'num4': [33, 32, 31], 
            'num5': [7, 6, 5], 
            'num6': [17, 16, 15], 
            'special_num': [3, 4, 5]
        })
        # 经 iloc[::-1] 倒序后为: 1 (奇/小), 2 (偶/大), 3 (奇/小)
        result = odd_even_ratio(df, periods=3, lottery_type='weilitsai', zone=1)
        assert result['total_odd'] == 12 # 6 (1期) + 6 (3期)
        assert result['total_even'] == 6 # 6 (2期)
        assert result['values'] == [1, -1, 1]

    def test_weilitsai_zone1_big_small_ratio(self):
        df = pd.DataFrame({
            'draw_date': ['2026-01-02', '2026-01-01'],
            'draw_number': [2, 1],
            'draw_issue': ['002', '001'],
            'num1': [20, 5], # 大, 小
            'num2': [25, 10], 
            'num3': [30, 15], 
            'num4': [35, 19], 
            'num5': [22, 2], 
            'num6': [28, 18], 
            'special_num': [8, 1]
        })
        # 经 iloc[::-1] 倒序后为: 1 (小), 2 (大)
        result = big_small_ratio(df, periods=2, lottery_type='weilitsai', zone=1)
        assert result['total_big'] == 6
        assert result['total_small'] == 6
        assert result['values'] == [-1, 1]

    def test_weilitsai_zone2_big_small_ratio(self):
        df = pd.DataFrame({
            'draw_date': ['2026-01-04', '2026-01-03', '2026-01-02', '2026-01-01'],
            'draw_number': [4, 3, 2, 1],
            'draw_issue': ['004', '003', '002', '001'],
            'num1': [1, 2, 3, 4],
            'num2': [1, 2, 3, 4],
            'num3': [1, 2, 3, 4],
            'num4': [1, 2, 3, 4],
            'num5': [1, 2, 3, 4],
            'num6': [1, 2, 3, 4],
            'special_num': [3, 8, 5, 4] # 小(<=4), 大(>=5), 大(>=5), 小(<=4)
        })
        # 经 iloc[::-1] 倒序后为: 1 (小) -> 2 (大) -> 3 (大) -> 4 (小)
        result = big_small_ratio(df, periods=4, lottery_type='weilitsai', zone=2)
        assert result['total_big'] == 2
        assert result['total_small'] == 2
        assert result['values'] == [-1, 1, 2, -1] # 4(小) -> -1; 5(大) -> 1; 8(大) -> 2; 3(小) -> -1

