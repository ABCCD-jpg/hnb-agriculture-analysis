import re
import pandas as pd
import unicodedata
import openpyxl
from agri_price_spider.config import PROVINCE_LIST

#清洗价格字段，转为float类型，如果无法转换则返回None
def clean_price(price_text: str) -> float | None:
    if pd.isna(price_text) or str(price_text).strip() == '':
        return None
    num_str = re.sub(r'[^\d.]', '', str(price_text))
    try:
        return float(num_str)
    except (ValueError, TypeError):
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
    if pd.isna(change_text) or str(change_text).strip() in ['-', '', '持平']:
        return 0.0
    change_str = re.sub(r'[^\d.-]', '', str(change_text))
    try:
        return float(change_str)
    except (ValueError, TypeError):
        return 0.0

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