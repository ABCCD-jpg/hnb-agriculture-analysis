# core/visualizer.py
import matplotlib.pyplot as plt
import seaborn as sns
import jieba
import os
import pandas as pd
from config import logger, WORDCLOUD_AVAILABLE

import matplotlib.pyplot as plt

# 设置中文字体，解决方框乱码
plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示方块

def generate_wordcloud(df: pd.DataFrame, output_dir: str):
    if not WORDCLOUD_AVAILABLE:
        logger.warning("wordcloud库未安装，跳过词云生成")
        return
    try:
        text = ' '.join(df['产品名称'].dropna().astype(str))
        if not text.strip():
            logger.warning("无有效产品名称，无法生成词云")
            return
        words = jieba.cut(text, cut_all=False)
        font_paths = ['simhei.ttf', 'C:/Windows/Fonts/msyh.ttc', '/System/Library/Fonts/PingFang.ttc']
        font_used = None
        for fp in font_paths:
            if os.path.exists(fp):
                font_used = fp
                break
        from wordcloud import WordCloud
        try:
            wordcloud = WordCloud(
                font_path=font_used,
                background_color='white',
                width=800,
                height=600,
                max_words=100,
                colormap='viridis'
            ).generate(' '.join(words))
        except:
            logger.warning("未找到合适中文字体，使用默认字体，中文可能显示为方框")
            wordcloud = WordCloud(
                font_paths=r"C:\Windows\Fonts\simhei.ttf" if os.name == 'nt' else "/System/Library/Fonts/PingFang.ttc",
                background_color='white',
                width=800,
                height=600,
                max_words=100,
                colormap='viridis'
            ).generate(' '.join(words))
        save_path = f'{output_dir}/产品名称词云.png'
        wordcloud.to_file(save_path)
        logger.info(f"词云图已保存：{save_path}")
    except Exception as e:
        logger.error(f"词云生成失败：{str(e)}", exc_info=True)

def plot_product_avg_comparison(df: pd.DataFrame, output_dir: str):
    try:
        prod_avg = df.groupby('产品名称')['价格(元/斤)'].mean().sort_values(ascending=False).head(20)
        if prod_avg.empty:
            logger.warning("无产品名称数据，跳过图5")
            return
        plt.figure(figsize=(12, 8))
        prod_avg.sort_values(ascending=True).plot(kind='barh', color='steelblue')
        plt.title('Top20 产品名称均价对比', fontsize=16, fontweight='bold')
        plt.xlabel('平均价格 (元/斤)', fontsize=12)
        plt.ylabel('产品名称', fontsize=12)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/产品名称均价对比.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("图5：产品名称均价对比 已保存")
    except Exception as e:
        logger.error(f"生成产品名称均价对比图失败：{str(e)}")

def plot_product_price_distribution(df: pd.DataFrame, output_dir: str):
    try:
        prod_counts = df.groupby(['品类', '产品名称']).size().reset_index(name='count')
        valid_prods = prod_counts[prod_counts['count'] >= 3]
        if valid_prods.empty:
            logger.warning("无足够样本的产品名称，跳过图6")
            return
        df_filtered = df.merge(valid_prods[['品类', '产品名称']], on=['品类', '产品名称'], how='inner')
        g = sns.catplot(
            x='产品名称', y='价格(元/斤)',
            col='品类', data=df_filtered,
            kind='box', sharex=False, col_wrap=2,
            height=4, aspect=1.5
        )
        g.fig.subplots_adjust(top=0.9)
        g.fig.suptitle('各品类下产品名称价格分布', fontsize=16, fontweight='bold')
        for ax in g.axes.flat:
            ax.set_xlabel('产品名称', fontsize=10)
            ax.set_ylabel('价格(元/斤)', fontsize=10)
            ax.tick_params(axis='x', rotation=45, labelsize=8)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/品类产品价格分布.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("图6：各品类下产品名称价格分布 已保存")
    except Exception as e:
        logger.error(f"生成品类产品价格分布图失败：{str(e)}")

def generate_visualizations(df: pd.DataFrame):
    logger.info("===== 开始生成可视化图表 =====")
    output_dir = 'assets/output'
    # 绘图代码完全复制原逻辑，省略重复内容，直接调用上面子函数
    # 图1 品类均价柱状图
    plt.figure(figsize=(12, 6))
    cate_avg = df.groupby('品类')['价格(元/斤)'].mean().sort_values(ascending=False)
    bars = sns.barplot(x=cate_avg.index, y=cate_avg.values, palette='Blues_d')
    plt.title('各品类农产品均价对比', fontsize=16, fontweight='bold')
    plt.xlabel('农产品品类', fontsize=12)
    plt.ylabel('平均价格 (元/斤)', fontsize=12)
    for i, v in enumerate(cate_avg.values):
        bars.text(i, v + max(cate_avg.values)*0.01, f'{v:.2f}',
                  ha='center', va='bottom', fontsize=11, fontweight='bold', color='darkred')
    plt.ylim(0, max(cate_avg.values)*1.15)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/各品类均价对比.png', dpi=300, bbox_inches='tight')
    plt.close()
    # 图2 价格区间饼图
    plt.figure(figsize=(8, 8))
    interval_count = df['价格区间'].value_counts()
    colors = ['#2E86AB', '#A23B72', '#F18F01']
    wedges, texts, autotexts = plt.pie(
        interval_count.values,
        labels=interval_count.index,
        autopct='%1.1f%%',
        colors=colors[:len(interval_count)],
        startangle=90,
        textprops={'fontsize': 12},
        pctdistance=0.75
    )
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(12)
    plt.title('农产品价格区间整体分布', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/价格区间分布.png', dpi=300, bbox_inches='tight')
    plt.close()
    # 图3 箱线图
    plt.figure(figsize=(14, 7))
    ax = sns.boxplot(x='品类', y='价格(元/斤)', data=df, palette='Set2')
    plt.title('各品类农产品价格波动分布', fontsize=16, fontweight='bold')
    plt.xlabel('农产品品类', fontsize=12)
    plt.ylabel('价格 (元/斤)', fontsize=12)
    cate_order = [tick.get_text() for tick in ax.get_xticklabels()]
    for i, cate in enumerate(cate_order):
        cate_data = df[df['品类'] == cate]['价格(元/斤)']
        mean_val = cate_data.mean()
        ax.text(i, mean_val, f'均值:{mean_val:.2f}',
                ha='center', va='bottom', fontsize=10, color='darkred', fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/品类价格波动箱线图.png', dpi=300, bbox_inches='tight')
    plt.close()
    # 子图调用
    generate_wordcloud(df, output_dir)
    plot_product_avg_comparison(df, output_dir)
    plot_product_price_distribution(df, output_dir)
    logger.info("所有可视化图表生成完成")