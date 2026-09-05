# core/spider.py
import time
import re
import math
import random
from playwright.sync_api import sync_playwright
from config import logger, LOGIN_COOKIE, HANGQING_HOME, DEBUG
from config.selectors import SELECTORS
from utils.data_tools import clean_change, clean_price, extract_province


def check_login_modal(page) -> bool:
    """检查是否出现登录弹窗"""
    try:
        modal = page.locator(SELECTORS['login_modal'])
        if modal.is_visible(timeout=800):
            modal_text = modal.inner_text(timeout=500)
            if '请登录' in modal_text or '继续浏览' in modal_text:
                return True
        return False
    except:
        return False


def _init_browser(playwright_instance):
    """初始化浏览器和上下文"""
    browser = playwright_instance.chromium.launch(
        headless=not DEBUG,
        args=['--disable-blink-features=AutomationControlled']
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        viewport={'width': 1366, 'height': 768}
    )
    return browser, context


def _add_cookies(context):
    """添加登录Cookie"""
    cookies = []
    for item in LOGIN_COOKIE.split(';'):
        if '=' in item:
            name, value = item.strip().split('=', 1)
            cookies.append({
                'name': name.strip(),
                'value': value.strip(),
                'domain': '.cnhnb.com',
                'path': '/'
            })
    if cookies:
        context.add_cookies(cookies)


def _search_keyword(page, keyword):
    """在页面上搜索关键词"""
    search_input = page.locator(SELECTORS['search_input'])
    search_input.click()
    search_input.fill('')
    time.sleep(random.uniform(0.3, 0.5))

    for char in keyword:
        search_input.type(char, delay=random.randint(100, 200))

    time.sleep(0.5)
    page.keyboard.press('Enter')
    time.sleep(0.5)

    # 点击搜索按钮（如果有的话）
    try:
        page.locator('div.s-r').click()
    except:
        pass

    logger.info(f"已搜索关键词：{keyword}")


def _extract_page_data(page):
    """提取当前页的数据"""
    return page.evaluate('''
        () => {
            const items = document.querySelectorAll('li.market-list-item');
            const list = [];
            items.forEach(li => {
                const texts = li.innerText.split('\\n').filter(t => t.trim());
                if (texts.length >= 4) {
                    list.push({
                        date: texts[0].trim(),
                        name: texts[1].trim(),
                        origin: texts[2].trim(),
                        price: texts[3].trim(),
                        change: texts[4] ? texts[4].trim() : '-'
                    });
                }
            });
            return list;
        }
    ''')


def _get_total_pages(page):
    """获取总页数"""
    try:
        total_text = page.locator(SELECTORS['total_count']).inner_text(timeout=2000)
        total_match = re.search(r'共\s*(\d+)\s*条', total_text)
        total_count = int(total_match.group(1)) if total_match else 0
        total_page = math.ceil(total_count / 15) if total_count else 1
        return total_page, total_count
    except Exception as e:
        logger.warning(f"获取总页数失败：{str(e)[:50]}")
        return 1, 0


def _goto_next_page(page):
    """翻到下一页，成功返回True，失败返回False"""
    next_btn = page.locator(SELECTORS['next_button']).first
    try:
        if next_btn.is_visible(timeout=1000) and not next_btn.is_disabled(timeout=1000):
            next_btn.click()
            time.sleep(random.uniform(2, 4))
            return True
        return False
    except:
        return False


def crawl_category(keyword: str, max_page: int) -> list[dict]:
    """爬取指定品类的行情数据"""
    result = []
    logger.info(f"===== 开始爬取品类：{keyword} =====")

    try:
        with sync_playwright() as p:
            # 初始化浏览器
            browser, context = _init_browser(p)
            _add_cookies(context)

            # 打开首页
            page = context.new_page()
            page.goto(HANGQING_HOME, wait_until='domcontentloaded', timeout=30000)
            time.sleep(random.uniform(1.5, 2.5))

            # 记录搜索前第一条数据
            first_item_before = None
            try:
                first_before = page.locator(SELECTORS['market_item']).first
                if first_before.is_visible(timeout=1000):
                    first_item_before = first_before.inner_text().strip()
            except:
                pass

            # 搜索关键词
            _search_keyword(page, keyword)

            # 等待加载
            page_loaded = False
            for retry in range(3):
                try:
                    # 等待列表项或空状态出现
                    page.wait_for_selector(
                        f"{SELECTORS['market_item']}, {SELECTORS['empty_state']}",
                        timeout=5000
                    )
                    page_loaded = True
                    break
                except:
                    if retry < 2:
                        logger.info(f"页面加载超时，重试 {retry + 1}/3...")
                        time.sleep(2)
                    else:
                        logger.warning(f"{keyword} 页面加载失败")
                        return result

            if not page_loaded:
                return result

            # 额外等待数据稳定
            time.sleep(random.uniform(1, 2))

            # 检测内容是否变化
            first_item_after = None
            try:
                first_after = page.locator(SELECTORS['market_item']).first
                if first_after.is_visible(timeout=1000):
                    first_item_after = first_after.inner_text().strip()
            except:
                pass

            # 前后都有商品，单页面没刷新，搜索失效
            if first_item_before and first_item_after and first_item_before == first_item_after:
                logger.warning(f"搜索后列表内容未变化，可能搜索失败或无结果，放弃该品类")
                return result
            # 无空白提示，但页面完全没有商品li标签，兜底拦截
            elif not first_item_after:
                logger.warning(f"搜索后未检测到列表项，放弃该品类")
                return result

            # 获取总页数
            total_page, total_count = _get_total_pages(page)
            actual_page = min(max_page, total_page)
            logger.info(f"总条数：{total_count} 条，总页数：{total_page} 页，本次爬取前 {actual_page} 页")

            # 逐页爬取
            last_flag = ''
            for page_num in range(1, actual_page + 1):
                logger.info(f"正在爬取第 {page_num} 页...")

                # 提取当前页数据
                page_data = []
                for retry in range(3):
                    try:
                        page.wait_for_selector(SELECTORS['market_item'], timeout=3000)
                        page_data = _extract_page_data(page)
                        if page_data:
                            break
                    except Exception as e:
                        logger.debug(f"第 {retry + 1} 次提取失败：{str(e)[:50]}")

                    logger.info(f"第 {retry + 1} 次提取为空，等待重试...")
                    time.sleep(1.5)

                # 检查登录弹窗
                if not page_data and check_login_modal(page):
                    logger.warning("检测到强制登录弹窗，终止爬取")
                    break

                if not page_data:
                    logger.info("多次重试无数据，已到达最后一页或无结果")
                    break

                # 检测重复内容
                current_flag = page_data[0]['name'] + page_data[0]['origin']
                if current_flag == last_flag:
                    logger.info("检测到重复内容，已到达最后一页")
                    break
                last_flag = current_flag

                # 处理数据
                for row in page_data:
                    cleaned_price = clean_price(row['price'])
                    if cleaned_price is None:
                        continue

                    result.append({
                        '品类': keyword,
                        '产品名称': row['name'],
                        '产地': row['origin'],
                        '省份': extract_province(row['origin']),
                        '原始价格文本': row['price'],
                        '价格(元/斤)': cleaned_price,
                        '涨跌幅(%)': clean_change(row['change']),
                        '发布日期': row['date']
                    })

                logger.info(f"本页提取 {len(page_data)} 条数据")

                # 翻页
                if page_num < actual_page:
                    if not _goto_next_page(page):
                        logger.info("下一页按钮不可用，停止翻页")
                        break

            browser.close()
            logger.info(f"{keyword} 爬取完成，共获取 {len(result)} 条有效数据")
            return result

    except Exception as e:
        logger.error(f"爬取 {keyword} 失败：{str(e)}", exc_info=True)
        return result