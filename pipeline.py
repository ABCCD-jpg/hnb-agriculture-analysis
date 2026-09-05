# pipeline.py
import os
import random
import time
import pandas as pd
from datetime import datetime

from config import logger, SAVE_PATH, OUTPUT_DIR
from core.spider import crawl_category
from core.database import insert_mongo_data
from core.analysis import data_preprocessing, run_full_statistics
from core.visualizer import generate_visualizations
from core.excel_report import generate_excel_report


def run_pipeline(keywords: list, max_page: int) -> dict:
    """
    完整的采集分析流程
    返回结果字典，包含成功状态、报告路径、统计信息等
    """
    result_info = {
        'success': False,
        'report_path': None,
        'total_records': 0,
        'failed_categories': [],
        'error_message': None
    }

    try:
        # 1. 爬取数据
        logger.info("===== 开始数据采集 =====")
        all_data = []
        failed_categories = []

        for i, kw in enumerate(keywords):
            try:
                logger.info(f"爬取品类 [{i + 1}/{len(keywords)}]: {kw}")
                data = crawl_category(kw, max_page)

                if data:
                    all_data.extend(data)
                    logger.info(f"品类 {kw} 成功获取 {len(data)} 条数据")
                else:
                    logger.warning(f"品类 {kw} 未获取到数据")
                    failed_categories.append(kw)

            except Exception as e:
                logger.error(f"品类 {kw} 爬取异常：{str(e)}")
                failed_categories.append(kw)

            # 品类间冷却
            if i < len(keywords) - 1:
                cool_time = random.uniform(15, 30)
                logger.info(f"冷却 {cool_time:.1f}s 后继续...")
                time.sleep(cool_time)

        result_info['failed_categories'] = failed_categories

        if not all_data:
            logger.error("所有品类均未获取到数据")
            result_info['error_message'] = "未获取到任何有效数据"
            return result_info

        # 2. 保存原始数据
        logger.info("===== 保存原始数据 =====")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        df_raw = pd.DataFrame(all_data)
        df_raw.to_csv(SAVE_PATH, index=False, encoding='utf-8-sig')
        logger.info(f"原始CSV已保存：{SAVE_PATH}")

        # 3. 数据清洗
        logger.info("===== 开始数据清洗 =====")
        df_clean = data_preprocessing(df_raw)
        # 确保"品类"列存在（修复groupby.apply的兼容性问题）
        if '品类' not in df_clean.columns:
            df_clean['品类'] = df_raw['品类']
        df_clean['品类'] = pd.Categorical(df_clean['品类'], categories=keywords, ordered=True)
        df_clean = df_clean.sort_values('品类')

        # 4. 入库
        logger.info("===== 写入MongoDB =====")
        insert_mongo_data(all_data)

        # 5. 统计分析
        logger.info("===== 执行统计分析 =====")
        stats = run_full_statistics(df_clean, keywords)

        # 6. 生成可视化
        logger.info("===== 生成可视化图表 =====")
        generate_visualizations(df_clean)

        # 7. 生成Excel报告
        logger.info("===== 生成Excel报告 =====")
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(OUTPUT_DIR, f"农产品价格分析报告_{now_str}.xlsx")
        generate_excel_report(df_clean, stats, report_path)

        result_info.update({
            'success': True,
            'report_path': report_path,
            'total_records': len(df_clean)
        })

        logger.info(f"✅ 全流程完成！共 {len(df_clean)} 条有效数据")
        return result_info

    except Exception as e:
        logger.error(f"流程执行失败：{str(e)}", exc_info=True)
        result_info['error_message'] = str(e)
        return result_info