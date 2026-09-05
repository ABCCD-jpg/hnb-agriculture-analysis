# tests/test_integration.py
import pytest
from config import logger
from core.database import insert_mongo_data, data_preprocessing_from_mongo
from core.analysis import data_preprocessing, run_full_statistics

pytestmark = pytest.mark.skip(reason="MongoDB相关测试，需要MongoDB环境")

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
    # 先写入测试数据
    test_data = [
        {"品类": "草莓", "产品名称": "草莓", "价格(元/斤)": 8.0, "省份": "江苏", "发布日期": "2026-08-10"},
        {"品类": "草莓", "产品名称": "草莓", "价格(元/斤)": 6.5, "省份": "江苏", "发布日期": "2026-08-10"},
        {"品类": "蓝莓", "产品名称": "蓝莓", "价格(元/斤)": 16.0, "省份": "上海", "发布日期": "2026-08-10"},
    ]
    mongo_test_collection.insert_many(test_data)
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

    # 验证统计值的正确性
    overall = stats_result["整体价格统计"]
    assert overall["总样本数"] == 3
    assert abs(overall["整体均价"] - (8.0 + 6.5 + 16.0) / 3) < 0.01

    # 验证价格区间分布
    price_dist = stats_result["价格区间分布"]
    assert price_dist.shape == (2, 3)  # 2个品类，3个价格区间

    # 验证省份覆盖
    cover = stats_result["产地覆盖统计"]
    assert cover.loc["草莓", "覆盖省份数"] == 1  # 草莓只有江苏
    assert cover.loc["蓝莓", "覆盖省份数"] == 1  # 蓝莓只有上海