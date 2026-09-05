# config/selectors.py
# 惠农网行情页面的CSS选择器配置
# 如果网站改版，只需要修改这个文件

SELECTORS = {
    # 搜索框
    'search_input': 'input.search-ctn',
    # 搜索结果列表项
    'market_item': 'li.market-list-item',
    # 下一页按钮
    'next_button': 'button.btn-next',
    # 总页数显示
    'total_count': 'span.eye-pagination__total',
    # 登录弹窗
    'login_modal': '.el-dialog__wrapper',
    # 空状态提示
    'empty_state': '.empty-page, .no-data, .el-empty',
    # 页码跳转输入框
    'page_jump_input': '.eye-pagination__jump input',
    # 页码跳转确认按钮
    'page_jump_confirm': '.eye-pagination__jump .btn-confirm',
}