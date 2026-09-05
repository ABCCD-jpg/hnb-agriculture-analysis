# tests/test_analysis_business.py
import pandas as pd
from core.analysis import data_preprocessing, run_full_statistics


def test_outlier_filtering_works():
    """
    测试异常值过滤是否有效
    30条正常数据（不同产地）+ 1条异常数据（100元）
    """
    # 用不同产地，避免被去重
    origins = [f'山东烟台{i}号基地' for i in range(1, 32)]

    df = pd.DataFrame({
        '品类': ['苹果'] * 31,
        '产品名称': [f'红富士{i}' for i in range(1, 32)],  # 不同产品编号
        '产地': origins,
        '省份': ['山东'] * 31,
        '价格(元/斤)': [3.0, 3.1, 3.2] * 10 + [100.0],
        '涨跌幅(%)': [0.0] * 31,
        '发布日期': ['2026-08-10'] * 31
    })

    df_clean = data_preprocessing(df)

    # 100元应该被过滤
    assert 100.0 not in df_clean['价格(元/斤)'].values
    # 剩余30条正常数据
    assert len(df_clean) == 30
    assert len(df_clean) == 30
    assert 3.0 <= df_clean['价格(元/斤)'].mean() <= 3.2


def test_statistics_values_correct():
    """测试统计值是否计算正确"""
    df = pd.DataFrame({
        '品类': ['苹果'] * 2 + ['香蕉'] * 2,
        '产品名称': ['红富士', '嘎啦', '香蕉', '帝王蕉'],
        '产地': ['山东', '陕西', '海南', '广西'],
        '省份': ['山东', '陕西', '海南', '广西'],
        '价格(元/斤)': [3.0, 4.0, 2.0, 3.0],
        '涨跌幅(%)': [0.0] * 4,
        '发布日期': ['2026-08-10'] * 4
    })

    df_clean = data_preprocessing(df)
    stats = run_full_statistics(df_clean, category_order=['苹果', '香蕉'])

    cate_stats = stats['品类核心统计']
    assert abs(cate_stats.loc['苹果', '均价'] - 3.5) < 0.01
    assert abs(cate_stats.loc['香蕉', '均价'] - 2.5) < 0.01
    assert cate_stats.loc['苹果', '样本数'] == 2
    assert cate_stats.loc['香蕉', '样本数'] == 2


def test_none_change_handling():
    """测试涨跌幅为None时的处理"""
    df = pd.DataFrame({
        '品类': ['苹果'],
        '产品名称': ['红富士'],
        '产地': ['山东'],
        '省份': ['山东'],
        '价格(元/斤)': [3.5],
        '涨跌幅(%)': [None],
        '发布日期': ['2026-08-10']
    })

    df_clean = data_preprocessing(df)
    assert df_clean['涨跌幅(%)'].iloc[0] == 0.0