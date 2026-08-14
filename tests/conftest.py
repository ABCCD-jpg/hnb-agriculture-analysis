# tests/conftest.py
# =====【必须放在文件第一处！！优先执行路径导入】=====
import sys
from pathlib import Path

# __file__ = tests/conftest.py
# .parent.parent 向上两级，定位 agri_price_spider 项目根目录
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import pytest
import pymongo
import pandas as pd
from config.settings import MONGO_URI

@pytest.fixture(scope="module")
def mongo_test_collection():
    """MongoDB测试集合，隔离正式业务数据"""
    client = pymongo.MongoClient(MONGO_URI)
    db = client["agri_price_test"]  # 独立测试库，不要和业务库重名
    coll = db["price_data"]

    coll.delete_many({})
    yield coll
    coll.delete_many({})
    client.close()

@pytest.fixture(scope="module")
def mock_raw_data():
    """模拟爬虫原始数据，严格匹配你CSV的中文表头"""
    raw_list = [
        {"产品名称": "草莓", "品类":"草莓", "价格(元/斤)": 8.0, "产地": "南京农副产品中心", "省份": "江苏", "发布日期":"2026-08-10", "涨跌幅(%)":0},
        {"产品名称": "蓝莓", "品类":"蓝莓", "价格(元/斤)": 16.0, "产地": "上海农产品市场", "省份": "上海", "发布日期":"2026-08-10", "涨跌幅(%)":0},
        {"产品名称": "草莓", "品类":"草莓", "价格(元/斤)": 6.5, "产地": "无锡农贸市场", "省份": "江苏", "发布日期":"2026-08-10", "涨跌幅(%)":0},
        # 增加一条重复数据，用来测试去重逻辑
        {"产品名称": "草莓", "品类":"草莓", "价格(元/斤)": 6.5, "产地": "无锡农贸市场", "省份": "江苏", "发布日期":"2026-08-10", "涨跌幅(%)":0},
    ]
    df = pd.DataFrame(raw_list)
    return df