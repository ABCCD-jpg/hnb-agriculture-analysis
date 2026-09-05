# tests/test_pipeline.py
from unittest.mock import patch
from pipeline import run_pipeline


def test_pipeline_isolates_crawl_failure():
    """测试：单个品类爬取失败不影响整体"""
    with patch('pipeline.crawl_category') as mock_crawl, patch('pipeline.time.sleep', return_value=None):
        mock_crawl.side_effect = [
            Exception("网络超时"),
            [
                {
                    '品类': '苹果',
                    '产品名称': '红富士',
                    '产地': '山东烟台',
                    '省份': '山东',
                    '原始价格文本': '3.5元/斤',
                    '价格(元/斤)': 3.5,
                    '涨跌幅(%)': 0.0,
                    '发布日期': '2026-08-10'
                },
                {
                    '品类': '苹果',
                    '产品名称': '嘎啦',
                    '产地': '陕西洛川',
                    '省份': '陕西',
                    '原始价格文本': '4.0元/斤',
                    '价格(元/斤)': 4.0,
                    '涨跌幅(%)': 0.0,
                    '发布日期': '2026-08-10'
                }
            ]
        ]

        result = run_pipeline(['草莓', '苹果'], max_page=1)

        assert result['success'] == True
        assert '草莓' in result['failed_categories']
        assert result['total_records'] == 2


def test_pipeline_all_fail():
    """测试：所有品类都失败"""
    with patch('pipeline.crawl_category') as mock_crawl, patch('pipeline.time.sleep', return_value=None):
        mock_crawl.side_effect = Exception("网络超时")

        result = run_pipeline(['草莓', '苹果'], max_page=1)

        assert result['success'] == False
        assert result['error_message'] == "未获取到任何有效数据"