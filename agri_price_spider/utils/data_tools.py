import re
import pandas as pd
import unicodedata
import openpyxl
from config.settings import PROVINCE_LIST

#清洗价格字段，转为float类型，如果无法转换则返回None
def clean_price(price_text: str) -> float | None:
    """
       清洗价格文本，提取数字部分
       如果遇到价格区间（如"3.5-4.5元/斤"），则取区间的下限作为价格
       如果价格文本为空或无法转换为数字，则返回None
       """
    if pd.isna(price_text) or str(price_text).strip() == '':
        return None
    # 先用正则提取第一个数字（包括小数点）
    # 比如 "3.5-4.5元/斤" 会匹配到 "3.5"
    match = re.search(r'\d+(\.\d+)?', str(price_text))
    if match:
        return float(match.group())

    return None

#从预定义列表PROVINCE_LIST提取省份信息，如果未匹配到，则返回'未知'
def extract_province(origin_text: str) -> str:
    if pd.isna(origin_text) or str(origin_text).strip() == '':
        return '未知'
    for prov in PROVINCE_LIST:
        if prov in str(origin_text):
            return prov
    return '未知'

#清洗涨跌幅
def clean_change(change_text: str) -> float | None:
    # 清洗涨跌幅字段，转为float类型，如果无法转换则返回None
    if pd.isna(change_text) or str(change_text).strip() in ['-', '', '持平']:
        return None

    change_str = re.sub(r'[^\d.-]', '', str(change_text))
    try:
        return float(change_str)
    except (ValueError, TypeError):
        return None

#计算表格列宽，纯计算不能调整
def display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in ('F', 'W') else 1 for c in str(text or ''))

#自动调整表格列宽
def auto_fit_columns(ws, min_w=8, max_w=50, padding=3):
    for col_cells in ws.columns:
        letter = None
        for cell in col_cells:
            if not isinstance(cell, openpyxl.cell.cell.MergedCell):
                letter = cell.column_letter
                break
        if not letter:
            continue
        w = max((display_width(c.value) for c in col_cells
                 if not isinstance(c, openpyxl.cell.cell.MergedCell) and c.value is not None), default=0)
        ws.column_dimensions[letter].width = max(min_w, min(w * 1.1 + padding, max_w))