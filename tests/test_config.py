"""
配置管理模块单元测试
"""

import pytest
from modules.config_manager import (
    DEFAULT_CONFIG,
    _deep_merge,
    load_global_config,
)


class TestDeepMerge:
    """深度合并测试"""

    def test_deep_merge_simple(self):
        """测试简单合并"""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        """测试嵌套合并"""
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3, "z": 4}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_deep_merge_empty_override(self):
        """测试空覆盖"""
        base = {"a": 1, "b": 2}
        result = _deep_merge(base, {})
        assert result == base

    def test_deep_merge_empty_base(self):
        """测试空基础"""
        override = {"a": 1}
        result = _deep_merge({}, override)
        assert result == override

    def test_deep_merge_override_replaces_non_dict(self):
        """测试非字典值被替换"""
        base = {"a": [1, 2, 3]}
        override = {"a": [4, 5]}
        result = _deep_merge(base, override)
        assert result == {"a": [4, 5]}


class TestDefaultConfig:
    """默认配置测试"""

    def test_default_config_has_ai(self):
        """测试包含 AI 配置"""
        assert "ai" in DEFAULT_CONFIG
        assert "platform" in DEFAULT_CONFIG["ai"]
        assert "model" in DEFAULT_CONFIG["ai"]

    def test_default_config_has_chart_periods(self):
        """测试包含图表期数配置"""
        assert "chart_periods" in DEFAULT_CONFIG
        assert "zodiac_trend" in DEFAULT_CONFIG["chart_periods"]

    def test_default_config_has_system(self):
        """测试包含系统配置"""
        assert "system" in DEFAULT_CONFIG
        assert "signup_bonus_points" in DEFAULT_CONFIG["system"]


class TestLoadGlobalConfig:
    """全局配置加载测试"""

    def test_load_global_config_returns_dict(self):
        """测试返回字典"""
        config = load_global_config()
        assert isinstance(config, dict)

    def test_load_global_config_has_required_keys(self):
        """测试包含必要键"""
        config = load_global_config()
        assert "ai" in config
        assert "chart_periods" in config
        assert "system" in config
