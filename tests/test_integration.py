# tests/test_integration.py
import pandas as pd
from config import logger
from core.database import insert_mongo_data, data_preprocessing_from_mongo
from core.analysis import data_preprocessing, run_full_statistics

def test_clean_data_save_mongo(mongo_test_collection, mock_raw_data):
    """
    集成测试1：原始数据 → data_preprocessing清洗 → 写入Mongo
    链路：爬虫原始df → 预处理（去重、空值、异常值过滤） → 入库
    """
    df_raw = mock_raw_data.copy()
    logger.info(f"原始数据行数：{len(df_raw)}")

    # 【调用你项目正式的清洗函数】
    df_clean = data_preprocessing(df_raw)

    # 断言1：原始4条，包含1条重复，清洗后应该只剩3条
    assert len(df_clean) == 3, f"预期清洗后3条，实际得到{len(df_clean)}条"

    # 断言2：价格区间字段成功生成（清洗函数新增的列）
    assert "价格区间" in df_clean.columns

    # 写入测试Mongo集合
    data_records = df_clean.to_dict("records")# 转换为字典列表,df_clean是dataframe
    insert_mongo_data(data_records, coll=mongo_test_collection)
    # 断言3：数据库入库条数正确
    db_count = mongo_test_collection.count_documents({})
    assert db_count == 3, f"数据库预期3条记录，实际{db_count}"

def test_read_mongo_and_statistics(mongo_test_collection):
    """
    集成测试2：Mongo读取数据 → run_full_statistics全维度统计分析
    链路：数据库读取清洗完成的数据 → 执行全套统计函数
    """
    # 从测试库读出数据
    df_load = data_preprocessing_from_mongo(coll=mongo_test_collection)
    assert not df_load.empty, "Mongo读取结果为空！"
    assert len(df_load) == 3

    # 【调用你的统计函数】品类顺序和数据内品类一致
    category_list = ["草莓", "蓝莓"]
    stats_result = run_full_statistics(df_load, category_order=category_list)

    # 断言：所有核心统计key都正常生成，没有报错
    assert "品类核心统计" in stats_result
    assert "价格区间分布" in stats_result
    assert "产地覆盖统计" in stats_result
    assert "省份均价Top5" in stats_result
    assert "整体价格统计" in stats_result

    # 校验草莓均价 (8.0 + 6.5) / 2 =7.25
    cate_df = stats_result["品类核心统计"]
    assert abs(cate_df.loc["草莓", "均价"] - 7.25) < 0.01
    assert cate_df.loc["蓝莓", "均价"] == 16.0