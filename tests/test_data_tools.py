# 解决分包后找不到utils工具函数的问题
import sys
from pathlib import Path
# 把项目根目录加入Python检索路径
sys.path.append(str(Path(__file__).parent.parent))

# 导入真正的清洗函数
from agri_price_spider.utils.data_tools import clean_price, extract_province, clean_change

def test_clean_price():
    # 正常带单位价格
    assert clean_price("3.5元/斤") == 3.5
    # 纯数字文本
    assert clean_price("12") == 12.0
    # 空字符串、空白
    assert clean_price("") is None
    assert clean_price("   ") is None
    # 无报价文字
    assert clean_price("暂无报价") is None
    # 特殊符号混杂
    assert clean_price("￥8.9/公斤") == 8.9
    # 无法转数字乱码
    assert clean_price("无数据") is None

def test_extract_province():
    # 正常匹配省份
    assert extract_province("山东济南白菜") == "山东"
    assert extract_province("广东湛江青菜") == "广东"
    # 文本不含任何省份
    assert extract_province("外地蔬菜") == "未知"
    # 空值、空白文本
    assert extract_province("") == "未知"
    assert extract_province("    ") == "未知"

def test_clean_change():
    # 正常正负涨幅
    assert clean_change("+5.2%") == 5.2
    assert clean_change("-3.8%") == -3.8
    # 持平、横线空数据统一返回0
    assert clean_change("持平") == 0.0
    assert clean_change("-") == 0.0
    assert clean_change("") == 0.0
    # 混杂符号
    assert clean_change("涨跌10.5个点") == 10.5
