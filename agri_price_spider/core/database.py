# core/database.py
import pandas as pd
import pymongo
from config import logger
from config.settings import MONGO_URI
MONGO_DB = "hnb_agriculture"
MONGO_COLL = "price_data"

# 仅内部使用的私有方法，外部不用管，不会改动你任何接口
def _get_default_collection():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    return db[MONGO_COLL]

# 批量插入Mongo【函数名、入参完全和你原来一模一样】
def insert_mongo_data(data_list, coll=None):
    """
    data_list: 爬虫抓取得到的字典列表
    coll: 可选参数（形参），自动适配正常爬虫和测试的集合（表）
    """
    if not data_list:
        logger.warning("待入库数据为空，跳过Mongo写入")
        return
    target_coll = coll if coll is not None else _get_default_collection()
    target_coll.insert_many(data_list)
    logger.info(f"✅ {len(data_list)} 条数据成功写入MongoDB")

#从MongoDB读取所有数据【函数名、入参完全不变】
def data_preprocessing_from_mongo(coll=None):
    # 从MongoDB读取所有数据，变成Pandas DataFrame
    target_coll = coll if coll is not None else _get_default_collection()
    cursor = target_coll.find({}, {'_id': 0}) # 不要MongoDB自带的_id字段
    df = pd.DataFrame(list(cursor))
    logger.info(f"从MongoDB读取到 {len(df)} 条原始数据")
    return df
