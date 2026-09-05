# core/analysis.py
import pandas as pd
from config import logger

# ===================== 5. 数据清洗 =====================
def data_preprocessing(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("===== 开始数据清洗与预处理 =====")
    original_count = len(df)

    # 去重
    df = df.drop_duplicates(subset=['产品名称', '产地', '价格(元/斤)', '发布日期'], keep='first')
    logger.info(f"去除重复行：{original_count - len(df)} 条")

    # 删除空值
    df = df.dropna(subset=['价格(元/斤)', '产品名称', '发布日期'])
    df['省份'] = df['省份'].fillna('未知')
    df['涨跌幅(%)'] = df['涨跌幅(%)'].fillna(0.0)

    # ---------- 按品类分别过滤异常值 ----------
    def filter_by_group(group):
        if len(group) < 3:
            return group
        mean = group['价格(元/斤)'].mean()
        std = group['价格(元/斤)'].std()
        lower = mean - 3 * std
        upper = mean + 3 * std
        return group[(group['价格(元/斤)'] >= lower) & (group['价格(元/斤)'] <= upper)]

    df = df.groupby('品类', group_keys=False).apply(lambda g: filter_by_group(g))
    logger.info(f"按品类过滤异常值后剩余 {len(df)} 条")

    # 日期与格式
    df['发布日期'] = pd.to_datetime(df['发布日期'], errors='coerce')
    df['价格(元/斤)'] = df['价格(元/斤)'].astype(float).round(2)
    df['涨跌幅(%)'] = df['涨跌幅(%)'].astype(float).round(2)

    # 价格区间划分
    low = df['价格(元/斤)'].quantile(0.33)
    high = df['价格(元/斤)'].quantile(0.67)
    df['价格区间'] = df['价格(元/斤)'].apply(
        lambda x: '低价区间' if x <= low else ('中价区间' if x <= high else '高价区间')
    )

    logger.info(f"数据清洗完成，最终有效数据：{len(df)} 条")
    return df

# ===================== 6. 统计分析 =====================
def run_full_statistics(df: pd.DataFrame, category_order: list = None) -> dict:
    logger.info("===== 开始全维度统计分析 =====")
    stats = {}
    if category_order is None:
        category_order = df['品类'].unique()

    cate_stats = df.groupby('品类', sort=False)['价格(元/斤)'].agg([
        'count', 'mean', 'median', 'std', 'min', 'max',
        ('极差', lambda x: x.max() - x.min())
    ]).round(2)
    cate_stats.columns = ['样本数', '均价', '中位数', '标准差', '最低价', '最高价', '极差']
    cate_stats['变异系数'] = (cate_stats['标准差'] / cate_stats['均价']).round(3)
    cate_stats = cate_stats.reindex(category_order)
    stats['品类核心统计'] = cate_stats

    price_interval = pd.crosstab(df['品类'], df['价格区间'], normalize='index').round(3) * 100
    price_interval = price_interval.reindex(category_order)
    stats['价格区间分布'] = price_interval

    cover_stats = df.groupby('品类', sort=False)['省份'].agg([
        ('覆盖省份数', 'nunique'), ('产地总数', 'count')
    ])
    cover_stats = cover_stats.reindex(category_order)
    stats['产地覆盖统计'] = cover_stats

    prov_top5 = {}
    for cate in category_order:
        prov_top5[cate] = df[df['品类'] == cate].groupby('省份')['价格(元/斤)'].agg([
            ('均价', 'mean'), ('样本数', 'count')
        ]).round(2).sort_values('均价', ascending=False).head(5)
    stats['省份均价Top5'] = prov_top5

    price_series = df['价格(元/斤)']
    stats['整体价格统计'] = pd.Series({
        '总样本数': price_series.count(),
        '整体均价': price_series.mean(),
        '整体中位数': price_series.median(),
        '整体标准差': price_series.std(),
        '整体最低价': price_series.min(),
        '整体最高价': price_series.max()
    }).round(2)

    logger.info("统计分析完成")
    return stats